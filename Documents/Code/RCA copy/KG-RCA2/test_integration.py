#!/usr/bin/env python3
"""
KG-RCA2 × LLM-DA 集成测试脚本
测试最小可运行用例
"""
import os
import sys
import json
import time
from pathlib import Path

# Add project paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Add LLM-DA path
LLM_DA_ROOT = os.path.abspath(os.path.join(PROJECT_ROOT, "LLM-DA"))
if LLM_DA_ROOT not in sys.path:
    sys.path.insert(0, LLM_DA_ROOT)

def test_tkg_export():
    """测试 TKG 导出功能"""
    print("🧪 测试 1: TKG 导出功能")
    print("=" * 50)
    
    try:
        from kg_rca.adapters.tkg_export import export_tkg_slices
        
        # 测试导出
        output_dir = "outputs"
        merged_dir = "LLM-DA/datasets/tkg"
        
        print(f"📊 导出目录: {output_dir}")
        print(f"📊 合并目录: {merged_dir}")
        
        result = export_tkg_slices(output_dir, merged_dir)
        
        if result['nodes_path']:
            print(f"✅ TKG 导出成功")
            print(f"   节点文件: {result['nodes_path']}")
            print(f"   边文件: {result['edges_path']}")
            print(f"   索引文件: {result['index_path']}")
            return True
        else:
            print(f"❌ TKG 导出失败")
            return False
            
    except Exception as e:
        print(f"❌ TKG 导出测试失败: {e}")
        return False

def test_tkg_loader():
    """测试 TKG 加载功能"""
    print("\n🧪 测试 2: TKG 加载功能")
    print("=" * 50)
    
    try:
        from data import TKGLoader
        
        # 检查数据文件是否存在
        nodes_path = "LLM-DA/datasets/tkg/nodes.parquet"
        edges_path = "LLM-DA/datasets/tkg/edges.parquet"
        index_path = "LLM-DA/datasets/tkg/index.json"
        
        if not all(os.path.exists(p) for p in [nodes_path, edges_path, index_path]):
            print(f"⚠️ 数据文件不存在，跳过测试")
            return False
        
        # 测试加载
        tkg_loader = TKGLoader(nodes_path, edges_path, index_path)
        
        # 测试时间窗口加载
        center_ts = "2021-03-04T14:32:00"
        G_win = tkg_loader.load_window_graph(center_ts, k_minutes=5)
        
        print(f"✅ TKG 加载成功")
        print(f"   窗口图: {G_win.number_of_nodes()} 节点, {G_win.number_of_edges()} 边")
        return True
        
    except Exception as e:
        print(f"❌ TKG 加载测试失败: {e}")
        return False

def test_temporal_walk():
    """测试时间约束随机游走"""
    print("\n🧪 测试 3: 时间约束随机游走")
    print("=" * 50)
    
    try:
        from temporal_walk import temporal_random_walk, WalkConfig
        import networkx as nx
        
        # 创建测试图
        G = nx.MultiDiGraph()
        
        # 添加节点
        G.add_node("svc:payment", type="Service", service="payment", timestamp=1000)
        G.add_node("met:payment:CPU:1001", type="MetricEvent", service="payment", metric="CPU", timestamp=1001)
        G.add_node("log:payment:error:1002", type="LogEvent", service="payment", level="ERROR", timestamp=1002)
        
        # 添加边
        G.add_edge("svc:payment", "met:payment:CPU:1001", type="has_metric", timestamp=1001)
        G.add_edge("svc:payment", "log:payment:error:1002", type="has_log", timestamp=1002)
        G.add_edge("met:payment:CPU:1001", "log:payment:error:1002", type="precedes", timestamp=1002)
        
        # 测试游走
        walk_config = WalkConfig(
            max_len=3,
            num_paths=10,
            time_monotonic=True
        )
        
        start_nodes = ["met:payment:CPU:1001"]
        paths = temporal_random_walk(G, start_nodes, walk_config)
        
        print(f"✅ 时间约束随机游走成功")
        print(f"   生成路径数: {len(paths)}")
        for i, path in enumerate(paths[:3]):
            print(f"   路径 {i+1}: {path}")
        
        return True
        
    except Exception as e:
        print(f"❌ 时间约束随机游走测试失败: {e}")
        return False

def test_llmda_rca():
    """测试 LLM-DA RCA 功能"""
    print("\n🧪 测试 4: LLM-DA RCA 功能")
    print("=" * 50)
    
    try:
        from Iteration_reasoning import run_llmda_rca
        
        # 检查数据文件
        nodes_path = "LLM-DA/datasets/tkg/nodes.parquet"
        edges_path = "LLM-DA/datasets/tkg/edges.parquet"
        index_path = "LLM-DA/datasets/tkg/index.json"
        
        if not all(os.path.exists(p) for p in [nodes_path, edges_path, index_path]):
            print(f"⚠️ 数据文件不存在，跳过测试")
            return False
        
        # 测试 RCA
        index_paths = {
            'nodes_path': nodes_path,
            'edges_path': edges_path,
            'index_path': index_path
        }
        
        top_info_id = "met:payment:CPU:2021-03-04T14:31:00"
        init_center_ts = "2021-03-04T14:32:00"
        
        result = run_llmda_rca(index_paths, top_info_id, init_center_ts, k_minutes=5)
        
        print(f"✅ LLM-DA RCA 成功")
        print(f"   根因服务: {result.get('root_service', 'unknown')}")
        print(f"   根因原因: {result.get('root_reason', 'unknown')}")
        print(f"   置信度: {result.get('confidence', 0.0):.3f}")
        
        return True
        
    except Exception as e:
        print(f"❌ LLM-DA RCA 测试失败: {e}")
        return False

def test_rca_agent():
    """测试 RCA Agent"""
    print("\n🧪 测试 5: RCA Agent")
    print("=" * 50)
    
    try:
        from agent.rca_llmda_agent import RCALLMDAgent
        
        # 创建 Agent
        agent = RCALLMDAgent(config_path="config.yaml")
        
        print(f"✅ RCA Agent 创建成功")
        print(f"   配置: {agent.config_path}")
        print(f"   数据路径: {agent.nodes_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ RCA Agent 测试失败: {e}")
        return False

def run_minimal_example():
    """运行最小可运行用例"""
    print("\n🚀 运行最小可运行用例")
    print("=" * 50)
    
    try:
        # 1. 生成分钟切片（如果不存在）
        print("📊 步骤 1: 生成分钟切片...")
        
        # 检查是否有现有的图谱文件
        output_dir = "outputs"
        if not os.path.exists(output_dir):
            print(f"⚠️ 输出目录不存在: {output_dir}")
            print("   请先运行 KG-RCA2 生成图谱文件")
            return False
        
        # 2. 导出标准化 TKG
        print("📊 步骤 2: 导出标准化 TKG...")
        
        from kg_rca.adapters.tkg_export import export_tkg_slices
        
        merged_dir = "LLM-DA/datasets/tkg"
        result = export_tkg_slices(output_dir, merged_dir)
        
        if not result['nodes_path']:
            print(f"❌ TKG 导出失败")
            return False
        
        print(f"✅ TKG 导出成功")
        
        # 3. 运行集成 RCA
        print("🧠 步骤 3: 运行集成 RCA...")
        
        from Iteration_reasoning import run_llmda_rca
        
        index_paths = {
            'nodes_path': result['nodes_path'],
            'edges_path': result['edges_path'],
            'index_path': result['index_path']
        }
        
        # 使用示例参数
        top_info_id = "met:payment:CPU:2021-03-04T14:31:00"
        init_center_ts = "2021-03-04T14:32:00"
        
        rca_result = run_llmda_rca(index_paths, top_info_id, init_center_ts, k_minutes=5)
        
        print(f"✅ 集成 RCA 完成")
        print(f"   根因服务: {rca_result.get('root_service', 'unknown')}")
        print(f"   根因原因: {rca_result.get('root_reason', 'unknown')}")
        print(f"   根因时间: {rca_result.get('root_time', 'unknown')}")
        print(f"   置信度: {rca_result.get('confidence', 0.0):.3f}")
        
        return True
        
    except Exception as e:
        print(f"❌ 最小可运行用例失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("🧪 KG-RCA2 × LLM-DA 集成测试")
    print("=" * 70)
    
    # 运行各项测试
    tests = [
        ("TKG 导出", test_tkg_export),
        ("TKG 加载", test_tkg_loader),
        ("时间约束随机游走", test_temporal_walk),
        ("LLM-DA RCA", test_llmda_rca),
        ("RCA Agent", test_rca_agent)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔍 运行测试: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ 测试 {test_name} 异常: {e}")
            results.append((test_name, False))
    
    # 运行最小可运行用例
    print(f"\n🚀 运行最小可运行用例")
    minimal_result = run_minimal_example()
    results.append(("最小可运行用例", minimal_result))
    
    # 输出测试结果
    print(f"\n📊 测试结果汇总")
    print("=" * 70)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n📈 总体结果: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！集成成功！")
    else:
        print("⚠️ 部分测试失败，请检查错误信息")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
