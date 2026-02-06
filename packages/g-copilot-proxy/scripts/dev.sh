#!/bin/bash
# Development server startup script

cd "$(dirname "$0")/.."

# Activate virtual environment if using poetry
if command -v poetry &> /dev/null; then
    echo "Starting with Poetry..."
    poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
else
    echo "Starting with uvicorn..."
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
fi
