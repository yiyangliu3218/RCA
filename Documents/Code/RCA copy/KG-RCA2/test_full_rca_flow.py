#!/usr/bin/env python3
"""
测试完整的 RCA 分析流程
验证 RCALLMDAgent 与 LLM-DA 的集成
"""
import os
import sys
import json
import pandas as pd
from pathlib import Path

# Add project paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Add LLM-DA path
LLM_DA_ROOT = os.path.abspath(os.path.join(PROJECT_ROOT, "LLM-DA"))
if LLM_DA_ROOT not in sys.path:
    sys.path.insert(0, LLM_DA_ROOT)

def create_test_data():
    """创建完整的测试数据"""
    print("📊 创建完整测试数据...")
    
    # 创建测试目录
    test_dirs = [
        "data/Bank",
        "outputs/Bank",
        "LLM-DA/datasets/tkg/Bank_1"
    ]
    
    for dir_path in test_dirs:
        os.makedirs(dir_path, exist_ok=True)
    
    # 创建测试 query.csv
    query_data = [
        {
            "problem_number": 1,
            "instruction": "At 2021-03-04 14:31:00, the payment service experienced high CPU usage and memory spikes, leading to HTTP 500 errors. Please analyze the root cause."
        }
    ]
    
    query_df = pd.DataFrame(query_data)
    query_df.to_csv("data/Bank/query.csv", index=False)
    
    # 创建测试 nodes.parquet
    nodes_data = [
        # 服务节点
        {"id": "svc:payment", "node_type": "service", "service": "payment", 
         "minute_ts": "2021-03-04T14:31:00Z", "event_ts": None},
        {"id": "svc:database", "node_type": "service", "service": "database", 
         "minute_ts": "2021-03-04T14:31:00Z", "event_ts": None},
        
        # 指标事件节点（高 zscore）
        {"id": "met:payment:CPU:2021-03-04T14:31:15.123Z", "node_type": "metric_event", 
         "service": "payment", "metric": "CPU", "zscore": 3.5, "value": 95.2,
         "minute_ts": "2021-03-04T14:31:00Z", "event_ts": "2021-03-04T14:31:15.123Z"},
        {"id": "met:payment:Memory:2021-03-04T14:31:45.456Z", "node_type": "metric_event", 
         "service": "payment", "metric": "Memory", "zscore": 2.8, "value": 88.5,
         "minute_ts": "2021-03-04T14:31:00Z", "event_ts": "2021-03-04T14:31:45.456Z"},
        
        # 日志事件节点
        {"id": "log:payment:HTTP_500_ERROR:2021-03-04T14:32:10.789Z", "node_type": "log_event", 
         "service": "payment", "template_id": "HTTP_500_ERROR", "severity": "ERROR",
         "minute_ts": "2021-03-04T14:32:00Z", "event_ts": "2021-03-04T14:32:10.789Z"},
    ]
    
    nodes_df = pd.DataFrame(nodes_data)
    nodes_df.to_parquet("LLM-DA/datasets/tkg/Bank_1/nodes.parquet", index=False)
    
    # 创建测试 edges.parquet
    edges_data = [
        # has_metric 边
        {"src": "svc:payment", "dst": "met:payment:CPU:2021-03-04T14:31:15.123Z", 
         "edge_type": "has_metric", "weight": 1.0, "minute_ts": "2021-03-04T14:31:00Z"},
        {"src": "svc:payment", "dst": "met:payment:Memory:2021-03-04T14:31:45.456Z", 
         "edge_type": "has_metric", "weight": 1.0, "minute_ts": "2021-03-04T14:31:00Z"},
        
        # has_log 边
        {"src": "svc:payment", "dst": "log:payment:HTTP_500_ERROR:2021-03-04T14:32:10.789Z", 
         "edge_type": "has_log", "weight": 1.0, "minute_ts": "2021-03-04T14:32:00Z"},
        
        # precedes 边
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
    
    edges_df = pd.DataFrame(edges_data)
    edges_df.to_parquet("LLM-DA/datasets/tkg/Bank_1/edges.parquet", index=False)
    
    # 创建测试 index.json
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
    
    with open("LLM-DA/datasets/tkg/Bank_1/index.json", 'w', encoding='utf-8') as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)
    
    print("✅ 完整测试数据创建完成")
    return True

def test_full_rca_flow():
    """测试完整的 RCA 分析流程"""
    print("\n🧪 测试完整的 RCA 分析流程")
    print("=" * 50)
    
    try:
        from agent.rca_llmda_agent import RCALLMDAgent
        
        # 创建测试数据
        create_test_data()
        
        # 创建 Agent
        agent = RCALLMDAgent()
        
        print(f"📊 测试参数:")
        print(f"   数据集: Bank")
        print(f"   问题编号: 1")
        
        # 测试完整的 RCA 分析流程
        print(f"\n🔄 开始完整 RCA 分析...")
        result = agent.run_rca_analysis("Bank", 1)
        
        print(f"\n📊 RCA 分析结果:")
        print(f"   状态: {result.get('status', 'unknown')}")
        
        if result.get('status') == 'success':
            print(f"   ✅ RCA 分析成功")
            print(f"   根因服务: {result.get('root_service', 'unknown')}")
            print(f"   根因原因: {result.get('root_reason', 'unknown')}")
            print(f"   根因时间: {result.get('root_time', 'unknown')}")
            print(f"   置信度: {result.get('confidence', 0.0):.3f}")
            print(f"   证据路径数: {len(result.get('evidence_paths', []))}")
            print(f"   使用规则数: {len(result.get('rules_used', []))}")
            
            # 验证结果质量
            if result.get('root_service') != 'unknown':
                print(f"   ✅ 根因服务识别成功")
            else:
                print(f"   ⚠️ 根因服务未识别")
            
            if result.get('evidence_paths'):
                print(f"   ✅ 证据路径生成成功")
            else:
                print(f"   ⚠️ 未生成证据路径")
            
            if result.get('rules_used'):
                print(f"   ✅ 规则学习成功")
            else:
                print(f"   ⚠️ 未学习到规则")
                
        else:
            print(f"   ❌ RCA 分析失败")
            print(f"   错误: {result.get('error', 'unknown error')}")
            return False
        
        # 检查输出文件
        result_file = "outputs/rca_analysis/Bank/problem_1_result.json"
        if os.path.exists(result_file):
            print(f"\n📤 结果文件保存成功: {result_file}")
            
            # 验证文件内容
            with open(result_file, 'r', encoding='utf-8') as f:
                saved_result = json.load(f)
            
            if saved_result.get('status') == 'success':
                print(f"   ✅ 结果文件包含正确的 status 字段")
            else:
                print(f"   ⚠️ 结果文件缺少 status 字段")
        else:
            print(f"   ❌ 结果文件保存失败")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_batch_analysis():
    """测试批量分析功能"""
    print(f"\n🧪 测试批量分析功能")
    print("=" * 40)
    
    try:
        from agent.rca_llmda_agent import RCALLMDAgent
        
        agent = RCALLMDAgent()
        
        # 创建多个测试问题
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
        
        # 测试批量分析
        print(f"📊 开始批量分析...")
        results = agent.batch_analysis("Bank", max_problems=2)
        
        print(f"📊 批量分析结果:")
        print(f"   总问题数: {len(results)}")
        
        successful = sum(1 for r in results if r.get('status') != 'failed')
        print(f"   成功数: {successful}")
        print(f"   失败数: {len(results) - successful}")
        
        # 验证批量结果
        if successful > 0:
            print(f"   ✅ 批量分析部分成功")
        else:
            print(f"   ⚠️ 批量分析全部失败")
        
        # 检查批量结果文件
        batch_result_file = "outputs/rca_analysis/Bank/batch_results.json"
        if os.path.exists(batch_result_file):
            print(f"   ✅ 批量结果文件保存成功: {batch_result_file}")
        else:
            print(f"   ⚠️ 批量结果文件保存失败")
        
        return True
        
    except Exception as e:
        print(f"❌ 批量分析测试失败: {e}")
        return False

def cleanup_test_data():
    """清理测试数据"""
    import shutil
    
    test_dirs = [
        "data/Bank",
        "outputs/Bank",
        "LLM-DA/datasets/tkg/Bank_1",
        "outputs/rca_analysis"
    ]
    
    for dir_path in test_dirs:
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
            print(f"🧹 清理测试数据: {dir_path}")

def main():
    """主测试函数"""
    print("🧪 完整的 RCA 分析流程测试")
    print("=" * 70)
    
    try:
        # 测试完整 RCA 流程
        flow_success = test_full_rca_flow()
        
        # 测试批量分析
        batch_success = test_batch_analysis()
        
        # 清理测试数据
        cleanup_test_data()
        
        # 输出结果
        print(f"\n📊 测试结果:")
        print(f"   完整流程: {'✅ 通过' if flow_success else '❌ 失败'}")
        print(f"   批量分析: {'✅ 通过' if batch_success else '❌ 失败'}")
        
        overall_success = flow_success and batch_success
        print(f"\n📈 总体结果: {'✅ 通过' if overall_success else '❌ 失败'}")
        
        return overall_success
        
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        cleanup_test_data()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
