#!/bin/bash
# Start script for GlyphMind AI Backend

# Set default port if not provided
PORT=${PORT:-8000}

# Start the FastAPI server
uvicorn server.app:app --host 0.0.0.0 --port $PORT
