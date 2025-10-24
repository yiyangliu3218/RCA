from pathlib import Path
from typing import Iterable, Tuple
from .graph import KnowledgeGraph, Node, Edge

def make_trimmed_copy(
    kg: KnowledgeGraph,
    drop_node_types: Iterable[str] = ("LogEvent",),            # 默认删掉日志节点
    drop_edge_types: Iterable[str] = ("has_log", "precedes"),  # 默认删掉 has_log 与 precedes 边
) -> KnowledgeGraph:
    """
    返回一份“修剪版”图：
    - 删除指定类型的节点（默认 LogEvent）；
    - 删除指定类型的边（默认 has_log、precedes）；
    - 仅在两端节点均保留的情况下复制边；
    - 复制图级元数据，并在 graph 属性加上 {"trimmed": True}。
    """
    # 新图
    kg_trim = KnowledgeGraph()

    # 复制图级元数据（可选）
    for k, v in getattr(kg.G, "graph", {}).items():
        kg_trim.G.graph[k] = v
    kg_trim.G.graph["trimmed"] = True

    # 固化要删除的类型集合
    drop_node_types = set(drop_node_types)
    drop_edge_types = set(drop_edge_types)

    # 复制节点：跳过要删除的类型
    for nid, data in kg.G.nodes(data=True):
        ntype = data.get("type", "")
        if ntype in drop_node_types:
            continue
        kg_trim.add_node(
            Node(
                id=nid,
                type=ntype,
                attrs={k: v for k, v in data.items() if k != "type"}
            )
        )

    # 复制边：跳过要删除的类型；且要求两端节点仍存在
    for u, v, key, edata in kg.G.edges(keys=True, data=True):
        etype = edata.get("type", key)
        if etype in drop_edge_types:
            continue
        if not (kg_trim.G.has_node(u) and kg_trim.G.has_node(v)):
            continue
        kg_trim.add_edge(
            Edge(
                src=u,
                dst=v,
                type=etype,
                attrs={kk: vv for kk, vv in edata.items() if kk != "type"}
            )
        )

    return kg_trim

def export_trimmed_csv(
    kg: KnowledgeGraph,
    nodes_csv: str,
    edges_csv: str,
    suffix: str = ".trim",
    drop_node_types: Iterable[str] = ("LogEvent",),
    drop_edge_types: Iterable[str] = ("has_log", "precedes"),
) -> Tuple[str, str]:
    """
    在不修改原图的前提下，导出一份“修剪版”CSV：
    - 输入为原图对象 kg 以及原图的 nodes_csv / edges_csv 路径；
    - 修剪版文件名会在原名处追加后缀（默认 ".trim"）；
    - 返回 (nodes_csv_trim, edges_csv_trim) 两个路径字符串。
    """
    # 构建修剪版副本
    kg_trim = make_trimmed_copy(
        kg,
        drop_node_types=drop_node_types,
        drop_edge_types=drop_edge_types
    )

    p_nodes = Path(nodes_csv)
    p_edges = Path(edges_csv)

    # 为修剪版构造文件名（若原名是 *.nodes.csv / *.edges.csv，则在中间追加 .trim）
    if p_nodes.name.endswith(".nodes.csv"):
        nodes_trim_name = p_nodes.name.replace(".nodes.csv", f".nodes{suffix}.csv")
    else:
        nodes_trim_name = p_nodes.stem + f"{suffix}.csv"

    if p_edges.name.endswith(".edges.csv"):
        edges_trim_name = p_edges.name.replace(".edges.csv", f".edges{suffix}.csv")
    else:
        edges_trim_name = p_edges.stem + f"{suffix}.csv"

    p_nodes_trim = p_nodes.with_name(nodes_trim_name)
    p_edges_trim = p_edges.with_name(edges_trim_name)

    # 确保目录存在（幂等）
    p_nodes_trim.parent.mkdir(parents=True, exist_ok=True)
    p_edges_trim.parent.mkdir(parents=True, exist_ok=True)

    # 落地 CSV
    kg_trim.to_csv(p_nodes_trim.as_posix(), p_edges_trim.as_posix())

    return p_nodes_trim.as_posix(), p_edges_trim.as_posix()