#!/usr/bin/env python3
"""
真正结合 LLM-DA 时序随机游走的动态 RCA 系统
"""
import sys
import os
import time
import json
import numpy as np
from typing import Dict, List, Any, Tuple
from collections import defaultdict, deque

# Add project paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
KG_RCA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "KG-RCA"))
if KG_RCA_DIR not in sys.path:
    sys.path.insert(0, KG_RCA_DIR)
LLM_DA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "LLM-DA"))
if LLM_DA_DIR not in sys.path:
    sys.path.insert(0, LLM_DA_DIR)

from kg_rca.builder import build_knowledge_graph
from kg_rca.graph import KnowledgeGraph
from DyRCA.walks.adapter import export_edges_for_temporal_walk, _node_id_map, RELATION_TO_ID, ID_TO_RELATION
from temporal_walk import Temporal_Walk, store_neighbors, store_edges


class LLMDAIntegratedRCA:
    """
    真正结合 LLM-DA 时序随机游走的动态 RCA 系统
    
    核心思想：
    1. 从新异常出发，使用 LLM-DA 的时序随机游走找到可能的根因路径
    2. 利用 Walk 减少计算量：只分析变化的部分，不重建整个图
    3. Agent 基于 Walk 结果智能决策下一步调查
    """
    
    def __init__(self):
        # 图状态
        self.kg = KnowledgeGraph()
        self.node_mapping = {}  # 原始节点ID -> 整数ID映射
        self.inv_node_mapping = {}  # 整数ID -> 原始节点ID映射
        
        # LLM-DA 组件
        self.temporal_walker = None
        self.learned_rules = {}
        
        # 动态状态
        self.recent_anomalies = deque(maxlen=100)
        self.service_states = {}
        self.walk_cache = {}
        
        # 时间窗口
        self.window_size = 300  # 5分钟
        self.last_update = time.time()
    
    def initialize_with_sample_data(self):
        """使用示例数据初始化系统"""
        print("🔧 初始化系统...")
        
        # 1. 构建初始知识图谱
        self.kg = build_knowledge_graph(
            traces_path="KG-RCA/sample_data/traces.json",
            logs_path="KG-RCA/sample_data/logs.jsonl",
            metrics_path="KG-RCA/sample_data/metrics.csv",
            incident_id="llm_da_integrated",
            window=None,
            enable_causal=False,
            resample_rule="60S",
        )
        
        # 2. 建立节点映射
        uid_to_int, int_to_uid = _node_id_map(self.kg.G)
        self.node_mapping = uid_to_int
        self.inv_node_mapping = int_to_uid
        
        # 3. 导出边数据给 LLM-DA
        edges = export_edges_for_temporal_walk(self.kg.G)
        
        # 4. 转换为 LLM-DA 格式
        quads = self._convert_to_llm_da_format(edges)
        
        # 5. 初始化 LLM-DA 时序随机游走
        inv_relation_id = self._create_inv_relation_mapping()
        self.temporal_walker = Temporal_Walk(
            learn_data=quads,
            inv_relation_id=inv_relation_id,
            transition_distr="exp"  # 使用指数分布
        )
        
        # 调试信息
        print(f"   - 关系数量: {len(self.temporal_walker.edges)}")
        for rel_id, edges in self.temporal_walker.edges.items():
            print(f"     关系 {rel_id}: {len(edges)} 条边")
        
        print(f"✅ 系统初始化完成")
        print(f"   - 图谱节点: {self.kg.G.number_of_nodes()}")
        print(f"   - 图谱边: {self.kg.G.number_of_edges()}")
        print(f"   - 时序游走数据: {len(quads)} 条边")
    
    def _convert_to_llm_da_format(self, edges: Dict[int, np.ndarray]) -> np.ndarray:
        """将我们的边数据转换为 LLM-DA 的四元组格式 [head, relation, tail, timestamp]"""
        quads = []
        
        for rel_id, edge_array in edges.items():
            for edge in edge_array:
                head, relation, tail, timestamp = edge
                quads.append([head, relation, tail, timestamp])
        
        return np.array(quads, dtype=np.int64)
    
    def _create_inv_relation_mapping(self) -> Dict[int, int]:
        """创建逆关系映射"""
        inv_mapping = {}
        for rel_name, rel_id in RELATION_TO_ID.items():
            # 简单的逆关系映射（实际应该更复杂）
            inv_mapping[rel_id] = rel_id + 1000  # 逆关系ID = 原ID + 1000
        return inv_mapping
    
    def process_new_anomaly(self, anomaly: Dict[str, Any]):
        """
        处理新异常：
        1. 使用 LLM-DA 时序随机游走找到可能的根因路径
        2. 更新 Walk 缓存
        3. Agent 决策
        """
        print(f"🚨 处理新异常: {anomaly}")
        
        # 1. 找到异常对应的整数节点ID
        anomaly_node_id = self._find_anomaly_node_id(anomaly)
        if anomaly_node_id is None:
            print("   ❌ 无法找到异常节点")
            return
        
        # 2. 使用 LLM-DA 时序随机游走
        root_cause_paths = self._llm_da_temporal_walk(anomaly_node_id)
        
        # 3. 更新 Walk 缓存
        self._update_walk_cache(anomaly, root_cause_paths)
        
        # 4. Agent 决策
        self._agent_decision(anomaly, root_cause_paths)
    
    def _find_anomaly_node_id(self, anomaly: Dict[str, Any]) -> int:
        """找到异常对应的整数节点ID"""
        service = anomaly.get('service')
        anomaly_type = anomaly.get('type')
        
        # 在图中查找对应的节点
        for node_id, data in self.kg.G.nodes(data=True):
            if (data.get('type') in ('LogEvent', 'MetricEvent') and 
                data.get('service') == service):
                return self.node_mapping.get(node_id)
        
        return None
    
    def _llm_da_temporal_walk(self, start_node_id: int, max_length: int = 3) -> List[Dict[str, Any]]:
        """
        使用 LLM-DA 时序随机游走找到根因路径
        
        核心价值：
        1. 从异常节点出发，沿着时序约束的路径走
        2. 找到可能的根因节点
        3. 返回完整的传播路径
        """
        print(f"🔍 LLM-DA 时序游走 from node {start_node_id}")
        
        root_cause_paths = []
        
        # 尝试不同长度的游走
        for L in range(2, max_length + 1):
            print(f"   尝试长度 {L} 的游走...")
            
            # 使用 LLM-DA 的 sample_walk 方法
            try:
                # 选择一个关系开始游走
                for rel_id in RELATION_TO_ID.values():
                    # 检查该关系是否有边
                    if rel_id not in self.temporal_walker.edges or len(self.temporal_walker.edges[rel_id]) == 0:
                        continue
                    
                    walk_successful, walk = self.temporal_walker.sample_walk(
                        L=L,
                        rel_idx=rel_id,
                        use_relax_time=False
                    )
                    
                    if walk_successful and walk:
                        # 检查游走是否从我们的异常节点开始
                        entities = walk.get('entities', [])
                        if entities and entities[0] == start_node_id:
                            path_info = self._analyze_walk_path(walk)
                            if path_info:
                                root_cause_paths.append(path_info)
                                print(f"     ✅ 找到路径: {path_info['path']}")
            
            except Exception as e:
                print(f"     ❌ 游走失败: {e}")
                continue
        
        return root_cause_paths
    
    def _analyze_walk_path(self, walk: Dict[str, Any]) -> Dict[str, Any]:
        """分析游走路径，提取根因信息"""
        if not walk:
            return None
        
        # 提取路径中的节点和关系
        entities = walk.get('entities', [])
        relations = walk.get('relations', [])
        timestamps = walk.get('timestamps', [])
        
        # 转换为原始节点ID
        original_path = []
        for node_id in entities:
            original_node = self.inv_node_mapping.get(node_id)
            if original_node:
                original_path.append(original_node)
        
        # 找到可能的根因节点（路径中的服务节点）
        root_cause_candidates = []
        for node_id in entities:
            original_node = self.inv_node_mapping.get(node_id)
            if original_node and self.kg.G.nodes[original_node].get('type') == 'Service':
                root_cause_candidates.append(original_node)
        
        return {
            'path': original_path,
            'root_cause_candidates': root_cause_candidates,
            'path_length': len(entities),
            'confidence': self._calculate_path_confidence(walk)
        }
    
    def _calculate_path_confidence(self, walk: Dict[str, Any]) -> float:
        """计算路径的置信度"""
        if not walk:
            return 0.0
        
        entities = walk.get('entities', [])
        timestamps = walk.get('timestamps', [])
        
        if not entities or not timestamps:
            return 0.0
        
        # 简单的置信度计算：基于路径长度和时间一致性
        length_factor = 1.0 / len(entities)  # 路径越短，置信度越高
        
        # 检查时间一致性
        time_consistency = 1.0
        for i in range(1, len(timestamps)):
            if timestamps[i] > timestamps[i-1]:  # 时间应该非递增
                time_consistency *= 0.5
        
        return length_factor * time_consistency
    
    def _update_walk_cache(self, anomaly: Dict[str, Any], paths: List[Dict[str, Any]]):
        """更新 Walk 缓存"""
        service = anomaly.get('service')
        
        self.walk_cache[service] = {
            'timestamp': anomaly.get('timestamp', time.time()),
            'paths': paths,
            'confidence': max([p['confidence'] for p in paths]) if paths else 0.0,
            'root_cause_candidates': list(set([
                candidate for path in paths 
                for candidate in path['root_cause_candidates']
            ]))
        }
        
        print(f"   📊 更新缓存: {service} -> {len(paths)} 条路径")
    
    def _agent_decision(self, anomaly: Dict[str, Any], paths: List[Dict[str, Any]]):
        """基于 Walk 结果的 Agent 决策"""
        print("🤖 Agent 决策")
        
        if not paths:
            print("   → 没有找到根因路径，继续监控")
            return
        
        # 1. 分析所有路径，找到最可能的根因
        all_candidates = defaultdict(int)
        for path in paths:
            for candidate in path['root_cause_candidates']:
                all_candidates[candidate] += path['confidence']
        
        if not all_candidates:
            print("   → 没有找到根因候选")
            return
        
        # 2. 选择最可能的根因
        best_candidate = max(all_candidates.items(), key=lambda x: x[1])
        root_cause_service, confidence = best_candidate
        
        print(f"   🎯 最可能的根因: {root_cause_service} (置信度: {confidence:.3f})")
        
        # 3. 生成调查计划
        self._generate_investigation_plan(root_cause_service, paths, confidence)
    
    def _generate_investigation_plan(self, root_cause_service: str, paths: List[Dict[str, Any]], confidence: float):
        """生成调查计划"""
        print(f"   📋 调查计划 for {root_cause_service}:")
        
        # 找到涉及该服务的路径
        relevant_paths = [p for p in paths if root_cause_service in p['root_cause_candidates']]
        
        for i, path in enumerate(relevant_paths[:3]):  # 只显示前3条
            print(f"     {i+1}. 路径: {' → '.join(path['path'])}")
            print(f"        置信度: {path['confidence']:.3f}")
            print(f"        长度: {path['path_length']}")
        
        # 生成具体的调查建议
        if confidence > 0.7:
            print(f"     🔥 高置信度！建议立即调查 {root_cause_service}")
        elif confidence > 0.4:
            print(f"     ⚠️  中等置信度，建议优先调查 {root_cause_service}")
        else:
            print(f"     📊 低置信度，建议继续收集证据")


def simulate_llm_da_integrated_rca():
    """模拟使用 LLM-DA 集成的动态 RCA"""
    print("🚀 启动 LLM-DA 集成的动态 RCA 系统")
    print("=" * 60)
    
    # 初始化系统
    rca = LLMDAIntegratedRCA()
    rca.initialize_with_sample_data()
    
    # 模拟新异常
    anomalies = [
        {
            'service': 'frontend',
            'type': 'error',
            'severity': 'ERROR',
            'timestamp': time.time() - 60,
            'message': 'HTTP 500 error'
        },
        {
            'service': 'payment',
            'type': 'error', 
            'severity': 'ERROR',
            'timestamp': time.time() - 30,
            'message': 'Payment gateway timeout'
        },
        {
            'service': 'checkout',
            'type': 'error',
            'severity': 'ERROR', 
            'timestamp': time.time() - 10,
            'message': 'Checkout process failed'
        }
    ]
    
    # 处理每个异常
    for i, anomaly in enumerate(anomalies, 1):
        print(f"\n🔄 === 异常批次 {i} ===")
        rca.process_new_anomaly(anomaly)
        time.sleep(1)
    
    print(f"\n✅ LLM-DA 集成 RCA 完成")
    print(f"📊 最终状态:")
    print(f"   - Walk 缓存: {len(rca.walk_cache)} 个服务")
    print(f"   - 节点映射: {len(rca.node_mapping)} 个节点")


if __name__ == "__main__":
    simulate_llm_da_integrated_rca()
