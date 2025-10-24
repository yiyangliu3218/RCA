from __future__ import annotations
from datetime import datetime, timezone, timedelta
import re

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


def parse_opencra_timestamp(ts_str: str | None) -> datetime | None:
    if not ts_str:
        return None

    try:
        unix_ts = int(ts_str)

        utc_dt = datetime.fromtimestamp(unix_ts, timezone.utc)

        correct_utc_dt = utc_dt + timedelta(hours=8)

        return correct_utc_dt
    except (ValueError, TypeError):
        return None

def extract_and_convert_datetime(text):
    date_patterns = [
        r'(\w+\s+\d{1,2},\s+\d{4})',  # March 4, 2021
        r'(\d{4}-\d{2}-\d{2})',  # 2021-03-04
        r'(\d{2}/\d{2}/\d{4})',  # 03/04/2021
    ]

    time_pattern = r'(?:between\s+)?(\d{1,2}:\d{2})\s*(?:to|and|-)\s*(\d{1,2}:\d{2})'

    extracted_date = None
    start_time = None
    end_time = None

    for pattern in date_patterns:
        date_match = re.search(pattern, text)
        if date_match:
            extracted_date = date_match.group(1)
            break

    time_match = re.search(time_pattern, text)
    if time_match:
        start_time = time_match.group(1)
        end_time = time_match.group(2)

    if not extracted_date or not start_time or not end_time:
        return None

    try:
        tz_utc8 = timezone(timedelta(hours=8))

        if ',' in extracted_date:
            date_obj = datetime.strptime(extracted_date, "%B %d, %Y")
        elif '-' in extracted_date:
            date_obj = datetime.strptime(extracted_date, "%Y-%m-%d")
        elif '/' in extracted_date:
            date_obj = datetime.strptime(extracted_date, "%m/%d/%Y")

        formatted_date = date_obj.strftime("%Y_%m_%d")

        start_datetime = datetime.strptime(
            f"{date_obj.strftime('%Y-%m-%d')} {start_time}",
            "%Y-%m-%d %H:%M"
        ).replace(tzinfo=tz_utc8)

        end_datetime = datetime.strptime(
            f"{date_obj.strftime('%Y-%m-%d')} {end_time}",
            "%Y-%m-%d %H:%M"
        ).replace(tzinfo=tz_utc8)

        start_timestamp = int(start_datetime.timestamp())
        end_timestamp = int(end_datetime.timestamp())

        return {
            'formatted_date': formatted_date,
            'start_timestamp': start_timestamp,
            'end_timestamp': end_timestamp,
        }

    except Exception as e:
        print(f"Error: {e}")
        return None