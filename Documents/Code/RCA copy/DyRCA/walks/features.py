from __future__ import annotations
from typing import Dict, List, Any, Iterable
import numpy as np


def compute_walk_features(edges_by_rel: Dict[int, np.ndarray], start_nodes: Iterable[int], 
                         service_nodes: set = None, max_hops: int = 3) -> Dict[int, Dict[str, float]]:
    """
    Enhanced temporal-walk features: finds propagation paths from anomalies to services.
    - edges_by_rel[rel] = np.ndarray[[sub, rel, obj, ts], ...]
    - start_nodes are integer node ids (same id space as adapter)
    Returns per-node features: path_count, unique_reach, last_ts_span, service_reachability
    """
    # Build adjacency: sub -> List[(obj, ts, rel_type)] across all relations
    adj: Dict[int, List[tuple[int, int, int]]] = {}
    for rel_id, arr in edges_by_rel.items():
        if arr.size == 0:
            continue
        for sub, _rel, obj, ts in arr:
            adj.setdefault(int(sub), []).append((int(obj), int(ts), rel_id))

    features: Dict[int, Dict[str, float]] = {}
    
    # Use provided service nodes or infer from graph structure
    if service_nodes is None:
        service_nodes = set()
        for rel_id, arr in edges_by_rel.items():
            for sub, _rel, obj, ts in arr:
                # Services are typically connected via "calls" relation (rel_id = 0)
                if rel_id == 0:  # "calls" relation
                    service_nodes.add(int(sub))
                    service_nodes.add(int(obj))
    
    # First, compute features for anomaly events (start_nodes)
    for s in start_nodes:
        # Enhanced DFS with service reachability tracking
        stack = [(int(s), -1, 0, [])]  # (node, last_ts, depth, path)
        visited_paths = 0
        reached = set()
        reached_services = set()
        last_ts = -1
        path_lengths = []
        
        while stack:
            node, prev_ts, depth, path = stack.pop()
            reached.add(node)
            if node in service_nodes:
                reached_services.add(node)
            last_ts = max(last_ts, prev_ts)
            
            if depth >= max_hops:
                continue
                
            for (nbr, ts, rel_type) in adj.get(node, []):
                # Temporal constraint: non-decreasing timestamps
                if ts < 0 or prev_ts < 0 or ts >= prev_ts:
                    visited_paths += 1
                    new_path = path + [rel_type]
                    path_lengths.append(len(new_path))
                    stack.append((nbr, ts, depth + 1, new_path))

        # Calculate service reachability score
        service_reachability = len(reached_services) / max(1, len(service_nodes))
        
        # Average path length to services
        avg_path_length = sum(path_lengths) / max(1, len(path_lengths)) if path_lengths else 0

        features[int(s)] = {
            "path_count": float(visited_paths),
            "unique_reach": float(len(reached)),
            "last_ts_span": float(last_ts if last_ts >= 0 else 0),
            "service_reachability": float(service_reachability),
            "avg_path_length": float(avg_path_length),
        }
    
    # Second, compute features for service nodes (how many anomalies can reach them)
    for service_node in service_nodes:
        # Count how many anomaly events can reach this service
        reachable_from_anomalies = 0
        path_lengths_to_service = []
        
        for anomaly_node in start_nodes:
            # Check if this anomaly can reach the service
            stack = [(int(anomaly_node), -1, 0)]  # (node, last_ts, depth)
            visited = set()
            
            while stack:
                node, prev_ts, depth = stack.pop()
                if node in visited or depth >= max_hops:
                    continue
                visited.add(node)
                
                if node == service_node:
                    reachable_from_anomalies += 1
                    path_lengths_to_service.append(depth)
                    break
                
                for (nbr, ts, rel_type) in adj.get(node, []):
                    if ts < 0 or prev_ts < 0 or ts >= prev_ts:
                        stack.append((nbr, ts, depth + 1))
        
        # Calculate service-specific features
        anomaly_reachability = reachable_from_anomalies / max(1, len(start_nodes))
        avg_path_length_to_service = sum(path_lengths_to_service) / max(1, len(path_lengths_to_service)) if path_lengths_to_service else 0
        
        # Also count how many other services this service can reach via calls
        service_reachability = 0
        if service_node in adj:
            for (nbr, ts, rel_type) in adj[service_node]:
                if nbr in service_nodes and rel_type == 0:  # calls relation
                    service_reachability += 1
        
        features[service_node] = {
            "path_count": float(len(path_lengths_to_service)),
            "unique_reach": float(reachable_from_anomalies),
            "last_ts_span": 0.0,  # Not applicable for services
            "service_reachability": float(anomaly_reachability),
            "avg_path_length": float(avg_path_length_to_service),
            "service_connections": float(service_reachability),  # How many services it calls
        }

    return features


