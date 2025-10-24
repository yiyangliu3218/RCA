# KG-RCA
Knowledge Graph for RCA

## Project layout
```
kg-rca/
├── build_kg.py                # CLI
├── kg_rca/
│   ├── __init__.py
│   ├── graph.py               # KnowledgeGraph wrapper (NetworkX MultiDiGraph)
│   ├── builder.py             # orchestrates parsers -> KG
│   ├── causal.py              # Apply causal inference to metrics data
│   ├── timeutil.py            # Utility function for time conversion
│   └── parsers/
│       ├── logs.py            # JSONL or plaintext logs → LogEvent nodes
│       ├── metrics.py         # CSV metrics (+ z-score anomalies) → MetricEvent nodes
│       └── traces.py          # Jaeger/OpenTelemetry-like JSON → Service nodes + calls
├── sample_data/               # tiny synthetic example
│   ├── logs.jsonl
│   ├── metrics.csv
│   └── traces.json
└── requirements.txt
```


## To test:
1. ```pip install -r requirements.txt ```
2. ```python build_kg.py   --traces sample_data/traces.json   --logs sample_data/logs.jsonl   --metrics sample_data/metrics.csv   --incident-id demo1   --start 2025-08-14T11:00:00Z --end 2025-08-14T12:00:00Z   --outdir outputs   --pc-alpha 0.05 --resample 60S```