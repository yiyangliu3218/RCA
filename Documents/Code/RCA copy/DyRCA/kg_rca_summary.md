# KG-RCA vs KG-RCA2 详细对比分析

## 🔍 核心区别总结

### 1. **功能定位**
- **KG-RCA**: 静态知识图谱构建，适合离线分析
- **KG-RCA2**: 动态时序知识图谱 (TKG)，适合实时监控

### 2. **数据处理方式**
- **KG-RCA**: 一次性处理所有数据，生成单一图谱
- **KG-RCA2**: 按分钟分桶处理，生成多个时间片图谱

### 3. **数据格式支持**
- **KG-RCA**: JSON (traces), JSONL (logs), CSV (metrics)
- **KG-RCA2**: 全部使用 CSV 格式，支持 OpenRCA 数据格式

### 4. **关键函数**
- **KG-RCA**: `build_knowledge_graph()`, `iter_spans()`, `iter_log_events()`, `iter_metrics()`
- **KG-RCA2**: 新增 `tkg_from_openrca()` ⭐, `iter_openrca_spans()`, `iter_openrca_log()`, `iter_openrca_metrics()`

## 📊 数据使用分析

### KG-RCA2 的数据控制策略

#### 1. **问题数量控制**
```python
# 只处理指定数量的问题
instruct_data = pd.read_csv(init_file)['instruction'][1:cut + 1]
# cut = args.problem_number (默认1)
```

#### 2. **时间窗口控制**
```python
# 严格的时间过滤
if start_ts is not None and t_sec < start_ts:
    continue
if end_ts is not None and t_sec > end_ts:
    continue
```

#### 3. **按分钟分桶**
```python
# 按分钟分桶处理，避免大图内存占用
tf = minute_bucket(t_sec)
minute_svcs[tf].add(svc)
```

### 数据量控制效果

1. **问题数量限制**: 默认只处理1个问题，避免处理所有问题
2. **时间窗口过滤**: 只处理指定时间范围的数据
3. **分片处理**: 按分钟生成独立图谱，避免大图内存占用
4. **增量处理**: 支持增量测试和部署

## 🔧 路径问题修复

### 当前问题
```python
# 硬编码路径，不适用于其他用户
init_file = f"C:/Users/yamin/Desktop/作业/projcet/KG-RCA/data/{dataset}/query.csv"
telemetry_folder = f'C:/Users/yamin/Desktop/作业/projcet/KG-RCA/data/{dataset}/telemetry'
```

### 修复方案
```python
# 使用环境变量和相对路径
data_root = os.getenv('KG_RCA_DATA_ROOT', './data')
init_file = os.path.join(data_root, dataset, 'query.csv')
telemetry_folder = os.path.join(data_root, dataset, 'telemetry')
```

### 使用方式
```bash
# 设置环境变量
export KG_RCA_DATA_ROOT=./data
export KG_RCA_OUTPUT_ROOT=./outputs

# 运行修复后的脚本
python build_kg_for_openrca_fixed.py --dataset Bank --problem_number 1
```

## 📈 性能优化

### 1. **内存使用优化**
- 按分钟分桶: 避免大图内存占用
- 分片存储: 每个时间片独立存储
- 及时清理: 处理完一个时间片后释放内存

### 2. **计算复杂度**
- 时间复杂度: O(n/60) - 按分钟处理
- 空间复杂度: O(1) 每片 - 分片存储
- 支持增量更新: 只处理变化的部分

### 3. **数据量控制**
- 问题数量限制: 避免处理所有问题
- 时间窗口过滤: 只处理指定时间范围
- 分片处理: 支持大规模数据处理

## 🎯 应用场景

### KG-RCA 适用场景
- 离线根因分析
- 历史事件分析
- 静态系统分析
- 研究原型开发

### KG-RCA2 适用场景
- 实时监控系统
- 动态故障分析
- 生产环境部署
- 大规模数据处理

## 💡 建议

### 1. **路径配置**
- 使用环境变量配置数据路径
- 支持相对路径和绝对路径
- 添加路径验证和错误处理

### 2. **性能优化**
- 继续使用分片处理策略
- 支持并行处理
- 添加内存监控和限制

### 3. **部署建议**
- 使用配置文件管理参数
- 支持多环境部署
- 添加日志和监控

## 🔄 迁移建议

### 从 KG-RCA 到 KG-RCA2
1. **数据格式转换**: 将 JSON/JSONL 数据转换为 CSV 格式
2. **时间处理**: 适应按分钟分桶的处理方式
3. **输出格式**: 适应多时间片输出格式
4. **性能调优**: 根据数据量调整分片大小

### 数据量测试建议
1. **小规模测试**: 使用 1-2 个问题测试功能
2. **中等规模**: 使用 5-10 个问题测试性能
3. **大规模测试**: 使用完整数据集测试稳定性
4. **性能监控**: 监控内存使用和处理时间

## 📋 总结

KG-RCA2 相比 KG-RCA 的主要优势：
1. **动态性**: 支持时序知识图谱和动态分析
2. **可扩展性**: 支持大规模数据处理
3. **实时性**: 适合生产环境部署
4. **灵活性**: 支持多种数据格式和配置

通过合理的数据量控制和性能优化，KG-RCA2 可以高效处理大规模数据，同时保持系统的稳定性和可维护性。
