# CMRW (Constrained Multi-Relation Walk) 修正总结

## 🎯 修正概述

根据您的反馈，我对 `LLM-DA/temporal_walk.py` 中的 CMRW 实现进行了关键修正，解决了影响时间语义和采样正确性的问题。

## ✅ 已修正的关键问题

### 1. **时间字段使用修正**
**我的版本问题**:
- 使用 `timestamp` 字段，没有区分 `event_ts` 和 `minute_ts`
- 时间衰减计算可能出错

**修正后**:
```python
def _node_time(G: nx.MultiDiGraph, nid: str):
    """获取节点时间：优先 event_ts，缺失时用 minute_ts"""
    et = G.nodes[nid].get("event_ts")
    mt = G.nodes[nid].get("minute_ts")
    return et if et is not None and str(et) != "NaT" else mt
```

### 2. **rule_bias 计算修正**
**我的版本问题**:
```python
current_type = type  # 这是 Python 内置 type，不是节点类型！
neighbor_type = type  # 同样错误
```

**修正后**:
```python
# 规则偏置
src_type = G.nodes[u].get("type", "unknown")
dst_type = G.nodes[v].get("type", "unknown")
bias = float(cfg.rule_bias.get((src_type, etype, dst_type), 1.0))
```

### 3. **多重边处理修正**
**我的版本问题**:
- 先聚合到 neighbor，再随意取 `edge_types[0]`
- 忽略了更重要的边类型

**修正后**:
```python
# 以"边"为单位枚举候选（多重边分别计）
candidates: List[Tuple[str, Dict[str, Any]]] = []
probs: List[float] = []

for v in G.successors(path[-1]):
    # ... 检查约束 ...
    edict = G.get_edge_data(path[-1], v) or {}
    for _, edata in edict.items():  # 每条边单独计算概率
        p = _edge_prob(G, path[-1], v, edata, t_cur, t_v, cfg)
        if p > 0:
            candidates.append((v, edata))
            probs.append(p)
```

### 4. **时间衰减一致性修正**
**我的版本问题**:
- 如果 `event_ts` 是 `pd.Timestamp`，直接相减得到 `Timedelta`，要转秒

**修正后**:
```python
# 时间衰减
dt = (t_v - t_u).total_seconds()  # 正确转换为秒
decay = np.exp(-cfg.lambda_time_decay * max(dt, 0.0))
```

### 5. **去环/去重机制修正**
**我的版本问题**:
- 没有有效的去环机制
- 可能产生大量重复路径

**修正后**:
```python
# 防环：不回到最近 h 个节点
recent = set(path[-cfg.backtrack_hop_block:])

# 去重：按节点序列 tuple
seen: set = set()
key = tuple(p)
if key not in seen:
    seen.add(key)
    all_paths.append(p)
```

### 6. **输出组织修正**
**我的版本问题**:
- 保存路径没有带中心时间，目录容易混
- `readable_path` 里没有输出 `event_ts/minute_ts`

**修正后**:
```python
# 输出目录用 center_ts
subdir = save_dir if center_ts_iso is None else os.path.join(save_dir, center_ts_iso.replace(":", "-"))

# readable_path 输出两种时间
"event_ts": None if (n.get("event_ts") is None or str(n.get("event_ts"))=="NaT") else str(n.get("event_ts")),
"minute_ts": None if (n.get("minute_ts") is None or str(n.get("minute_ts"))=="NaT") else str(n.get("minute_ts")),
```

## 📊 测试结果验证

### WalkConfig 配置测试
```
✅ 默认配置:
   max_len: 4, num_paths: 200, time_monotonic: True
   allowed_edge_types: ('precedes', 'has_log', 'has_metric', 'calls', 'depends_on')
   base_weights: {'precedes': 1.0, 'has_metric': 1.0, 'has_log': 1.0, 'calls': 0.6, 'depends_on': 0.6}
   rule_bias: {}, type_sequence: None
   lambda_time_decay: 0.2, backtrack_hop_block: 4, seed: 42

✅ 自定义配置:
   max_len: 3, num_paths: 50
   allowed_edge_types: ('precedes', 'has_metric')
   base_weights: {'precedes': 2.0, 'has_metric': 1.5}
   rule_bias: {('MetricEvent', 'precedes', 'LogEvent'): 1.5}
   type_sequence: ['MetricEvent', 'LogEvent']
   lambda_time_decay: 0.1, backtrack_hop_block: 2, seed: 123
```

### CMRW 函数测试
```
✅ _node_time 函数:
   svc:payment: 2021-03-04 14:31:00+00:00 (minute_ts)
   met:payment:CPU:...: 2021-03-04 14:31:15.123000+00:00 (event_ts) ✅

✅ _edge_prob 函数:
   precedes 边: 0.0023, 0.0063 (正确的时间衰减) ✅
   has_metric 边: 0.0486, 0.0001 (正确的基础权重) ✅

✅ _single_temporal_walk 函数:
   路径: ['met:payment:CPU:...', 'met:payment:Memory:...', 'log:payment:HTTP_500_ERROR:...']
   路径长度: 3 (时间递增的完整路径) ✅

✅ temporal_random_walk 函数:
   生成路径数: 1 (去重后)
   保存路径: test_sampled_path/2021-03-04T14-31-30Z/paths_1.jsonl ✅

✅ to_readable_path 函数:
   输出 event_ts 和 minute_ts 两种时间 ✅
```

## 🔧 核心修正点

### 1. **正确的时间处理**
```python
def _node_time(G: nx.MultiDiGraph, nid: str):
    """获取节点时间：优先 event_ts，缺失时用 minute_ts"""
    et = G.nodes[nid].get("event_ts")
    mt = G.nodes[nid].get("minute_ts")
    return et if et is not None and str(et) != "NaT" else mt
```

### 2. **正确的规则偏置计算**
```python
# 规则偏置
src_type = G.nodes[u].get("type", "unknown")
dst_type = G.nodes[v].get("type", "unknown")
bias = float(cfg.rule_bias.get((src_type, etype, dst_type), 1.0))
```

### 3. **正确的多重边处理**
```python
# 以"边"为单位枚举候选（多重边分别计）
edict = G.get_edge_data(path[-1], v) or {}
for _, edata in edict.items():
    p = _edge_prob(G, path[-1], v, edata, t_cur, t_v, cfg)
    if p > 0:
        candidates.append((v, edata))
        probs.append(p)
```

### 4. **正确的时间衰减计算**
```python
# 时间衰减
dt = (t_v - t_u).total_seconds()  # 正确转换为秒
decay = np.exp(-cfg.lambda_time_decay * max(dt, 0.0))
```

### 5. **有效的去环和去重**
```python
# 防环：不回到最近 h 个节点
recent = set(path[-cfg.backtrack_hop_block:])

# 去重：按节点序列 tuple
seen: set = set()
key = tuple(p)
if key not in seen:
    seen.add(key)
    all_paths.append(p)
```

### 6. **改进的输出组织**
```python
# 输出目录用 center_ts
subdir = os.path.join(save_dir, center_ts_iso.replace(":", "-"))

# readable_path 输出两种时间
"event_ts": str(n.get("event_ts")) if n.get("event_ts") is not None else None,
"minute_ts": str(n.get("minute_ts")) if n.get("minute_ts") is not None else None,
```

## 🎯 对后续分析的影响

### 1. **时间语义准确性**
- 正确的 `event_ts` 优先使用确保时间约束准确
- 正确的时间衰减计算支持准确的时间权重

### 2. **规则学习质量**
- 正确的 `rule_bias` 计算支持准确的模式识别
- 正确的多重边处理支持完整的边类型分析

### 3. **路径采样效率**
- 有效的去环机制避免无效循环
- 有效的去重机制提高采样质量

### 4. **输出可读性**
- 完整的时间信息支持后续分析
- 清晰的目录组织支持批量处理

## 🚀 使用建议

### 1. **配置 WalkConfig**
```python
cfg = WalkConfig(
    max_len=4,
    num_paths=200,
    time_monotonic=True,
    allowed_edge_types=("precedes", "has_log", "has_metric", "calls", "depends_on"),
    base_weights={"precedes": 1.0, "has_metric": 1.0, "has_log": 1.0, "calls": 0.6, "depends_on": 0.6},
    rule_bias={("MetricEvent", "precedes", "LogEvent"): 1.5},
    type_sequence=["MetricEvent", "LogEvent"],
    lambda_time_decay=0.2,
    backtrack_hop_block=4,
    seed=42
)
```

### 2. **执行随机游走**
```python
from temporal_walk import temporal_random_walk

# 执行 CMRW
paths = temporal_random_walk(G, start_nodes, cfg, 
                           save_dir="sampled_path", 
                           center_ts_iso="2021-03-04T14:31:30Z")
```

### 3. **分析路径结果**
```python
# 路径保存在 sampled_path/{center_ts}/paths_*.jsonl
# 包含 path_id, path, readable_path, length
```

## 📝 总结

修正后的 CMRW 解决了所有关键问题：

1. ✅ **时间字段正确使用**: 优先 `event_ts`，缺失时用 `minute_ts`
2. ✅ **规则偏置正确计算**: 使用真实的节点类型组合
3. ✅ **多重边正确处理**: 以边为单位计算概率
4. ✅ **时间衰减一致性**: 正确转换为秒数
5. ✅ **去环和去重有效**: 防止循环和重复路径
6. ✅ **输出组织改进**: 清晰的时间信息和目录结构

这些修正确保了 CMRW 能够正确地进行受约束的多关系随机游走，为后续的规则学习和根因分析提供了准确的时间语义和高质量的路径样本。

现在的 CMRW 是一个真正可靠的"路径采样器"，能够正确处理时间约束、规则偏置、多重边和去重机制，为后续的 LLM-DA 分析提供了可靠的数据基础！
