"""Generalized causal discovery utilities for metrics data using PC (causallearn)."""
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

def _safe_col(service: str, metric: str) -> str:
    return f"{service}|{metric}"

def metrics_to_dataframe(
    rows: List[Dict],
    start: Optional[pd.Timestamp] = None,
    end: Optional[pd.Timestamp] = None,
    resample_rule: Optional[str] = None,
    fill: str = "ffill",
) -> pd.DataFrame:
    """Convert metric rows to a wide time-indexed DataFrame."""
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df = df.dropna(subset=["time", "service", "metric"]).copy()
    df["col"] = df.apply(lambda r: _safe_col(str(r["service"]), str(r["metric"])), axis=1)
    df = df[["time", "col", "value"]]
    df = df.groupby(["time", "col"], as_index=False).mean()
    df = df.pivot(index="time", columns="col", values="value").sort_index()

    # Ensure tz-aware UTC index
    idx = pd.DatetimeIndex(df.index)
    df.index = idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")

    if start is not None:
        start = pd.to_datetime(start).tz_convert("UTC") if getattr(start, "tzinfo", None) else pd.to_datetime(start).tz_localize("UTC")
        df = df[df.index >= start]
    if end is not None:
        end = pd.to_datetime(end).tz_convert("UTC") if getattr(end, "tzinfo", None) else pd.to_datetime(end).tz_localize("UTC")
        df = df[df.index <= end]
    if resample_rule:
        df = df.resample(resample_rule).mean()
    if fill == "ffill":
        df = df.ffill().bfill()
    elif fill == "interpolate":
        df = df.interpolate(limit_direction="both")
    return df

def run_pc(df: pd.DataFrame, alpha: float = 0.05, stable: bool = True, verbose: bool = False) -> Dict:
    """Run PC algorithm and build causal edges from its adjacency matrix."""
    # Filter constant/NaN-only columns
    usable = []
    for c in df.columns:
        col = df[c].astype(float)
        if col.isna().all():
            continue
        if np.nanstd(col.values) == 0:
            continue
        usable.append(c)
    df2 = df[usable].copy()
    if df2.empty or df2.shape[1] < 2:
        return {"variables": list(df2.columns), "directed": [], "undirected": []}

    # Normalize data for Fisher-Z
    vals = df2.values.astype(float)
    vals = (vals - np.nanmean(vals, axis=0)) / (np.nanstd(vals, axis=0) + 1e-8)
    vals = np.nan_to_num(vals, nan=0.0)

    try:
        from causallearn.search.ConstraintBased.PC import pc
        from causallearn.utils.cit import fisherz
    except Exception as e:
        raise ImportError("causallearn is required for run_pc(); please install it.") from e

    # Run PC
    cg = pc(pd.DataFrame(vals, columns=df2.columns).to_numpy(), alpha=alpha, indep_test_func=fisherz, stable=stable, verbose=verbose)
    adj_matrix = cg.G.graph  # shape: (n, n)

    import networkx as nx
    G = nx.DiGraph()
    undirected = set()
    for i in range(len(adj_matrix)):
        for j in range(len(adj_matrix)):
            if adj_matrix[i, j] == -1:  # i -> j
                G.add_edge(i, j)
            elif adj_matrix[i, j] == 1:  # j -> i
                G.add_edge(j, i)
            elif adj_matrix[i, j] == 2:  # undirected edge
                undirected.add(tuple(sorted((i, j))))

    nodes = sorted(G.nodes())
    nx_adj = np.asarray(nx.to_numpy_array(G, nodelist=nodes))

    variables = list(df2.columns)
    directed = []
    for i in range(len(nodes)):
        for j in range(len(nodes)):
            if nx_adj[i, j] != 0:
                src = variables[nodes[i]]
                dst = variables[nodes[j]]
                directed.append((src, dst))

    # Map undirected node indices to variable names
    undirected_vars = []
    for (i, j) in undirected:
        undirected_vars.append((variables[i], variables[j]))

    return {"variables": variables, "directed": sorted(set(directed)), "undirected": sorted(set(undirected_vars))}
