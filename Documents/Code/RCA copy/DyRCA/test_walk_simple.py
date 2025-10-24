#!/usr/bin/env python3
"""
Simple test to verify walk features are working correctly.
"""
import sys
import os

# Add project paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
KG_RCA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "KG-RCA"))
if KG_RCA_DIR not in sys.path:
    sys.path.insert(0, KG_RCA_DIR)

from kg_rca.builder import build_knowledge_graph
from DyRCA.walks.adapter import export_edges_for_temporal_walk, _node_id_map
from DyRCA.walks.features import compute_walk_features


def test_walk_features():
    """Test walk features with a simple scenario."""
    print("🧪 Testing Walk Features")
    print("=" * 40)
    
    # Build a simple graph
    kg = build_knowledge_graph(
        traces_path="KG-RCA/sample_data/traces.json",
        logs_path="KG-RCA/sample_data/logs.jsonl",
        metrics_path="KG-RCA/sample_data/metrics.csv",
        incident_id="walk_test",
        window=None,
        enable_causal=False,
        resample_rule="60S",
    )
    
    # Get node mappings
    uid_to_int, int_to_uid = _node_id_map(kg.G)
    
    print(f"📊 Graph has {kg.G.number_of_nodes()} nodes and {kg.G.number_of_edges()} edges")
    
    # Show all node types
    node_types = {}
    for nid, data in kg.G.nodes(data=True):
        node_type = data.get('type', 'Unknown')
        node_types[node_type] = node_types.get(node_type, 0) + 1
    print(f"📊 Node types: {node_types}")
    
    # Show all edge types
    edge_types = {}
    for u, v, k, data in kg.G.edges(keys=True, data=True):
        edge_type = data.get('type', 'Unknown')
        edge_types[edge_type] = edge_types.get(edge_type, 0) + 1
    print(f"📊 Edge types: {edge_types}")
    
    # Export edges
    edges = export_edges_for_temporal_walk(kg.G)
    print(f"📊 Exported edges: {len(edges)} relation types")
    for rel_id, arr in edges.items():
        print(f"   Relation {rel_id}: {len(arr)} edges")
        if len(arr) > 0:
            print(f"     Sample: {arr[0]}")
    
    # Find service nodes and anomaly events
    service_nodes = set()
    start_nodes = []
    for nid, data in kg.G.nodes(data=True):
        if data.get("type") == "Service":
            if nid in uid_to_int:
                service_nodes.add(uid_to_int[nid])
        elif data.get("type") in ("MetricEvent", "LogEvent"):
            if nid in uid_to_int:
                start_nodes.append(uid_to_int[nid])
    
    print(f"📊 Found {len(service_nodes)} service nodes and {len(start_nodes)} anomaly events")
    
    # Test walk features
    walk_feats = compute_walk_features(edges, start_nodes, service_nodes)
    print(f"📊 Computed walk features for {len(walk_feats)} nodes")
    
    # Show some results
    print("\n🔍 Sample walk features:")
    count = 0
    for node_id, features in walk_feats.items():
        if count < 5:
            original_node = int_to_uid.get(node_id, f"node_{node_id}")
            print(f"   {original_node}: {features}")
            count += 1
    
    # Check if any service has non-zero features
    print("\n🔍 Service walk features:")
    for node_id, features in walk_feats.items():
        original_node = int_to_uid.get(node_id, f"node_{node_id}")
        if original_node.startswith("svc:"):
            print(f"   {original_node}: {features}")
            if any(v > 0 for v in features.values()):
                print(f"     ✅ Has non-zero features!")
            else:
                print(f"     ❌ All features are zero")


if __name__ == "__main__":
    test_walk_features()
