#!/usr/bin/env python3
"""
测试修正后的 TKG 导出功能
验证关键修正点
"""
import os
import sys
import json
import pandas as pd
import networkx as nx
from pathlib import Path
from datetime import datetime

# Add project paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def create_test_graph():
    """创建测试图谱，包含各种节点和边类型"""
    G = nx.MultiDiGraph()
    
    # 添加服务节点
    G.add_node("svc:payment", type="Service", service="payment")
    G.add_node("svc:database", type="Service", service="database")
    
    # 添加指标事件节点（带真实时间戳）
    G.add_node("met:payment:CPU:1001", 
               type="MetricEvent", 
               service="payment", 
               metric="CPU", 
               timestamp="2021-03-04T14:31:15.123Z",
               zscore=2.5,
               value=85.2)
    
    G.add_node("met:payment:Memory:1002", 
               type="MetricEvent", 
               service="payment", 
               metric="Memory", 
               timestamp="2021-03-04T14:31:45.456Z",
               zscore=3.1,
               value=92.8)
    
    # 添加日志事件节点（带真实时间戳）
    G.add_node("log:payment:error:1003", 
               type="LogEvent", 
               service="payment", 
               level="ERROR",
               template_id="HTTP_500_ERROR",
               timestamp="2021-03-04T14:32:10.789Z",
               message="Internal server error")
    
    # 添加边
    G.add_edge("svc:payment", "met:payment:CPU:1001", 
               type="has_metric", weight=1.0)
    G.add_edge("svc:payment", "met:payment:Memory:1002", 
               type="has_metric", weight=1.0)
    G.add_edge("svc:payment", "log:payment:error:1003", 
               type="has_log", weight=1.0)
    
    # 添加 precedes 边（时间递增）
    G.add_edge("met:payment:CPU:1001", "met:payment:Memory:1002", 
               type="precedes", weight=1.0)
    G.add_edge("met:payment:Memory:1002", "log:payment:error:1003", 
               type="precedes", weight=1.0)
    
    # 添加服务调用边
    G.add_edge("svc:payment", "svc:database", 
               type="calls", weight=0.8)
    
    return G

def test_tkg_export():
    """测试修正后的 TKG 导出功能"""
    print("🧪 测试修正后的 TKG 导出功能")
    print("=" * 60)
    
    try:
        from kg_rca.adapters.tkg_export import export_tkg_slices, validate_tkg_export
        
        # 创建测试目录结构
        test_output_dir = "test_outputs"
        test_merged_dir = "test_merged"
        
        # 创建测试图谱文件
        os.makedirs(f"{test_output_dir}/Bank/2021-03-04/14-31-00", exist_ok=True)
        os.makedirs(f"{test_output_dir}/Bank/2021-03-04/14-32-00", exist_ok=True)
        
        # 创建测试图谱
        G1 = create_test_graph()
        G2 = create_test_graph()  # 第二个时间片的图谱
        
        # 保存测试图谱
        nx.write_graphml(G1, f"{test_output_dir}/Bank/2021-03-04/14-31-00/test.graphml")
        nx.write_graphml(G2, f"{test_output_dir}/Bank/2021-03-04/14-32-00/test.graphml")
        
        print(f"✅ 创建测试图谱文件")
        
        # 测试导出
        result = export_tkg_slices(test_output_dir, test_merged_dir)
        
        if result['nodes_path']:
            print(f"✅ TKG 导出成功")
            
            # 验证导出结果
            if validate_tkg_export(result['nodes_path'], result['edges_path'], result['index_path']):
                print(f"✅ 数据验证通过")
                
                # 详细分析结果
                analyze_export_results(result)
            else:
                print(f"❌ 数据验证失败")
        else:
            print(f"❌ TKG 导出失败")
        
        # 清理测试文件
        import shutil
        if os.path.exists(test_output_dir):
            shutil.rmtree(test_output_dir)
        if os.path.exists(test_merged_dir):
            shutil.rmtree(test_merged_dir)
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def analyze_export_results(result):
    """分析导出结果，验证关键修正点"""
    print(f"\n🔍 分析导出结果")
    print("=" * 40)
    
    # 读取导出的数据
    nodes_df = pd.read_parquet(result['nodes_path'])
    edges_df = pd.read_parquet(result['edges_path'])
    
    print(f"📊 节点数据:")
    print(f"   总节点数: {len(nodes_df)}")
    print(f"   列名: {list(nodes_df.columns)}")
    
    # 检查节点类型分布
    node_types = nodes_df['node_type'].value_counts()
    print(f"   节点类型分布: {dict(node_types)}")
    
    # 检查时间戳字段
    event_ts_count = nodes_df['event_ts'].notna().sum()
    minute_ts_count = nodes_df['minute_ts'].notna().sum()
    print(f"   事件时间戳: {event_ts_count}/{len(nodes_df)}")
    print(f"   分钟时间戳: {minute_ts_count}/{len(nodes_df)}")
    
    # 检查服务节点是否没有事件时间
    service_nodes = nodes_df[nodes_df['node_type'] == 'Service']
    service_with_event_ts = service_nodes['event_ts'].notna().sum()
    print(f"   服务节点带事件时间: {service_with_event_ts}/{len(service_nodes)} (应该为0)")
    
    # 检查事件节点是否有事件时间
    event_nodes = nodes_df[nodes_df['node_type'].isin(['MetricEvent', 'LogEvent'])]
    event_with_event_ts = event_nodes['event_ts'].notna().sum()
    print(f"   事件节点带事件时间: {event_with_event_ts}/{len(event_nodes)}")
    
    print(f"\n📊 边数据:")
    print(f"   总边数: {len(edges_df)}")
    print(f"   列名: {list(edges_df.columns)}")
    
    # 检查边类型分布
    edge_types = edges_df['edge_type'].value_counts()
    print(f"   边类型分布: {dict(edge_types)}")
    
    # 检查 precedes 边的时间约束
    precedes_edges = edges_df[edges_df['edge_type'] == 'precedes']
    if len(precedes_edges) > 0:
        print(f"   precedes 边数: {len(precedes_edges)}")
        
        # 验证时间约束
        valid_precedes = 0
        for _, edge in precedes_edges.iterrows():
            src_node = nodes_df[nodes_df['id'] == edge['src']]
            dst_node = nodes_df[nodes_df['id'] == edge['dst']]
            
            if len(src_node) > 0 and len(dst_node) > 0:
                src_ts = src_node.iloc[0].get('event_ts') or src_node.iloc[0].get('minute_ts', 0)
                dst_ts = dst_node.iloc[0].get('event_ts') or dst_node.iloc[0].get('minute_ts', 0)
                
                if src_ts < dst_ts:
                    valid_precedes += 1
        
        print(f"   时间约束满足: {valid_precedes}/{len(precedes_edges)}")
    
    # 检查节点ID规范化
    print(f"\n📊 节点ID规范化:")
    sample_nodes = nodes_df.head(10)
    for _, node in sample_nodes.iterrows():
        print(f"   {node['id']} (类型: {node['node_type']})")
    
    # 检查属性类型转换
    print(f"\n📊 属性类型转换:")
    numeric_cols = ['zscore', 'weight']
    for col in numeric_cols:
        if col in nodes_df.columns:
            non_null_count = nodes_df[col].notna().sum()
            print(f"   {col}: {non_null_count} 个非空值")

def test_coerce_attr():
    """测试属性类型转换函数"""
    print(f"\n🧪 测试属性类型转换")
    print("=" * 40)
    
    from kg_rca.adapters.tkg_export import coerce_attr
    
    test_cases = [
        ("123", int),
        ("123.45", float),
        ("true", bool),
        ("false", bool),
        ("2021-03-04T14:31:15.123Z", datetime),
        ("1643721075.123", datetime),
        ("normal_string", str),
        (None, type(None)),
        ("", type(None))
    ]
    
    for value, expected_type in test_cases:
        result = coerce_attr(value)
        actual_type = type(result)
        status = "✅" if isinstance(result, expected_type) else "❌"
        print(f"   {status} {value} -> {result} ({actual_type.__name__})")

def test_parse_timestamp():
    """测试时间戳解析函数"""
    print(f"\n🧪 测试时间戳解析")
    print("=" * 40)
    
    from kg_rca.adapters.tkg_export import parse_timestamp_from_path
    
    test_paths = [
        Path("outputs/Bank/2021-03-04/14-31-00"),
        Path("outputs/Bank/2021-03-05/09-15-30"),
        Path("outputs/Telecom/2021-03-04/14-31-00"),
        Path("invalid/path")
    ]
    
    for path in test_paths:
        dt, ts = parse_timestamp_from_path(path)
        status = "✅" if dt is not None else "❌"
        print(f"   {status} {path} -> {dt} ({ts})")

def main():
    """主测试函数"""
    print("🧪 修正后的 TKG 导出功能测试")
    print("=" * 70)
    
    # 测试属性类型转换
    test_coerce_attr()
    
    # 测试时间戳解析
    test_parse_timestamp()
    
    # 测试完整导出流程
    success = test_tkg_export()
    
    print(f"\n📊 测试结果: {'✅ 通过' if success else '❌ 失败'}")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
