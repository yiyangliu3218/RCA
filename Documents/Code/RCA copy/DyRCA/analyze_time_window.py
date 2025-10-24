#!/usr/bin/env python3
"""
分析 KG-RCA 的时间窗口处理机制
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
from kg_rca.parsers.traces import iter_spans
from kg_rca.parsers.logs import iter_log_events
from kg_rca.parsers.metrics import iter_metrics


def analyze_time_window_mechanism():
    """分析 KG-RCA 的时间窗口处理机制"""
    print("🔍 分析 KG-RCA 的时间窗口处理机制")
    print("=" * 60)
    
    # 1. 分析代码结构
    print("📋 1. KG-RCA 的时间窗口机制:")
    print("   🔧 build_knowledge_graph() 函数签名:")
    print("      def build_knowledge_graph(")
    print("          window: Optional[Dict[str, str]] = None,  # 时间窗口参数")
    print("          ...")
    print("      )")
    
    print("\n   📊 时间窗口处理逻辑:")
    print("      start = _parse_iso(window.get('start')) if window else None")
    print("      end = _parse_iso(window.get('end')) if window else None")
    
    # 2. 分析不同类型数据的处理
    print("\n📋 2. 不同类型数据的时间过滤:")
    
    print("\n   📝 Logs 处理:")
    print("      for ev in iter_log_events(logs_path):")
    print("          t = to_aware_utc(ev.get('time'))")
    print("          if (start and t and t < start) or (end and t and t > end):")
    print("              continue  # 跳过时间窗口外的事件")
    print("          # 处理时间窗口内的事件")
    
    print("\n   📈 Metrics 处理:")
    print("      for an in anomalies:")
    print("          t = to_aware_utc(an.get('time'))")
    print("          if (start and t and t < start) or (end and t and t > end):")
    print("              continue  # 跳过时间窗口外的异常")
    print("          # 处理时间窗口内的异常")
    
    print("\n   🔗 Traces 处理:")
    print("      # 注意：traces 没有时间过滤！")
    print("      span_list = list(iter_spans(traces_path))  # 读取所有 traces")
    print("      # 没有时间窗口检查")
    
    # 3. 实际测试
    print("\n📋 3. 实际测试时间窗口:")
    
    # 测试1：无时间窗口
    print("\n   🧪 测试1: 无时间窗口")
    kg1 = build_knowledge_graph(
        traces_path="KG-RCA/sample_data/traces.json",
        logs_path="KG-RCA/sample_data/logs.jsonl",
        metrics_path="KG-RCA/sample_data/metrics.csv",
        incident_id="no_window",
        window=None,  # 无时间窗口
        enable_causal=False,
    )
    
    print(f"      - 节点数: {kg1.G.number_of_nodes()}")
    print(f"      - 边数: {kg1.G.number_of_edges()}")
    
    # 统计时间范围
    log_times = []
    metric_times = []
    
    for node_id, data in kg1.G.nodes(data=True):
        if data.get('type') == 'LogEvent':
            time_str = data.get('time')
            if time_str:
                log_times.append(time_str)
        elif data.get('type') == 'MetricEvent':
            time_str = data.get('time')
            if time_str:
                metric_times.append(time_str)
    
    if log_times:
        print(f"      - Log 时间范围: {min(log_times)} 到 {max(log_times)}")
    if metric_times:
        print(f"      - Metric 时间范围: {min(metric_times)} 到 {max(metric_times)}")
    
    # 测试2：有时间窗口
    print("\n   🧪 测试2: 有时间窗口")
    kg2 = build_knowledge_graph(
        traces_path="KG-RCA/sample_data/traces.json",
        logs_path="KG-RCA/sample_data/logs.jsonl",
        metrics_path="KG-RCA/sample_data/metrics.csv",
        incident_id="with_window",
        window={
            "start": "2025-08-14T11:05:00Z",
            "end": "2025-08-14T11:10:00Z"
        },
        enable_causal=False,
    )
    
    print(f"      - 节点数: {kg2.G.number_of_nodes()}")
    print(f"      - 边数: {kg2.G.number_of_edges()}")
    
    # 统计时间窗口内的数据
    windowed_log_times = []
    windowed_metric_times = []
    
    for node_id, data in kg2.G.nodes(data=True):
        if data.get('type') == 'LogEvent':
            time_str = data.get('time')
            if time_str:
                windowed_log_times.append(time_str)
        elif data.get('type') == 'MetricEvent':
            time_str = data.get('time')
            if time_str:
                windowed_metric_times.append(time_str)
    
    if windowed_log_times:
        print(f"      - 窗口内 Log 时间范围: {min(windowed_log_times)} 到 {max(windowed_log_times)}")
    if windowed_metric_times:
        print(f"      - 窗口内 Metric 时间范围: {min(windowed_metric_times)} 到 {max(windowed_metric_times)}")
    
    # 4. 分析结果
    print("\n📋 4. 分析结果:")
    print(f"   📊 数据量对比:")
    print(f"      - 无窗口: {kg1.G.number_of_nodes()} 节点, {kg1.G.number_of_edges()} 边")
    print(f"      - 有窗口: {kg2.G.number_of_nodes()} 节点, {kg2.G.number_of_edges()} 边")
    print(f"      - 减少: {kg1.G.number_of_nodes() - kg2.G.number_of_nodes()} 节点, {kg1.G.number_of_edges() - kg2.G.number_of_edges()} 边")
    
    # 5. 关键发现
    print("\n📋 5. 关键发现:")
    print("   ✅ KG-RCA 确实有时间快照机制:")
    print("      - 支持通过 window 参数指定时间窗口")
    print("      - 对 Logs 和 Metrics 进行时间过滤")
    print("      - 只包含时间窗口内的事件")
    
    print("\n   ⚠️  但是有重要限制:")
    print("      - Traces 没有时间过滤！")
    print("      - 所有 traces 都会被包含，不管时间")
    print("      - 这可能导致图谱包含时间窗口外的调用关系")
    
    print("\n   🎯 这意味着:")
    print("      - KG-RCA 生成的是'混合时间快照'")
    print("      - 事件节点有时间约束")
    print("      - 但服务调用关系没有时间约束")
    print("      - 图谱可能包含历史调用关系 + 当前时间窗口的事件")


def analyze_traces_time_issue():
    """分析 traces 时间问题"""
    print("\n\n🔍 深入分析 Traces 时间问题")
    print("=" * 60)
    
    print("📋 Traces 处理代码分析:")
    print("   🔧 iter_spans() 函数:")
    print("      - 读取整个 traces.json 文件")
    print("      - 解析所有 spans")
    print("      - 没有时间过滤逻辑")
    
    print("\n   🔧 derive_service_calls() 函数:")
    print("      - 基于所有 spans 推导服务调用关系")
    print("      - 不考虑时间窗口")
    print("      - 生成所有可能的调用关系")
    
    print("\n   ⚠️  问题:")
    print("      - 如果 traces.json 包含历史数据")
    print("      - 但 window 只指定了当前时间窗口")
    print("      - 图谱会包含历史调用关系 + 当前事件")
    print("      - 这可能导致错误的根因分析")
    
    # 实际测试
    print("\n🧪 实际测试 traces 时间问题:")
    
    # 读取 traces 数据
    spans = list(iter_spans("KG-RCA/sample_data/traces.json"))
    print(f"   - 总 spans 数: {len(spans)}")
    
    # 分析时间范围
    span_times = []
    for span in spans:
        if span.get('startTime'):
            span_times.append(span['startTime'].isoformat())
    
    if span_times:
        print(f"   - Spans 时间范围: {min(span_times)} 到 {max(span_times)}")
    
    # 分析服务调用
    from kg_rca.parsers.traces import derive_service_calls
    service_calls = list(derive_service_calls(spans))
    print(f"   - 服务调用关系数: {len(service_calls)}")
    
    print("\n   🎯 结论:")
    print("      - Traces 确实没有时间过滤")
    print("      - 所有历史调用关系都会被包含")
    print("      - 这是 KG-RCA 设计上的一个限制")


def suggest_improvements():
    """建议改进方案"""
    print("\n\n💡 改进建议")
    print("=" * 60)
    
    print("📋 1. 修复 Traces 时间过滤:")
    print("   🔧 在 iter_spans() 中添加时间过滤:")
    print("      def iter_spans(path: str, start=None, end=None):")
    print("          for span in spans:")
    print("              if start and span['startTime'] < start:")
    print("                  continue")
    print("              if end and span['startTime'] > end:")
    print("                  continue")
    print("              yield span")
    
    print("\n📋 2. 动态时间窗口:")
    print("   🔧 支持滑动时间窗口:")
    print("      - 实时更新窗口")
    print("      - 增量添加新数据")
    print("      - 移除过期数据")
    
    print("\n📋 3. 分层时间处理:")
    print("   🔧 不同类型数据使用不同时间策略:")
    print("      - 事件数据: 严格时间窗口")
    print("      - 调用关系: 可配置的时间窗口")
    print("      - 服务拓扑: 长期稳定关系")
    
    print("\n📋 4. 时间一致性检查:")
    print("   🔧 添加时间一致性验证:")
    print("      - 检查事件时间与调用关系时间的一致性")
    print("      - 标记时间不一致的边")
    print("      - 提供时间冲突报告")


if __name__ == "__main__":
    analyze_time_window_mechanism()
    analyze_traces_time_issue()
    suggest_improvements()
