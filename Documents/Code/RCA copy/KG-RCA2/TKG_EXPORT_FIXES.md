# TKG Export 修正总结

## 🎯 修正概述

根据您的反馈，我对 `tkg_export.py` 进行了关键修正，解决了影响 CMRW 与时间规则正确性的问题。

## ✅ 已修正的关键问题

### 1. **时间戳来源修正**
**问题**: 原来使用目录名 HH-MM-SS 作为整图统一 timestamp，导致所有事件节点同一时刻，precedes 无法反映真实先后。

**修正**: 
- 优先从节点/边属性读取真实时间（`event_ts`, `timestamp`, `ts`, `time`）
- 支持多种时间格式：ISO 格式、Unix 时间戳
- 添加 `event_ts`（事件真实时间）和 `minute_ts`（分钟起点时间）两个字段

### 2. **服务节点时间处理**
**问题**: 服务节点被强行赋予事件时间，误导随机游走。

**修正**:
- 服务节点：`event_ts=None`，只保留 `minute_ts` 用于拼窗
- 事件节点（MetricEvent/LogEvent）：设置真实的 `event_ts`

### 3. **属性类型转换**
**问题**: GraphML 属性类型全是字符串，导致后续计算错误。

**修正**:
- 实现 `coerce_attr()` 函数，强制转换属性类型
- 支持转换：`int`, `float`, `bool`, `datetime`, `str`
- 自动识别时间戳格式并转换

### 4. **precedes 校验优化**
**问题**: 原来使用 O(N²) 循环 + list.index()，且比较的是目录分钟。

**修正**:
- 先构建 `id→node` 字典，O(1) 查找
- 使用 `event_ts` 比较（缺失时用 `minute_ts`）
- 大幅提升验证效率

### 5. **节点ID全局唯一性**
**问题**: 不同分钟里复用同一 id 会导致覆盖/冲突。

**修正**:
- 事件节点：`{kind}:{svc}:{name}:{iso_ts}` 格式
- 服务节点：`svc:{name}` 格式（允许复用）
- 确保全局唯一性

### 6. **日期补全支持**
**问题**: 只解析 HH-MM-SS，多天数据会混淆。

**修正**:
- 支持 `dataset/date/time/` 三层解析
- 自动识别 `YYYY-MM-DD` 和 `HH-MM-SS` 格式
- 组合完整的时间戳

### 7. **文件格式兼容**
**问题**: 只支持 GraphML 格式。

**修正**:
- 支持多种格式：`.graphml`, `.pkl`, `.gexf`, `.json`
- 自动检测文件格式并选择对应加载器

### 8. **输出 Schema 对齐**
**问题**: 缺少为后续 walk 加速的冗余字段。

**修正**:
- **nodes.parquet**: `node_type`, `service`, `metric`, `template_id`, `event_ts`, `minute_ts`, `zscore`, `severity`
- **edges.parquet**: `edge_type`, `src_type`, `dst_type`, `minute_ts`, `event_ts`

## 📊 测试结果验证

### 属性类型转换测试
```
✅ 123 -> 123 (int)
✅ 123.45 -> 123.45 (float)  
✅ true -> True (bool)
✅ false -> False (bool)
✅ 2021-03-04T14:31:15.123Z -> 2021-03-04 14:31:15.123000+00:00 (Timestamp)
✅ normal_string -> normal_string (str)
```

### 时间戳解析测试
```
✅ outputs/Bank/2021-03-04/14-31-00 -> 2021-03-04 14:31:00 (1614868260.0)
✅ outputs/Bank/2021-03-05/09-15-30 -> 2021-03-05 09:15:30 (1614935730.0)
✅ outputs/Telecom/2021-03-04/14-31-00 -> 2021-03-04 14:31:00 (1614868260.0)
```

### 导出结果验证
```
📊 节点数据:
   总节点数: 10
   节点类型分布: {'Service': 4, 'MetricEvent': 4, 'LogEvent': 2}
   事件时间戳: 6/10
   分钟时间戳: 10/10
   服务节点带事件时间: 0/4 (应该为0) ✅
   事件节点带事件时间: 6/6 ✅

📊 边数据:
   总边数: 12
   边类型分布: {'has_metric': 4, 'precedes': 4, 'has_log': 2, 'calls': 2}
   precedes 边数: 4
   时间约束满足: 4/4 ✅
```

## 🔧 新增功能

### 1. **智能属性转换**
```python
def coerce_attr(value: Any) -> Union[str, int, float, bool, datetime, None]:
    """强制转换 GraphML 属性类型"""
    # 自动识别并转换数值、布尔值、时间戳等
```

### 2. **多层时间解析**
```python
def parse_timestamp_from_path(path: Path) -> Tuple[Optional[datetime], Optional[float]]:
    """从路径解析时间戳，支持 dataset/date/time/ 三层结构"""
```

### 3. **节点ID规范化**
```python
def normalize_node_id(node_id: str, node_type: str, attrs: Dict[str, Any]) -> str:
    """规范化节点ID，确保全局唯一性"""
```

### 4. **多格式文件支持**
```python
def load_graph_file(file_path: Path) -> Optional[nx.MultiDiGraph]:
    """加载图谱文件，支持多种格式"""
```

## 📈 性能提升

1. **时间约束验证**: 从 O(N²) 优化到 O(N)
2. **属性类型转换**: 批量处理，减少重复转换
3. **文件格式检测**: 自动选择最优加载器
4. **内存使用**: 分批处理，支持大规模数据

## 🎯 对后续 CMRW 的影响

### 1. **时间约束准确性**
- 真实的 `event_ts` 确保 precedes 边反映实际时间先后
- 服务节点不设置事件时间，避免误导随机游走

### 2. **规则学习质量**
- 正确的属性类型支持准确的数值计算
- 规范化的节点ID避免重复和冲突

### 3. **路径采样效率**
- 冗余字段加速后续查询
- 优化的数据结构支持快速遍历

## 🚀 使用建议

### 1. **数据准备**
确保图谱文件包含正确的时间戳属性：
```python
# 节点属性示例
{
    'type': 'MetricEvent',
    'service': 'payment',
    'metric': 'CPU',
    'timestamp': '2021-03-04T14:31:15.123Z',  # 真实事件时间
    'zscore': 2.5,
    'value': 85.2
}
```

### 2. **目录结构**
推荐使用三层目录结构：
```
outputs/
├── Bank/
│   ├── 2021-03-04/
│   │   ├── 14-31-00/
│   │   │   └── graph.graphml
│   │   └── 14-32-00/
│   │       └── graph.graphml
│   └── 2021-03-05/
│       └── 09-15-30/
│           └── graph.graphml
```

### 3. **验证导出结果**
```python
from kg_rca.adapters.tkg_export import validate_tkg_export

# 验证导出数据
validate_tkg_export(nodes_path, edges_path, index_path)
```

## 📝 总结

修正后的 `tkg_export.py` 解决了所有关键问题：

1. ✅ **时间戳来源正确**: 优先使用真实事件时间
2. ✅ **服务节点处理**: 不设置事件时间，避免误导
3. ✅ **属性类型转换**: 自动转换 GraphML 字符串属性
4. ✅ **性能优化**: O(N²) → O(N) 的验证效率提升
5. ✅ **全局唯一性**: 规范化的节点ID格式
6. ✅ **多格式支持**: 兼容多种图谱文件格式
7. ✅ **Schema 对齐**: 为后续 walk 优化的冗余字段

这些修正确保了 CMRW 与时间规则的准确性，为后续的根因分析提供了可靠的数据基础。
