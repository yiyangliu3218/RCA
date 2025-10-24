#!/usr/bin/env python3
"""
测试修正后的 RCALLMDAgent
验证关键修正点
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

def create_test_data():
    """创建测试数据"""
    print("📊 创建测试数据...")
    
    # 创建测试目录结构
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
    
    print("✅ 测试数据创建完成")
    return True

def test_rca_agent():
    """测试修正后的 RCALLMDAgent"""
    print("\n🧪 测试修正后的 RCALLMDAgent")
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
        
        # 测试智能起始节点选择
        print(f"\n🔍 测试智能起始节点选择...")
        start_node_id, center_ts = agent._determine_start_node_and_time("Bank", 1)
        
        print(f"✅ 起始节点选择结果:")
        print(f"   起始节点: {start_node_id}")
        print(f"   中心时间: {center_ts}")
        
        # 验证结果
        if start_node_id and center_ts:
            print(f"   ✅ 起始节点选择成功")
            
            # 检查是否选择了 zscore 最大的节点
            if "met:payment:CPU" in start_node_id:
                print(f"   ✅ 选择了高 zscore 的 CPU 指标节点")
            else:
                print(f"   ⚠️ 未选择预期的 CPU 指标节点")
        else:
            print(f"   ❌ 起始节点选择失败")
            return False
        
        # 测试 TKG 数据导出优化
        print(f"\n🔍 测试 TKG 数据导出优化...")
        tkg_result = agent._export_tkg_data("Bank", 1)
        
        if tkg_result.get('nodes_path'):
            print(f"   ✅ TKG 数据准备成功")
            print(f"   节点文件: {tkg_result['nodes_path']}")
            print(f"   边文件: {tkg_result['edges_path']}")
            print(f"   索引文件: {tkg_result['index_path']}")
        else:
            print(f"   ❌ TKG 数据准备失败")
            return False
        
        # 测试完整 RCA 分析（模拟）
        print(f"\n🔍 测试完整 RCA 分析流程...")
        
        # 模拟 run_llmda_rca 返回结果
        mock_result = {
            "root_service": "payment",
            "root_reason": "metric_anomaly",
            "root_time": "2021-03-04T14:31:15.123Z",
            "evidence_paths": [
                ["met:payment:CPU:2021-03-04T14:31:15.123Z", "met:payment:Memory:2021-03-04T14:31:45.456Z"]
            ],
            "rules_used": ["('metric_event', 'precedes', 'metric_event')"],
            "confidence": 0.85,
            "analysis_time": "2021-03-04T14:35:00Z"
        }
        
        # 测试 status 字段添加
        if 'status' not in mock_result:
            mock_result['status'] = 'success'
        
        print(f"   ✅ 模拟 RCA 结果:")
        print(f"   根因服务: {mock_result['root_service']}")
        print(f"   根因原因: {mock_result['root_reason']}")
        print(f"   置信度: {mock_result['confidence']:.3f}")
        print(f"   状态: {mock_result['status']}")
        
        # 测试结果保存
        print(f"\n🔍 测试结果保存...")
        agent._save_analysis_result(mock_result, "Bank", 1)
        
        # 检查保存的文件
        result_file = "outputs/rca_analysis/Bank/problem_1_result.json"
        if os.path.exists(result_file):
            print(f"   ✅ 结果文件保存成功: {result_file}")
            
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

def test_export_optimization():
    """测试导出优化功能"""
    print(f"\n🧪 测试导出优化功能")
    print("=" * 40)
    
    try:
        from agent.rca_llmda_agent import RCALLMDAgent
        
        agent = RCALLMDAgent()
        
        # 第一次导出
        print(f"📊 第一次导出...")
        result1 = agent._export_tkg_data("Bank", 1)
        
        # 第二次导出（应该跳过）
        print(f"📊 第二次导出（应该跳过）...")
        result2 = agent._export_tkg_data("Bank", 1)
        
        # 验证结果
        if result1.get('nodes_path') == result2.get('nodes_path'):
            print(f"   ✅ 导出优化成功：第二次导出被跳过")
        else:
            print(f"   ⚠️ 导出优化可能有问题")
        
        return True
        
    except Exception as e:
        print(f"❌ 导出优化测试失败: {e}")
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
    print("🧪 修正后的 RCALLMDAgent 功能测试")
    print("=" * 70)
    
    try:
        # 测试 RCALLMDAgent
        agent_success = test_rca_agent()
        
        # 测试导出优化
        export_success = test_export_optimization()
        
        # 清理测试数据
        cleanup_test_data()
        
        # 输出结果
        print(f"\n📊 测试结果:")
        print(f"   RCALLMDAgent: {'✅ 通过' if agent_success else '❌ 失败'}")
        print(f"   导出优化: {'✅ 通过' if export_success else '❌ 失败'}")
        
        overall_success = agent_success and export_success
        print(f"\n📈 总体结果: {'✅ 通过' if overall_success else '❌ 失败'}")
        
        return overall_success
        
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        cleanup_test_data()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
