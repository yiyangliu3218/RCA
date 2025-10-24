#!/bin/bash

# KG-RCA Virtual Environment Setup Script

echo "Setting up KG-RCA virtual environment..."

# Check if virtual environment already exists
if [ -d "venv" ]; then
    echo "Virtual environment already exists. Activating..."
    source venv/bin/activate
    echo "Virtual environment activated!"
    echo "To deactivate, run: deactivate"
    echo "To activate again later, run: source venv/bin/activate"
else
    echo "Creating new virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    
    echo "Upgrading pip..."
    python3 -m pip install --upgrade pip
    
    echo "Installing dependencies..."
    pip install -r requirements.txt
    
    echo "Setup complete! Virtual environment is now active."
    echo "To deactivate, run: deactivate"
    echo "To activate again later, run: source venv/bin/activate"
fi

echo ""
echo "You can now run the KG-RCA project:"
echo "python build_kg.py --traces sample_data/traces.json --logs sample_data/logs.jsonl --metrics sample_data/metrics.csv --incident-id demo1 --start 2025-08-14T11:00:00Z --end 2025-08-14T12:00:00Z --outdir outputs --pc-alpha 0.05 --resample 60S"
