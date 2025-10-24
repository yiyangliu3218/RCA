from typing import Iterable, Dict, Any
from datetime import datetime
import json, re
from ..timeutil import parse_any_ts_utc, to_aware_utc, parse_opencra_timestamp
import csv
import pandas as pd

_TS_KEYS = ["timestamp","time","ts","@timestamp"]
_SVC_KEYS = ["service","service_name","svc","component"]
_LVL_KEYS = ["level","severity","lvl"]
_MSG_KEYS = ["message","msg","log","text"]

def _parse_time(s: str):
    return parse_any_ts_utc(s)

def iter_log_events(path: str) -> Iterable[Dict[str,Any]]:
    """
    Yields dicts with keys: time (UTC-aware), service, level, message, raw
    Supports JSONL or plaintext: "2025-08-14T11:06:00Z ERROR frontend HTTP 500 ..."
    """

    if path.endswith('.csv'):
        with open(path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 转换 Unix 时间戳为 datetime 对象
                dt = parse_opencra_timestamp(row.get("timestamp"))

                # 尝试从日志内容推断级别
                level = infer_log_level(row["value"])

                yield {
                    "time": dt,
                    "service": row["cmdb_id"],
                    "level": level,
                    "message": f"{row['log_name']}: {row['value']}",
                    "raw": row,
                }

    elif path.endswith(".jsonl"):
        with open(path, "r") as f:
            for line in f:
                line=line.strip()
                if not line:
                    continue

                obj=None
                if line.startswith("{") and line.endswith("}"):
                    try:
                        obj=json.loads(line)
                    except Exception:
                        obj=None
                if obj is None:
                    m=re.match(r"^(?P<ts>\S+)\s+(?P<level>[A-Z]+)\s+(?P<service>[\w\-]+)\s+(?P<message>.*)$", line)
                    if m:
                        d=m.groupdict()
                        yield {
                            "time": _parse_time(d["ts"]),
                            "service": d["service"],
                            "level": d["level"],
                            "message": d["message"],
                            "raw": line,
                        }
                    continue

                # normalize JSONL
                ts=next((obj[k] for k in _TS_KEYS if k in obj), None)
                svc=next((obj[k] for k in _SVC_KEYS if k in obj), None)
                lvl=next((obj[k] for k in _LVL_KEYS if k in obj), None)
                msg=next((obj[k] for k in _MSG_KEYS if k in obj), None)
                yield {
                    "time": _parse_time(ts),
                    "service": str(svc) if svc else None,
                    "level": str(lvl) if lvl else None,
                    "message": str(msg) if msg else None,
                    "raw": obj,
                }

def iter_openrca_log(path, window):
    df = pd.read_csv(path)
    log_df = df[(df['timestamp'] >= window.get("start")) &
                  (df['timestamp'] <= window.get("end"))]

    records = log_df.to_dict("records")

    log_list = [
        {
            "time": row["timestamp"],
            "service": row["cmdb_id"],
            "level": infer_log_level(row["value"]),
            "message": f"{row['log_name']}: {row['value']}",
            "raw": row,
        }
        for row in records
    ]
    return log_list


def infer_log_level(log_message: str) -> str:
    message = log_message.lower()
    if any(word in message for word in ["error", "exception", "fail", "critical"]):
        return "ERROR"
    elif any(word in message for word in ["warn", "alert", "notice"]):
        return "WARN"
    else:
        return "UNKNOWN"
