#!/usr/bin/env python3
"""
KG-RCA2 × LLM-DA 快速启动脚本
演示完整的集成流程
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

def step1_generate_kg():
    """步骤 1: 生成知识图谱"""
    print("🔄 步骤 1: 生成知识图谱")
    print("=" * 50)
    
    try:
        # 检查是否有现有的图谱文件
        output_dir = "outputs"
        if os.path.exists(output_dir) and len(list(Path(output_dir).glob("**/*.graphml"))) > 0:
            print(f"✅ 发现现有图谱文件，跳过生成")
            return True
        
        # 如果没有图谱文件，提示用户先运行 KG-RCA2
        print(f"⚠️ 未发现图谱文件，请先运行以下命令生成图谱:")
        print(f"   python build_kg_for_openrca_fixed.py --dataset Bank --problem_number 1")
        print(f"   或者使用修复后的脚本:")
        print(f"   python build_kg_for_openrca.py --dataset Bank --problem_number 1")
        
        return False
        
    except Exception as e:
        print(f"❌ 步骤 1 失败: {e}")
        return False

def step2_export_tkg():
    """步骤 2: 导出标准化 TKG"""
    print("\n🔄 步骤 2: 导出标准化 TKG")
    print("=" * 50)
    
    try:
        from kg_rca.adapters.tkg_export import export_tkg_slices
        
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
            return result
        else:
            print(f"❌ TKG 导出失败")
            return None
            
    except Exception as e:
        print(f"❌ 步骤 2 失败: {e}")
        return None

def step3_run_rca():
    """步骤 3: 运行集成 RCA"""
    print("\n🔄 步骤 3: 运行集成 RCA")
    print("=" * 50)
    
    try:
        from Iteration_reasoning import run_llmda_rca
        
        # 构建索引路径
        index_paths = {
            'nodes_path': 'LLM-DA/datasets/tkg/nodes.parquet',
            'edges_path': 'LLM-DA/datasets/tkg/edges.parquet',
            'index_path': 'LLM-DA/datasets/tkg/index.json'
        }
        
        # 检查文件是否存在
        if not all(os.path.exists(p) for p in index_paths.values()):
            print(f"❌ 数据文件不存在，请先完成步骤 2")
            return None
        
        # 使用示例参数
        top_info_id = "met:payment:CPU:2021-03-04T14:31:00"
        init_center_ts = "2021-03-04T14:32:00"
        
        print(f"🎯 起始节点: {top_info_id}")
        print(f"🎯 中心时间: {init_center_ts}")
        
        # 运行 RCA
        result = run_llmda_rca(index_paths, top_info_id, init_center_ts, k_minutes=5)
        
        print(f"✅ 集成 RCA 完成")
        print(f"   根因服务: {result.get('root_service', 'unknown')}")
        print(f"   根因原因: {result.get('root_reason', 'unknown')}")
        print(f"   根因时间: {result.get('root_time', 'unknown')}")
        print(f"   置信度: {result.get('confidence', 0.0):.3f}")
        
        return result
        
    except Exception as e:
        print(f"❌ 步骤 3 失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def step4_save_results(result):
    """步骤 4: 保存结果"""
    print("\n🔄 步骤 4: 保存结果")
    print("=" * 50)
    
    try:
        # 创建输出目录
        output_dir = "outputs/rca_runs"
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存结果
        result_file = os.path.join(output_dir, "quick_start_result.json")
        
        # 添加元数据
        result['metadata'] = {
            'analysis_time': time.strftime("%Y-%m-%d %H:%M:%S"),
            'version': '1.0.0',
            'description': 'KG-RCA2 × LLM-DA 集成快速启动结果'
        }
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 结果已保存到: {result_file}")
        
        # 打印结果摘要
        print(f"\n📊 结果摘要:")
        print(f"   根因服务: {result.get('root_service', 'unknown')}")
        print(f"   根因原因: {result.get('root_reason', 'unknown')}")
        print(f"   根因时间: {result.get('root_time', 'unknown')}")
        print(f"   置信度: {result.get('confidence', 0.0):.3f}")
        print(f"   证据路径数: {len(result.get('evidence_paths', []))}")
        print(f"   使用规则数: {len(result.get('rules_used', []))}")
        
        return True
        
    except Exception as e:
        print(f"❌ 步骤 4 失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 KG-RCA2 × LLM-DA 快速启动")
    print("=" * 70)
    print("本脚本将演示完整的集成流程:")
    print("1. 生成知识图谱")
    print("2. 导出标准化 TKG")
    print("3. 运行集成 RCA")
    print("4. 保存结果")
    print("=" * 70)
    
    # 步骤 1: 生成知识图谱
    if not step1_generate_kg():
        print("\n⚠️ 请先运行 KG-RCA2 生成图谱文件")
        print("   命令: python build_kg_for_openrca_fixed.py --dataset Bank --problem_number 1")
        return False
    
    # 步骤 2: 导出标准化 TKG
    tkg_result = step2_export_tkg()
    if not tkg_result:
        print("\n❌ TKG 导出失败，无法继续")
        return False
    
    # 步骤 3: 运行集成 RCA
    rca_result = step3_run_rca()
    if not rca_result:
        print("\n❌ RCA 分析失败，无法继续")
        return False
    
    # 步骤 4: 保存结果
    if not step4_save_results(rca_result):
        print("\n❌ 结果保存失败")
        return False
    
    print("\n🎉 快速启动完成！")
    print("=" * 70)
    print("✅ 所有步骤成功完成")
    print("📊 结果已保存到 outputs/rca_runs/quick_start_result.json")
    print("🔍 可以查看该文件了解详细的分析结果")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
