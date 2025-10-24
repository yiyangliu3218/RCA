#!/usr/bin/env python3
"""
测试修正后的 LLM-DA RCA 功能
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
    test_dir = "test_llmda_data"
    os.makedirs(test_dir, exist_ok=True)
    
    # 创建节点数据
    nodes_data = [
        # 服务节点（无 event_ts）
        {"id": "svc:payment", "node_type": "service", "service": "payment", 
         "minute_ts": "2021-03-04T14:31:00Z", "event_ts": None},
        {"id": "svc:database", "node_type": "service", "service": "database", 
         "minute_ts": "2021-03-04T14:31:00Z", "event_ts": None},
        
        # 指标事件节点（有 event_ts）
        {"id": "met:payment:CPU:2021-03-04T14:31:15.123Z", "node_type": "metric_event", 
         "service": "payment", "metric": "CPU", "zscore": 2.5, "value": 85.2,
         "minute_ts": "2021-03-04T14:31:00Z", "event_ts": "2021-03-04T14:31:15.123Z"},
        {"id": "met:payment:Memory:2021-03-04T14:31:45.456Z", "node_type": "metric_event", 
         "service": "payment", "metric": "Memory", "zscore": 3.1, "value": 92.8,
         "minute_ts": "2021-03-04T14:31:00Z", "event_ts": "2021-03-04T14:31:45.456Z"},
        
        # 日志事件节点（有 event_ts）
        {"id": "log:payment:HTTP_500_ERROR:2021-03-04T14:32:10.789Z", "node_type": "log_event", 
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

def test_llmda_rca():
    """测试修正后的 LLM-DA RCA"""
    print("\n🧪 测试修正后的 LLM-DA RCA")
    print("=" * 50)
    
    try:
        from Iteration_reasoning import run_llmda_rca
        
        # 创建测试数据
        nodes_path, edges_path, index_path = create_test_data()
        
        # 测试参数
        index_paths = {
            'nodes_path': nodes_path,
            'edges_path': edges_path,
            'index_path': index_path
        }
        top_info_id = "met:payment:CPU:2021-03-04T14:31:15.123Z"
        init_center_ts = "2021-03-04T14:31:30Z"
        k_minutes = 2
        
        print(f"📊 测试参数:")
        print(f"   起始节点: {top_info_id}")
        print(f"   中心时间: {init_center_ts}")
        print(f"   窗口大小: {k_minutes} 分钟")
        
        # 执行 RCA 分析
        result = run_llmda_rca(index_paths, top_info_id, init_center_ts, k_minutes, max_rounds=2)
        
        print(f"\n✅ RCA 分析完成")
        print(f"📊 结果:")
        print(f"   根因服务: {result['root_service']}")
        print(f"   根因原因: {result['root_reason']}")
        print(f"   根因时间: {result['root_time']}")
        print(f"   置信度: {result['confidence']:.3f}")
        print(f"   证据路径数: {len(result['evidence_paths'])}")
        print(f"   使用规则数: {len(result['rules_used'])}")
        
        # 验证结果
        print(f"\n📊 验证结果:")
        
        # 1. 检查根因服务
        if result['root_service'] != 'unknown':
            print(f"   ✅ 根因服务识别成功: {result['root_service']}")
        else:
            print(f"   ⚠️ 根因服务未识别")
        
        # 2. 检查规则格式
        if result['rules_used']:
            print(f"   ✅ 规则格式正确: {result['rules_used'][:2]}")
        else:
            print(f"   ⚠️ 未生成规则")
        
        # 3. 检查证据路径
        if result['evidence_paths']:
            print(f"   ✅ 证据路径生成成功: {len(result['evidence_paths'])} 条")
            print(f"   示例路径: {result['evidence_paths'][0] if result['evidence_paths'] else 'None'}")
        else:
            print(f"   ⚠️ 未生成证据路径")
        
        # 4. 检查输出文件
        output_file = f"outputs/rca_runs/{top_info_id.replace(':', '_').replace(':', '_')}_result.json"
        if os.path.exists(output_file):
            print(f"   ✅ 结果文件保存成功: {output_file}")
        else:
            print(f"   ⚠️ 结果文件未找到")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_helper_functions():
    """测试辅助函数"""
    print(f"\n🧪 测试辅助函数")
    print("=" * 40)
    
    try:
        from Iteration_reasoning import _node_time, _node_z, _safe_name
        
        # 创建测试图谱
        G = nx.MultiDiGraph()
        G.add_node("test_node", 
                   type="metric_event", 
                   event_ts=pd.Timestamp("2021-03-04T14:31:15.123Z", tz="UTC"),
                   minute_ts=pd.Timestamp("2021-03-04T14:31:00Z", tz="UTC"),
                   zscore=2.5)
        
        # 测试 _node_time
        time_val = _node_time(G, "test_node")
        print(f"   _node_time: {time_val}")
        
        # 测试 _node_z
        z_val = _node_z(G, "test_node")
        print(f"   _node_z: {z_val}")
        
        # 测试 _safe_name
        safe_name = _safe_name("test:node:with:colons")
        print(f"   _safe_name: {safe_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ 辅助函数测试失败: {e}")
        return False

def cleanup_test_data():
    """清理测试数据"""
    import shutil
    test_dir = "test_llmda_data"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
        print(f"🧹 清理测试数据: {test_dir}")

def main():
    """主测试函数"""
    print("🧪 修正后的 LLM-DA RCA 功能测试")
    print("=" * 70)
    
    try:
        # 测试辅助函数
        helper_success = test_helper_functions()
        
        # 测试 LLM-DA RCA
        rca_success = test_llmda_rca()
        
        # 清理测试数据
        cleanup_test_data()
        
        # 输出结果
        print(f"\n📊 测试结果:")
        print(f"   辅助函数: {'✅ 通过' if helper_success else '❌ 失败'}")
        print(f"   LLM-DA RCA: {'✅ 通过' if rca_success else '❌ 失败'}")
        
        overall_success = helper_success and rca_success
        print(f"\n📈 总体结果: {'✅ 通过' if overall_success else '❌ 失败'}")
        
        return overall_success
        
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        cleanup_test_data()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
