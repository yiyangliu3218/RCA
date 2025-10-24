#!/usr/bin/env python3
import argparse, json, os
from kg_rca.builder import build_knowledge_graph

def main():
    ap = argparse.ArgumentParser(description="Build Knowledge Graph from traces/logs/metrics (+ causal discovery)")
    ap.add_argument("--traces", type=str, default=f"C:/Users/yamin/Desktop/作业/projcet/KG-RCA/data/Bank/telemetry/2021_03_04/trace/trace_span.csv", help="Path to traces JSON (Jaeger-like)")
    ap.add_argument("--logs", type=str, default=f"C:/Users/yamin/Desktop/作业/projcet/KG-RCA/data/Bank/telemetry/2021_03_04/log/log_service.csv", help="Path to logs JSONL or text")
    ap.add_argument("--metrics", type=str, default=f"C:/Users/yamin/Desktop/作业/projcet/KG-RCA/data/Bank/telemetry/2021_03_04/metric/metric_container.csv",
                    help="Path to metrics CSV (time,service,metric,value)")
    ap.add_argument("--incident-id", type=str, default="demo1", help="Incident identifier")
    ap.add_argument("--start", type=str, default="2025-08-14T11:00:00Z", help="ISO start time filter (inclusive)")
    ap.add_argument("--end", type=str, default="2025-08-14T12:00:00Z", help="ISO end time filter (inclusive)")
    ap.add_argument("--outdir", type=str, default="outputs", help="Output directory")
    ap.add_argument("--no-causal", action="store_true", help="Disable causal discovery on metrics")
    ap.add_argument("--pc-alpha", type=float, default=0.05, help="PC test alpha (default 0.05)")
    ap.add_argument("--resample", type=str, default="60S", help="Resample rule for metrics (e.g., 60S, 5T)")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    

    kg = build_knowledge_graph(
        traces_path=args.traces,
        logs_path=args.logs,
        metrics_path=args.metrics,
        incident_id=args.incident_id,
        window={"start": args.start, "end": args.end} if (args.start or args.end) else None,
        enable_causal=not args.no_causal,
        pc_alpha=args.pc_alpha,
        resample_rule=args.resample,
    )
    # Exports
    graphml = os.path.join(args.outdir, f"{args.incident_id}.graphml")
    nodes_csv = os.path.join(args.outdir, f"{args.incident_id}.nodes.csv")
    edges_csv = os.path.join(args.outdir, f"{args.incident_id}.edges.csv")
    kg.to_csv(nodes_csv, edges_csv)
    with open(os.path.join(args.outdir, f"{args.incident_id}.summary.json"), "w") as f:
        json.dump(kg.summary(), f, indent=2, default=str)
    try:
        kg.to_graphml(graphml)
    except Exception:
        pass
    print(json.dumps(kg.summary(), indent=2))

if __name__ == "__main__":
    main()

"""
Outputs
 - outputs/demo1.summary.json — node/edge counts by type
 - outputs/demo1.nodes.csv, outputs/demo1.edges.csv — tabular exports
 - outputs/demo1.graphml — open in Gephi, yEd, or import to Neo4j

Graph schema:
Node types:
    - Incident — the incident container
    - Service — each microservice discovered in traces/logs/metrics
    - LogEvent — individual log records (within time window)
    - MetricEvent — metric anomalies detected via z-score

Edge types:
    - involves — Incident → Service
    - calls — Service → Service (derived from trace parent/child across services)
    - has_log — Service → LogEvent
    - has_metric_anomaly — Service → MetricEvent
    - precedes — Event → Event within a service (temporal order; dt_seconds attr)

"""