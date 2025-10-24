import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timezone
import tiktoken
from openai import OpenAI, RateLimitError

MODEL_NAME = "gpt-5-mini"
MAX_TOKENS = 1000
MAX_RETRY = 5
ENCODING = "o200k_base"
SPAN_SECONDS = 5 * 60
HALF_SPAN = SPAN_SECONDS // 2
MAX_FILE_CHARS = 18000
TZ_OFFSET_SECONDS = 8*3600

OPENAI_API_KEY = ''

INITIAL_AGENT_PROMPT = """
You are an experienced SRE assisting Root Cause Analysis (RCA) for a microservice incident.

Context:
- Seed anomaly (top_info): {top_info}
- Evidence windows (5-minute window centered at {center_ts}): JSON below contains one or more per-minute bundles, each including trimmed graph CSV previews and (optional) graphml/text.
- IMPORTANT: Use the evidence as primary signals. Be concise and precise. Do not invent services/files.

Evidence (JSON):
{window_json}

Task:
1) Provide an analysis summary for the window (what's going on, which services show anomalies/signals, how they relate).
2) Provide a suspect list with confidence scores in [0,1].
3) Decide action:
   - "continue": we will analyze another 5-minute window centered at next_center_ts (Unix seconds). Choose a minute center that helps you validate or refute your current hypothesis.
   - "stop": you are confident to finish now (next_center_ts=null).
4) Return STRICT JSON (no extra text, no markdown). Schema:

{{
  "action": "continue" | "stop",
  "next_center_ts": <int or null>,
  "analysis": {{
    "focus_service": "<service id or ''>",
    "window": {{"start": {start_ts}, "end": {end_ts}}},
    "observations": ["<bullet 1>", "<bullet 2>", "..."],
    "suspects": [
      {{"service": "<svc>", "score": 0.0, "reason": "<short reason>"}},
      ...
    ],
    "evidence": [
      {{"type": "nodes_trim_csv", "minute_ts": <int>, "lines": <int>}},
      {{"type": "edges_trim_csv", "minute_ts": <int>, "lines": <int>}},
      {{"type": "graphml_text",  "minute_ts": <int>, "chars": <int>}}
    ],
    "confidence": 0.0
  }}
}}
"""

LOOP_AGENT_PROMPT = """
You are continuing Root Cause Analysis (RCA) for a microservice incident.

Context:
- Previous analyses (analysis_list): JSON array where each item is the prior "analysis" object.
- Current 5-minute window, centered at {center_ts}, provided as JSON evidence.

Previous analyses:
{analysis_list_json}

Evidence (JSON):
{window_json}

Task:
1) Integrate the new evidence with analysis_list. Provide updated observations and suspects.
2) Decide action:
   - "continue": choose next_center_ts (Unix seconds) for the next 5-minute window to inspect;
   - "stop": confident to finish (next_center_ts=null).
3) Return STRICT JSON (no extra text). Schema:

{{
  "action": "continue" | "stop",
  "next_center_ts": <int or null>,
  "analysis": {{
    "focus_service": "<service id or ''>",
    "window": {{"start": {start_ts}, "end": {end_ts}}},
    "observations": ["<bullet 1>", "<bullet 2>", "..."],
    "suspects": [
      {{"service": "<svc>", "score": 0.0, "reason": "<short reason>"}},
      ...
    ],
    "evidence": [
      {{"type": "nodes_trim_csv", "minute_ts": <int>, "lines": <int>}},
      {{"type": "edges_trim_csv", "minute_ts": <int>, "lines": <int>}},
      {{"type": "graphml_text",  "minute_ts": <int>, "chars": <int>}}
    ],
    "confidence": 0.0
  }}
}}
"""



def get_openai_json(messages: List[Dict[str, Any]], api_key: str, max_tokens: int = MAX_TOKENS) -> Dict[str, Any]:
    enc = tiktoken.get_encoding(ENCODING)
    try:
        serialized = json.dumps(messages, ensure_ascii=False)
        approx_in_tokens = len(enc.encode(serialized))
    except Exception:
        approx_in_tokens = 0

    client = OpenAI(api_key=api_key)
    for attempt in range(MAX_RETRY):
        try:
            resp = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content.strip()
            return json.loads(content)
        except RateLimitError:
            if attempt < MAX_RETRY - 1:
                time.sleep(2 * (attempt + 1) ** 2)
                continue
            raise
        except json.JSONDecodeError:

            if attempt < MAX_RETRY - 1:
                max_tokens = int(max_tokens * 1.5)
                continue
            raise
    return {}



def floor_to_minute(ts: int) -> int:
    return (int(ts) // 60) * 60

def ts_to_dirs(ts: int, tz_offset_seconds: int = TZ_OFFSET_SECONDS) -> Tuple[str, str]:

    dt = datetime.fromtimestamp(ts + tz_offset_seconds, tz=timezone.utc)
    date_dir = dt.strftime("%Y_%m_%d")
    time_dir = dt.strftime("%H-%M-00")  # 按分钟对齐，秒固定 00
    return date_dir, time_dir

def minute_dirs_in_window(center_ts: int, half_span: int = HALF_SPAN, tz_offset_seconds: int = TZ_OFFSET_SECONDS) -> List[Tuple[int, str, str]]:

    start_ts = center_ts - half_span
    end_ts = center_ts + half_span
    mins = []
    m = floor_to_minute(start_ts)
    while m <= end_ts:
        d, t = ts_to_dirs(m, tz_offset_seconds)
        mins.append((m, d, t))
        m += 60
    return mins



def read_text_if_exists(path: Path, max_chars: int = MAX_FILE_CHARS) -> Tuple[str, int]:
    if not path.exists() or not path.is_file():
        return "", 0
    try:
        txt = path.read_text(encoding="utf-8", errors="replace")
        if len(txt) > max_chars:
            return txt[:max_chars], max_chars
        return txt, len(txt)
    except Exception:
        return "", 0



def gather_window_context(
    base_dir: str,
    dataset: str,
    incident_id: str,
    center_ts: int,
    tz_offset_seconds: int = TZ_OFFSET_SECONDS
) -> Dict[str, Any]:

    bundles: List[Dict[str, Any]] = []
    for minute_ts, date_dir, time_dir in minute_dirs_in_window(center_ts, HALF_SPAN, tz_offset_seconds):
        root = Path(base_dir) / dataset / date_dir / time_dir

        nodes_trim = root / f"{incident_id}.nodes.trim.csv"
        edges_trim = root / f"{incident_id}.edges.trim.csv"

        nodes_full = root / f"{incident_id}.nodes.csv"
        edges_full = root / f"{incident_id}.edges.csv"

        graphml = root / f"{incident_id}.graphml"
        summary = root / f"{incident_id}.summary.txt"

        nodes_text, nodes_len = ("", 0)
        edges_text, edges_len = ("", 0)

        if nodes_trim.exists():
            nodes_text, nodes_len = read_text_if_exists(nodes_trim)
        elif nodes_full.exists():
            nodes_text, nodes_len = read_text_if_exists(nodes_full)

        if edges_trim.exists():
            edges_text, edges_len = read_text_if_exists(edges_trim)
        elif edges_full.exists():
            edges_text, edges_len = read_text_if_exists(edges_full)

        graphml_text, graphml_chars = read_text_if_exists(graphml)
        summary_text, _ = read_text_if_exists(summary, max_chars=6000)

        if nodes_len == 0 and edges_len == 0 and graphml_chars == 0 and not summary_text:
            continue

        bundles.append({
            "minute_ts": minute_ts,
            "paths": {
                "nodes_trim": str(nodes_trim),
                "edges_trim": str(edges_trim),
                "nodes_full": str(nodes_full),
                "edges_full": str(edges_full),
                "graphml": str(graphml),
                "summary": str(summary),
            },
            "previews": {
                "nodes_trim_or_full": {"chars": nodes_len, "text": nodes_text},
                "edges_trim_or_full": {"chars": edges_len, "text": edges_text},
                "graphml_text": {"chars": graphml_chars, "text": graphml_text},
                "summary_text": summary_text,
            }
        })

    return {
        "center_ts": center_ts,
        "bundles": bundles
    }



def run_rca_session(
    base_dir: str,
    dataset: str,
    incident_id: str,
    top_info: Dict[str, Any],
    api_key: str,
    out_dir: str = "outputs/rca_runs",
    max_iters: int = 6,
    tz_offset_seconds: int = TZ_OFFSET_SECONDS
) -> Path:

    assert "time" in top_info and isinstance(top_info["time"], int), "top_info['time'] (int seconds) is required"
    run_root = Path(out_dir) / incident_id / f"run_{floor_to_minute(top_info['time'])}"
    run_root.mkdir(parents=True, exist_ok=True)

    # Step 0: Initial
    center_ts = top_info["time"]
    win0 = gather_window_context(base_dir, dataset, incident_id, center_ts, tz_offset_seconds)
    start_ts = center_ts - HALF_SPAN
    end_ts = center_ts + HALF_SPAN

    messages = [
        {
            "role": "system",
            "content": INITIAL_AGENT_PROMPT.format(
                top_info=json.dumps(top_info, ensure_ascii=False),
                center_ts=center_ts,
                window_json=json.dumps(win0, ensure_ascii=False, indent=2),
                start_ts=start_ts,
                end_ts=end_ts
            ),
        },
        {"role": "user", "content": "Return STRICT JSON only. No extra text."},
    ]
    step0 = get_openai_json(messages, api_key)
    (run_root / "step_000_init.json").write_text(json.dumps(step0, ensure_ascii=False, indent=2))

    analysis_list: List[Dict[str, Any]] = []
    if isinstance(step0.get("analysis"), dict):
        analysis_list.append(step0["analysis"])

    action = step0.get("action", "stop")
    next_center_ts = step0.get("next_center_ts")

    # Loop
    step_idx = 1
    while action == "continue" and isinstance(next_center_ts, int) and step_idx <= max_iters:
        win = gather_window_context(base_dir, dataset, incident_id, next_center_ts, tz_offset_seconds)
        start_ts = next_center_ts - HALF_SPAN
        end_ts = next_center_ts + HALF_SPAN

        messages = [
            {
                "role": "system",
                "content": LOOP_AGENT_PROMPT.format(
                    center_ts=next_center_ts,
                    analysis_list_json=json.dumps(analysis_list, ensure_ascii=False, indent=2),
                    window_json=json.dumps(win, ensure_ascii=False, indent=2),
                    start_ts=start_ts,
                    end_ts=end_ts,
                ),
            },
            {"role": "user", "content": "Return STRICT JSON only. No extra text."},
        ]
        step = get_openai_json(messages, api_key)
        (run_root / f"step_{step_idx:03d}_loop.json").write_text(json.dumps(step, ensure_ascii=False, indent=2))

        if isinstance(step.get("analysis"), dict):
            analysis_list.append(step["analysis"])
        action = step.get("action", "stop")
        next_center_ts = step.get("next_center_ts")
        step_idx += 1

    final_payload = {
        "top_info": top_info,
        "iterations": step_idx - 1,
        "last_action": action,
        "last_center_ts": next_center_ts if isinstance(next_center_ts, int) else None,
        "all_analyses": analysis_list,
        "final_suspects": analysis_list[-1].get("suspects", []) if analysis_list else []
    }
    (run_root / "final_summary.json").write_text(json.dumps(final_payload, ensure_ascii=False, indent=2))
    return run_root



def controller_loop(output_dir,base_dir,top_info):

    DATASET = "Bank"
    INCIDENT_ID = "openrca_1"

    api_key = OPENAI_API_KEY
    if not api_key:
        raise RuntimeError("Please set OPENAI_API_KEY environment variable or fill api_key.")

    run_dir = run_rca_session(
        base_dir=base_dir,
        dataset=DATASET,
        incident_id=INCIDENT_ID,
        top_info=top_info,
        api_key=api_key,
        out_dir="output_dir",
        max_iters=3,
        tz_offset_seconds=8*3600
    )
    print(f"[RCA finished] saved to: {run_dir.as_posix()}")

if __name__ == "__main__":
    """
    使用示例：
    1) 先确保 base_dir/dataset/date/time 下存在你的 per-minute 产物（图构建阶段已导出了 CSV/GraphML）
    2) 准备 top_info，比如 detect_anomalies 返回的 z 最大项：{"service":"svc:payments","time":1693561200,"abs_z":5.2}
    3) 设置 OPENAI_API_KEY 环境变量或直接填入
    4) 运行后在 outputs/rca_runs/{incident_id}/run_{minute_ts}/ 下查看每步 JSON 与 final_summary.json
    """

    # —— 基本参数（请按你的目录与数据修改）——
    BASE_DIR = "outputs"            # 你的图产物根目录
    DATASET = "Bank"                # 数据集名（第二层目录）
    INCIDENT_ID = "openrca_1"       # 事故ID（文件前缀）
    TOP_INFO = {
        "service": 'Redis02',
        "time": 1614852840,         # 秒级 Unix 时间（示例），用你的 detect_anomalies 的 top_info["time"]
        "abs_z": 10069.963269857832
    }

    api_key = OPENAI_API_KEY
    if not api_key:
        raise RuntimeError("Please set OPENAI_API_KEY environment variable or fill api_key.")

    run_dir = run_rca_session(
        base_dir=BASE_DIR,
        dataset=DATASET,
        incident_id=INCIDENT_ID,
        top_info=TOP_INFO,
        api_key=api_key,
        out_dir="outputs/rca_runs",
        max_iters=3,
        tz_offset_seconds=TZ_OFFSET_SECONDS,   # 若你的分钟目录是 UTC+8，可以设置为 8*3600
    )
    print(f"[RCA finished] saved to: {run_dir.as_posix()}")
