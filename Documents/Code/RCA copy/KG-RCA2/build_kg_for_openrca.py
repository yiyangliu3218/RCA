#!/usr/bin/env python3
import argparse, json, os
from kg_rca.builder import build_knowledge_graph,tkg_from_openrca
import pandas as pd
from kg_rca.timeutil import extract_and_convert_datetime,parse_opencra_timestamp
from pathlib import Path
from kg_rca.util import export_trimmed_csv

def main():
    ap = argparse.ArgumentParser(description="Build Knowledge Graph from traces/logs/metrics (+ causal discovery)")
    ap.add_argument("--dataset", type=str, default="Bank")
    ap.add_argument("--problem_number", type=int, default=1)
    ap.add_argument("--incident-id", type=str, default="openrca_1", help="Incident identifier")
    ap.add_argument("--outdir", type=str, default="outputs", help="Output directory")
    ap.add_argument("--no-causal" ,action="store_true", help="Disable causal discovery on metrics")
    ap.add_argument("--pc-alpha", type=float, default=0.05, help="PC test alpha (default 0.05)")
    ap.add_argument("--resample", type=str, default="60S", help="Resample rule for metrics (e.g., 60S, 5T)")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    dataset = args.dataset
    init_file = f"C:/Users/yamin/Desktop/作业/projcet/KG-RCA/data/{dataset}/query.csv"
    telemetry_folder = f'C:/Users/yamin/Desktop/作业/projcet/KG-RCA/data/{dataset}/telemetry'
    cut = args.problem_number

    instruct_data = pd.read_csv(init_file)['instruction'][1:cut + 1]
    scoring_data = pd.read_csv(init_file)['scoring_points'][1:cut + 1]

    for item in instruct_data:
        time_dict = extract_and_convert_datetime(item)
        data_time = time_dict['formatted_date']
        start_time = time_dict['start_timestamp']
        end_time = time_dict['end_timestamp']
        trace_path = telemetry_folder + f'/{data_time}/trace/trace_span.csv'
        metrics_path = telemetry_folder + f'/{data_time}/metric/metric_container.csv'
        log_path = telemetry_folder + f'/{data_time}/log/log_service.csv'

        ### the test for tkg
        test_list, top_info =tkg_from_openrca(
            traces_path=trace_path,
            logs_path=log_path,
            metrics_path=metrics_path,
            incident_id=args.incident_id,
            window={"start": start_time, "end": end_time} if (start_time or end_time) else None,
#
        )

        # kg = build_knowledge_graph(
        #     traces_path=trace_path,
        #     logs_path=log_path,
        #     metrics_path=metrics_path,
        #     incident_id=args.incident_id,
        #     window={"start": start_time, "end": end_time} if (start_time or end_time) else None,
        #     enable_causal=not args.no_causal,
        #    pc_alpha=args.pc_alpha,
        #     resample_rule=args.resample,
        # )
        # Export
        for ts_time,kg in test_list:
            time = parse_opencra_timestamp(str(ts_time))
            time = time.strftime("%H-%M-%S")

            base = Path(args.outdir) / dataset / data_time / time
            graphml = base / f"{args.incident_id}.graphml"
            nodes_csv = base / f"{args.incident_id}.nodes.csv"
            edges_csv = base / f"{args.incident_id}.edges.csv"
            summary_path = base / f"{args.incident_id}.summary.json"
            kg.to_csv(nodes_csv, edges_csv)
            with open(summary_path, "w") as f:
                json.dump(kg.summary(), f, indent=2, default=str)
            try:
                kg.to_graphml(graphml)
            except Exception:
                pass
            print(json.dumps(kg.summary(), indent=2))

            nodes_csv_trim, edges_csv_trim = export_trimmed_csv(kg, nodes_csv, edges_csv)

            trim_kg = 1


if __name__ == "__main__":
    main()