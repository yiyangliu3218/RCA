#!/usr/bin/env python3
"""
Enhanced knowledge graph visualization for KG-RCA.
"""
import argparse
import json
import os
import sys
from kg_rca.builder import build_knowledge_graph
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


def visualize_knowledge_graph(kg, output_path="outputs/kg_visualization.png"):
    """Create a visual representation of the knowledge graph."""
    G = kg.G
    
    # Create figure
    plt.figure(figsize=(16, 12))
    
    # Define node colors by type
    node_colors = {
        'Incident': '#FF6B6B',      # Red
        'Service': '#4ECDC4',       # Teal  
        'LogEvent': '#45B7D1',      # Blue
        'MetricEvent': '#96CEB4',   # Green
        'MetricVariable': '#FFEAA7', # Yellow
    }
    
    # Define edge colors by type
    edge_colors = {
        'involves': '#2C3E50',      # Dark blue
        'calls': '#E74C3C',         # Red
        'has_log': '#3498DB',       # Blue
        'has_metric_anomaly': '#27AE60', # Green
        'precedes': '#9B59B6',      # Purple
        'causes': '#F39C12',        # Orange
        'adjacent': '#95A5A6',      # Gray
    }
    
    # Get node positions using spring layout
    pos = nx.spring_layout(G, k=3, iterations=50)
    
    # Draw nodes by type
    for node_type, color in node_colors.items():
        nodes = [n for n, d in G.nodes(data=True) if d.get('type') == node_type]
        if nodes:
            nx.draw_networkx_nodes(G, pos, nodelist=nodes, 
                                 node_color=color, node_size=300, 
                                 alpha=0.8, label=node_type)
    
    # Draw edges by type
    for edge_type, color in edge_colors.items():
        edges = [(u, v) for u, v, k, d in G.edges(keys=True, data=True) 
                if d.get('type') == edge_type]
        if edges:
            nx.draw_networkx_edges(G, pos, edgelist=edges, 
                                 edge_color=color, alpha=0.6, 
                                 width=2, label=edge_type)
    
    # Add labels for services only (to avoid clutter)
    service_labels = {n: n.replace('svc:', '') for n, d in G.nodes(data=True) 
                     if d.get('type') == 'Service'}
    nx.draw_networkx_labels(G, pos, service_labels, font_size=8, font_weight='bold')
    
    # Create legend
    legend_elements = []
    for node_type, color in node_colors.items():
        legend_elements.append(mpatches.Patch(color=color, label=f'Node: {node_type}'))
    for edge_type, color in edge_colors.items():
        legend_elements.append(mpatches.Patch(color=color, label=f'Edge: {edge_type}'))
    
    plt.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1, 1))
    plt.title("Knowledge Graph for Root Cause Analysis", fontsize=16, fontweight='bold')
    plt.axis('off')
    plt.tight_layout()
    
    # Save the plot
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"📊 Knowledge graph visualization saved to: {output_path}")


def export_graph_statistics(kg, output_path="outputs/kg_statistics.json"):
    """Export detailed graph statistics."""
    G = kg.G
    
    # Node statistics
    node_types = {}
    for n, d in G.nodes(data=True):
        node_type = d.get('type', 'Unknown')
        node_types[node_type] = node_types.get(node_type, 0) + 1
    
    # Edge statistics  
    edge_types = {}
    for u, v, k, d in G.edges(keys=True, data=True):
        edge_type = d.get('type', 'Unknown')
        edge_types[edge_type] = edge_types.get(edge_type, 0) + 1
    
    # Service connectivity
    service_connectivity = {}
    for n, d in G.nodes(data=True):
        if d.get('type') == 'Service':
            in_degree = G.in_degree(n)
            out_degree = G.out_degree(n)
            service_connectivity[n] = {
                'in_degree': in_degree,
                'out_degree': out_degree,
                'total_connections': in_degree + out_degree
            }
    
    # Anomaly distribution
    anomaly_distribution = {}
    for n, d in G.nodes(data=True):
        if d.get('type') in ('LogEvent', 'MetricEvent'):
            service = d.get('service', 'Unknown')
            anomaly_distribution[service] = anomaly_distribution.get(service, 0) + 1
    
    statistics = {
        'summary': {
            'total_nodes': G.number_of_nodes(),
            'total_edges': G.number_of_edges(),
            'node_types': node_types,
            'edge_types': edge_types
        },
        'service_connectivity': service_connectivity,
        'anomaly_distribution': anomaly_distribution,
        'graph_density': nx.density(G),
        'is_connected': nx.is_weakly_connected(G)
    }
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(statistics, f, indent=2, default=str)
    
    print(f"📈 Graph statistics saved to: {output_path}")
    return statistics


def main():
    parser = argparse.ArgumentParser(description="Visualize KG-RCA knowledge graph")
    parser.add_argument("--traces", type=str, default="sample_data/traces.json")
    parser.add_argument("--logs", type=str, default="sample_data/logs.jsonl")
    parser.add_argument("--metrics", type=str, default="sample_data/metrics.csv")
    parser.add_argument("--incident-id", type=str, default="visualization_demo")
    parser.add_argument("--outdir", type=str, default="outputs")
    parser.add_argument("--enable-causal", action="store_true", help="Enable causal discovery")
    args = parser.parse_args()
    
    print("🔍 Building knowledge graph for visualization...")
    
    # Build knowledge graph
    kg = build_knowledge_graph(
        traces_path=args.traces,
        logs_path=args.logs,
        metrics_path=args.metrics,
        incident_id=args.incident_id,
        window=None,
        enable_causal=args.enable_causal,
        resample_rule="60S",
    )
    
    # Export standard outputs
    graphml_path = os.path.join(args.outdir, f"{args.incident_id}.graphml")
    nodes_csv = os.path.join(args.outdir, f"{args.incident_id}.nodes.csv")
    edges_csv = os.path.join(args.outdir, f"{args.incident_id}.edges.csv")
    summary_json = os.path.join(args.outdir, f"{args.incident_id}.summary.json")
    
    kg.to_csv(nodes_csv, edges_csv)
    with open(summary_json, "w") as f:
        json.dump(kg.summary(), f, indent=2, default=str)
    
    try:
        kg.to_graphml(graphml_path)
        print(f"📊 GraphML exported to: {graphml_path}")
    except Exception as e:
        print(f"⚠️  GraphML export failed: {e}")
    
    # Create visualization
    viz_path = os.path.join(args.outdir, f"{args.incident_id}_visualization.png")
    visualize_knowledge_graph(kg, viz_path)
    
    # Export detailed statistics
    stats_path = os.path.join(args.outdir, f"{args.incident_id}_statistics.json")
    stats = export_graph_statistics(kg, stats_path)
    
    # Print summary
    print(f"\n📊 Knowledge Graph Summary:")
    print(f"   Nodes: {stats['summary']['total_nodes']}")
    print(f"   Edges: {stats['summary']['total_edges']}")
    print(f"   Node types: {stats['summary']['node_types']}")
    print(f"   Edge types: {stats['summary']['edge_types']}")
    print(f"   Graph density: {stats['graph_density']:.3f}")
    print(f"   Connected: {stats['is_connected']}")


if __name__ == "__main__":
    main()