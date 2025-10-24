from __future__ import annotations
import json, sys, os
from typing import List

# Ensure we can import both this package (DyRCA) and sibling project KG-RCA
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
KG_RCA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "KG-RCA"))
if KG_RCA_DIR not in sys.path:
    sys.path.insert(0, KG_RCA_DIR)
from kg_rca.builder import build_knowledge_graph  # type: ignore
from DyRCA.scoring.twist import TwistScorer
from DyRCA.scoring.ranker import FusionRanker
from DyRCA.walks.adapter import export_edges_for_temporal_walk
from DyRCA.walks.features import compute_walk_features
from DyRCA.agents.rerank import ReRankingAgent
from DyRCA.streaming import Streamer
from DyRCA.window import SlidingWindow


def main():
    # One-off build using KG-RCA sample data
    kg = build_knowledge_graph(
        traces_path="KG-RCA/sample_data/traces.json",
        logs_path="KG-RCA/sample_data/logs.jsonl",
        metrics_path="KG-RCA/sample_data/metrics.csv",
        incident_id="demo_dyn",
        window=None,
        enable_causal=False,
        resample_rule="60S",
    )

    # Initialize components
    twist = TwistScorer()
    fusion_ranker = FusionRanker(weights={"twist": 0.6, "walk_reachability": 0.2, "walk_path_density": 0.2})
    agent = ReRankingAgent()
    
    # Get node mappings
    from DyRCA.walks.adapter import _node_id_map
    uid_to_int, int_to_uid = _node_id_map(kg.G)
    
    # Find service nodes and anomaly events
    service_nodes = set()
    start_nodes: List[int] = []
    for nid, data in kg.G.nodes(data=True):
        if data.get("type") == "Service":
            if nid in uid_to_int:
                service_nodes.add(uid_to_int[nid])
        elif data.get("type") in ("MetricEvent", "LogEvent"):
            if nid in uid_to_int:
                start_nodes.append(uid_to_int[nid])
    
    print(f"Found {len(service_nodes)} service nodes and {len(start_nodes)} anomaly events")
    
    # Get walk features
    edges = export_edges_for_temporal_walk(kg.G)
    print(f"🔍 Debug: Found {len(edges)} edge types in graph")
    for rel_id, arr in edges.items():
        print(f"   Relation {rel_id}: {len(arr)} edges")
    
    walk_feats = compute_walk_features(edges, start_nodes, service_nodes)
    print(f"🔍 Debug: Computed walk features for {len(walk_feats)} nodes")
    
    # Debug: show some walk features
    print("🔍 Sample walk features:")
    for node_id, features in list(walk_feats.items())[:3]:
        original_node = int_to_uid.get(node_id, f"node_{node_id}")
        print(f"   {original_node}: {features}")
    
    # Initial TWIST ranking
    twist_ranking = twist.rank(kg)
    
    # Create service ID to int ID mapping
    service_id_mapping = {service_id: uid_to_int[service_id] for service_id, _, _ in twist_ranking 
                         if service_id in uid_to_int}
    
    # Debug: show service node mappings
    print("🔍 Service node mappings:")
    for service_id, int_id in service_id_mapping.items():
        if int_id in walk_feats:
            print(f"   {service_id} (int_id: {int_id}): {walk_feats[int_id]}")
        else:
            print(f"   {service_id} (int_id: {int_id}): NO WALK FEATURES")
    
    # Initial fusion ranking
    current_ranking = fusion_ranker.rank(twist_ranking, walk_feats, service_id_mapping)
    
    print("\n=== Initial Fusion Ranking ===")
    for i, (service_id, score, details) in enumerate(current_ranking[:5]):
        print(f"{i+1}. {service_id}: {score:.3f}")
        print(f"   TWIST: {details.get('normalized_twist', 0):.3f}, Walk: {details.get('walk_score', 0):.3f}")
        print(f"   Reachability: {details.get('walk_reachability', 0):.3f}, Paths: {details.get('walk_path_count', 0):.0f}")
    
    # Multi-round iterative ranking
    print("\n=== Multi-Round Iterative Ranking ===")
    for round_num in range(3):
        print(f"\n--- Round {round_num + 1} ---")
        
        # Pick next candidate to investigate
        candidate = agent.pick_next(current_ranking)
        if not candidate:
            break
            
        print(f"Investigating: {candidate}")
        
        # Simulate evidence gathering (in real implementation, this would analyze logs, metrics, etc.)
        # For demo, we'll use a simple heuristic based on walk features
        int_id = service_id_mapping.get(candidate, -1)
        if int_id in walk_feats:
            walk_feat = walk_feats[int_id]
            # Higher reachability and path count = higher confidence
            confidence = min(1.0, (walk_feat.get("service_reachability", 0) + 
                                 walk_feat.get("path_count", 0) / 10.0))
        else:
            confidence = 0.5
            
        print(f"Evidence confidence: {confidence:.3f}")
        
        # Update ranking based on evidence
        current_ranking = agent.update(current_ranking, candidate, {"confidence": confidence})
        
        # Show updated top 3
        print("Updated top 3:")
        for i, (service_id, score, details) in enumerate(current_ranking[:3]):
            print(f"  {i+1}. {service_id}: {score:.3f}")
    
    print(f"\n=== Final Ranking ===")
    for i, (service_id, score, details) in enumerate(current_ranking[:5]):
        print(f"{i+1}. {service_id}: {score:.3f}")
        print(f"   Details: {details}")
    
    # Final summary
    print("\n=== Summary ===")
    print(f"Initial TWIST top 3: {[s[0] for s in twist_ranking[:3]]}")
    print(f"Final fusion top 3: {[s[0] for s in current_ranking[:3]]}")
    print(f"Agent history: {len(agent.history)} investigations")

    # Placeholder streaming loop (no-op batches)
    window = SlidingWindow(size_minutes=60)
    streamer = Streamer(every_seconds=1.0)
    for _batch in streamer.iter_batches(max_iters=1):
        window.evict_old(kg)


if __name__ == "__main__":
    main()


