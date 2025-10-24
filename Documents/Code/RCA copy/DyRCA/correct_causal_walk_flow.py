#!/usr/bin/env python3
"""
正确的因果推断 + 随机游走流程
"""
import sys
import os
import time
import json
from typing import Dict, List, Any
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


class CorrectCausalWalkRCA:
    """
    正确的因果推断 + 随机游走流程
    
    流程：
    1. 数据采集 → 2. 异常检测 → 3. 图构建 → 4. 因果推断 → 5. 随机游走 → 6. 根因定位
    """
    
    def __init__(self):
        # 图状态
        self.kg = KnowledgeGraph()
        self.node_mapping = {}
        self.inv_node_mapping = {}
        
        # 因果推断结果
        self.causal_edges = {}  # 存储因果边
        self.causal_strength = {}  # 存储因果强度
        
        # 动态状态
        self.recent_anomalies = deque(maxlen=100)
        self.walk_cache = {}
        
        # 时间窗口
        self.window_size = 300  # 5分钟
        self.last_update = time.time()
    
    def initialize_with_causal_discovery(self):
        """正确的初始化：包含因果推断"""
        print("🔧 初始化系统（包含因果推断）...")
        
        # 1. 构建知识图谱 + 因果推断
        print("   📊 步骤1: 构建知识图谱")
        self.kg = build_knowledge_graph(
            traces_path="KG-RCA/sample_data/traces.json",
            logs_path="KG-RCA/sample_data/logs.jsonl",
            metrics_path="KG-RCA/sample_data/metrics.csv",
            incident_id="causal_walk_rca",
            window=None,
            enable_causal=True,  # ✅ 开启因果推断！
            pc_alpha=0.05,
            resample_rule="60S",
        )
        
        # 2. 建立节点映射
        uid_to_int, int_to_uid = _node_id_map(self.kg.G)
        self.node_mapping = uid_to_int
        self.inv_node_mapping = int_to_uid
        
        # 3. 提取因果推断结果
        print("   🧠 步骤2: 提取因果推断结果")
        self._extract_causal_edges()
        
        print(f"✅ 系统初始化完成")
        print(f"   - 图谱节点: {self.kg.G.number_of_nodes()}")
        print(f"   - 图谱边: {self.kg.G.number_of_edges()}")
        print(f"   - 因果边: {len(self.causal_edges)}")
    
    def _extract_causal_edges(self):
        """提取因果推断的结果"""
        causal_count = 0
        adjacent_count = 0
        
        for u, v, k, data in self.kg.G.edges(keys=True, data=True):
            edge_type = data.get('type')
            if edge_type == 'causes':
                causal_count += 1
                # 存储因果边信息
                self.causal_edges[(u, v)] = {
                    'method': data.get('method', 'PC'),
                    'alpha': data.get('alpha', 0.05),
                    'strength': 1.0  # 可以后续计算因果强度
                }
            elif edge_type == 'adjacent':
                adjacent_count += 1
        
        print(f"     - 因果边 (causes): {causal_count}")
        print(f"     - 相邻边 (adjacent): {adjacent_count}")
    
    def process_new_anomaly_with_causal_walk(self, anomaly: Dict[str, Any]):
        """
        正确的异常处理流程：
        1. 异常检测 → 2. 基于因果图的随机游走 → 3. 根因定位
        """
        print(f"🚨 处理新异常: {anomaly}")
        
        # 1. 找到异常对应的节点
        anomaly_node_id = self._find_anomaly_node_id(anomaly)
        if anomaly_node_id is None:
            print("   ❌ 无法找到异常节点")
            return
        
        # 2. 基于因果图的随机游走
        root_cause_paths = self._causal_guided_walk(anomaly_node_id)
        
        # 3. 更新缓存
        self._update_walk_cache(anomaly, root_cause_paths)
        
        # 4. Agent决策
        self._agent_decision(anomaly, root_cause_paths)
    
    def _find_anomaly_node_id(self, anomaly: Dict[str, Any]) -> int:
        """找到异常对应的整数节点ID"""
        service = anomaly.get('service')
        anomaly_type = anomaly.get('type')
        severity = anomaly.get('severity')
        
        candidates = []
        
        # 按服务名查找所有相关节点
        for node_id, data in self.kg.G.nodes(data=True):
            if data.get('service') == service:
                # 按类型和严重程度过滤
                if data.get('type') == 'LogEvent' and anomaly_type == 'error':
                    if data.get('level') == severity or severity == 'ERROR':
                        candidates.append((node_id, data, 'log_error'))
                
                elif data.get('type') == 'MetricEvent':
                    # 按异常程度过滤（Z-score）
                    z_score = abs(data.get('z', 0))
                    if z_score > 2.0:  # 高异常值
                        candidates.append((node_id, data, 'metric_anomaly'))
        
        # 选择最佳候选（异常程度最高的）
        if candidates:
            candidates.sort(key=lambda x: abs(x[1].get('z', 0)), reverse=True)
            best_candidate = candidates[0]
            print(f"   🎯 选择异常节点: {best_candidate[0]} (类型: {best_candidate[2]}, Z-score: {best_candidate[1].get('z', 0):.2f})")
            return self.node_mapping.get(best_candidate[0])
        
        return None
    
    def _causal_guided_walk(self, start_node_id: int, max_hops: int = 3) -> List[Dict[str, Any]]:
        """
        基于因果图的随机游走
        
        关键改进：
        1. 优先走因果边 (causes)
        2. 考虑因果强度
        3. 时序约束仍然有效
        """
        print(f"🧠 因果引导的随机游走 from node {start_node_id}")
        
        # 导出边数据
        edges = export_edges_for_temporal_walk(self.kg.G)
        
        # 构建邻接表，区分因果边和普通边
        causal_adj = defaultdict(list)  # 因果边
        normal_adj = defaultdict(list)  # 普通边
        
        for rel_id, edge_array in edges.items():
            for edge in edge_array:
                head, relation, tail, timestamp = edge
                head_str = self.inv_node_mapping.get(head)
                tail_str = self.inv_node_mapping.get(tail)
                
                # 检查是否是因果边
                if (head_str, tail_str) in self.causal_edges:
                    causal_adj[head].append((tail, timestamp, relation, 'causal'))
                else:
                    normal_adj[head].append((tail, timestamp, relation, 'normal'))
        
        root_cause_paths = []
        visited = set()
        
        # 优先从因果边开始游走
        queue = deque([(start_node_id, 0, [start_node_id], 0, 'start')])  # (node, hop, path, last_ts, edge_type)
        
        while queue:
            current_node, hop, path, last_ts, edge_type = queue.popleft()
            
            if hop >= max_hops or current_node in visited:
                continue
            
            visited.add(current_node)
            
            # 检查是否可能是根因
            if self._is_root_cause_candidate(current_node):
                path_info = {
                    'path': [self.inv_node_mapping.get(n, f"node_{n}") for n in path],
                    'root_cause': self.inv_node_mapping.get(current_node, f"node_{current_node}"),
                    'hop_distance': hop,
                    'confidence': self._calculate_causal_confidence(path, hop, edge_type),
                    'causal_path': self._is_causal_path(path)
                }
                root_cause_paths.append(path_info)
                print(f"   ✅ 找到根因路径: {' → '.join(path_info['path'])} (因果路径: {path_info['causal_path']})")
            
            # 优先遍历因果边
            for neighbor, timestamp, relation, edge_type in causal_adj.get(current_node, []):
                if timestamp <= last_ts or last_ts == 0:
                    if neighbor not in visited:
                        queue.append((neighbor, hop + 1, path + [neighbor], timestamp, 'causal'))
            
            # 然后遍历普通边
            for neighbor, timestamp, relation, edge_type in normal_adj.get(current_node, []):
                if timestamp <= last_ts or last_ts == 0:
                    if neighbor not in visited:
                        queue.append((neighbor, hop + 1, path + [neighbor], timestamp, 'normal'))
        
        return root_cause_paths
    
    def _is_causal_path(self, path: List[int]) -> bool:
        """判断路径是否包含因果边"""
        for i in range(len(path) - 1):
            head_str = self.inv_node_mapping.get(path[i])
            tail_str = self.inv_node_mapping.get(path[i + 1])
            if (head_str, tail_str) in self.causal_edges:
                return True
        return False
    
    def _calculate_causal_confidence(self, path: List[int], hop_distance: int, edge_type: str) -> float:
        """基于因果关系的置信度计算"""
        if not path:
            return 0.0
        
        # 基础置信度
        length_factor = 1.0 / (hop_distance + 1)
        
        # 因果路径加分
        causal_bonus = 1.0 if self._is_causal_path(path) else 0.5
        
        # 因果边类型加分
        edge_bonus = 1.0 if edge_type == 'causal' else 0.7
        
        return length_factor * causal_bonus * edge_bonus
    
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
    
    def _update_walk_cache(self, anomaly: Dict[str, Any], paths: List[Dict[str, Any]]):
        """更新 Walk 缓存"""
        service = anomaly.get('service')
        
        self.walk_cache[service] = {
            'timestamp': anomaly.get('timestamp', time.time()),
            'paths': paths,
            'confidence': max([p['confidence'] for p in paths]) if paths else 0.0,
            'root_causes': list(set([p['root_cause'] for p in paths])),
            'causal_paths': [p for p in paths if p.get('causal_path', False)]
        }
        
        print(f"   📊 更新缓存: {service} -> {len(paths)} 条路径 ({len([p for p in paths if p.get('causal_path', False)])} 条因果路径)")
    
    def _agent_decision(self, anomaly: Dict[str, Any], paths: List[Dict[str, Any]]):
        """基于因果 Walk 结果的 Agent 决策"""
        print("🤖 Agent 决策（基于因果推断）")
        
        if not paths:
            print("   → 没有找到根因路径，继续监控")
            return
        
        # 1. 优先分析因果路径
        causal_paths = [p for p in paths if p.get('causal_path', False)]
        if causal_paths:
            print(f"   🧠 发现 {len(causal_paths)} 条因果路径，优先分析")
            best_path = max(causal_paths, key=lambda x: x['confidence'])
        else:
            best_path = max(paths, key=lambda x: x['confidence'])
        
        root_cause = best_path['root_cause']
        confidence = best_path['confidence']
        
        print(f"   🎯 最可能的根因: {root_cause} (置信度: {confidence:.3f})")
        print(f"   📋 路径类型: {'因果路径' if best_path.get('causal_path', False) else '时序路径'}")
        
        # 生成调查计划
        self._generate_causal_investigation_plan(root_cause, paths, confidence)
    
    def _generate_causal_investigation_plan(self, root_cause_service: str, paths: List[Dict[str, Any]], confidence: float):
        """生成基于因果关系的调查计划"""
        print(f"   📋 因果调查计划 for {root_cause_service}:")
        
        # 找到涉及该服务的路径
        relevant_paths = [p for p in paths if p['root_cause'] == root_cause_service]
        causal_paths = [p for p in relevant_paths if p.get('causal_path', False)]
        
        print(f"     - 总路径数: {len(relevant_paths)}")
        print(f"     - 因果路径数: {len(causal_paths)}")
        
        for i, path in enumerate(relevant_paths[:3]):  # 只显示前3条
            path_type = "因果路径" if path.get('causal_path', False) else "时序路径"
            print(f"     {i+1}. {path_type}: {' → '.join(path['path'])}")
            print(f"        置信度: {path['confidence']:.3f}")
        
        # 生成具体的调查建议
        if len(causal_paths) > 0:
            print(f"     🔥 发现因果路径！建议重点调查 {root_cause_service}")
        elif confidence > 0.7:
            print(f"     🔥 高置信度！建议立即调查 {root_cause_service}")
        elif confidence > 0.4:
            print(f"     ⚠️  中等置信度，建议优先调查 {root_cause_service}")
        else:
            print(f"     📊 低置信度，建议继续收集证据")


def demonstrate_correct_flow():
    """演示正确的因果推断 + 随机游走流程"""
    print("🚀 演示正确的因果推断 + 随机游走流程")
    print("=" * 70)
    
    # 初始化系统
    rca = CorrectCausalWalkRCA()
    rca.initialize_with_causal_discovery()
    
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
        }
    ]
    
    # 处理每个异常
    for i, anomaly in enumerate(anomalies, 1):
        print(f"\n🔄 === 异常批次 {i} ===")
        rca.process_new_anomaly_with_causal_walk(anomaly)
        time.sleep(1)
    
    print(f"\n✅ 因果推断 + 随机游走完成")
    print(f"📊 最终状态:")
    print(f"   - Walk 缓存: {len(rca.walk_cache)} 个服务")
    print(f"   - 因果边: {len(rca.causal_edges)} 条")


if __name__ == "__main__":
    demonstrate_correct_flow()
