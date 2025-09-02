#!/bin/bash

echo "=== CurtainTime Local Development Server ==="
echo "Dashboard: http://127.0.0.1:8000/dashboard"
echo "API Docs: http://127.0.0.1:8000/docs"
echo "Press Ctrl+C to stop"
echo ""

# Ensure we're in the right directory
cd "$(dirname "$0")"

# Run the FastAPI server with reload
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
