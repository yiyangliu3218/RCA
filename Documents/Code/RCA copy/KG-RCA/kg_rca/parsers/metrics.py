from typing import Iterable, Dict, Any, List
from datetime import datetime
import csv, math, statistics
from ..timeutil import parse_any_ts_utc

def _parse_time(s: str):
    return parse_any_ts_utc(s)

def iter_metrics(path: str) -> Iterable[Dict[str,Any]]:
    """
    CSV header: time,service,metric,value
    Yields dicts with time (UTC-aware), service, metric, value
    """
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            t = _parse_time(row.get("time",""))
            svc = row.get("service","")
            met = row.get("metric","")
            try:
                val = float(row.get("value","nan"))
            except:
                val = float("nan")
            yield {"time": t, "service": svc, "metric": met, "value": val}

def load_metrics_rows(path: str) -> List[Dict[str,Any]]:
    return list(iter_metrics(path))

def detect_anomalies(rows: List[Dict[str,Any]], z_thresh: float = 2.0):
    """
    Group by (service, metric) and flag points with |z|>=z_thresh using population stdev.
    """
    from collections import defaultdict
    groups = defaultdict(list)
    for r in rows:
        if r["time"] is None or r["service"]=="" or r["metric"]=="":
            continue
        groups[(r["service"], r["metric"])].append(r)

    anomalies = []
    for (svc, met), lst in groups.items():
        lst = sorted(lst, key=lambda x: x["time"])
        vals = [x["value"] for x in lst if math.isfinite(x["value"])]
        if len(vals) < 5:
            continue
        mean = sum(vals)/len(vals)
        # population stdev
        stdev = (sum((v-mean)**2 for v in vals)/len(vals))**0.5 or 1.0
        for x in lst:
            v = x["value"]
            if not math.isfinite(v):
                continue
            z = (v - mean) / stdev
            if abs(z) >= z_thresh:
                anomalies.append({
                    "time": x["time"], "service": svc, "metric": met, "value": v, "z": z
                })
    return anomalies
