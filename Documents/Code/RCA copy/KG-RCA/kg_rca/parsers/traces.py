from typing import Iterable, Dict, Any, List
from datetime import datetime
import json
from ..timeutil import to_aware_utc, parse_any_ts_utc

def _parse_time(ts):
    # Jaeger often uses epoch millis; handle that, else delegate to ISO parser
    try:
        ts_int = int(ts)
        if ts_int > 10_000_000_000:  # milliseconds
            return to_aware_utc(datetime.fromtimestamp(ts_int/1000.0))
        return to_aware_utc(datetime.fromtimestamp(ts_int))
    except Exception:
        return parse_any_ts_utc(ts)

def iter_spans(path: str) -> Iterable[Dict[str,Any]]:
    with open(path, "r") as f:
        data = json.load(f)
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
        for tr in data["data"]:
            procmap = {p.get("id"): p for p in tr.get("processes",[])}
            for sp in tr.get("spans", []):
                pid = sp.get("processID") or sp.get("processId")
                proc = procmap.get(pid, {})
                yield {
                    "traceId": sp.get("traceID") or sp.get("traceId"),
                    "spanId": sp.get("spanID") or sp.get("spanId"),
                    "parentSpanId": next((r.get("spanID") or r.get("spanId") or r.get("parentSpanId")
                                          for r in sp.get("references") or []
                                          if (r.get("refType") in ("CHILD_OF","FOLLOWS_FROM")
                                              or r.get("type") in ("CHILD_OF","FOLLOWS_FROM"))), None),
                    "service": proc.get("serviceName") or proc.get("service") or sp.get("service"),
                    "operation": sp.get("operationName") or sp.get("name"),
                    "startTime": _parse_time(sp.get("startTime") or sp.get("timestamp")),
                    "duration": sp.get("duration"),
                }
    elif isinstance(data, list):
        for sp in data:
            yield {
                "traceId": sp.get("traceID") or sp.get("traceId"),
                "spanId": sp.get("spanID") or sp.get("spanId"),
                "parentSpanId": sp.get("parentSpanId"),
                "service": sp.get("service") or sp.get("serviceName"),
                "operation": sp.get("operationName") or sp.get("name"),
                "startTime": _parse_time(sp.get("startTime") or sp.get("timestamp")),
                "duration": sp.get("duration"),
            }

def derive_service_calls(spans: List[Dict[str,Any]]):
    by_id = {s["spanId"]: s for s in spans if s.get("spanId")}
    calls = set()
    for sp in spans:
        parent_id = sp.get("parentSpanId")
        if not parent_id:
            continue
        parent = by_id.get(parent_id)
        if not parent:
            continue
        s_from = parent.get("service"); s_to = sp.get("service")
        if s_from and s_to and s_from != s_to:
            calls.add((s_from, s_to))
    return sorted(list(calls))
