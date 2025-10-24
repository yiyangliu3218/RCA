#!/usr/bin/env python3
"""
测试修正后的 CMRW (Constrained Multi-Relation Walk) 功能
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

def create_test_graph():
    """创建测试图谱，包含各种节点和边类型"""
    G = nx.MultiDiGraph()
    
    # 添加服务节点（无 event_ts）
    G.add_node("svc:payment", type="Service", service="payment", 
               minute_ts=pd.Timestamp("2021-03-04T14:31:00Z", tz="UTC"))
    G.add_node("svc:database", type="Service", service="database", 
               minute_ts=pd.Timestamp("2021-03-04T14:31:00Z", tz="UTC"))
    
    # 添加指标事件节点（有 event_ts）
    G.add_node("met:payment:CPU:2021-03-04T14:31:15.123Z", 
               type="MetricEvent", service="payment", metric="CPU", 
               zscore=2.5, value=85.2,
               minute_ts=pd.Timestamp("2021-03-04T14:31:00Z", tz="UTC"),
               event_ts=pd.Timestamp("2021-03-04T14:31:15.123Z", tz="UTC"))
    
    G.add_node("met:payment:Memory:2021-03-04T14:31:45.456Z", 
               type="MetricEvent", service="payment", metric="Memory", 
               zscore=3.1, value=92.8,
               minute_ts=pd.Timestamp("2021-03-04T14:31:00Z", tz="UTC"),
               event_ts=pd.Timestamp("2021-03-04T14:31:45.456Z", tz="UTC"))
    
    # 添加日志事件节点（有 event_ts）
    G.add_node("log:payment:HTTP_500_ERROR:2021-03-04T14:32:10.789Z", 
               type="LogEvent", service="payment", template_id="HTTP_500_ERROR", 
               severity="ERROR",
               minute_ts=pd.Timestamp("2021-03-04T14:32:00Z", tz="UTC"),
               event_ts=pd.Timestamp("2021-03-04T14:32:10.789Z", tz="UTC"))
    
    # 添加边
    G.add_edge("svc:payment", "met:payment:CPU:2021-03-04T14:31:15.123Z", 
               type="has_metric", weight=1.0, 
               minute_ts=pd.Timestamp("2021-03-04T14:31:00Z", tz="UTC"))
    G.add_edge("svc:payment", "met:payment:Memory:2021-03-04T14:31:45.456Z", 
               type="has_metric", weight=1.0, 
               minute_ts=pd.Timestamp("2021-03-04T14:31:00Z", tz="UTC"))
    G.add_edge("svc:payment", "log:payment:HTTP_500_ERROR:2021-03-04T14:32:10.789Z", 
               type="has_log", weight=1.0, 
               minute_ts=pd.Timestamp("2021-03-04T14:32:00Z", tz="UTC"))
    
    # 添加 precedes 边（时间递增）
    G.add_edge("met:payment:CPU:2021-03-04T14:31:15.123Z", 
               "met:payment:Memory:2021-03-04T14:31:45.456Z", 
               type="precedes", weight=1.0, 
               minute_ts=pd.Timestamp("2021-03-04T14:31:00Z", tz="UTC"))
    G.add_edge("met:payment:Memory:2021-03-04T14:31:45.456Z", 
               "log:payment:HTTP_500_ERROR:2021-03-04T14:32:10.789Z", 
               type="precedes", weight=1.0, 
               minute_ts=pd.Timestamp("2021-03-04T14:32:00Z", tz="UTC"))
    
    # 添加 calls 边
    G.add_edge("svc:payment", "svc:database", 
               type="calls", weight=0.8, 
               minute_ts=pd.Timestamp("2021-03-04T14:31:00Z", tz="UTC"))
    
    return G

def test_cmrw_functions():
    """测试修正后的 CMRW 函数"""
    print("🧪 测试修正后的 CMRW 函数")
    print("=" * 50)
    
    try:
        from temporal_walk import WalkConfig, _node_time, _type_ok, _edge_prob, _single_temporal_walk, temporal_random_walk, to_readable_path
        
        # 创建测试图谱
        G = create_test_graph()
        print(f"✅ 创建测试图谱: {G.number_of_nodes()} 节点, {G.number_of_edges()} 边")
        
        # 测试 _node_time 函数
        print(f"\n📊 测试 _node_time 函数:")
        for node_id in G.nodes():
            time_val = _node_time(G, node_id)
            print(f"   {node_id}: {time_val}")
        
        # 测试 _type_ok 函数
        print(f"\n📊 测试 _type_ok 函数:")
        type_sequence = ["MetricEvent", "MetricEvent", "LogEvent"]
        for i, node_id in enumerate(G.nodes()):
            is_ok = _type_ok(G, node_id, i, type_sequence)
            node_type = G.nodes[node_id].get("type", "unknown")
            print(f"   位置 {i}: {node_id} (类型: {node_type}) -> {is_ok}")
        
        # 测试 _edge_prob 函数
        print(f"\n📊 测试 _edge_prob 函数:")
        cfg = WalkConfig()
        for u, v, data in G.edges(data=True):
            t_u = _node_time(G, u)
            t_v = _node_time(G, v)
            prob = _edge_prob(G, u, v, data, t_u, t_v, cfg)
            print(f"   {u} -> {v} ({data.get('type', 'unknown')}): {prob:.4f}")
        
        # 测试 _single_temporal_walk 函数
        print(f"\n📊 测试 _single_temporal_walk 函数:")
        start_node = "met:payment:CPU:2021-03-04T14:31:15.123Z"
        path = _single_temporal_walk(G, start_node, cfg)
        if path:
            print(f"   从 {start_node} 开始的路径: {path}")
            print(f"   路径长度: {len(path)}")
        else:
            print(f"   从 {start_node} 开始没有找到有效路径")
        
        # 测试 temporal_random_walk 函数
        print(f"\n📊 测试 temporal_random_walk 函数:")
        start_nodes = ["met:payment:CPU:2021-03-04T14:31:15.123Z"]
        cfg.num_paths = 10  # 减少路径数量用于测试
        
        paths = temporal_random_walk(G, start_nodes, cfg, save_dir="test_sampled_path", 
                                   center_ts_iso="2021-03-04T14:31:30Z")
        
        print(f"   生成路径数: {len(paths)}")
        for i, path in enumerate(paths[:3]):  # 只显示前3条路径
            print(f"   路径 {i+1}: {path}")
        
        # 测试 to_readable_path 函数
        print(f"\n📊 测试 to_readable_path 函数:")
        if paths:
            readable = to_readable_path(G, paths[0])
            print(f"   可读路径:")
            for node_info in readable:
                print(f"     {node_info}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_walk_config():
    """测试 WalkConfig 配置"""
    print(f"\n🧪 测试 WalkConfig 配置")
    print("=" * 40)
    
    try:
        from temporal_walk import WalkConfig
        
        # 测试默认配置
        cfg = WalkConfig()
        print(f"✅ 默认配置:")
        print(f"   max_len: {cfg.max_len}")
        print(f"   num_paths: {cfg.num_paths}")
        print(f"   time_monotonic: {cfg.time_monotonic}")
        print(f"   allowed_edge_types: {cfg.allowed_edge_types}")
        print(f"   base_weights: {cfg.base_weights}")
        print(f"   rule_bias: {cfg.rule_bias}")
        print(f"   type_sequence: {cfg.type_sequence}")
        print(f"   lambda_time_decay: {cfg.lambda_time_decay}")
        print(f"   backtrack_hop_block: {cfg.backtrack_hop_block}")
        print(f"   seed: {cfg.seed}")
        
        # 测试自定义配置
        custom_cfg = WalkConfig(
            max_len=3,
            num_paths=50,
            time_monotonic=True,
            allowed_edge_types=("precedes", "has_metric"),
            base_weights={"precedes": 2.0, "has_metric": 1.5},
            rule_bias={("MetricEvent", "precedes", "LogEvent"): 1.5},
            type_sequence=["MetricEvent", "LogEvent"],
            lambda_time_decay=0.1,
            backtrack_hop_block=2,
            seed=123
        )
        
        print(f"\n✅ 自定义配置:")
        print(f"   max_len: {custom_cfg.max_len}")
        print(f"   num_paths: {custom_cfg.num_paths}")
        print(f"   allowed_edge_types: {custom_cfg.allowed_edge_types}")
        print(f"   base_weights: {custom_cfg.base_weights}")
        print(f"   rule_bias: {custom_cfg.rule_bias}")
        print(f"   type_sequence: {custom_cfg.type_sequence}")
        print(f"   lambda_time_decay: {custom_cfg.lambda_time_decay}")
        print(f"   backtrack_hop_block: {custom_cfg.backtrack_hop_block}")
        print(f"   seed: {custom_cfg.seed}")
        
        return True
        
    except Exception as e:
        print(f"❌ WalkConfig 测试失败: {e}")
        return False

def cleanup_test_data():
    """清理测试数据"""
    import shutil
    test_dir = "test_sampled_path"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
        print(f"🧹 清理测试数据: {test_dir}")

def main():
    """主测试函数"""
    print("🧪 修正后的 CMRW 功能测试")
    print("=" * 70)
    
    try:
        # 测试 WalkConfig
        config_success = test_walk_config()
        
        # 测试 CMRW 函数
        cmrw_success = test_cmrw_functions()
        
        # 清理测试数据
        cleanup_test_data()
        
        # 输出结果
        print(f"\n📊 测试结果:")
        print(f"   WalkConfig: {'✅ 通过' if config_success else '❌ 失败'}")
        print(f"   CMRW 函数: {'✅ 通过' if cmrw_success else '❌ 失败'}")
        
        overall_success = config_success and cmrw_success
        print(f"\n📈 总体结果: {'✅ 通过' if overall_success else '❌ 失败'}")
        
        return overall_success
        
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        cleanup_test_data()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
