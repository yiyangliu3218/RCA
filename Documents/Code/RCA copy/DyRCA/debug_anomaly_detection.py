#!/usr/bin/env python3
"""
调试异常节点检测过程
"""
import sys
import os
import time
import json
from typing import Dict, List, Any

# Add project paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
KG_RCA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "KG-RCA"))
if KG_RCA_DIR not in sys.path:
    sys.path.insert(0, KG_RCA_DIR)

from kg_rca.builder import build_knowledge_graph
from DyRCA.walks.adapter import _node_id_map


def debug_anomaly_detection():
    """调试异常节点检测过程"""
    print("🔍 调试异常节点检测过程")
    print("=" * 50)
    
    # 1. 构建知识图谱
    print("📊 构建知识图谱...")
    kg = build_knowledge_graph(
        traces_path="KG-RCA/sample_data/traces.json",
        logs_path="KG-RCA/sample_data/logs.jsonl",
        metrics_path="KG-RCA/sample_data/metrics.csv",
        incident_id="debug_anomaly",
        window=None,
        enable_causal=False,
        resample_rule="60S",
    )
    
    # 2. 建立节点映射
    uid_to_int, int_to_uid = _node_id_map(kg.G)
    
    print(f"✅ 图谱构建完成")
    print(f"   - 总节点数: {kg.G.number_of_nodes()}")
    print(f"   - 总边数: {kg.G.number_of_edges()}")
    
    # 3. 分析所有节点类型
    print(f"\n📊 节点类型分析:")
    node_types = {}
    for node_id, data in kg.G.nodes(data=True):
        node_type = data.get('type', 'Unknown')
        node_types[node_type] = node_types.get(node_type, 0) + 1
    
    for node_type, count in node_types.items():
        print(f"   - {node_type}: {count} 个节点")
    
    # 4. 分析异常相关节点
    print(f"\n🚨 异常相关节点分析:")
    
    # 4.1 LogEvent 节点
    log_events = []
    for node_id, data in kg.G.nodes(data=True):
        if data.get('type') == 'LogEvent':
            log_events.append((node_id, data))
    
    print(f"   📝 LogEvent 节点 ({len(log_events)} 个):")
    for i, (node_id, data) in enumerate(log_events[:5]):  # 只显示前5个
        service = data.get('service', 'Unknown')
        level = data.get('level', 'Unknown')
        message = data.get('message', '')[:50] + '...' if len(data.get('message', '')) > 50 else data.get('message', '')
        print(f"     {i+1}. {node_id}")
        print(f"        服务: {service}")
        print(f"        级别: {level}")
        print(f"        消息: {message}")
        print(f"        整数ID: {uid_to_int.get(node_id, 'N/A')}")
    
    # 4.2 MetricEvent 节点
    metric_events = []
    for node_id, data in kg.G.nodes(data=True):
        if data.get('type') == 'MetricEvent':
            metric_events.append((node_id, data))
    
    print(f"\n   📈 MetricEvent 节点 ({len(metric_events)} 个):")
    for i, (node_id, data) in enumerate(metric_events[:5]):  # 只显示前5个
        service = data.get('service', 'Unknown')
        metric_name = data.get('metric', 'Unknown')
        z_score = data.get('z', 0)
        print(f"     {i+1}. {node_id}")
        print(f"        服务: {service}")
        print(f"        指标: {metric_name}")
        print(f"        Z-score: {z_score}")
        print(f"        整数ID: {uid_to_int.get(node_id, 'N/A')}")
    
    # 5. 模拟异常检测过程
    print(f"\n🔍 模拟异常检测过程:")
    
    # 模拟的异常
    test_anomalies = [
        {'service': 'frontend', 'type': 'error', 'severity': 'ERROR'},
        {'service': 'payment', 'type': 'error', 'severity': 'ERROR'},
        {'service': 'checkout', 'type': 'error', 'severity': 'ERROR'},
        {'service': 'nonexistent', 'type': 'error', 'severity': 'ERROR'},  # 不存在的服务
    ]
    
    for anomaly in test_anomalies:
        print(f"\n   🚨 检测异常: {anomaly}")
        
        # 查找对应的节点
        found_nodes = []
        for node_id, data in kg.G.nodes(data=True):
            if (data.get('type') in ('LogEvent', 'MetricEvent') and 
                data.get('service') == anomaly['service']):
                found_nodes.append((node_id, data))
        
        if found_nodes:
            print(f"     ✅ 找到 {len(found_nodes)} 个相关节点:")
            for node_id, data in found_nodes[:3]:  # 只显示前3个
                node_type = data.get('type')
                int_id = uid_to_int.get(node_id, 'N/A')
                print(f"       - {node_id} (类型: {node_type}, 整数ID: {int_id})")
                
                # 显示节点详情
                if node_type == 'LogEvent':
                    level = data.get('level', 'Unknown')
                    print(f"         级别: {level}")
                elif node_type == 'MetricEvent':
                    z_score = data.get('z', 0)
                    print(f"         Z-score: {z_score}")
        else:
            print(f"     ❌ 没有找到相关节点")
    
    # 6. 分析异常检测的挑战
    print(f"\n⚠️  异常检测的挑战:")
    print(f"   1. 服务名称匹配: 需要确保异常中的服务名与图中的服务名一致")
    print(f"   2. 节点类型选择: LogEvent vs MetricEvent")
    print(f"   3. 时间窗口: 异常可能对应多个时间点的节点")
    print(f"   4. 节点选择策略: 如果有多个匹配节点，选择哪一个？")
    
    # 7. 改进的异常检测策略
    print(f"\n💡 改进的异常检测策略:")
    
    def improved_find_anomaly_nodes(anomaly: Dict[str, Any], kg, uid_to_int):
        """改进的异常节点查找"""
        service = anomaly.get('service')
        anomaly_type = anomaly.get('type')
        severity = anomaly.get('severity')
        
        candidates = []
        
        # 1. 按服务名查找
        for node_id, data in kg.G.nodes(data=True):
            if data.get('service') == service:
                # 2. 按类型过滤
                if data.get('type') == 'LogEvent' and anomaly_type == 'error':
                    # 3. 按严重程度过滤
                    if data.get('level') == severity or severity == 'ERROR':
                        candidates.append((node_id, data, 'log_error'))
                
                elif data.get('type') == 'MetricEvent':
                    # 4. 按异常程度过滤（Z-score）
                    z_score = abs(data.get('z', 0))
                    if z_score > 2.0:  # 高异常值
                        candidates.append((node_id, data, 'metric_anomaly'))
        
        # 5. 选择最佳候选
        if candidates:
            # 优先选择异常程度高的
            candidates.sort(key=lambda x: abs(x[1].get('z', 0)), reverse=True)
            best_candidate = candidates[0]
            return uid_to_int.get(best_candidate[0]), best_candidate
        
        return None, None
    
    # 测试改进的策略
    print(f"\n🧪 测试改进的异常检测策略:")
    for anomaly in test_anomalies:
        print(f"\n   🚨 检测异常: {anomaly}")
        node_id, node_data = improved_find_anomaly_nodes(anomaly, kg, uid_to_int)
        
        if node_id is not None:
            print(f"     ✅ 找到最佳节点: {node_data[0]}")
            print(f"        类型: {node_data[1].get('type')}")
            print(f"        整数ID: {node_id}")
            print(f"        异常类型: {node_data[2]}")
        else:
            print(f"     ❌ 没有找到合适的节点")


if __name__ == "__main__":
    debug_anomaly_detection()
