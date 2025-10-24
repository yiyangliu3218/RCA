from typing import Optional, Dict, Any, List
from datetime import datetime
from collections import defaultdict

from .graph import KnowledgeGraph, Node, Edge
from .parsers.logs import iter_log_events,iter_openrca_log
from .parsers.metrics import iter_metrics, detect_anomalies, load_metrics_rows,iter_openrca_metrics
from .parsers.traces import iter_spans, derive_service_calls,iter_openrca_spans
from .causal import metrics_to_dataframe, run_pc
from .timeutil import parse_any_ts_utc, to_aware_utc

from typing import Optional, Dict, Any, List, Tuple, DefaultDict, Set
Triple = Tuple[str, str, str]

def _parse_iso(s: Optional[str]):
    return parse_any_ts_utc(s)  # always UTC-aware or None


def build_knowledge_graph(
    traces_path: Optional[str] = None,
    logs_path: Optional[str] = None,
    metrics_path: Optional[str] = None,
    incident_id: Optional[str] = None,
    window: Optional[Dict[str, str]] = None,
    enable_causal: bool = True,
    pc_alpha: float = 0.05,
    resample_rule: Optional[str] = '60S',
) -> KnowledgeGraph:
    start = _parse_iso(window.get("start")) if window else None
    end = _parse_iso(window.get("end")) if window else None

    kg = KnowledgeGraph()
    incident_id = incident_id or "incident"
    kg.add_node(Node(id=f"incident:{incident_id}", type="Incident", attrs={"id": incident_id}))

    # --- Traces → Services + calls ---
    services = set()
    span_list: List[Dict[str, Any]] = []
    if traces_path:
        # used for oepenrca
        if traces_path.endswith(".csv"):
            span_list = iter_openrca_spans(traces_path,window)
        else:
            span_list = list(iter_spans(traces_path))
        for s in span_list:
            if s.get("service"):
                services.add(s["service"])
        for svc in services:
            kg.add_node(Node(id=f"svc:{svc}", type="Service", attrs={"name": svc}))
            kg.add_edge(Edge(src=f"incident:{incident_id}", dst=f"svc:{svc}", type="involves"))
        for a, b in derive_service_calls(span_list):
            kg.add_edge(Edge(src=f"svc:{a}", dst=f"svc:{b}", type="calls"))

    # --- Logs → LogEvent ---
    if logs_path:
        # used for openrca
        if logs_path.endswith(".csv"):
            log_events = iter_openrca_log(logs_path,window)
            for ev in log_events:
                t = to_aware_utc(ev.get("time"))

                svc = ev.get("service") or "unknown"
                if f"svc:{svc}" not in kg.G:
                    kg.add_node(Node(id=f"svc:{svc}", type="Service", attrs={"name": svc}))
                    kg.add_edge(Edge(src=f"incident:{incident_id}", dst=f"svc:{svc}", type="involves"))
                eid = f"log:{svc}:{t.isoformat() if t else 'na'}:{abs(hash(ev.get('message'))) % 100000}"
                kg.add_node(Node(
                    id=eid,
                    type="LogEvent",
                    attrs={
                        "service": svc,
                        "time": t.isoformat() if t else None,
                        "level": ev.get("level"),
                        "message": ev.get("message")
                    }
                ))
                kg.add_edge(Edge(src=f"svc:{svc}", dst=eid, type="has_log"))
        else:
            for ev in iter_log_events(logs_path):
                t = to_aware_utc(ev.get("time"))
                if (start and t and t < start) or (end and t and t > end):
                    continue
                svc = ev.get("service") or "unknown"
                if f"svc:{svc}" not in kg.G:
                    kg.add_node(Node(id=f"svc:{svc}", type="Service", attrs={"name": svc}))
                    kg.add_edge(Edge(src=f"incident:{incident_id}", dst=f"svc:{svc}", type="involves"))
                eid = f"log:{svc}:{t.isoformat() if t else 'na'}:{abs(hash(ev.get('message')))%100000}"
                kg.add_node(Node(
                    id=eid,
                    type="LogEvent",
                    attrs={
                        "service": svc,
                        "time": t.isoformat() if t else None,
                        "level": ev.get("level"),
                        "message": ev.get("message")
                    }
                ))
                kg.add_edge(Edge(src=f"svc:{svc}", dst=eid, type="has_log"))

    # --- Metrics → MetricEvent (anomalies only) ---
    rows_all: List[Dict[str, Any]] = []
    if metrics_path:
        # metrics process for openrca
        if metrics_path.endswith(".csv"):
            rows_all = iter_openrca_metrics(metrics_path,window)
            anomalies = detect_anomalies(rows_all,window)
            for an in anomalies:
                t = to_aware_utc(an.get("time"))
                if (start and t and t < start) or (end and t and t > end):
                    continue
                svc = an["service"]
                met = an["metric"]
                if f"svc:{svc}" not in kg.G:
                    kg.add_node(Node(id=f"svc:{svc}", type="Service", attrs={"name": svc}))
                    kg.add_edge(Edge(src=f"incident:{incident_id}", dst=f"svc:{svc}", type="involves"))
                mid = f"met:{svc}:{met}:{t.isoformat() if t else 'na'}"
                kg.add_node(Node(
                    id=mid,
                    type="MetricEvent",
                    attrs={
                        "service": svc,
                        "metric": met,
                        "time": t.isoformat() if t else None,
                        "value": an.get("value"),
                        "z": an.get("z")
                    }
                ))
                kg.add_edge(Edge(src=f"svc:{svc}", dst=mid, type="has_metric_anomaly"))
        else:
            rows_all = list(iter_metrics(metrics_path,sample=False))
            anomalies = detect_anomalies(rows_all)
            for an in anomalies:
                t = to_aware_utc(an.get("time"))
                if (start and t and t < start) or (end and t and t > end):
                    continue
                svc = an["service"]
                met = an["metric"]
                if f"svc:{svc}" not in kg.G:
                    kg.add_node(Node(id=f"svc:{svc}", type="Service", attrs={"name": svc}))
                    kg.add_edge(Edge(src=f"incident:{incident_id}", dst=f"svc:{svc}", type="involves"))
                mid = f"met:{svc}:{met}:{t.isoformat() if t else 'na'}"
                kg.add_node(Node(
                    id=mid,
                    type="MetricEvent",
                    attrs={
                        "service": svc,
                        "metric": met,
                        "time": t.isoformat() if t else None,
                        "value": an.get("value"),
                        "z": an.get("z")
                    }
                ))
                kg.add_edge(Edge(src=f"svc:{svc}", dst=mid, type="has_metric_anomaly"))

    # --- Causal Discovery ---
    if enable_causal and metrics_path:
        try:
            import pandas as pd
            df = metrics_to_dataframe(
                rows_all,
                start=start,
                end=end,
                resample_rule=resample_rule,
                fill="ffill",
            )
            if not df.empty and df.shape[1] >= 2:
                result = run_pc(df, alpha=pc_alpha, stable=True, verbose=False)

                # MetricVariable nodes
                for col in result['variables']:
                    svc, met = col.split('|', 1) if '|' in col else (col, 'value')
                    mvar_id = f"mvar:{svc}:{met}"
                    if mvar_id not in kg.G:
                        kg.add_node(Node(id=mvar_id, type="MetricVariable", attrs={"service": svc, "metric": met}))
                        if f"svc:{svc}" not in kg.G:
                            kg.add_node(Node(id=f"svc:{svc}", type="Service", attrs={"name": svc}))
                            kg.add_edge(Edge(src=f"incident:{incident_id}", dst=f"svc:{svc}", type="involves"))
                        kg.add_edge(Edge(src=f"svc:{svc}", dst=mvar_id, type="has_metric"))

                # Directed causal edges
                for a, b in result['directed']:
                    sa, ma = a.split('|', 1) if '|' in a else (a, 'value')
                    sb, mb = b.split('|', 1) if '|' in b else (b, 'value')
                    kg.add_edge(Edge(
                        src=f"mvar:{sa}:{ma}",
                        dst=f"mvar:{sb}:{mb}",
                        type="causes",
                        attrs={"method": "PC", "alpha": pc_alpha}
                    ))

                # Undirected adjacency edges
                for a, b in result['undirected']:
                    sa, ma = a.split('|', 1) if '|' in a else (a, 'value')
                    sb, mb = b.split('|', 1) if '|' in b else (b, 'value')
                    kg.add_edge(Edge(
                        src=f"mvar:{sa}:{ma}",
                        dst=f"mvar:{sb}:{mb}",
                        type="adjacent",
                        attrs={"method": "PC", "alpha": pc_alpha}
                    ))
        except Exception:
            import traceback
            traceback.print_exc()

    # --- Temporal precedence edges among events per service ---
    service_events: Dict[str, List[str]] = defaultdict(list)
    for nid, data in kg.G.nodes(data=True):
        if data.get("type") in ("LogEvent", "MetricEvent"):
            service_events[data.get("service")].append(nid)

    def get_time(nid):
        t = kg.G.nodes[nid].get("time")
        try:
            return to_aware_utc(datetime.fromisoformat(t)) if t else None
        except Exception:
            return None

    for svc, nids in service_events.items():
        nids = sorted(nids, key=lambda x: (get_time(x) or datetime.min.replace(tzinfo=None)))
        for i in range(len(nids) - 1):
            t0, t1 = get_time(nids[i]), get_time(nids[i + 1])
            if t0 and t1:
                kg.add_edge(Edge(
                    src=nids[i],
                    dst=nids[i + 1],
                    type="precedes",
                    attrs={"dt_seconds": (t1 - t0).total_seconds()}
                ))

    return kg


def minute_bucket(t_sec: int) -> int:
    """对齐到该分钟起始秒（例如 12:00:59 -> 12:00:00）。"""
    return (int(t_sec) // 60) * 60

def compute_calls_by_minute(
    span_list: List[Dict[str, Any]],
    start_ts: Optional[int],
    end_ts: Optional[int],
) -> Dict[int, Set[Tuple[str, str]]]:
    """
    从 spans 推出“带时间的调用事件”，并按分钟分桶：
      - 先按 trace_id 分组并按开始时间排序；
      - 在每个 trace 内，用相邻服务对 (sa -> sb) 近似一次调用，
        调用时间取下一个 span 的开始时间 t_child；
      - 仅保留时间位于 [start_ts, end_ts] 的事件；
      - 返回：{ minute_ts: { (sa, sb), ... }, ... }。
    约定：span 的时间字段（start/startTime/timestamp/time）已规范为“秒级整型”。
    """
    calls_by_min: DefaultDict[int, Set[Tuple[str, str]]] = defaultdict(set)

    # 若没有 trace_id，无法做相邻服务近似，返回空（调用方可采用保守策略）
    if not any(s.get("traceId") for s in span_list):
        return calls_by_min

    # 按 trace_id 分组，元素为 (t_sec, service)
    traces: DefaultDict[str, List[Tuple[int, str]]] = defaultdict(list)
    for s in span_list:
        tid = s.get("traceId")
        if not tid:
            continue
        # 已规范化为秒级整型：优先级 start > startTime > timestamp > time
        t = s.get("startTime")
        if t is None:
            continue
        # 秒级窗口过滤
        if start_ts is not None and t < start_ts:
            continue
        if end_ts is not None and t > end_ts:
            continue
        svc = s.get("service") or "unknown"
        traces[tid].append((int(t), svc))

    # 每个 trace 内按时间排序，取相邻服务对作为一次调用
    for tid, lst in traces.items():
        lst.sort(key=lambda x: x[0])  # (t_sec, svc)
        for i in range(len(lst) - 1):
            sa = lst[i][1]
            t_child, sb = lst[i + 1]
            if sa == sb:
                continue
            tf = minute_bucket(t_child)  # 调用发生时间按分钟分桶
            calls_by_min[tf].add((sa, sb))

    return calls_by_min

def tkg_from_openrca(
    traces_path: Optional[str],
    logs_path: Optional[str],
    metrics_path: Optional[str],
    incident_id: Optional[str],
    window: Optional[Dict[str, Any]],
    anomalies_only: bool = True,
    add_precedes: bool = True,
) -> List[Tuple[int, KnowledgeGraph]]:
    """
    基于 openrca 的 CSV 输入，按“分钟”切片，返回 [(minute_ts, KG_该分钟), ...]（按时间升序）。
    - 严格用秒级窗口过滤：start_ts <= t_sec <= end_ts
    - 对通过过滤的事件做分钟分桶
    - 每个分钟生成独立 KnowledgeGraph；所有节点/边均用你的 Node/Edge 类
    - calls 来源：derive_service_calls(span_list)（不依赖 span_id/parent_id）
    - precedes 仅在“同一分钟”内串联同一服务的多个事件，避免跨分钟悬空节点
    """
    inc = incident_id or "incident"
    start_ts = window.get("start") if window and "start" in window else None
    end_ts   = window.get("end")   if window and "end" in window   else None

    # 分桶容器
    minute_svcs: DefaultDict[int, Set[str]] = defaultdict(set)        # 该分钟出现过的服务
    minute_logs: DefaultDict[int, List[Dict[str, Any]]] = defaultdict(list)      # 该分钟的日志事件
    minute_mets: DefaultDict[int, List[Dict[str, Any]]] = defaultdict(list)      # 该分钟的指标异常事件

    # ========== 1) Traces：收集服务与 calls ==========
    span_list: List[Dict[str, Any]] = []
    call_pairs: Set[Tuple[str, str]] = set()

    if traces_path and traces_path.endswith(".csv"):
        span_list = list(iter_openrca_spans(traces_path, window))
        # 服务出现的时间：从常见字段里兜底取时间
        for sp in span_list:
            svc = sp.get("service") or "unknown"
            t_raw = sp.get("start") or sp.get("startTime") or sp.get("timestamp") or sp.get("time")
            t_sec = t_raw
            if t_sec is None:
                continue
            if start_ts is not None and t_sec < start_ts:
                continue
            if end_ts is not None and t_sec > end_ts:
                continue
            tf = minute_bucket(t_sec)
            minute_svcs[tf].add(svc)

        # calls：与 build_knowledge_graph 相同的来源
        for a, b in derive_service_calls(span_list):
            if a and b and a != b:
                call_pairs.add((a, b))

    calls_by_minute = compute_calls_by_minute(span_list, start_ts, end_ts)

    # ========== 2) Logs：事件 + 服务记名 ==========
    if logs_path and logs_path.endswith(".csv"):
        for ev in iter_openrca_log(logs_path, window):
            svc = ev.get("service") or "unknown"
            t_sec = ev.get("time")
            if t_sec is None:
                continue
            if start_ts is not None and t_sec < start_ts:
                continue
            if end_ts is not None and t_sec > end_ts:
                continue
            tf = minute_bucket(t_sec)
            minute_svcs[tf].add(svc)
            # 规范化事件结构（ID 用秒级避免 isoformat 混型）
            ev_norm = {
                "id": f"log:{svc}:{t_sec}:{abs(hash(ev.get('message'))) % 100000}",
                "service": svc,
                "time_sec": t_sec,
                "level": ev.get("level"),
                "message": ev.get("message"),
                "type": "LogEvent",
            }
            minute_logs[tf].append(ev_norm)

    # ========== 3) Metrics：默认只取异常；事件 + 服务记名 ==========
    if metrics_path and metrics_path.endswith(".csv"):
        rows = list(iter_openrca_metrics(metrics_path, window))
        rows_iter, top_info = detect_anomalies(rows, window)
        for an in rows_iter:
            svc = an.get("service") or "unknown"
            met = an.get("metric") or "value"
            t_sec = an.get("time")
            if t_sec is None:
                continue
            if start_ts is not None and t_sec < start_ts:
                continue
            if end_ts is not None and t_sec > end_ts:
                continue
            tf = minute_bucket(t_sec)
            minute_svcs[tf].add(svc)
            an_norm = {
                "id": f"met:{svc}:{met}:{t_sec}",
                "service": svc,
                "metric": met,
                "time_sec": t_sec,
                "value": an.get("value"),
                "z": an.get("z"),
                "type": "MetricEvent",
            }
            minute_mets[tf].append(an_norm)

    # ========== 4) 生成每分钟的 KnowledgeGraph ==========
    all_minutes = sorted(set(minute_svcs.keys()) |
                         set(minute_logs.keys()) |
                         set(minute_mets.keys()))

    results: List[Tuple[int, KnowledgeGraph]] = []

    for tf in all_minutes:
        kg = KnowledgeGraph()
        # 给图设置元数据（可选）
        kg.G.graph["minute_ts"] = tf
        kg.G.graph["incident"] = inc

        # 4.1 事件：Log / Metric —— 节点 + 边
        # 先把所有服务记名，顺便建服务节点
        for svc in minute_svcs.get(tf, set()):
            kg.add_node(Node(id=f"svc:{svc}", type="Service", attrs={"name": svc}))
        # 日志事件
        for ev in minute_logs.get(tf, []):
            svc = ev["service"]
            kg.add_node(Node(
                id=ev["id"],
                type="LogEvent",
                attrs={
                    "service": svc,
                    "time_sec": ev["time_sec"],
                    "level": ev.get("level"),
                    "message": ev.get("message"),
                }
            ))
            kg.add_edge(Edge(src=f"svc:{svc}", dst=ev["id"], type="has_log"))
        # 指标异常事件
        for an in minute_mets.get(tf, []):
            svc = an["service"]
            kg.add_node(Node(
                id=an["id"],
                type="MetricEvent",
                attrs={
                    "service": svc,
                    "metric": an["metric"],
                    "time_sec": an["time_sec"],
                    "value": an.get("value"),
                    "z": an.get("z"),
                }
            ))
            kg.add_edge(Edge(src=f"svc:{svc}", dst=an["id"], type="has_metric_anomaly"))

        # 4.2 incident 节点 + involves（仅该分钟出现的服务）
        kg.add_node(Node(id=f"incident:{inc}", type="Incident", attrs={"id": inc}))
        for svc in minute_svcs.get(tf, set()):
            kg.add_edge(Edge(src=f"incident:{inc}", dst=f"svc:{svc}", type="involves"))

        # 4.3 calls（仅当该分钟 a、b 都出现时）
        pairs_this_min = calls_by_minute.get(tf, set())
        for a, b in pairs_this_min:
            # 保险起见：若本分钟未先建过服务节点，则补建
            if f"svc:{a}" not in kg.G:
                kg.add_node(Node(id=f"svc:{a}", type="Service", attrs={"name": a}))
            if f"svc:{b}" not in kg.G:
                kg.add_node(Node(id=f"svc:{b}", type="Service", attrs={"name": b}))
            kg.add_edge(Edge(src=f"svc:{a}", dst=f"svc:{b}", type="calls"))

        # 4.4 precedes（同一分钟内，同一服务多事件按 time_sec 串联）
        if add_precedes:
            # 聚合该分钟内每个服务的事件（log+metric），按 time_sec 排序
            per_svc_events: DefaultDict[str, List[str]] = defaultdict(list)
            # 事件节点已存在，不需要再建
            for ev in minute_logs.get(tf, []):
                per_svc_events[ev["service"]].append(ev["id"])
            for an in minute_mets.get(tf, []):
                per_svc_events[an["service"]].append(an["id"])
            for svc, ids in per_svc_events.items():
                # 按 time_sec 排序：先取 (id -> time_sec) 映射
                id2t = {}
                for ev in minute_logs.get(tf, []):
                    if ev["service"] == svc:
                        id2t[ev["id"]] = ev["time_sec"]
                for an in minute_mets.get(tf, []):
                    if an["service"] == svc:
                        id2t[an["id"]] = an["time_sec"]
                ids_sorted = sorted(ids, key=lambda x: id2t.get(x, 0))
                for i in range(len(ids_sorted) - 1):
                    kg.add_edge(Edge(src=ids_sorted[i], dst=ids_sorted[i+1], type="precedes"))

        results.append((tf, kg))

    return results, top_info