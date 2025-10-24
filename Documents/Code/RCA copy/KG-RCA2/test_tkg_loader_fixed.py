#!/usr/bin/env python3
"""
测试修正后的 TKGLoader 功能
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

# Add LLM-DA path
LLM_DA_ROOT = os.path.abspath(os.path.join(PROJECT_ROOT, "LLM-DA"))
if LLM_DA_ROOT not in sys.path:
    sys.path.insert(0, LLM_DA_ROOT)

def create_test_data():
    """创建测试数据，模拟导出的 TKG 格式"""
    print("📊 创建测试数据...")
    
    # 创建测试目录
    test_dir = "test_tkg_data"
    os.makedirs(test_dir, exist_ok=True)
    
    # 创建节点数据
    nodes_data = [
        # 服务节点（无 event_ts）
        {"id": "svc:payment", "node_type": "Service", "service": "payment", 
         "minute_ts": "2021-03-04T14:31:00Z", "event_ts": None},
        {"id": "svc:database", "node_type": "Service", "service": "database", 
         "minute_ts": "2021-03-04T14:31:00Z", "event_ts": None},
        
        # 指标事件节点（有 event_ts）
        {"id": "met:payment:CPU:2021-03-04T14:31:15.123Z", "node_type": "MetricEvent", 
         "service": "payment", "metric": "CPU", "zscore": 2.5, "value": 85.2,
         "minute_ts": "2021-03-04T14:31:00Z", "event_ts": "2021-03-04T14:31:15.123Z"},
        {"id": "met:payment:Memory:2021-03-04T14:31:45.456Z", "node_type": "MetricEvent", 
         "service": "payment", "metric": "Memory", "zscore": 3.1, "value": 92.8,
         "minute_ts": "2021-03-04T14:31:00Z", "event_ts": "2021-03-04T14:31:45.456Z"},
        
        # 日志事件节点（有 event_ts）
        {"id": "log:payment:HTTP_500_ERROR:2021-03-04T14:32:10.789Z", "node_type": "LogEvent", 
         "service": "payment", "template_id": "HTTP_500_ERROR", "severity": "ERROR",
         "minute_ts": "2021-03-04T14:32:00Z", "event_ts": "2021-03-04T14:32:10.789Z"},
    ]
    
    # 创建边数据
    edges_data = [
        # has_metric 边
        {"src": "svc:payment", "dst": "met:payment:CPU:2021-03-04T14:31:15.123Z", 
         "edge_type": "has_metric", "weight": 1.0, "minute_ts": "2021-03-04T14:31:00Z"},
        {"src": "svc:payment", "dst": "met:payment:Memory:2021-03-04T14:31:45.456Z", 
         "edge_type": "has_metric", "weight": 1.0, "minute_ts": "2021-03-04T14:31:00Z"},
        
        # has_log 边
        {"src": "svc:payment", "dst": "log:payment:HTTP_500_ERROR:2021-03-04T14:32:10.789Z", 
         "edge_type": "has_log", "weight": 1.0, "minute_ts": "2021-03-04T14:32:00Z"},
        
        # precedes 边（时间递增）
        {"src": "met:payment:CPU:2021-03-04T14:31:15.123Z", 
         "dst": "met:payment:Memory:2021-03-04T14:31:45.456Z", 
         "edge_type": "precedes", "weight": 1.0, "minute_ts": "2021-03-04T14:31:00Z"},
        {"src": "met:payment:Memory:2021-03-04T14:31:45.456Z", 
         "dst": "log:payment:HTTP_500_ERROR:2021-03-04T14:32:10.789Z", 
         "edge_type": "precedes", "weight": 1.0, "minute_ts": "2021-03-04T14:32:00Z"},
        
        # calls 边
        {"src": "svc:payment", "dst": "svc:database", 
         "edge_type": "calls", "weight": 0.8, "minute_ts": "2021-03-04T14:31:00Z"},
    ]
    
    # 创建索引数据
    index_data = {
        "time_range": {
            "start": 1614868260.0,
            "end": 1614868320.0
        },
        "minutes": [
            {
                "time_str": "14-31-00",
                "minute_ts": 1614868260.0,
                "minute_dt": "2021-03-04T14:31:00Z",
                "nodes_count": 4,
                "edges_count": 3,
                "graph_path": "test.graphml"
            },
            {
                "time_str": "14-32-00", 
                "minute_ts": 1614868320.0,
                "minute_dt": "2021-03-04T14:32:00Z",
                "nodes_count": 1,
                "edges_count": 2,
                "graph_path": "test.graphml"
            }
        ],
        "total_nodes": 5,
        "total_edges": 6
    }
    
    # 保存数据
    nodes_df = pd.DataFrame(nodes_data)
    edges_df = pd.DataFrame(edges_data)
    
    nodes_path = os.path.join(test_dir, "nodes.parquet")
    edges_path = os.path.join(test_dir, "edges.parquet")
    index_path = os.path.join(test_dir, "index.json")
    
    nodes_df.to_parquet(nodes_path, index=False)
    edges_df.to_parquet(edges_path, index=False)
    
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 测试数据创建完成")
    print(f"   节点文件: {nodes_path}")
    print(f"   边文件: {edges_path}")
    print(f"   索引文件: {index_path}")
    
    return nodes_path, edges_path, index_path

def test_tkg_loader():
    """测试修正后的 TKGLoader"""
    print("\n🧪 测试修正后的 TKGLoader")
    print("=" * 50)
    
    try:
        from data import TKGLoader
        
        # 创建测试数据
        nodes_path, edges_path, index_path = create_test_data()
        
        # 测试加载器初始化
        print("\n📊 测试加载器初始化...")
        loader = TKGLoader(nodes_path, edges_path, index_path)
        
        # 测试时间窗口加载
        print("\n📊 测试时间窗口加载...")
        center_ts = "2021-03-04T14:31:30Z"  # 中心时间
        G = loader.load_window_graph(center_ts, k_minutes=2)
        
        print(f"✅ 时间窗口图加载成功")
        print(f"   节点数: {G.number_of_nodes()}")
        print(f"   边数: {G.number_of_edges()}")
        
        # 验证节点属性
        print(f"\n📊 验证节点属性...")
        for node_id, attrs in G.nodes(data=True):
            print(f"   节点 {node_id}:")
            print(f"     类型: {attrs.get('type', 'unknown')}")
            print(f"     事件时间: {attrs.get('event_ts', 'None')}")
            print(f"     分钟时间: {attrs.get('minute_ts', 'None')}")
            if 'service' in attrs:
                print(f"     服务: {attrs['service']}")
            if 'zscore' in attrs:
                print(f"     Z-score: {attrs['zscore']}")
        
        # 验证边属性
        print(f"\n📊 验证边属性...")
        for src, dst, attrs in G.edges(data=True):
            print(f"   边 {src} -> {dst}:")
            print(f"     类型: {attrs.get('type', 'unknown')}")
            print(f"     权重: {attrs.get('weight', 1.0)}")
            print(f"     分钟时间: {attrs.get('minute_ts', 'None')}")
        
        # 验证时间约束
        print(f"\n📊 验证时间约束...")
        precedes_edges = [(u, v, d) for u, v, d in G.edges(data=True) if d.get('type') == 'precedes']
        print(f"   precedes 边数: {len(precedes_edges)}")
        
        for u, v, d in precedes_edges:
            u_event_ts = G.nodes[u].get('event_ts')
            v_event_ts = G.nodes[v].get('event_ts')
            u_minute_ts = G.nodes[u].get('minute_ts')
            v_minute_ts = G.nodes[v].get('minute_ts')
            
            print(f"   {u} -> {v}:")
            print(f"     {u}: event_ts={u_event_ts}, minute_ts={u_minute_ts}")
            print(f"     {v}: event_ts={v_event_ts}, minute_ts={v_minute_ts}")
            
            # 检查时间约束
            u_ts = u_event_ts if pd.notna(u_event_ts) else u_minute_ts
            v_ts = v_event_ts if pd.notna(v_event_ts) else v_minute_ts
            
            if pd.notna(u_ts) and pd.notna(v_ts):
                is_valid = u_ts < v_ts
                print(f"     时间约束: {u_ts} < {v_ts} = {is_valid}")
        
        # 测试其他方法
        print(f"\n📊 测试其他方法...")
        
        # 测试获取可用时间戳
        timestamps = loader.get_available_timestamps()
        print(f"   可用时间戳: {timestamps}")
        
        # 测试根据ID获取节点
        node_info = loader.get_node_by_id("svc:payment")
        if node_info:
            print(f"   节点 svc:payment 信息: {node_info}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_to_time_function():
    """测试 to_time 函数"""
    print(f"\n🧪 测试 to_time 函数")
    print("=" * 40)
    
    try:
        from data import to_time
        
        test_cases = [
            ("2021-03-04T14:31:15.123Z", "ISO 字符串"),
            (1614868275.123, "Unix 时间戳"),
            (1614868275, "Unix 时间戳（整数）"),
            (pd.Timestamp("2021-03-04T14:31:15.123Z"), "pd.Timestamp"),
        ]
        
        for value, description in test_cases:
            result = to_time(value)
            print(f"   {description}: {value} -> {result} (UTC: {result.tz})")
        
        return True
        
    except Exception as e:
        print(f"❌ to_time 测试失败: {e}")
        return False

def cleanup_test_data():
    """清理测试数据"""
    import shutil
    test_dir = "test_tkg_data"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
        print(f"🧹 清理测试数据: {test_dir}")

def main():
    """主测试函数"""
    print("🧪 修正后的 TKGLoader 功能测试")
    print("=" * 70)
    
    try:
        # 测试 to_time 函数
        to_time_success = test_to_time_function()
        
        # 测试 TKGLoader
        loader_success = test_tkg_loader()
        
        # 清理测试数据
        cleanup_test_data()
        
        # 输出结果
        print(f"\n📊 测试结果:")
        print(f"   to_time 函数: {'✅ 通过' if to_time_success else '❌ 失败'}")
        print(f"   TKGLoader: {'✅ 通过' if loader_success else '❌ 失败'}")
        
        overall_success = to_time_success and loader_success
        print(f"\n📈 总体结果: {'✅ 通过' if overall_success else '❌ 失败'}")
        
        return overall_success
        
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        cleanup_test_data()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
