# TKGLoader 修正总结

## 🎯 修正概述

根据您的反馈，我对 `LLM-DA/data.py` 中的 `TKGLoader` 进行了关键修正，解决了影响"时间语义"和后续采样正确性的问题。

## ✅ 已修正的关键问题

### 1. **时间字段使用修正**
**问题**: 原来使用 `row['timestamp']` 过滤和比较，把服务节点（无真实事件时间）和事件节点混在一起。

**修正**: 
- **过滤窗口**: 使用 `minute_ts`（不是 event_ts）——因为我们要把这个中心分钟的"全部观测"拉进来
- **precedes 校验**: 使用 `event_ts`（若缺，退回 `minute_ts`）
- 明确区分两种时间字段的用途

### 2. **缺少 networkx 导入**
**问题**: 函数签名里用了 `nx.MultiDiGraph`，但没 `import networkx as nx`。

**修正**: 添加了 `import networkx as nx`

### 3. **attrs 列的类型处理**
**问题**: 从 parquet 读出来 `attrs` 可能是字符串（JSON）或 `bytes`，直接 `update(attrs)` 会报错或丢字段。

**修正**: 
```python
# attrs 列清洗
extra = r.get("attrs")
if isinstance(extra, (str, bytes)):
    try:
        extra = json.loads(extra)
    except Exception:
        extra = {}
if isinstance(extra, dict):
    attrs.update(extra)
```

### 4. **边/节点的类型与数值规范**
**问题**: 保证 `weight` 是 `float`、时间列是 `pd.Timestamp`（不是 float epoch），否则 CMRW 里做时间衰减会很难看。

**修正**:
- 统一时间类型为 `pd.Timestamp`（UTC）
- 规范 `weight` 为 `float` 类型
- 使用 `pd.to_datetime(..., utc=True, errors="coerce")` 确保 UTC 时区

### 5. **UTC/时区一致性**
**问题**: `datetime.fromtimestamp` 生成的是本地时间，最好统一用 `utc`，避免跨机器差异。

**修正**: 
- 所有时间处理统一使用 UTC
- `to_time()` 函数统一返回 UTC 时间戳
- 使用 `pd.to_datetime(..., utc=True)` 确保时区一致性

## 📊 测试结果验证

### to_time 函数测试
```
✅ ISO 字符串: 2021-03-04T14:31:15.123Z -> 2021-03-04 14:31:15.123000+00:00 (UTC: UTC)
✅ Unix 时间戳: 1614868275.123 -> 2021-03-04 14:31:15.122999907+00:00 (UTC: UTC)
✅ Unix 时间戳（整数）: 1614868275 -> 2021-03-04 14:31:15+00:00 (UTC: UTC)
✅ pd.Timestamp: 2021-03-04 14:31:15.123000+00:00 -> 2021-03-04 14:31:15.123000+00:00 (UTC: UTC)
```

### TKGLoader 功能测试
```
✅ 时间窗口图加载成功
   节点数: 5
   边数: 6

✅ 节点属性验证:
   服务节点: event_ts=NaT, minute_ts=2021-03-04 14:31:00+00:00 ✅
   事件节点: event_ts=2021-03-04 14:31:15.123000+00:00, minute_ts=2021-03-04 14:31:00+00:00 ✅

✅ 时间约束验证:
   precedes 边数: 2
   时间约束满足: 2/2 ✅
   CPU -> Memory: 14:31:15.123 < 14:31:45.456 = True ✅
   Memory -> Log: 14:31:45.456 < 14:32:10.789 = True ✅
```

## 🔧 核心修正点

### 1. **时间字段区分使用**
```python
# ✅ 用 minute_ts 过滤（事件真实时间用于校验/排序，不用于取窗）
window_nodes = nd[(nd["minute_ts"] >= start_dt) & (nd["minute_ts"] <= end_dt)].copy()

# ✅ precedes 时间校验：event_ts 优先，其次 minute_ts
def ntime(nid):
    et = G.nodes[nid].get("event_ts")
    mt = G.nodes[nid].get("minute_ts")
    return et if pd.notna(et) else mt
```

### 2. **统一时间类型（UTC）**
```python
# ✅ 统一时间类型（pd.Timestamp，UTC）
for col in ("event_ts", "minute_ts"):
    if col in self.nodes_df.columns:
        self.nodes_df[col] = pd.to_datetime(self.nodes_df[col], utc=True, errors="coerce")
```

### 3. **属性类型规范**
```python
# ✅ 规范 weight
if "weight" in self.edges_df.columns:
    self.edges_df["weight"] = pd.to_numeric(self.edges_df["weight"], errors="coerce").fillna(1.0)
```

### 4. **attrs 列清洗**
```python
# attrs 列清洗
extra = r.get("attrs")
if isinstance(extra, (str, bytes)):
    try:
        extra = json.loads(extra)
    except Exception:
        extra = {}
if isinstance(extra, dict):
    attrs.update(extra)
```

### 5. **to_time 函数统一 UTC**
```python
def to_time(ts_any) -> pd.Timestamp:
    if isinstance(ts_any, pd.Timestamp):
        return ts_any.tz_convert("UTC") if ts_any.tzinfo else ts_any.tz_localize("UTC")
    if isinstance(ts_any, (int, float)):
        return pd.to_datetime(ts_any, unit="s", utc=True)
    if isinstance(ts_any, str):
        try:
            return pd.to_datetime(ts_any, utc=True)
        except Exception:
            return pd.to_datetime(float(ts_any), unit="s", utc=True)
    raise ValueError(f"Unsupported ts type: {type(ts_any)}")
```

## 🎯 对后续 CMRW 的影响

### 1. **时间语义准确性**
- **过滤窗口**: 使用 `minute_ts` 确保包含该分钟的全部观测
- **时间约束**: 使用 `event_ts` 确保 precedes 边反映真实时间先后
- **服务节点**: 不设置事件时间，避免误导随机游走

### 2. **数据类型一致性**
- 统一的 UTC 时区避免跨机器差异
- 规范的 `float` 权重支持准确的时间衰减计算
- 正确的 `pd.Timestamp` 类型支持时间运算

### 3. **属性完整性**
- 正确的 `attrs` 解析确保不丢失字段
- 规范化的数据类型支持后续计算

## 🚀 使用建议

### 1. **数据格式要求**
确保导出的 TKG 数据包含正确的列名：
```python
# 节点列: id, node_type, service, metric, template_id, event_ts, minute_ts, attrs
# 边列: src, dst, edge_type, weight, minute_ts, attrs
```

### 2. **时间格式要求**
- `event_ts`: 事件真实时间（仅事件节点有）
- `minute_ts`: 分钟起点时间（所有节点都有）
- 统一使用 UTC 时区

### 3. **使用示例**
```python
from data import TKGLoader

# 初始化加载器
loader = TKGLoader("nodes.parquet", "edges.parquet", "index.json")

# 加载时间窗口图
center_ts = "2021-03-04T14:31:30Z"
G = loader.load_window_graph(center_ts, k_minutes=5)

# 验证时间约束
precedes_edges = [(u, v, d) for u, v, d in G.edges(data=True) if d.get('type') == 'precedes']
print(f"precedes 边数: {len(precedes_edges)}")
```

## 📝 总结

修正后的 `TKGLoader` 解决了所有关键问题：

1. ✅ **时间字段正确使用**: 区分 `event_ts` 和 `minute_ts` 的用途
2. ✅ **导入完整性**: 添加缺失的 `networkx` 导入
3. ✅ **属性类型处理**: 正确处理 `attrs` 列的类型转换
4. ✅ **数据类型规范**: 统一时间类型和权重类型
5. ✅ **时区一致性**: 统一使用 UTC 时区

这些修正确保了 TKGLoader 能够正确地将"离线导出的 TKG 数据"转换成 **NetworkX MultiDiGraph** 的**运行时视图**，为后续的 CMRW 和 LLM 分析提供了准确的时间语义和数据类型基础。

现在的 TKGLoader 是一个真正可靠的"数据加载器"，能够正确处理时间窗口、属性类型和时区一致性，为后续的根因分析提供了可靠的数据基础！
