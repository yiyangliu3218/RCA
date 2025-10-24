#!/usr/bin/env python3
"""
RCA LLM-DA Agent - KG-RCA2 与 LLM-DA 集成入口
调用 run_llmda_rca 完成整案 RCA 分析
"""
import os
import sys
import json
import yaml
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

# Add project paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Add LLM-DA path
LLM_DA_ROOT = os.path.abspath(os.path.join(PROJECT_ROOT, "LLM-DA"))
if LLM_DA_ROOT not in sys.path:
    sys.path.insert(0, LLM_DA_ROOT)

from kg_rca.adapters.tkg_export import export_tkg_slices
from kg_rca.timeutil import extract_and_convert_datetime


class RCALLMDAgent:
    """
    RCA LLM-DA Agent for integrated root cause analysis
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize RCA LLM-DA Agent
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()
        
        # LLM-DA integration paths
        self.llmda_config = self.config.get('llmda', {})
        self.nodes_path = self.llmda_config.get('nodes_path', 'LLM-DA/datasets/tkg/nodes.parquet')
        self.edges_path = self.llmda_config.get('edges_path', 'LLM-DA/datasets/tkg/edges.parquet')
        self.index_path = self.llmda_config.get('index_path', 'LLM-DA/datasets/tkg/index.json')
        self.k_minutes = self.llmda_config.get('k_minutes', 5)
        
        print(f"🤖 RCA LLM-DA Agent 初始化完成")
        print(f"   配置文件: {config_path}")
        print(f"   数据路径: {self.nodes_path}")
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        else:
            print(f"⚠️ 配置文件不存在: {self.config_path}")
            return {}
    
    def run_rca_analysis(self, dataset: str, problem_number: int = 1) -> Dict[str, Any]:
        """
        运行 RCA 分析
        
        Args:
            dataset: Dataset name (Bank, Telecom, etc.)
            problem_number: Problem number to analyze
            
        Returns:
            RCA analysis results
        """
        print(f"🔄 开始 RCA 分析")
        print(f"   数据集: {dataset}")
        print(f"   问题编号: {problem_number}")
        
        # 1. 导出 TKG 数据
        print("📊 步骤 1: 导出 TKG 数据...")
        tkg_result = self._export_tkg_data(dataset, problem_number)
        
        if not tkg_result['nodes_path']:
            return {
                'error': 'Failed to export TKG data',
                'status': 'failed'
            }
        
        # 2. 运行 LLM-DA RCA
        print("🧠 步骤 2: 运行 LLM-DA RCA...")
        rca_result = self._run_llmda_rca(tkg_result, dataset, problem_number)
        
        # 3. 保存结果
        print("💾 步骤 3: 保存结果...")
        self._save_analysis_result(rca_result, dataset, problem_number)
        
        return rca_result
    
    def _export_tkg_data(self, dataset: str, problem_number: int) -> Dict[str, Any]:
        """
        导出 TKG 数据（优化：避免重复导出，按 dataset/problem_number 分目录）
        
        Args:
            dataset: Dataset name
            problem_number: Problem number
            
        Returns:
            Export result dictionary
        """
        # 构建输出目录路径（按 dataset/problem_number 分目录）
        output_dir = f"outputs/{dataset}"
        merged_dir = f"LLM-DA/datasets/tkg/{dataset}_{problem_number}"
        
        # 检查是否已存在且新于源文件
        nodes_path = os.path.join(merged_dir, "nodes.parquet")
        edges_path = os.path.join(merged_dir, "edges.parquet")
        index_path = os.path.join(merged_dir, "index.json")
        
        # 检查是否需要重新导出
        need_export = True
        if all(os.path.exists(p) for p in [nodes_path, edges_path, index_path]):
            # 检查源文件时间
            source_graphml = os.path.join(output_dir, f"{dataset}_{problem_number}.graphml")
            if os.path.exists(source_graphml):
                source_mtime = os.path.getmtime(source_graphml)
                target_mtime = min(os.path.getmtime(p) for p in [nodes_path, edges_path, index_path])
                if target_mtime > source_mtime:
                    need_export = False
                    print(f"✅ TKG 数据已存在且最新，跳过导出")
        
        if need_export:
            # 导出 TKG 切片
            result = export_tkg_slices(output_dir, merged_dir)
        else:
            # 返回现有文件路径
            result = {
                'nodes_path': nodes_path,
                'edges_path': edges_path,
                'index_path': index_path
            }
        
        if result.get('nodes_path'):
            print(f"✅ TKG 数据准备完成")
            print(f"   节点文件: {result['nodes_path']}")
            print(f"   边文件: {result['edges_path']}")
            print(f"   索引文件: {result['index_path']}")
        else:
            print(f"❌ TKG 导出失败")
        
        return result
    
    def _run_llmda_rca(self, tkg_result: Dict[str, Any], dataset: str, problem_number: int) -> Dict[str, Any]:
        """
        运行 LLM-DA RCA 分析
        
        Args:
            tkg_result: TKG export result
            dataset: Dataset name
            problem_number: Problem number
            
        Returns:
            RCA analysis result
        """
        try:
            # 导入 LLM-DA 模块
            from Iteration_reasoning import run_llmda_rca
            
            # 构建索引路径
            index_paths = {
                'nodes_path': tkg_result['nodes_path'],
                'edges_path': tkg_result['edges_path'],
                'index_path': tkg_result['index_path']
            }
            
            # 确定起始节点和时间
            top_info_id, init_center_ts = self._determine_start_node_and_time(dataset, problem_number)
            
            if not top_info_id:
                return {
                    'error': 'Failed to determine start node',
                    'status': 'failed'
                }
            
            print(f"🎯 起始节点: {top_info_id}")
            print(f"🎯 中心时间: {init_center_ts}")
            
            # 运行 LLM-DA RCA
            result = run_llmda_rca(
                index_paths=index_paths,
                top_info_id=top_info_id,
                init_center_ts=init_center_ts,
                k_minutes=self.k_minutes
            )
            
            # 确保返回结果包含 status 字段
            if 'status' not in result:
                result['status'] = 'success'
            
            return result
            
        except Exception as e:
            print(f"❌ LLM-DA RCA 运行失败: {e}")
            return {
                'error': str(e),
                'status': 'failed'
            }
    
    def _determine_start_node_and_time(self, dataset: str, problem_number: int) -> tuple:
        """
        确定起始节点和时间（智能选择：在时间窗口内找 zscore 最大的 metric_event）
        
        Args:
            dataset: Dataset name
            problem_number: Problem number
            
        Returns:
            Tuple of (start_node_id, center_timestamp)
        """
        # 读取查询文件
        query_file = f"data/{dataset}/query.csv"
        
        if not os.path.exists(query_file):
            print(f"⚠️ 查询文件不存在: {query_file}")
            return None, None
        
        try:
            df = pd.read_csv(query_file)
            
            if problem_number > len(df):
                print(f"⚠️ 问题编号 {problem_number} 超出范围")
                return None, None
            
            # 获取问题描述
            instruction = df.iloc[problem_number - 1]['instruction']
            
            # 提取时间信息
            time_dict = extract_and_convert_datetime(instruction)
            center_ts = None
            
            if time_dict and isinstance(time_dict, dict):
                center_ts = time_dict.get('formatted_date')
            
            # 如果无法从 instruction 提取时间，使用 index.json 的中位分钟
            if not center_ts:
                center_ts = self._get_median_time_from_index(dataset, problem_number)
                if not center_ts:
                    print(f"⚠️ 无法确定中心时间")
                    return None, None
            
            # 智能选择起始节点：在导出的 nodes.parquet 中找 zscore 最大的 metric_event
            start_node_id = self._find_best_start_node(dataset, problem_number, center_ts)
            
            if not start_node_id:
                print(f"⚠️ 未找到合适的起始节点，使用默认时间")
                # 如果找不到合适的节点，使用默认的异常指标事件
                start_node_id = f"met:payment:CPU:{center_ts}"
            
            return start_node_id, center_ts
            
        except Exception as e:
            print(f"❌ 确定起始节点失败: {e}")
            return None, None
    
    def _find_best_start_node(self, dataset: str, problem_number: int, center_ts: str) -> Optional[str]:
        """
        在导出的 nodes.parquet 中找 zscore 最大的 metric_event 作为起始节点
        
        Args:
            dataset: Dataset name
            problem_number: Problem number
            center_ts: Center timestamp
            
        Returns:
            Best start node ID or None
        """
        try:
            # 构建节点文件路径
            merged_dir = f"LLM-DA/datasets/tkg/{dataset}_{problem_number}"
            nodes_path = os.path.join(merged_dir, "nodes.parquet")
            
            if not os.path.exists(nodes_path):
                print(f"⚠️ 节点文件不存在: {nodes_path}")
                return None
            
            # 读取节点数据
            nodes_df = pd.read_parquet(nodes_path)
            
            # 过滤 metric_event 节点
            metric_nodes = nodes_df[nodes_df['node_type'] == 'metric_event'].copy()
            
            if metric_nodes.empty:
                print(f"⚠️ 未找到 metric_event 节点")
                return None
            
            # 计算时间窗口（center_ts ± k_minutes）
            center_dt = pd.to_datetime(center_ts)
            window_start = center_dt - pd.Timedelta(minutes=self.k_minutes)
            window_end = center_dt + pd.Timedelta(minutes=self.k_minutes)
            
            # 过滤时间窗口内的节点
            metric_nodes['event_ts'] = pd.to_datetime(metric_nodes['event_ts'], errors='coerce')
            metric_nodes['minute_ts'] = pd.to_datetime(metric_nodes['minute_ts'], errors='coerce')
            
            # 使用 event_ts 或 minute_ts
            metric_nodes['time_ts'] = metric_nodes['event_ts'].fillna(metric_nodes['minute_ts'])
            
            # 过滤时间窗口
            window_nodes = metric_nodes[
                (metric_nodes['time_ts'] >= window_start) & 
                (metric_nodes['time_ts'] <= window_end)
            ]
            
            if window_nodes.empty:
                print(f"⚠️ 时间窗口内未找到 metric_event 节点")
                return None
            
            # 找 zscore 最大的节点
            window_nodes['zscore'] = pd.to_numeric(window_nodes['zscore'], errors='coerce').fillna(0)
            best_node = window_nodes.loc[window_nodes['zscore'].idxmax()]
            
            print(f"🎯 选择起始节点: {best_node['id']} (zscore: {best_node['zscore']:.2f})")
            return best_node['id']
            
        except Exception as e:
            print(f"❌ 查找起始节点失败: {e}")
            return None
    
    def _get_median_time_from_index(self, dataset: str, problem_number: int) -> Optional[str]:
        """
        从 index.json 获取中位分钟时间作为兜底
        
        Args:
            dataset: Dataset name
            problem_number: Problem number
            
        Returns:
            Median timestamp string or None
        """
        try:
            # 构建索引文件路径
            merged_dir = f"LLM-DA/datasets/tkg/{dataset}_{problem_number}"
            index_path = os.path.join(merged_dir, "index.json")
            
            if not os.path.exists(index_path):
                print(f"⚠️ 索引文件不存在: {index_path}")
                return None
            
            # 读取索引数据
            with open(index_path, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            # 获取分钟列表
            minutes = index_data.get('minutes', [])
            if not minutes:
                print(f"⚠️ 索引文件中没有分钟数据")
                return None
            
            # 计算中位分钟
            median_idx = len(minutes) // 2
            median_minute = minutes[median_idx]
            center_ts = median_minute.get('minute_dt')
            
            if center_ts:
                print(f"🎯 使用索引中位时间: {center_ts}")
                return center_ts
            else:
                print(f"⚠️ 无法从索引获取时间")
                return None
                
        except Exception as e:
            print(f"❌ 获取中位时间失败: {e}")
            return None
    
    def _save_analysis_result(self, result: Dict[str, Any], dataset: str, problem_number: int):
        """
        保存分析结果
        
        Args:
            result: Analysis result
            dataset: Dataset name
            problem_number: Problem number
        """
        # 创建输出目录
        output_dir = f"outputs/rca_analysis/{dataset}"
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存结果
        result_file = os.path.join(output_dir, f"problem_{problem_number}_result.json")
        
        # 添加元数据
        result['metadata'] = {
            'dataset': dataset,
            'problem_number': problem_number,
            'analysis_time': datetime.now().isoformat(),
            'config': self.config
        }
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"📤 分析结果已保存到: {result_file}")
    
    def batch_analysis(self, dataset: str, max_problems: int = 5) -> List[Dict[str, Any]]:
        """
        批量分析多个问题
        
        Args:
            dataset: Dataset name
            max_problems: Maximum number of problems to analyze
            
        Returns:
            List of analysis results
        """
        print(f"🔄 开始批量分析: {dataset} (最多 {max_problems} 个问题)")
        
        results = []
        
        for problem_number in range(1, max_problems + 1):
            print(f"\n📊 分析问题 {problem_number}/{max_problems}")
            
            try:
                result = self.run_rca_analysis(dataset, problem_number)
                results.append(result)
                
                if result.get('status') == 'failed':
                    print(f"❌ 问题 {problem_number} 分析失败")
                    continue
                
                print(f"✅ 问题 {problem_number} 分析完成")
                print(f"   根因服务: {result.get('root_service', 'unknown')}")
                print(f"   根因原因: {result.get('root_reason', 'unknown')}")
                print(f"   置信度: {result.get('confidence', 0.0):.3f}")
                
            except Exception as e:
                print(f"❌ 问题 {problem_number} 分析异常: {e}")
                results.append({
                    'problem_number': problem_number,
                    'error': str(e),
                    'status': 'failed'
                })
        
        # 保存批量结果
        batch_result_file = f"outputs/rca_analysis/{dataset}/batch_results.json"
        with open(batch_result_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n📤 批量分析结果已保存到: {batch_result_file}")
        
        return results


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="RCA LLM-DA Agent")
    parser.add_argument("--dataset", type=str, default="Bank", help="Dataset name")
    parser.add_argument("--problem_number", type=int, default=1, help="Problem number")
    parser.add_argument("--batch", action="store_true", help="Run batch analysis")
    parser.add_argument("--max_problems", type=int, default=3, help="Maximum problems for batch analysis")
    parser.add_argument("--config", type=str, default="config.yaml", help="Configuration file")
    
    args = parser.parse_args()
    
    # 创建 Agent
    agent = RCALLMDAgent(config_path=args.config)
    
    if args.batch:
        # 批量分析
        results = agent.batch_analysis(args.dataset, args.max_problems)
        
        # 统计结果
        successful = sum(1 for r in results if r.get('status') != 'failed')
        print(f"\n📊 批量分析完成: {successful}/{len(results)} 个问题成功")
        
    else:
        # 单问题分析
        result = agent.run_rca_analysis(args.dataset, args.problem_number)
        
        if result.get('status') != 'failed':
            print(f"\n✅ 分析完成")
            print(f"   根因服务: {result.get('root_service', 'unknown')}")
            print(f"   根因原因: {result.get('root_reason', 'unknown')}")
            print(f"   根因时间: {result.get('root_time', 'unknown')}")
            print(f"   置信度: {result.get('confidence', 0.0):.3f}")
        else:
            print(f"\n❌ 分析失败: {result.get('error', 'unknown error')}")


if __name__ == "__main__":
    main()
