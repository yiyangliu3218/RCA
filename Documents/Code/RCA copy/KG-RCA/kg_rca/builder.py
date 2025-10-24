from typing import Optional, Dict, Any, List
from datetime import datetime
from collections import defaultdict

from .graph import KnowledgeGraph, Node, Edge
from .parsers.logs import iter_log_events
from .parsers.metrics import iter_metrics, detect_anomalies, load_metrics_rows
from .parsers.traces import iter_spans, derive_service_calls
from .causal import metrics_to_dataframe, run_pc
from .timeutil import parse_any_ts_utc, to_aware_utc


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
        rows_all = list(iter_metrics(metrics_path))
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
