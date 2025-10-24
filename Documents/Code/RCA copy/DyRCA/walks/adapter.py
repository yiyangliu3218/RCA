from __future__ import annotations
from typing import Dict, Tuple, Any
from collections import defaultdict
import numpy as np


RELATION_TO_ID = {
    "calls": 0,
    "precedes": 1,
    "correlates_with": 2,
    "affects": 3,
}

ID_TO_RELATION = {v: k for k, v in RELATION_TO_ID.items()}

# Optional inverse relations if你需要避免走回头路
INVERSE_RELATION_ID = {
    0: 1000,   # calls^-1
    1: 1001,   # precedes^-1 (rarely used)
    2: 1002,
    3: 1003,
}


def _node_id_map(G) -> Tuple[Dict[Any, int], Dict[int, Any]]:
    uid_to_int: Dict[Any, int] = {}
    int_to_uid: Dict[int, Any] = {}
    for i, nid in enumerate(G.nodes()):
        uid_to_int[nid] = i
        int_to_uid[i] = nid
    return uid_to_int, int_to_uid


def export_edges_for_temporal_walk(G) -> Dict[int, np.ndarray]:
    """
    Export MultiDiGraph edges to {rel_id: np.ndarray[[sub, rel, obj, ts], ...]}.
    - sub/obj are integer node ids (dense reindex)
    - rel is integer relation id via RELATION_TO_ID
    - ts from edge attr "time"/"ts"/"timestamp" if present else 0
    """
    uid_to_int, _ = _node_id_map(G)
    buckets = defaultdict(list)

    for u, v, _k, data in G.edges(keys=True, data=True):
        rel = data.get("type") or data.get("rel") or ""
        if rel not in RELATION_TO_ID:
            continue
        rel_id = RELATION_TO_ID[rel]
        ts = data.get("time") or data.get("ts") or data.get("timestamp") or 0
        try:
            ts_i = int(ts) if isinstance(ts, (int, float)) else 0
        except Exception:
            ts_i = 0
        buckets[rel_id].append([uid_to_int[u], rel_id, uid_to_int[v], ts_i])

    return {rid: np.asarray(arr, dtype=np.int64) for rid, arr in buckets.items()}


