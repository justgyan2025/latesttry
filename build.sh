#!/bin/bash

# Clean up any previous builds
rm -rf .venv

# Create a virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install core dependencies first
pip install flask gunicorn python-dotenv requests

# Install yfinance with minimal dependencies
pip install yfinance --no-deps
pip install pandas

# Cleanup
find .venv -name "*.pyc" -delete
find .venv -name "__pycache__" -delete

# This step helps identify what's taking up space
echo "Size of .venv directory:"
du -h -d 1 .venv/ 