from dataclasses import dataclass, field
from typing import Any, Dict
import json
import networkx as nx
from collections import Counter

@dataclass
class Node:
    id: str
    type: str
    attrs: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Edge:
    src: str
    dst: str
    type: str
    attrs: Dict[str, Any] = field(default_factory=dict)

class KnowledgeGraph:
    def __init__(self):
        self.G = nx.MultiDiGraph()

    def add_node(self, node: Node):
        if not self.G.has_node(node.id):
            self.G.add_node(node.id, **{"type": node.type, **node.attrs})
        else:
            self.G.nodes[node.id].update({"type": node.type, **node.attrs})

    def add_edge(self, edge: Edge):
        self.G.add_edge(edge.src, edge.dst, key=edge.type, **{"type": edge.type, **edge.attrs})

    def _coerce_for_graphml(self, v: Any) -> Any:
        # GraphML supports: str, int, float, bool  (and None → omit or "")
        if v is None:
            return ""
        if isinstance(v, (str, int, float, bool)):
            return v
        # everything else → JSON string (fallback to str for non-serializables)
        try:
            return json.dumps(v, default=str)
        except Exception:
            return str(v)

    def to_graphml(self, path: str):
        # Build a sanitized copy with scalarized attributes
        H = nx.MultiDiGraph()
        # graph-level attrs (if you ever set them)
        for k, v in getattr(self.G, "graph", {}).items():
            H.graph[k] = self._coerce_for_graphml(v)

        for n, data in self.G.nodes(data=True):
            H.add_node(n, **{k: self._coerce_for_graphml(v) for k, v in data.items()})

        for u, v, k, data in self.G.edges(keys=True, data=True):
            # ensure edge key is a string (GraphML is happier)
            ek = str(k)
            H.add_edge(u, v, key=ek, **{kk: self._coerce_for_graphml(vv) for kk, vv in data.items()})

        nx.write_graphml(H, path)

    def to_csv(self, nodes_path: str, edges_path: str):
        import csv
        with open(nodes_path, "w", newline="") as f:
            w = csv.writer(f); w.writerow(["id","type","attrs"])
            for nid, data in self.G.nodes(data=True):
                w.writerow([nid, data.get("type",""), {k:v for k,v in data.items() if k!="type"}])
        with open(edges_path, "w", newline="") as f:
            w = csv.writer(f); w.writerow(["src","dst","type","attrs"])
            for u,v,key,data in self.G.edges(keys=True, data=True):
                w.writerow([u,v,data.get("type",key), {k:v for k,v in data.items() if k!="type"}])

    def summary(self):
        node_types = Counter([d.get("type","") for _,d in self.G.nodes(data=True)])
        edge_types = Counter([d.get("type","") for *_,d in self.G.edges(data=True)])
        return {"nodes": self.G.number_of_nodes(),
                "edges": self.G.number_of_edges(),
                "node_types": dict(node_types),
                "edge_types": dict(edge_types)}
