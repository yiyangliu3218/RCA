from __future__ import annotations
from datetime import datetime, timezone

def to_aware_utc(dt: datetime | None) -> datetime | None:
    """Return a UTC-aware datetime (or None). Naive → UTC; Aware → converted to UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def parse_any_ts_utc(s: str | None) -> datetime | None:
    """Parse many timestamp shapes into a UTC-aware datetime."""
    if not s:
        return None
    s = str(s).strip()
    # Common ISO / RFC3339 handling
    try:
        # Normalize trailing Z to +00:00 for fromisoformat
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return to_aware_utc(datetime.fromisoformat(s))
    except Exception:
        pass
    # Fallbacks: add more formats as you encounter them
    for fmt in ("%Y-%m-%d %H:%M:%S",):
        try:
            return to_aware_utc(datetime.strptime(s, fmt))
        except Exception:
            pass
    return None
