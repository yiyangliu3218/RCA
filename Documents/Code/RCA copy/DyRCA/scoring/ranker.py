from __future__ import annotations
from typing import List, Tuple, Dict, Any
import statistics


class FusionRanker:
    """Fusion ranker combining TWIST scores with walk features."""
    
    def __init__(self, weights: Dict[str, float] = None):
        self.weights = weights or {
            "twist": 0.6,
            "walk_reachability": 0.2,
            "walk_path_density": 0.2
        }
    
    def rank(self, twist_ranking: List[Tuple[str, float, Dict[str, Any]]], 
             walk_features: Dict[int, Dict[str, float]],
             node_id_mapping: Dict[str, int]) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Combine TWIST scores with walk features.
        
        Args:
            twist_ranking: [(service_id, twist_score, twist_details), ...]
            walk_features: {int_node_id: {walk_feature_dict}}
            node_id_mapping: {service_id: int_node_id}
        """
        # Calculate walk-based scores for each service
        walk_scores = {}
        for service_id, twist_score, twist_details in twist_ranking:
            int_id = node_id_mapping.get(service_id)
            if int_id and int_id in walk_features:
                walk_feat = walk_features[int_id]
                # Service reachability: how many services are reachable from anomalies
                reachability = walk_feat.get("service_reachability", 0.0)
                # Path density: average paths per anomaly that reach this service
                path_density = walk_feat.get("path_count", 0.0) / max(1.0, walk_feat.get("unique_reach", 1.0))
                # Service connections: how many other services this service calls
                service_connections = walk_feat.get("service_connections", 0.0)
                
                walk_score = (
                    self.weights["walk_reachability"] * reachability +
                    self.weights["walk_path_density"] * min(path_density, 1.0) +  # cap at 1.0
                    0.3 * min(service_connections / 5.0, 1.0)  # normalize service connections
                )
            else:
                walk_score = 0.0
            
            walk_scores[service_id] = walk_score
        
        # Normalize walk scores to [0, 1] range
        if walk_scores:
            max_walk = max(walk_scores.values())
            if max_walk > 0:
                for service_id in walk_scores:
                    walk_scores[service_id] /= max_walk
        
        # Normalize TWIST scores to [0, 1] range
        twist_scores = [score for _, score, _ in twist_ranking]
        if twist_scores:
            max_twist = max(twist_scores)
            min_twist = min(twist_scores)
            twist_range = max_twist - min_twist
            if twist_range > 0:
                normalized_twist = [(score - min_twist) / twist_range for score in twist_scores]
            else:
                normalized_twist = [0.5] * len(twist_scores)
        else:
            normalized_twist = []
        
        # Combine scores
        fusion_ranking = []
        for i, (service_id, twist_score, twist_details) in enumerate(twist_ranking):
            normalized_twist_score = normalized_twist[i] if i < len(normalized_twist) else 0.0
            walk_score = walk_scores.get(service_id, 0.0)
            
            fusion_score = (
                self.weights["twist"] * normalized_twist_score +
                (1 - self.weights["twist"]) * walk_score
            )
            
            # Enhanced details including walk features
            enhanced_details = twist_details.copy()
            enhanced_details.update({
                "walk_reachability": walk_features.get(node_id_mapping.get(service_id, -1), {}).get("service_reachability", 0.0),
                "walk_path_count": walk_features.get(node_id_mapping.get(service_id, -1), {}).get("path_count", 0.0),
                "walk_score": walk_score,
                "normalized_twist": normalized_twist_score,
                "fusion_score": fusion_score
            })
            
            fusion_ranking.append((service_id, fusion_score, enhanced_details))
        
        # Sort by fusion score
        fusion_ranking.sort(key=lambda x: x[1], reverse=True)
        return fusion_ranking

