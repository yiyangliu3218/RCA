#!/usr/bin/env python3
import argparse, json, os
from kg_rca.builder import build_knowledge_graph, tkg_from_openrca
import pandas as pd
from kg_rca.timeutil import extract_and_convert_datetime, parse_opencra_timestamp
from pathlib import Path
from kg_rca.util import export_trimmed_csv

def get_data_paths(dataset: str, data_root: str = None):
    """获取数据路径，支持环境变量和相对路径"""
    if data_root is None:
        data_root = os.getenv('KG_RCA_DATA_ROOT', './data')
    
    # 支持相对路径和绝对路径
    if not os.path.isabs(data_root):
        data_root = os.path.abspath(data_root)
    
    init_file = os.path.join(data_root, dataset, 'query.csv')
    telemetry_folder = os.path.join(data_root, dataset, 'telemetry')
    
    return init_file, telemetry_folder

def validate_paths(init_file: str, telemetry_folder: str):
    """验证路径是否存在"""
    if not os.path.exists(init_file):
        raise FileNotFoundError(f'Query file not found: {init_file}')
    
    if not os.path.exists(telemetry_folder):
        raise FileNotFoundError(f'Telemetry folder not found: {telemetry_folder}')
    
    print(f"✅ Data paths validated:")
    print(f"   Query file: {init_file}")
    print(f"   Telemetry folder: {telemetry_folder}")

def main():
    ap = argparse.ArgumentParser(description="Build Knowledge Graph from traces/logs/metrics (+ causal discovery)")
    ap.add_argument("--dataset", type=str, default="Bank", help="Dataset name (Bank, Telecom, etc.)")
    ap.add_argument("--data-root", type=str, default=None, help="Data root directory (default: ./data)")
    ap.add_argument("--problem_number", type=int, default=1, help="Number of problems to process")
    ap.add_argument("--incident-id", type=str, default="openrca_1", help="Incident identifier")
    ap.add_argument("--outdir", type=str, default="outputs", help="Output directory")
    ap.add_argument("--no-causal", action="store_true", help="Disable causal discovery on metrics")
    ap.add_argument("--pc-alpha", type=float, default=0.05, help="PC test alpha (default 0.05)")
    ap.add_argument("--resample", type=str, default="60S", help="Resample rule for metrics (e.g., 60S, 5T)")
    args = ap.parse_args()

    # 创建输出目录
    os.makedirs(args.outdir, exist_ok=True)

    # 获取数据路径
    init_file, telemetry_folder = get_data_paths(args.dataset, args.data_root)
    
    # 验证路径
    validate_paths(init_file, telemetry_folder)

    # 读取问题数据
    try:
        instruct_data = pd.read_csv(init_file)['instruction'][1:args.problem_number + 1]
        scoring_data = pd.read_csv(init_file)['scoring_points'][1:args.problem_number + 1]
        print(f"📊 Loaded {len(instruct_data)} problems from {init_file}")
    except Exception as e:
        print(f"❌ Error reading query file: {e}")
        return

    # 处理每个问题
    for i, item in enumerate(instruct_data):
        print(f"\n🔄 Processing problem {i+1}/{len(instruct_data)}")
        
        try:
            time_dict = extract_and_convert_datetime(item)
            data_time = time_dict['formatted_date']
            start_time = time_dict['start_timestamp']
            end_time = time_dict['end_timestamp']
            
            # 构建文件路径
            trace_path = os.path.join(telemetry_folder, data_time, 'trace', 'trace_span.csv')
            metrics_path = os.path.join(telemetry_folder, data_time, 'metric', 'metric_container.csv')
            log_path = os.path.join(telemetry_folder, data_time, 'log', 'log_service.csv')
            
            print(f"   📁 Data time: {data_time}")
            print(f"   📁 Trace: {trace_path}")
            print(f"   📁 Metrics: {metrics_path}")
            print(f"   📁 Logs: {log_path}")
            
            # 验证数据文件存在
            for path in [trace_path, metrics_path, log_path]:
                if not os.path.exists(path):
                    print(f"   ⚠️  Warning: {path} not found")
            
            # 使用 tkg_from_openrca 处理
            print(f"   🔄 Running tkg_from_openrca...")
            test_list, top_info = tkg_from_openrca(
                traces_path=trace_path,
                logs_path=log_path,
                metrics_path=metrics_path,
                incident_id=args.incident_id,
                window={"start": start_time, "end": end_time} if (start_time or end_time) else None,
            )
            
            print(f"   📊 Generated {len(test_list)} time slices")
            
            # 导出结果
            for ts_time, kg in test_list:
                time = parse_opencra_timestamp(str(ts_time))
                time_str = time.strftime("%H-%M-%S")
                
                # 创建输出目录
                base = Path(args.outdir) / args.dataset / data_time / time_str
                base.mkdir(parents=True, exist_ok=True)
                
                # 输出文件路径
                graphml = base / f"{args.incident_id}.graphml"
                nodes_csv = base / f"{args.incident_id}.nodes.csv"
                edges_csv = base / f"{args.incident_id}.edges.csv"
                summary_path = base / f"{args.incident_id}.summary.json"
                
                # 导出数据
                kg.to_csv(nodes_csv, edges_csv)
                with open(summary_path, "w") as f:
                    json.dump(kg.summary(), f, indent=2, default=str)
                
                try:
                    kg.to_graphml(graphml)
                except Exception as e:
                    print(f"   ⚠️  Warning: Could not export GraphML: {e}")
                
                print(f"   📤 Exported to: {base}")
                print(f"      - Nodes: {nodes_csv}")
                print(f"      - Edges: {edges_csv}")
                print(f"      - Summary: {summary_path}")
                
                # 导出修剪后的CSV
                try:
                    nodes_csv_trim, edges_csv_trim = export_trimmed_csv(kg, nodes_csv, edges_csv)
                    print(f"      - Trimmed: {nodes_csv_trim}, {edges_csv_trim}")
                except Exception as e:
                    print(f"   ⚠️  Warning: Could not export trimmed CSV: {e}")
                
                # 打印图谱摘要
                summary = kg.summary()
                print(f"   📊 Graph summary: {summary['nodes']} nodes, {summary['edges']} edges")
        
        except Exception as e:
            print(f"   ❌ Error processing problem {i+1}: {e}")
            continue
    
    print(f"\n✅ Processing complete!")

if __name__ == "__main__":
    main()
