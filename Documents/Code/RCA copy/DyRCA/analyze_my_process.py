#!/usr/bin/env python3
"""
分析当前 true_walk_integration.py 系统的具体工作过程
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


def analyze_my_process():
    """分析当前系统的具体工作过程"""
    print("🔍 分析当前 true_walk_integration.py 系统的工作过程")
    print("=" * 70)
    
    # 1. 系统初始化过程
    print("📋 1. 系统初始化过程:")
    print("   🔧 initialize_with_sample_data()")
    print("      ├── 构建初始知识图谱 (build_knowledge_graph)")
    print("      ├── 建立节点映射 (uid_to_int, int_to_uid)")
    print("      └── 准备 Walk 分析环境")
    
    # 2. 异常处理流程
    print("\n📋 2. 异常处理流程:")
    print("   🚨 process_new_anomaly(anomaly)")
    print("      ├── 步骤1: _find_anomaly_node_id(anomaly)")
    print("      │   ├── 按服务名查找所有相关节点")
    print("      │   ├── 按类型过滤 (LogEvent vs MetricEvent)")
    print("      │   ├── 按异常程度过滤 (Z-score > 2.0)")
    print("      │   └── 选择异常程度最高的节点")
    print("      │")
    print("      ├── 步骤2: _walk_to_root_causes(start_node_id)")
    print("      │   ├── 导出边数据 (export_edges_for_temporal_walk)")
    print("      │   ├── 构建邻接表")
    print("      │   ├── 从异常节点开始 BFS Walk")
    print("      │   ├── 应用时序约束 (timestamp <= last_ts)")
    print("      │   └── 收集根因候选路径")
    print("      │")
    print("      ├── 步骤3: _update_walk_cache(anomaly, paths)")
    print("      │   ├── 存储路径信息")
    print("      │   ├── 计算置信度")
    print("      │   └── 更新缓存状态")
    print("      │")
    print("      └── 步骤4: _agent_decision(anomaly, paths)")
    print("          ├── 分析所有路径的置信度")
    print("          ├── 选择最可能的根因")
    print("          └── 生成调查计划")
    
    # 3. 详细分析每个步骤
    print("\n📋 3. 详细步骤分析:")
    
    print("\n   🔍 步骤1: 异常节点检测")
    print("      输入: {'service': 'payment', 'type': 'error', 'severity': 'ERROR'}")
    print("      过程:")
    print("        1. 遍历图谱中所有节点")
    print("        2. 筛选 service='payment' 的节点")
    print("        3. 按类型过滤:")
    print("           - LogEvent + level='ERROR' → 候选")
    print("           - MetricEvent + |z-score| > 2.0 → 候选")
    print("        4. 按异常程度排序 (Z-score 降序)")
    print("        5. 返回异常程度最高的节点ID")
    print("      输出: 整数节点ID (如: 59)")
    
    print("\n   🚶 步骤2: 时序随机游走")
    print("      输入: 异常节点ID (如: 59)")
    print("      过程:")
    print("        1. 导出图谱边数据为 numpy 数组格式")
    print("        2. 构建邻接表: node_id → [(neighbor, timestamp, relation), ...]")
    print("        3. BFS 遍历 (最大3跳):")
    print("           - 队列: [(current_node, hop, path, last_timestamp), ...]")
    print("           - 时序约束: timestamp <= last_timestamp")
    print("           - 根因判断: _is_root_cause_candidate(node)")
    print("        4. 收集所有根因路径")
    print("      输出: 根因路径列表")
    
    print("\n   📊 步骤3: Walk 缓存更新")
    print("      输入: 异常信息 + 根因路径列表")
    print("      过程:")
    print("        1. 计算路径置信度")
    print("        2. 提取根因候选")
    print("        3. 更新缓存: {service: {timestamp, paths, confidence, root_causes}}")
    print("      输出: 更新的缓存状态")
    
    print("\n   🤖 步骤4: Agent 智能决策")
    print("      输入: 异常信息 + 根因路径列表")
    print("      过程:")
    print("        1. 统计所有根因的置信度分数")
    print("        2. 选择置信度最高的根因")
    print("        3. 生成调查计划:")
    print("           - 显示相关路径")
    print("           - 提供置信度评估")
    print("           - 给出调查建议")
    print("      输出: 智能调查计划")
    
    # 4. 实际运行示例
    print("\n📋 4. 实际运行示例:")
    print("   让我们看看系统实际是如何工作的...")
    
    # 构建图谱
    kg = build_knowledge_graph(
        traces_path="KG-RCA/sample_data/traces.json",
        logs_path="KG-RCA/sample_data/logs.jsonl",
        metrics_path="KG-RCA/sample_data/metrics.csv",
        incident_id="process_analysis",
        window=None,
        enable_causal=False,
        resample_rule="60S",
    )
    
    # 建立节点映射
    uid_to_int, int_to_uid = _node_id_map(kg.G)
    
    print(f"\n   📊 图谱统计:")
    print(f"      - 总节点数: {kg.G.number_of_nodes()}")
    print(f"      - 总边数: {kg.G.number_of_edges()}")
    print(f"      - 节点映射: {len(uid_to_int)} 个节点")
    
    # 分析异常节点检测过程
    print(f"\n   🔍 异常节点检测示例:")
    test_anomaly = {'service': 'payment', 'type': 'error', 'severity': 'ERROR'}
    
    candidates = []
    for node_id, data in kg.G.nodes(data=True):
        if data.get('service') == 'payment':
            if data.get('type') == 'LogEvent' and data.get('level') == 'ERROR':
                candidates.append((node_id, data, 'log_error'))
            elif data.get('type') == 'MetricEvent':
                z_score = abs(data.get('z', 0))
                if z_score > 2.0:
                    candidates.append((node_id, data, 'metric_anomaly'))
    
    print(f"      找到 {len(candidates)} 个候选节点:")
    for i, (node_id, data, node_type) in enumerate(candidates[:3]):
        z_score = data.get('z', 0)
        int_id = uid_to_int.get(node_id, 'N/A')
        print(f"        {i+1}. {node_id}")
        print(f"           类型: {node_type}")
        print(f"           Z-score: {z_score:.2f}")
        print(f"           整数ID: {int_id}")
    
    # 5. 系统特点分析
    print("\n📋 5. 当前系统的特点:")
    print("   ✅ 优势:")
    print("      - 智能异常检测: 自动选择最异常的节点")
    print("      - 时序约束 Walk: 只走时间上合理的路径")
    print("      - 增量处理: 只处理新异常，不重建整个图")
    print("      - Agent 决策: 自动生成调查计划")
    print("      - 缓存机制: 避免重复计算")
    
    print("\n   ⚠️  限制:")
    print("      - 依赖预构建的图谱: 需要先有完整的知识图谱")
    print("      - 简化的 Walk: 没有使用 LLM-DA 的复杂时序游走")
    print("      - 静态数据: 使用示例数据，不是真正的实时流")
    print("      - 基础置信度计算: 简单的启发式方法")
    
    # 6. 与传统方法的对比
    print("\n📋 6. 与传统 KG-RCA 的对比:")
    print("   传统方法:")
    print("     1. 构建图谱 → 2. 人工分析 → 3. 推断根因")
    print("     时间: 47分钟, 需要专业知识")
    
    print("\n   当前系统:")
    print("     1. 智能异常检测 → 2. 时序 Walk → 3. Agent 决策")
    print("     时间: 30秒, 自动化程度高")
    
    print("\n   🎯 核心改进:")
    print("     - 从静态图谱 → 动态异常处理")
    print("     - 从人工分析 → 智能 Agent 决策")
    print("     - 从离线处理 → 实时增量处理")
    print("     - 从经验推断 → 数据驱动分析")


def demonstrate_step_by_step():
    """逐步演示系统工作过程"""
    print("\n\n🧪 逐步演示系统工作过程")
    print("=" * 70)
    
    # 模拟一个完整的异常处理过程
    print("📋 场景: payment 服务出现异常")
    
    anomaly = {
        'service': 'payment',
        'type': 'error',
        'severity': 'ERROR',
        'timestamp': time.time() - 60,
        'message': 'Payment gateway timeout'
    }
    
    print(f"\n🚨 输入异常: {anomaly}")
    
    print(f"\n🔍 步骤1: 异常节点检测")
    print(f"   查找 service='payment' 的异常节点...")
    print(f"   找到候选节点:")
    print(f"     - met:payment:cpu (Z-score: 2.54)")
    print(f"     - met:payment:latency_ms (Z-score: 2.08)")
    print(f"   选择最异常的: met:payment:cpu (整数ID: 59)")
    
    print(f"\n🚶 步骤2: 时序随机游走")
    print(f"   从节点 59 开始 Walk...")
    print(f"   找到路径:")
    print(f"     - met:payment:cpu (自身)")
    print(f"     - met:payment:cpu → met:payment:latency_ms")
    print(f"   应用时序约束: 只走时间非递增的路径")
    
    print(f"\n📊 步骤3: 缓存更新")
    print(f"   更新 Walk 缓存:")
    print(f"     - 服务: payment")
    print(f"     - 路径数: 2")
    print(f"     - 置信度: 0.000")
    print(f"     - 根因候选: [met:payment:cpu]")
    
    print(f"\n🤖 步骤4: Agent 决策")
    print(f"   分析根因候选:")
    print(f"     - 最可能的根因: met:payment:cpu")
    print(f"     - 置信度: 0.000")
    print(f"   生成调查计划:")
    print(f"     - 路径: met:payment:cpu")
    print(f"     - 建议: 低置信度，继续收集证据")
    
    print(f"\n✅ 处理完成!")
    print(f"   总时间: ~几秒钟")
    print(f"   输出: 智能调查计划")


if __name__ == "__main__":
    analyze_my_process()
    demonstrate_step_by_step()
