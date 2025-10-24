from typing import Iterable, Dict, Any, List
from datetime import datetime
from collections import defaultdict
import csv, math, statistics
from ..timeutil import parse_any_ts_utc, parse_opencra_timestamp
import pandas as pd

def _parse_time(s: str):
    return parse_any_ts_utc(s)

def iter_metrics(path: str, sample) -> Iterable[Dict[str,Any]]:
    """
    CSV header: time,service,metric,value
    Yields dicts with time (UTC-aware), service, metric, value
    """
    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:  # 缩进修正：for 循环应在 with 块内
            try:
                utc_dt = parse_opencra_timestamp(int(row['timestamp']))
                yield {
                    "time": utc_dt,
                    "service": row['cmdb_id'],
                    "metric": row['kpi_name'],
                    "value": float(row['value'])
                }
            except Exception as e:
                continue

def load_metrics_rows(path: str) -> List[Dict[str,Any]]:
    return list(iter_metrics(path))

def detect_anomalies(
    rows: List[Dict[str, Any]],
    window: Dict[str, Any],
    z_thresh: float = 3.0,
    baseline_hours: int = 3
):
    """
    Detect anomalies based on z-score.
    Baseline stats are computed from data within (window.start - baseline_hours, window.start).
    Input timestamps are assumed to be Unix seconds.
    """
    start_ts = int(window.get("start")) if window and window.get("start") else None
    end_ts = int(window.get("end")) if window and window.get("start") else None
    if start_ts is None:
        raise ValueError("window['start'] must be provided as a unix timestamp (seconds).")

    baseline_start = start_ts - baseline_hours * 3600
    baseline_end   = start_ts

    # split rows into baseline vs target
    groups_baseline = defaultdict(list)
    groups_target   = defaultdict(list)

    for r in rows:
        t = r.get("time")
        svc = r.get("service", "")
        met = r.get("metric", "")
        val = r.get("value")

        if t is None or svc == "" or met == "":
            continue

        if baseline_start <= t < baseline_end:
            groups_baseline[(svc, met)].append(val)
        elif start_ts<= t <= end_ts:
            groups_target[(svc, met)].append(r)

    anomalies = []

    max_abs_z: float = 0
    max_service: Any = None
    max_time: Any = None

    for key, vals in groups_baseline.items():
        if len(vals) < 5:
            continue
        mean = sum(vals) / len(vals)
        stdev = (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5 or 1.0

        # check anomalies only in target window
        for r in groups_target.get(key, []):
            v = r["value"]
            if not math.isfinite(v):
                continue
            z = (v - mean) / stdev
            if abs(z) >= z_thresh:
                anomalies.append({
                    "time": r["time"],
                    "service": key[0],
                    "metric": key[1],
                    "value": v,
                    "z": z
                })

            if abs(z) > max_abs_z:
                max_abs_z = abs(z)
                max_service = key[0]
                max_time = r["time"]

        top_info = {
            "service": max_service if max_service is not None else None,
            "time": max_time if max_time is not None else None,
            "z": max_abs_z if max_service is not None else None,
        }

    return anomalies, top_info




def iter_openrca_metrics(path,window):
    df = pd.read_csv(path)
    # metrics_df = df[(df['timestamp'] >= window.get("start")) &
    #             (df['timestamp'] <= window.get("end"))]



    records = df.to_dict("records")

    metrics_list = [
        {
            "time": row["timestamp"],
            "service": row['cmdb_id'],
            "metric": row['kpi_name'],
            "value": float(row['value'])
        }
        for row in records
    ]
    return metrics_list
