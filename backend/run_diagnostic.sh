#!/bin/bash

# roundZero Diagnostic Runner
# Runs comprehensive system diagnostics

set -e

echo "\ud83d\udd0d roundZero Diagnostic Suite"
echo "=============================="
echo ""

# Check if we're in the backend directory
if [ -f "app/main.py" ]; then
    echo "\u2713 Detected backend directory"
    
    # Check if .env exists
    if [ ! -f ".env" ]; then
        echo "\u26a0\ufe0f  Warning: .env file not found in backend directory"
        echo "   Diagnostic will use system environment variables only"
        echo ""
    fi
    
    # Install dependencies if needed
    echo "\ud83d\udce6 Checking dependencies..."
    
    # Check for uv
    if command -v uv &> /dev/null; then
        echo "\u2713 Using uv for dependency management"
        
        # Install diagnostic dependencies
        uv pip install httpx websockets python-dotenv --quiet || true
        
        # Run the diagnostic
        echo ""
        echo "\ud83d\ude80 Starting diagnostic..."
        echo ""
        uv run python diagnose_roundzero.py
    else
        echo "\u26a0\ufe0f  uv not found, trying pip..."
        
        # Fallback to pip
        pip install httpx websockets python-dotenv --quiet || true
        
        echo ""
        echo "\ud83d\ude80 Starting diagnostic..."
        echo ""
        python diagnose_roundzero.py
    fi
else
    echo "\u274c Error: This script should be run from the backend directory"
    echo "   cd to your roundZero/backend directory first"
    exit 1
fi
