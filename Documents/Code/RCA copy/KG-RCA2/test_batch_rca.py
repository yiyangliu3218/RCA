#!/usr/bin/env python3
"""
测试批量 RCA 分析功能
"""
import os
import sys
import json
import pandas as pd
import networkx as nx
from pathlib import Path

# Add project paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Add LLM-DA path
LLM_DA_ROOT = os.path.abspath(os.path.join(PROJECT_ROOT, "LLM-DA"))
if LLM_DA_ROOT not in sys.path:
    sys.path.insert(0, LLM_DA_ROOT)

def create_batch_test_data():
    """创建批量测试数据"""
    print("📊 创建批量测试数据...")
    
    # 创建测试目录
    test_dirs = [
        "data/Bank",
        "outputs/Bank",
        "LLM-DA/datasets/tkg/Bank_1",
        "LLM-DA/datasets/tkg/Bank_2"
    ]
    
    for dir_path in test_dirs:
        os.makedirs(dir_path, exist_ok=True)
    
    # 创建测试 query.csv（多个问题）
    query_data = [
        {
            "problem_number": 1,
            "instruction": "At 2021-03-04 14:31:00, the payment service experienced high CPU usage and memory spikes, leading to HTTP 500 errors. Please analyze the root cause."
        },
        {
            "problem_number": 2,
            "instruction": "At 2021-03-04 14:35:00, the database service showed connection timeout errors. Please analyze the root cause."
        }
    ]
    
    query_df = pd.DataFrame(query_data)
    query_df.to_csv("data/Bank/query.csv", index=False)
    
    # 为每个问题创建 GraphML 文件
    for problem_num in [1, 2]:
        G = nx.MultiDiGraph()
        
        # 添加节点
        G.add_node("svc:payment", type="service", service="payment", minute_ts="2021-03-04T14:31:00Z")
        G.add_node("svc:database", type="service", service="database", minute_ts="2021-03-04T14:31:00Z")
        G.add_node(f"met:payment:CPU:2021-03-04T14:31:15.123Z", type="metric_event", service="payment", 
                   metric="CPU", zscore=3.5, value=95.2, minute_ts="2021-03-04T14:31:00Z", 
                   event_ts="2021-03-04T14:31:15.123Z")
        G.add_node(f"met:payment:Memory:2021-03-04T14:31:45.456Z", type="metric_event", service="payment", 
                   metric="Memory", zscore=2.8, value=88.5, minute_ts="2021-03-04T14:31:00Z", 
                   event_ts="2021-03-04T14:31:45.456Z")
        G.add_node(f"log:payment:HTTP_500_ERROR:2021-03-04T14:32:10.789Z", type="log_event", service="payment", 
                   template_id="HTTP_500_ERROR", severity="ERROR", minute_ts="2021-03-04T14:32:00Z", 
                   event_ts="2021-03-04T14:32:10.789Z")
        
        # 添加边
        G.add_edge("svc:payment", f"met:payment:CPU:2021-03-04T14:31:15.123Z", type="has_metric", weight=1.0, minute_ts="2021-03-04T14:31:00Z")
        G.add_edge("svc:payment", f"met:payment:Memory:2021-03-04T14:31:45.456Z", type="has_metric", weight=1.0, minute_ts="2021-03-04T14:31:00Z")
        G.add_edge("svc:payment", f"log:payment:HTTP_500_ERROR:2021-03-04T14:32:10.789Z", type="has_log", weight=1.0, minute_ts="2021-03-04T14:32:00Z")
        G.add_edge(f"met:payment:CPU:2021-03-04T14:31:15.123Z", f"met:payment:Memory:2021-03-04T14:31:45.456Z", type="precedes", weight=1.0, minute_ts="2021-03-04T14:31:00Z")
        G.add_edge(f"met:payment:Memory:2021-03-04T14:31:45.456Z", f"log:payment:HTTP_500_ERROR:2021-03-04T14:32:10.789Z", type="precedes", weight=1.0, minute_ts="2021-03-04T14:32:00Z")
        G.add_edge("svc:payment", "svc:database", type="calls", weight=0.8, minute_ts="2021-03-04T14:31:00Z")
        
        # 保存 GraphML 文件
        graphml_path = f"outputs/Bank/Bank_{problem_num}.graphml"
        nx.write_graphml(G, graphml_path)
        print(f"✅ 创建 GraphML 文件: {graphml_path}")
        
        # 创建对应的 TKG 数据
        nodes_data = [
            {"id": "svc:payment", "node_type": "service", "service": "payment", 
             "minute_ts": "2021-03-04T14:31:00Z", "event_ts": None},
            {"id": "svc:database", "node_type": "service", "service": "database", 
             "minute_ts": "2021-03-04T14:31:00Z", "event_ts": None},
            {"id": f"met:payment:CPU:2021-03-04T14:31:15.123Z", "node_type": "metric_event", 
             "service": "payment", "metric": "CPU", "zscore": 3.5, "value": 95.2,
             "minute_ts": "2021-03-04T14:31:00Z", "event_ts": "2021-03-04T14:31:15.123Z"},
            {"id": f"met:payment:Memory:2021-03-04T14:31:45.456Z", "node_type": "metric_event", 
             "service": "payment", "metric": "Memory", "zscore": 2.8, "value": 88.5,
             "minute_ts": "2021-03-04T14:31:00Z", "event_ts": "2021-03-04T14:31:45.456Z"},
            {"id": f"log:payment:HTTP_500_ERROR:2021-03-04T14:32:10.789Z", "node_type": "log_event", 
             "service": "payment", "template_id": "HTTP_500_ERROR", "severity": "ERROR",
             "minute_ts": "2021-03-04T14:32:00Z", "event_ts": "2021-03-04T14:32:10.789Z"},
        ]
        
        nodes_df = pd.DataFrame(nodes_data)
        nodes_df.to_parquet(f"LLM-DA/datasets/tkg/Bank_{problem_num}/nodes.parquet", index=False)
        
        # 创建 edges.parquet
        edges_data = [
            {"src": "svc:payment", "dst": f"met:payment:CPU:2021-03-04T14:31:15.123Z", 
             "edge_type": "has_metric", "weight": 1.0, "minute_ts": "2021-03-04T14:31:00Z"},
            {"src": "svc:payment", "dst": f"met:payment:Memory:2021-03-04T14:31:45.456Z", 
             "edge_type": "has_metric", "weight": 1.0, "minute_ts": "2021-03-04T14:31:00Z"},
            {"src": "svc:payment", "dst": f"log:payment:HTTP_500_ERROR:2021-03-04T14:32:10.789Z", 
             "edge_type": "has_log", "weight": 1.0, "minute_ts": "2021-03-04T14:32:00Z"},
            {"src": f"met:payment:CPU:2021-03-04T14:31:15.123Z", 
             "dst": f"met:payment:Memory:2021-03-04T14:31:45.456Z", 
             "edge_type": "precedes", "weight": 1.0, "minute_ts": "2021-03-04T14:31:00Z"},
            {"src": f"met:payment:Memory:2021-03-04T14:31:45.456Z", 
             "dst": f"log:payment:HTTP_500_ERROR:2021-03-04T14:32:10.789Z", 
             "edge_type": "precedes", "weight": 1.0, "minute_ts": "2021-03-04T14:32:00Z"},
            {"src": "svc:payment", "dst": "svc:database", 
             "edge_type": "calls", "weight": 0.8, "minute_ts": "2021-03-04T14:31:00Z"},
        ]
        
        edges_df = pd.DataFrame(edges_data)
        edges_df.to_parquet(f"LLM-DA/datasets/tkg/Bank_{problem_num}/edges.parquet", index=False)
        
        # 创建 index.json
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
                    "graph_path": f"Bank_{problem_num}.graphml"
                },
                {
                    "time_str": "14-32-00", 
                    "minute_ts": 1614868320.0,
                    "minute_dt": "2021-03-04T14:32:00Z",
                    "nodes_count": 1,
                    "edges_count": 2,
                    "graph_path": f"Bank_{problem_num}.graphml"
                }
            ],
            "total_nodes": 5,
            "total_edges": 6
        }
        
        with open(f"LLM-DA/datasets/tkg/Bank_{problem_num}/index.json", 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)
    
    print("✅ 批量测试数据创建完成")
    return True

def test_batch_analysis():
    """测试批量分析功能"""
    print("\n🧪 测试批量分析功能")
    print("=" * 50)
    
    try:
        from agent.rca_llmda_agent import RCALLMDAgent
        
        # 创建测试数据
        create_batch_test_data()
        
        # 创建 Agent
        agent = RCALLMDAgent()
        
        print(f"📊 测试参数:")
        print(f"   数据集: Bank")
        print(f"   最大问题数: 2")
        
        # 测试批量分析
        print(f"\n🔄 开始批量分析...")
        results = agent.batch_analysis("Bank", max_problems=2)
        
        print(f"\n📊 批量分析结果:")
        print(f"   总问题数: {len(results)}")
        
        successful = sum(1 for r in results if r.get('status') != 'failed')
        failed = len(results) - successful
        
        print(f"   成功数: {successful}")
        print(f"   失败数: {failed}")
        
        # 详细结果
        for i, result in enumerate(results, 1):
            print(f"\n   问题 {i}:")
            print(f"     状态: {result.get('status', 'unknown')}")
            if result.get('status') == 'success':
                print(f"     根因服务: {result.get('root_service', 'unknown')}")
                print(f"     根因原因: {result.get('root_reason', 'unknown')}")
                print(f"     置信度: {result.get('confidence', 0.0):.3f}")
            else:
                print(f"     错误: {result.get('error', 'unknown error')}")
        
        # 验证批量结果
        if successful > 0:
            print(f"\n   ✅ 批量分析部分成功")
        else:
            print(f"\n   ⚠️ 批量分析全部失败")
            return False
        
        # 检查批量结果文件
        batch_result_file = "outputs/rca_analysis/Bank/batch_results.json"
        if os.path.exists(batch_result_file):
            print(f"\n📤 批量结果文件保存成功: {batch_result_file}")
            
            # 验证文件内容
            with open(batch_result_file, 'r', encoding='utf-8') as f:
                saved_results = json.load(f)
            
            if len(saved_results) == 2:
                print(f"   ✅ 批量结果文件包含正确的问题数量")
            else:
                print(f"   ⚠️ 批量结果文件问题数量不正确")
        else:
            print(f"\n   ❌ 批量结果文件保存失败")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 批量分析测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def cleanup_test_data():
    """清理测试数据"""
    import shutil
    
    test_dirs = [
        "data/Bank",
        "outputs/Bank",
        "LLM-DA/datasets/tkg/Bank_1",
        "LLM-DA/datasets/tkg/Bank_2",
        "outputs/rca_analysis"
    ]
    
    for dir_path in test_dirs:
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
            print(f"🧹 清理测试数据: {dir_path}")

def main():
    """主测试函数"""
    print("🧪 批量 RCA 分析功能测试")
    print("=" * 70)
    
    try:
        # 测试批量分析
        batch_success = test_batch_analysis()
        
        # 清理测试数据
        cleanup_test_data()
        
        # 输出结果
        print(f"\n📊 测试结果:")
        print(f"   批量分析: {'✅ 通过' if batch_success else '❌ 失败'}")
        
        print(f"\n📈 总体结果: {'✅ 通过' if batch_success else '❌ 失败'}")
        
        return batch_success
        
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        cleanup_test_data()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
