from typing import Iterable, Dict, Any
from datetime import datetime
import json, re
from ..timeutil import parse_any_ts_utc, to_aware_utc

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
