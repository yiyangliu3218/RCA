# KG-RCA2 × LLM-DA 集成文档

## 🎯 概述

本项目实现了 **KG-RCA2 的分钟级 TKG** 与 **LLM-DA 的规则学习 + 受约束随机游走** 的集成，实现了"采样 → 规则 → 偏置 → 滚动 RCA"的闭环 MVP。

## 🏗️ 架构设计

### 核心组件

1. **TKG 导出模块** (`kg_rca/adapters/tkg_export.py`)
   - 导出分钟切片为统一格式
   - 支持 Parquet 和 JSON 格式
   - 时间约束验证

2. **TKG 加载器** (`LLM-DA/data.py` 中的 `TKGLoader`)
   - 加载时间窗口子图
   - 支持多种时间格式
   - 图结构验证

3. **受约束随机游走** (`LLM-DA/temporal_walk.py` 中的 `CMRW`)
   - 时间递增约束
   - 边类型过滤
   - 规则偏置支持

4. **规则学习与排序** (`LLM-DA/Iteration_reasoning.py`)
   - 从路径学习规则
   - 规则排序和偏置
   - 根因打分

5. **RCA Agent** (`agent/rca_llmda_agent.py`)
   - 集成入口
   - 批量分析支持
   - 结果保存

## 📁 文件结构

```
KG-RCA2/
├── kg_rca/
│   └── adapters/
│       └── tkg_export.py          # TKG 导出模块
├── agent/
│   └── rca_llmda_agent.py         # RCA 集成入口
├── config.yaml                    # 配置文件
├── test_integration.py            # 集成测试
├── quick_start.py                 # 快速启动脚本
└── README_INTEGRATION.md          # 本文档

LLM-DA/
├── data.py                        # 新增 TKGLoader 类
├── temporal_walk.py               # 新增 CMRW 功能
└── Iteration_reasoning.py         # 新增 run_llmda_rca 函数
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 安装依赖
pip install pandas networkx pyarrow pyyaml

# 确保路径正确
export PYTHONPATH="${PYTHONPATH}:$(pwd)/LLM-DA"
```

### 2. 生成知识图谱

```bash
# 使用修复后的脚本生成图谱
python build_kg_for_openrca_fixed.py --dataset Bank --problem_number 1

# 或者使用原始脚本（需要修改路径）
python build_kg_for_openrca.py --dataset Bank --problem_number 1
```

### 3. 运行集成测试

```bash
# 运行集成测试
python test_integration.py

# 运行快速启动
python quick_start.py
```

### 4. 使用 RCA Agent

```bash
# 单问题分析
python agent/rca_llmda_agent.py --dataset Bank --problem_number 1

# 批量分析
python agent/rca_llmda_agent.py --dataset Bank --batch --max_problems 3
```

## 🔧 配置说明

### config.yaml 配置项

```yaml
# LLM-DA 集成配置
llmda:
  # 数据路径
  nodes_path: "LLM-DA/datasets/tkg/nodes.parquet"
  edges_path: "LLM-DA/datasets/tkg/edges.parquet"
  index_path: "LLM-DA/datasets/tkg/index.json"
  
  # 时间窗口配置
  k_minutes: 5  # 时间窗口大小（分钟）
  
  # 随机游走配置
  walk:
    max_len: 4  # 最大路径长度
    num_paths: 200  # 路径数量
    lambda_time_decay: 0.2  # 时间衰减参数
    
  # 评分配置
  score:
    alpha_support: 0.4  # 支持度权重
    beta_temporal_earliness: 0.3  # 时间早发性权重
    gamma_upstreamness: 0.2  # 上游性权重
    delta_noise: 0.1  # 噪声权重
```

## 📊 数据流程

### 1. 数据导出流程

```
KG-RCA2 分钟切片 → TKG 导出 → 标准化格式 → LLM-DA 加载
```

### 2. 分析流程

```
时间窗口图 → 受约束随机游走 → 规则学习 → 根因打分 → 结果输出
```

### 3. 输出格式

```json
{
  "root_service": "payment",
  "root_reason": "metric_anomaly",
  "root_time": "2021-03-04T14:31:00",
  "confidence": 0.85,
  "evidence_paths": [...],
  "rules_used": [...],
  "analysis_time": "2024-01-01T12:00:00"
}
```

## 🧪 测试说明

### 测试项目

1. **TKG 导出测试**: 验证分钟切片导出功能
2. **TKG 加载测试**: 验证时间窗口图加载
3. **时间约束随机游走测试**: 验证 CMRW 功能
4. **LLM-DA RCA 测试**: 验证完整 RCA 流程
5. **RCA Agent 测试**: 验证集成入口

### 运行测试

```bash
# 运行所有测试
python test_integration.py

# 运行特定测试
python -c "from test_integration import test_tkg_export; test_tkg_export()"
```

## 🔍 故障排除

### 常见问题

1. **路径问题**
   ```bash
   # 确保路径正确
   export PYTHONPATH="${PYTHONPATH}:$(pwd)/LLM-DA"
   ```

2. **依赖问题**
   ```bash
   # 安装缺失的依赖
   pip install pandas networkx pyarrow pyyaml
   ```

3. **数据文件不存在**
   ```bash
   # 先运行 KG-RCA2 生成图谱
   python build_kg_for_openrca_fixed.py --dataset Bank --problem_number 1
   ```

### 调试模式

```bash
# 启用详细输出
export KG_RCA_DEBUG=true
export KG_RCA_VERBOSE=true

# 运行测试
python test_integration.py
```

## 📈 性能优化

### 内存优化

- 使用分片处理避免大图内存占用
- 及时释放不需要的数据
- 使用生成器处理大数据

### 计算优化

- 按分钟分桶处理
- 支持增量更新
- 并行处理支持

## 🔄 扩展说明

### 添加新的边类型

1. 在 `tkg_export.py` 中添加新的边类型处理
2. 在 `temporal_walk.py` 中更新 `allowed_edge_types`
3. 在 `config.yaml` 中配置权重

### 添加新的评分维度

1. 在 `_score_root_causes` 中添加新的评分逻辑
2. 在 `config.yaml` 中配置权重
3. 更新结果输出格式

## 📝 开发指南

### 代码规范

- 使用类型注解
- 添加详细的文档字符串
- 遵循 PEP 8 规范
- 添加单元测试

### 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 创建 Pull Request

## 📞 支持

如有问题，请：

1. 查看本文档
2. 运行测试脚本
3. 检查日志输出
4. 提交 Issue

---

**注意**: 本集成遵循最小侵入原则，不破坏 LLM-DA 原有功能，仅新增 API/类，原函数保留。
