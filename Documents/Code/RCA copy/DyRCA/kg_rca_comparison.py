#!/usr/bin/env python3
"""
KG-RCA vs KG-RCA2 详细对比分析
"""
import sys
import os
from typing import Dict, List, Any

# Add project paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def analyze_kg_rca_differences():
    """分析 KG-RCA 和 KG-RCA2 的区别"""
    print("🔍 KG-RCA vs KG-RCA2 详细对比分析")
    print("=" * 70)
    
    # 1. 核心功能对比
    print("📋 1. 核心功能对比:")
    print("\n   🔧 KG-RCA (原始版本):")
    print("      - 静态知识图谱构建")
    print("      - 支持 JSON/JSONL/CSV 格式")
    print("      - 单次时间窗口处理")
    print("      - 因果推断 (PC算法)")
    print("      - 输出: GraphML, CSV, JSON")
    
    print("\n   🚀 KG-RCA2 (增强版本):")
    print("      - 动态时序知识图谱 (TKG)")
    print("      - 支持 OpenRCA 数据格式")
    print("      - 按分钟切片处理")
    print("      - 时序随机游走")
    print("      - 输出: 多个时间片的图谱")
    
    # 2. 数据处理方式对比
    print("\n📋 2. 数据处理方式对比:")
    print("\n   📊 KG-RCA 数据处理:")
    print("      - 一次性读取所有数据")
    print("      - 应用时间窗口过滤")
    print("      - 生成单一知识图谱")
    print("      - 格式: JSON (traces), JSONL (logs), CSV (metrics)")
    
    print("\n   📊 KG-RCA2 数据处理:")
    print("      - 按分钟分桶处理")
    print("      - 每个分钟生成独立图谱")
    print("      - 支持 OpenRCA CSV 格式")
    print("      - 格式: CSV (所有数据源)")
    
    # 3. 关键函数对比
    print("\n📋 3. 关键函数对比:")
    print("\n   🔧 KG-RCA 核心函数:")
    print("      - build_knowledge_graph()")
    print("      - iter_spans()")
    print("      - iter_log_events()")
    print("      - iter_metrics()")
    print("      - run_pc() (因果推断)")
    
    print("\n   🚀 KG-RCA2 新增函数:")
    print("      - tkg_from_openrca() ⭐ 核心新功能")
    print("      - iter_openrca_spans()")
    print("      - iter_openrca_log()")
    print("      - iter_openrca_metrics()")
    print("      - minute_bucket() (时间分桶)")
    
    # 4. 数据格式对比
    print("\n📋 4. 数据格式对比:")
    print("\n   📁 KG-RCA 数据格式:")
    print("      - traces.json (Jaeger格式)")
    print("      - logs.jsonl (JSON Lines)")
    print("      - metrics.csv (时间,服务,指标,值)")
    
    print("\n   📁 KG-RCA2 数据格式:")
    print("      - trace_span.csv (OpenRCA格式)")
    print("      - log_service.csv (OpenRCA格式)")
    print("      - metric_container.csv (OpenRCA格式)")
    print("      - query.csv (问题描述)")
    
    # 5. 时间处理对比
    print("\n📋 5. 时间处理对比:")
    print("\n   ⏰ KG-RCA 时间处理:")
    print("      - 单次时间窗口过滤")
    print("      - 静态图谱构建")
    print("      - 时间约束: start <= time <= end")
    
    print("\n   ⏰ KG-RCA2 时间处理:")
    print("      - 按分钟分桶")
    print("      - 动态图谱序列")
    print("      - 时间约束: 秒级精确过滤")
    print("      - 支持时序分析")
    
    # 6. 输出结果对比
    print("\n📋 6. 输出结果对比:")
    print("\n   📤 KG-RCA 输出:")
    print("      - 单一知识图谱")
    print("      - 静态分析结果")
    print("      - 因果关系图")
    
    print("\n   📤 KG-RCA2 输出:")
    print("      - 多个时间片图谱")
    print("      - 时序演化分析")
    print("      - 动态根因追踪")
    
    # 7. 应用场景对比
    print("\n📋 7. 应用场景对比:")
    print("\n   🎯 KG-RCA 适用场景:")
    print("      - 离线根因分析")
    print("      - 历史事件分析")
    print("      - 静态系统分析")
    print("      - 研究原型开发")
    
    print("\n   🎯 KG-RCA2 适用场景:")
    print("      - 实时监控系统")
    print("      - 动态故障分析")
    print("      - 生产环境部署")
    print("      - 大规模数据处理")


def analyze_data_usage():
    """分析 KG-RCA2 的数据使用情况"""
    print("\n\n📊 KG-RCA2 数据使用分析")
    print("=" * 70)
    
    print("📋 1. 数据来源和路径:")
    print("   📁 数据根目录: C:/Users/yamin/Desktop/作业/projcet/KG-RCA/data/")
    print("   📁 数据集: {dataset} (如 Bank, Telecom 等)")
    print("   📁 遥测数据: {dataset}/telemetry/")
    print("   📁 查询文件: {dataset}/query.csv")
    
    print("\n📋 2. 数据文件结构:")
    print("   📄 query.csv:")
    print("      - instruction: 问题描述")
    print("      - scoring_points: 评分要点")
    print("      - 支持多问题处理 (problem_number)")
    
    print("\n   📁 telemetry/{data_time}/:")
    print("      - trace/trace_span.csv: 调用链数据")
    print("      - metric/metric_container.csv: 指标数据")
    print("      - log/log_service.csv: 日志数据")
    
    print("\n📋 3. 数据处理策略:")
    print("   🔄 按问题数量处理:")
    print("      - 默认处理1个问题 (--problem_number=1)")
    print("      - 可配置处理多个问题")
    print("      - 每个问题独立分析")
    
    print("\n   ⏰ 按时间窗口处理:")
    print("      - 从 instruction 提取时间信息")
    print("      - 应用严格的时间过滤")
    print("      - 按分钟分桶生成图谱")
    
    print("\n📋 4. 数据量控制:")
    print("   📊 问题数量控制:")
    print("      - instruct_data[1:cut+1] 只取前N个问题")
    print("      - 避免处理所有问题")
    print("      - 支持增量测试")
    
    print("\n   📊 时间窗口控制:")
    print("      - 严格的时间过滤")
    print("      - 只处理指定时间范围")
    print("      - 避免处理全量数据")
    
    print("\n📋 5. 输出控制:")
    print("   📤 分层输出:")
    print("      - 按数据集分组")
    print("      - 按日期分组")
    print("      - 按时间分组")
    print("      - 避免输出文件冲突")
    
    print("\n   📤 文件管理:")
    print("      - 自动创建目录结构")
    print("      - 时间戳命名")
    print("      - 支持批量处理")


def suggest_path_modifications():
    """建议路径修改"""
    print("\n\n💡 路径修改建议")
    print("=" * 70)
    
    print("📋 1. 当前路径问题:")
    print("   ❌ 硬编码路径: C:/Users/yamin/Desktop/作业/projcet/KG-RCA/data/")
    print("   ❌ 用户特定路径: 不适用于其他用户")
    print("   ❌ 绝对路径: 不便于部署")
    
    print("\n📋 2. 建议修改:")
    print("   ✅ 使用相对路径:")
    print("      - 数据目录: ./data/{dataset}/")
    print("      - 输出目录: ./outputs/")
    print("      - 配置文件: ./config/")
    
    print("\n   ✅ 环境变量配置:")
    print("      - DATA_ROOT = os.getenv('KG_RCA_DATA_ROOT', './data')")
    print("      - OUTPUT_ROOT = os.getenv('KG_RCA_OUTPUT_ROOT', './outputs')")
    
    print("\n   ✅ 配置文件支持:")
    print("      - config.yaml 配置文件")
    print("      - 支持多环境配置")
    print("      - 路径模板化")
    
    print("\n📋 3. 具体修改建议:")
    print("   🔧 修改 build_kg_for_openrca.py:")
    print("      ```python")
    print("      # 原代码:")
    print("      init_file = f\"C:/Users/yamin/Desktop/作业/projcet/KG-RCA/data/{dataset}/query.csv\"")
    print("      ")
    print("      # 修改为:")
    print("      data_root = os.getenv('KG_RCA_DATA_ROOT', './data')")
    print("      init_file = os.path.join(data_root, dataset, 'query.csv')")
    print("      ```")
    
    print("\n   🔧 添加路径验证:")
    print("      ```python")
    print("      if not os.path.exists(init_file):")
    print("          raise FileNotFoundError(f'Query file not found: {init_file}')")
    print("      ```")
    
    print("\n   🔧 支持多种数据源:")
    print("      ```python")
    print("      # 支持本地和远程数据源")
    print("      if init_file.startswith('http'):")
    print("          # 远程数据源")
    print("      else:")
    print("          # 本地数据源")
    print("      ```")


def analyze_performance_considerations():
    """分析性能考虑"""
    print("\n\n⚡ 性能分析")
    print("=" * 70)
    
    print("📋 1. 数据量控制策略:")
    print("   📊 问题数量限制:")
    print("      - 默认只处理1个问题")
    print("      - 可配置处理数量")
    print("      - 避免内存溢出")
    
    print("\n   📊 时间窗口限制:")
    print("      - 严格时间过滤")
    print("      - 按分钟分桶")
    print("      - 避免处理全量数据")
    
    print("\n📋 2. 内存使用优化:")
    print("   💾 分片处理:")
    print("      - 按分钟生成独立图谱")
    print("      - 避免大图内存占用")
    print("      - 支持流式处理")
    
    print("\n   💾 数据清理:")
    print("      - 及时释放不需要的数据")
    print("      - 使用生成器处理大数据")
    print("      - 避免重复数据存储")
    
    print("\n📋 3. 计算复杂度:")
    print("   ⚡ 时间复杂度:")
    print("      - 按分钟处理: O(n/60)")
    print("      - 避免全量计算")
    print("      - 增量更新支持")
    
    print("\n   ⚡ 空间复杂度:")
    print("      - 分片存储: O(1) 每片")
    print("      - 避免大图存储")
    print("      - 支持分布式处理")


if __name__ == "__main__":
    analyze_kg_rca_differences()
    analyze_data_usage()
    suggest_path_modifications()
    analyze_performance_considerations()
