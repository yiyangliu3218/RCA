#!/usr/bin/env python3
"""
真正结合 Walk 的动态 RCA 系统 - 简化版演示

核心思想：
1. Walk 的真正价值：从异常出发，快速找到可能的根因路径
2. 减少计算量：只分析变化的部分，不重建整个图
3. 时序约束：只走时间上合理的路径
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

from kg_rca.builder import build_knowledge_graph
from kg_rca.graph import KnowledgeGraph
from DyRCA.walks.adapter import export_edges_for_temporal_walk, _node_id_map


class TrueWalkRCA:
    """
    真正结合 Walk 的动态 RCA 系统
    
    Walk 的核心价值：
    1. 从新异常出发，快速找到可能的根因路径
    2. 利用时序约束，只走时间上合理的路径
    3. 减少计算量：只分析变化的部分，不重建整个图
    """
    
    def __init__(self):
        # 图状态
        self.kg = KnowledgeGraph()
        self.node_mapping = {}
        self.inv_node_mapping = {}
        
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
            incident_id="true_walk_rca",
            window=None,
            enable_causal=False,
            resample_rule="60S",
        )
        
        # 2. 建立节点映射
        uid_to_int, int_to_uid = _node_id_map(self.kg.G)
        self.node_mapping = uid_to_int
        self.inv_node_mapping = int_to_uid
        
        print(f"✅ 系统初始化完成")
        print(f"   - 图谱节点: {self.kg.G.number_of_nodes()}")
        print(f"   - 图谱边: {self.kg.G.number_of_edges()}")
    
    def process_new_anomaly(self, anomaly: Dict[str, Any]):
        """
        处理新异常：
        1. 使用 Walk 快速找到可能的根因路径
        2. 更新 Walk 缓存
        3. Agent 决策
        """
        print(f"🚨 处理新异常: {anomaly}")
        
        # 1. 找到异常对应的节点
        anomaly_node_id = self._find_anomaly_node_id(anomaly)
        if anomaly_node_id is None:
            print("   ❌ 无法找到异常节点")
            return
        
        # 2. 使用 Walk 找到根因路径
        root_cause_paths = self._walk_to_root_causes(anomaly_node_id)
        
        # 3. 更新 Walk 缓存
        self._update_walk_cache(anomaly, root_cause_paths)
        
        # 4. Agent 决策
        self._agent_decision(anomaly, root_cause_paths)
    
    def _find_anomaly_node_id(self, anomaly: Dict[str, Any]) -> int:
        """找到异常对应的整数节点ID - 改进版"""
        service = anomaly.get('service')
        anomaly_type = anomaly.get('type')
        severity = anomaly.get('severity')
        
        candidates = []
        
        # 1. 按服务名查找所有相关节点
        for node_id, data in self.kg.G.nodes(data=True):
            if data.get('service') == service:
                # 2. 按类型和严重程度过滤
                if data.get('type') == 'LogEvent' and anomaly_type == 'error':
                    if data.get('level') == severity or severity == 'ERROR':
                        candidates.append((node_id, data, 'log_error'))
                
                elif data.get('type') == 'MetricEvent':
                    # 3. 按异常程度过滤（Z-score）
                    z_score = abs(data.get('z', 0))
                    if z_score > 2.0:  # 高异常值
                        candidates.append((node_id, data, 'metric_anomaly'))
        
        # 4. 选择最佳候选（异常程度最高的）
        if candidates:
            # 优先选择异常程度高的
            candidates.sort(key=lambda x: abs(x[1].get('z', 0)), reverse=True)
            best_candidate = candidates[0]
            print(f"   🎯 选择异常节点: {best_candidate[0]} (类型: {best_candidate[2]}, Z-score: {best_candidate[1].get('z', 0):.2f})")
            return self.node_mapping.get(best_candidate[0])
        
        return None
    
    def _walk_to_root_causes(self, start_node_id: int, max_hops: int = 3) -> List[Dict[str, Any]]:
        """
        Walk 的核心价值：
        1. 从异常节点出发，沿着时序约束的路径走
        2. 找到可能的根因节点
        3. 返回完整的传播路径
        
        这里展示 Walk 如何减少计算量：
        - 不需要重新计算整个图
        - 只从异常点出发，沿着路径走
        - 利用时序约束，过滤不合理的路径
        """
        print(f"🔍 Walk 分析 from node {start_node_id}")
        
        # 导出边数据
        edges = export_edges_for_temporal_walk(self.kg.G)
        
        # 构建邻接表
        adj = defaultdict(list)
        for rel_id, edge_array in edges.items():
            for edge in edge_array:
                head, relation, tail, timestamp = edge
                adj[head].append((tail, timestamp, relation))
        
        root_cause_paths = []
        
        # 从异常节点开始 Walk
        visited = set()
        queue = deque([(start_node_id, 0, [start_node_id], 0)])  # (node, hop, path, last_timestamp)
        
        while queue:
            current_node, hop, path, last_ts = queue.popleft()
            
            if hop >= max_hops or current_node in visited:
                continue
            
            visited.add(current_node)
            
            # 检查当前节点是否可能是根因
            if self._is_root_cause_candidate(current_node):
                path_info = {
                    'path': [self.inv_node_mapping.get(n, f"node_{n}") for n in path],
                    'root_cause': self.inv_node_mapping.get(current_node, f"node_{current_node}"),
                    'hop_distance': hop,
                    'confidence': self._calculate_confidence(path, hop)
                }
                root_cause_paths.append(path_info)
                print(f"   ✅ 找到根因路径: {' → '.join(path_info['path'])}")
            
            # 继续 Walk：找邻居节点
            for neighbor, timestamp, relation in adj.get(current_node, []):
                # 时序约束：时间应该非递增（异常传播的时间顺序）
                if timestamp <= last_ts or last_ts == 0:
                    if neighbor not in visited:
                        queue.append((neighbor, hop + 1, path + [neighbor], timestamp))
        
        return root_cause_paths
    
    def _is_root_cause_candidate(self, node_id: int) -> bool:
        """判断节点是否可能是根因"""
        original_node = self.inv_node_mapping.get(node_id)
        if not original_node:
            return False
        
        # 检查节点类型
        node_data = self.kg.G.nodes.get(original_node, {})
        node_type = node_data.get('type')
        
        # 服务节点更可能是根因
        if node_type == 'Service':
            return True
        
        # 有异常的指标事件也可能是根因
        if node_type == 'MetricEvent':
            z_score = node_data.get('z', 0)
            if abs(z_score) > 2.0:  # 高异常值
                return True
        
        return False
    
    def _calculate_confidence(self, path: List[int], hop_distance: int) -> float:
        """计算路径的置信度"""
        if not path:
            return 0.0
        
        # 简单的置信度计算
        length_factor = 1.0 / (hop_distance + 1)  # 路径越短，置信度越高
        
        # 检查路径中的服务节点数量
        service_count = 0
        for node_id in path:
            original_node = self.inv_node_mapping.get(node_id)
            if original_node and self.kg.G.nodes[original_node].get('type') == 'Service':
                service_count += 1
        
        service_factor = service_count / len(path)  # 服务节点比例
        
        return length_factor * service_factor
    
    def _update_walk_cache(self, anomaly: Dict[str, Any], paths: List[Dict[str, Any]]):
        """更新 Walk 缓存"""
        service = anomaly.get('service')
        
        self.walk_cache[service] = {
            'timestamp': anomaly.get('timestamp', time.time()),
            'paths': paths,
            'confidence': max([p['confidence'] for p in paths]) if paths else 0.0,
            'root_causes': list(set([p['root_cause'] for p in paths]))
        }
        
        print(f"   📊 更新缓存: {service} -> {len(paths)} 条路径")
    
    def _agent_decision(self, anomaly: Dict[str, Any], paths: List[Dict[str, Any]]):
        """基于 Walk 结果的 Agent 决策"""
        print("🤖 Agent 决策")
        
        if not paths:
            print("   → 没有找到根因路径，继续监控")
            return
        
        # 1. 分析所有路径，找到最可能的根因
        root_cause_scores = defaultdict(float)
        for path in paths:
            root_cause = path['root_cause']
            root_cause_scores[root_cause] += path['confidence']
        
        # 2. 选择最可能的根因
        best_root_cause = max(root_cause_scores.items(), key=lambda x: x[1])
        root_cause_service, confidence = best_root_cause
        
        print(f"   🎯 最可能的根因: {root_cause_service} (置信度: {confidence:.3f})")
        
        # 3. 生成调查计划
        self._generate_investigation_plan(root_cause_service, paths, confidence)
    
    def _generate_investigation_plan(self, root_cause_service: str, paths: List[Dict[str, Any]], confidence: float):
        """生成调查计划"""
        print(f"   📋 调查计划 for {root_cause_service}:")
        
        # 找到涉及该服务的路径
        relevant_paths = [p for p in paths if p['root_cause'] == root_cause_service]
        
        for i, path in enumerate(relevant_paths[:3]):  # 只显示前3条
            print(f"     {i+1}. 路径: {' → '.join(path['path'])}")
            print(f"        置信度: {path['confidence']:.3f}")
            print(f"        距离: {path['hop_distance']}")
        
        # 生成具体的调查建议
        if confidence > 0.7:
            print(f"     🔥 高置信度！建议立即调查 {root_cause_service}")
        elif confidence > 0.4:
            print(f"     ⚠️  中等置信度，建议优先调查 {root_cause_service}")
        else:
            print(f"     📊 低置信度，建议继续收集证据")


def simulate_true_walk_rca():
    """模拟使用真正 Walk 的动态 RCA"""
    print("🚀 启动真正 Walk 集成的动态 RCA 系统")
    print("=" * 60)
    
    # 初始化系统
    rca = TrueWalkRCA()
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
    
    print(f"\n✅ 真正 Walk 集成 RCA 完成")
    print(f"📊 最终状态:")
    print(f"   - Walk 缓存: {len(rca.walk_cache)} 个服务")
    print(f"   - 节点映射: {len(rca.node_mapping)} 个节点")


if __name__ == "__main__":
    simulate_true_walk_rca()
