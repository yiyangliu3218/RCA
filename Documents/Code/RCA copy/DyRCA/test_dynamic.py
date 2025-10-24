#!/usr/bin/env python3
"""
Test dynamic RCA with simulated real-time data updates.
"""
import time
import json
import os
import sys
from datetime import datetime, timedelta

# Add project paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
KG_RCA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "KG-RCA"))
if KG_RCA_DIR not in sys.path:
    sys.path.insert(0, KG_RCA_DIR)

from kg_rca.builder import build_knowledge_graph
from DyRCA.scoring.twist import TwistScorer
from DyRCA.scoring.ranker import FusionRanker
from DyRCA.walks.adapter import export_edges_for_temporal_walk, _node_id_map
from DyRCA.walks.features import compute_walk_features
from DyRCA.agents.rerank import ReRankingAgent


def simulate_data_update(round_num: int):
    """Simulate new data arriving (logs, metrics, traces)."""
    # In real scenario, this would be:
    # - New log entries appended to logs.jsonl
    # - New metrics data points in metrics.csv  
    # - New trace spans in traces.json
    
    print(f"📊 Simulating data update round {round_num}...")
    
    # Simulate different scenarios
    if round_num == 1:
        print("  → New ERROR logs detected in frontend service")
        print("  → Memory usage spike in checkout service")
    elif round_num == 2:
        print("  → Payment service response time increased")
        print("  → New trace spans showing slow database calls")
    elif round_num == 3:
        print("  → Multiple services showing degraded performance")
        print("  → Error rate spike across the system")
    
    # Simulate processing delay
    time.sleep(1)


def run_dynamic_rca():
    """Run dynamic RCA with simulated real-time updates."""
    print("🚀 Starting Dynamic RCA Test")
    print("=" * 50)
    
    # Initial build
    print("\n📈 Building initial knowledge graph...")
    kg = build_knowledge_graph(
        traces_path="KG-RCA/sample_data/traces.json",
        logs_path="KG-RCA/sample_data/logs.jsonl", 
        metrics_path="KG-RCA/sample_data/metrics.csv",
        incident_id="dynamic_test",
        window=None,
        enable_causal=False,
        resample_rule="60S",
    )
    
    # Initialize components
    twist = TwistScorer()
    fusion_ranker = FusionRanker()
    agent = ReRankingAgent()
    
    # Get node mappings
    uid_to_int, int_to_uid = _node_id_map(kg.G)
    
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
    
    print(f"📊 Found {len(service_nodes)} services, {len(start_nodes)} anomalies")
    
    # Dynamic loop - simulate 3 rounds of data updates
    for round_num in range(1, 4):
        print(f"\n🔄 === DYNAMIC ROUND {round_num} ===")
        
        # Simulate new data arriving
        simulate_data_update(round_num)
        
        # Rebuild knowledge graph (in real scenario, this would be incremental)
        print("🔄 Rebuilding knowledge graph with new data...")
        kg = build_knowledge_graph(
            traces_path="KG-RCA/sample_data/traces.json",
            logs_path="KG-RCA/sample_data/logs.jsonl",
            metrics_path="KG-RCA/sample_data/metrics.csv", 
            incident_id=f"dynamic_test_round_{round_num}",
            window=None,
            enable_causal=False,
            resample_rule="60S",
        )
        
        # Recalculate everything
        edges = export_edges_for_temporal_walk(kg.G)
        walk_feats = compute_walk_features(edges, start_nodes, service_nodes)
        twist_ranking = twist.rank(kg)
        
        service_id_mapping = {service_id: uid_to_int[service_id] for service_id, _, _ in twist_ranking 
                             if service_id in uid_to_int}
        
        current_ranking = fusion_ranker.rank(twist_ranking, walk_feats, service_id_mapping)
        
        print(f"\n📊 Round {round_num} Results:")
        for i, (service_id, score, details) in enumerate(current_ranking[:3]):
            print(f"  {i+1}. {service_id}: {score:.3f}")
            print(f"     TWIST: {details.get('normalized_twist', 0):.3f}, Walk: {details.get('walk_score', 0):.3f}")
        
        # Agent investigation
        candidate = agent.pick_next(current_ranking)
        if candidate:
            print(f"\n🔍 Agent investigating: {candidate}")
            
            # Simulate evidence gathering
            int_id = service_id_mapping.get(candidate, -1)
            if int_id in walk_feats:
                walk_feat = walk_feats[int_id]
                confidence = min(1.0, (walk_feat.get("service_reachability", 0) + 
                                     walk_feat.get("path_count", 0) / 10.0))
            else:
                confidence = 0.5
            
            print(f"   Evidence confidence: {confidence:.3f}")
            
            # Update ranking
            current_ranking = agent.update(current_ranking, candidate, {"confidence": confidence})
            
            print(f"   Updated top 3:")
            for i, (service_id, score, _) in enumerate(current_ranking[:3]):
                print(f"     {i+1}. {service_id}: {score:.3f}")
        
        print(f"   Agent history: {len(agent.history)} investigations")
        
        # Simulate time passing
        time.sleep(2)
    
    print(f"\n✅ Dynamic RCA Test Complete!")
    print(f"📊 Total investigations: {len(agent.history)}")
    print(f"🎯 Final top service: {current_ranking[0][0] if current_ranking else 'None'}")


if __name__ == "__main__":
    run_dynamic_rca()
