# RCA (Root Cause Analysis) Project

This repository contains multiple components for Root Cause Analysis (RCA) in distributed systems, combining knowledge graph-based approaches with LLM-driven analysis.

## Project Structure

### DyRCA
Dynamic Root Cause Analysis implementation with:
- Agent-based RCA using LLMs
- Causal walk analysis
- Time window analysis
- Streaming RCA capabilities

### KG-RCA
Knowledge Graph-based Root Cause Analysis:
- Graph construction from logs, metrics, and traces
- Causal relationship analysis
- Visualization tools

### KG-RCA2
Enhanced version of KG-RCA with:
- LLM-DA integration
- Agent-based RCA
- Improved scoring mechanisms
- Temporal knowledge graph support

### LLM-DA
LLM-driven Dynamic Analysis:
- Rule learning and application
- Temporal walk analysis
- Model adaptation for different LLMs
- Reasoning capabilities

## Features

- **Multi-modal Data Processing**: Handles logs, metrics, and traces
- **Knowledge Graph Construction**: Builds causal graphs from system data
- **LLM Integration**: Uses large language models for intelligent analysis
- **Dynamic Analysis**: Real-time RCA capabilities
- **Agent-based Architecture**: Modular and extensible design

## Getting Started

Each component has its own requirements and setup instructions. Please refer to the individual README files in each directory.

## Requirements

- Python 3.8+
- Various ML and graph processing libraries (see individual requirements.txt files)

## License

This project is for research and educational purposes.

## Contributing

Please feel free to submit issues and enhancement requests.
