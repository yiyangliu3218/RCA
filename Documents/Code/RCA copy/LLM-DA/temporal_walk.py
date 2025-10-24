import numpy as np
import pandas as pd


def initialize_temporal_walk(version_id, data, transition_distr):
    idx_map = {
        'all':np.array(data.train_idx.tolist() + data.valid_idx.tolist()+data.test_idx.tolist()),
        'train_valid': np.array(data.train_idx.tolist() + data.valid_idx.tolist()),
        'train': np.array(data.train_idx.tolist()),
        'test': np.array(data.test_idx.tolist()),
        'valid': np.array(data.valid_idx.tolist())
    }
    return Temporal_Walk(idx_map[version_id], data.inv_relation_id, transition_distr)

class Temporal_Walk(object):
    def __init__(self, learn_data, inv_relation_id, transition_distr):
        """
        Initialize temporal random walk object.

        Parameters:
            learn_data (np.ndarray): data on which the rules should be learned
            inv_relation_id (dict): mapping of relation to inverse relation
            transition_distr (str): transition distribution
                                    "unif" - uniform distribution
                                    "exp"  - exponential distribution

        Returns:
            None
        """

        self.learn_data = learn_data
        self.inv_relation_id = inv_relation_id
        self.transition_distr = transition_distr
        self.neighbors = store_neighbors(learn_data)
        self.edges = store_edges(learn_data)

    def sample_start_edge(self, rel_idx):
        """
        Define start edge distribution.

        Parameters:
            rel_idx (int): relation index

        Returns:
            start_edge (np.ndarray): start edge
        """

        rel_edges = self.edges[rel_idx]
        start_edge = rel_edges[np.random.choice(len(rel_edges))]

        return start_edge

    def sample_next_edge(self, filtered_edges, cur_ts):
        """
        Define next edge distribution.

        Parameters:
            filtered_edges (np.ndarray): filtered (according to time) edges
            cur_ts (int): current timestamp

        Returns:
            next_edge (np.ndarray): next edge
        """

        if self.transition_distr == "unif":
            next_edge = filtered_edges[np.random.choice(len(filtered_edges))]
        elif self.transition_distr == "exp":
            tss = filtered_edges[:, 3]
            prob = np.exp(tss - cur_ts)
            try:
                prob = prob / np.sum(prob)
                next_edge = filtered_edges[
                    np.random.choice(range(len(filtered_edges)), p=prob)
                ]
            except ValueError:  # All timestamps are far away
                next_edge = filtered_edges[np.random.choice(len(filtered_edges))]

        return next_edge

    def transition_step(self, cur_node, cur_ts, prev_edge, start_node, step, L, target_cur_ts=None):
        """
        Sample a neighboring edge given the current node and timestamp.
        In the second step (step == 1), the next timestamp should be smaller than the current timestamp.
        In the other steps, the next timestamp should be smaller than or equal to the current timestamp.
        In the last step (step == L-1), the edge should connect to the source of the walk (cyclic walk).
        It is not allowed to go back using the inverse edge.

        Parameters:
            cur_node (int): current node
            cur_ts (int): current timestamp
            prev_edge (np.ndarray): previous edge
            start_node (int): start node
            step (int): number of current step
            L (int): length of random walk
            target_cur_ts (int, optional): target current timestamp for relaxed time. Defaults to cur_ts.

        Returns:
            next_edge (np.ndarray): next edge
        """

        next_edges = self.neighbors[cur_node]
        if target_cur_ts is None:
            target_cur_ts = cur_ts

        if step == 1:  # The next timestamp should be smaller than the current timestamp
            filtered_edges = next_edges[next_edges[:, 3] < target_cur_ts]
        else:  # The next timestamp should be smaller than or equal to the current timestamp
            filtered_edges = next_edges[next_edges[:, 3] <= target_cur_ts]
            # Delete inverse edge
            inv_edge = [
                cur_node,
                self.inv_relation_id[prev_edge[1]],
                prev_edge[0],
                cur_ts,
            ]
            row_idx = np.where(np.all(filtered_edges == inv_edge, axis=1))
            filtered_edges = np.delete(filtered_edges, row_idx, axis=0)

        if step == L - 1:  # Find an edge that connects to the source of the walk
            filtered_edges = filtered_edges[filtered_edges[:, 2] == start_node]

        if len(filtered_edges):
            next_edge = self.sample_next_edge(filtered_edges, cur_ts)
        else:
            next_edge = []

        return next_edge

    def transition_step_with_relax_time(self, cur_node, cur_ts, prev_edge, start_node, step, L, target_cur_ts):
        """
        Wrapper for transition_step with relaxed time handling.

        Parameters:
            cur_node (int): current node
            cur_ts (int): current timestamp
            prev_edge (np.ndarray): previous edge
            start_node (int): start node
            step (int): number of current step
            L (int): length of random walk
            target_cur_ts (int): target current timestamp for relaxed time

        Returns:
            next_edge (np.ndarray): next edge
        """
        return self.transition_step(cur_node, cur_ts, prev_edge, start_node, step, L, target_cur_ts)

    def sample_walk(self, L, rel_idx, use_relax_time=False):
        """
        Try to sample a cyclic temporal random walk of length L (for a rule of length L-1).

        Parameters:
            L (int): length of random walk
            rel_idx (int): relation index
            use_relax_time (bool): whether to use relaxed time sampling

        Returns:
            walk_successful (bool): if a cyclic temporal random walk has been successfully sampled
            walk (dict): information about the walk (entities, relations, timestamps)
        """

        walk_successful = True
        walk = dict()
        prev_edge = self.sample_start_edge(rel_idx)
        start_node = prev_edge[0]
        cur_node = prev_edge[2]
        cur_ts = prev_edge[3]
        target_cur_ts = cur_ts
        walk["entities"] = [start_node, cur_node]
        walk["relations"] = [prev_edge[1]]
        walk["timestamps"] = [cur_ts]

        for step in range(1, L):
            if use_relax_time:
                next_edge = self.transition_step_with_relax_time(
                    cur_node, cur_ts, prev_edge, start_node, step, L, target_cur_ts
                )
            else:
                next_edge = self.transition_step(
                    cur_node, cur_ts, prev_edge, start_node, step, L
                )

            if len(next_edge):
                cur_node = next_edge[2]
                cur_ts = next_edge[3]
                walk["relations"].append(next_edge[1])
                walk["entities"].append(cur_node)
                walk["timestamps"].append(cur_ts)
                prev_edge = next_edge
            else:  # No valid neighbors (due to temporal or cyclic constraints)
                walk_successful = False
                break

        return walk_successful, walk


def store_neighbors(quads):
    """
    Store all neighbors (outgoing edges) for each node.

    Parameters:
        quads (np.ndarray): indices of quadruples

    Returns:
        neighbors (dict): neighbors for each node
    """

    # 将 quads 转换为 DataFrame
    df = pd.DataFrame(quads, columns=['head', 'relation', 'target', 'timestamp'])

    # 按 'node' 列分组，并将每组转换为数组
    neighbors = {node: group.values for node, group in df.groupby('head')}

    return neighbors


def store_edges(quads):
    """
    Store all edges for each relation.

    Parameters:
        quads (np.ndarray): indices of quadruples

    Returns:
        edges (dict): edges for each relation
    """

    edges = dict()
    relations = list(set(quads[:, 1]))
    for rel in relations:
        edges[rel] = quads[quads[:, 1] == rel]

    return edges


# ========== CMRW (Constrained Multi-Relation Walk) for KG-RCA2 Integration ==========

import networkx as nx
import random
import json
import os
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

@dataclass
class WalkConfig:
    """Configuration for constrained multi-relation walk"""
    max_len: int = 4
    num_paths: int = 200
    time_monotonic: bool = True
    allowed_edge_types: tuple = ("precedes", "has_log", "has_metric", "calls", "depends_on")
    base_weights: dict = None
    rule_bias: dict = None                  # { (src_type, edge_type, dst_type): weight }
    type_sequence: List[str] = None         # e.g. ["metric_event","metric_event","log_event"]
    lambda_time_decay: float = 0.2
    backtrack_hop_block: int = 4            # 禁止回到最近 h 个节点
    seed: int = 42
    
    def __post_init__(self):
        if self.base_weights is None:
            self.base_weights = {
                "precedes": 1.0,
                "has_metric": 1.0,
                "has_log": 1.0,
                "calls": 0.6,
                "depends_on": 0.6
            }
        if self.rule_bias is None:
            self.rule_bias = {}
        random.seed(self.seed)
        np.random.seed(self.seed)


def _node_time(G: nx.MultiDiGraph, nid: str):
    """获取节点时间：优先 event_ts，缺失时用 minute_ts"""
    et = G.nodes[nid].get("event_ts")
    mt = G.nodes[nid].get("minute_ts")
    return et if et is not None and str(et) != "NaT" else mt


def _type_ok(G, nid: str, idx_in_path: int, type_sequence: Optional[List[str]]):
    """检查节点类型是否符合序列约束"""
    if not type_sequence:
        return True
    if idx_in_path >= len(type_sequence):
        return True
    need = type_sequence[idx_in_path]
    return (G.nodes[nid].get("type") == need)


def _edge_prob(G, u: str, v: str, edata: Dict[str, Any], t_u, t_v, cfg: WalkConfig) -> float:
    """计算边的转移概率"""
    etype = edata.get("type", "unknown")
    if etype not in cfg.allowed_edge_types:
        return 0.0

    # 时间约束
    if cfg.time_monotonic:
        if t_u is None or t_v is None:
            return 0.0
        if t_v <= t_u:
            return 0.0
        dt = (t_v - t_u).total_seconds()
        if dt < 0:
            return 0.0
    else:
        dt = 0.0

    base = float(cfg.base_weights.get(etype, 1.0))

    # 规则偏置
    src_type = G.nodes[u].get("type", "unknown")
    dst_type = G.nodes[v].get("type", "unknown")
    bias = float(cfg.rule_bias.get((src_type, etype, dst_type), 1.0))

    # 时间衰减
    decay = np.exp(-cfg.lambda_time_decay * max(dt, 0.0))

    return base * bias * decay


def _single_temporal_walk(G: nx.MultiDiGraph, start_node: str, cfg: WalkConfig) -> Optional[List[str]]:
    """执行单次时间约束的随机游走"""
    if start_node not in G:
        return None

    path = [start_node]
    t_cur = _node_time(G, start_node)

    for step in range(cfg.max_len - 1):
        # 以"边"为单位枚举候选（多重边分别计）
        candidates: List[Tuple[str, Dict[str, Any]]] = []
        probs: List[float] = []

        # 防环：不回到最近 h 个节点
        recent = set(path[-cfg.backtrack_hop_block:])

        for v in G.successors(path[-1]):
            if v in recent:
                continue
            # 节点类型序列约束：下一个节点位置是 len(path)
            if not _type_ok(G, v, len(path), cfg.type_sequence):
                continue

            t_v = _node_time(G, v)
            edict = G.get_edge_data(path[-1], v) or {}
            for _, edata in edict.items():
                p = _edge_prob(G, path[-1], v, edata, t_cur, t_v, cfg)
                if p > 0:
                    candidates.append((v, edata))
                    probs.append(p)

        if not candidates:
            break

        probs = np.array(probs, dtype=float)
        probs = probs / probs.sum()
        idx = np.random.choice(len(candidates), p=probs)
        next_node, chosen_edge = candidates[idx]

        path.append(next_node)
        t_cur = _node_time(G, next_node)

    return path if len(path) > 1 else None


def temporal_random_walk(G: nx.MultiDiGraph, start_nodes: List[str], cfg: WalkConfig,
                         save_dir: Optional[str] = "sampled_path",
                         center_ts_iso: Optional[str] = None) -> List[List[str]]:
    """
    满足：时间递增 + 边类型允许 + (可选)节点类型序列 的路径采样。
    转移概率 ∝ base_weights[e.type] * rule_bias.get(pattern,1.0) * exp(-λΔt)。
    结果写入 LLM-DA/sampled_path/{center_ts}/paths.jsonl（可读格式）。
    """
    all_paths: List[List[str]] = []
    seen: set = set()  # 去重：按节点序列 tuple

    for s in start_nodes:
        for _ in range(cfg.num_paths):
            p = _single_temporal_walk(G, s, cfg)
            if p and len(p) > 1:
                key = tuple(p)
                if key not in seen:
                    seen.add(key)
                    all_paths.append(p)

    # 保存
    if save_dir:
        subdir = save_dir if center_ts_iso is None else os.path.join(save_dir, center_ts_iso.replace(":", "-"))
        os.makedirs(subdir, exist_ok=True)
        outpath = os.path.join(subdir, f"paths_{len(all_paths)}.jsonl")
        with open(outpath, "w", encoding="utf-8") as f:
            for i, p in enumerate(all_paths):
                f.write(json.dumps({
                    "path_id": i,
                    "path": p,
                    "readable_path": to_readable_path(G, p),
                    "length": len(p)
                }, ensure_ascii=False) + "\n")
        print(f"📤 saved {len(all_paths)} paths -> {outpath}")

    return all_paths




def to_readable_path(G: nx.MultiDiGraph, path_ids: List[str]) -> List[Dict[str, Any]]:
    """将路径ID转换为可读格式"""
    out = []
    for nid in path_ids:
        n = G.nodes[nid]
        out.append({
            "id": nid,
            "node_type": n.get("type", "unknown"),
            "service": n.get("service"),
            "metric": n.get("metric"),
            "template_id": n.get("template_id"),
            "event_ts": None if (n.get("event_ts") is None or str(n.get("event_ts"))=="NaT") else str(n.get("event_ts")),
            "minute_ts": None if (n.get("minute_ts") is None or str(n.get("minute_ts"))=="NaT") else str(n.get("minute_ts")),
        })
    return out