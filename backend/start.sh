#!/bin/bash
# production start script for Render

# Run training pipeline if model doesn't exist (optional, but good for first boot)
if [ ! -f "models/crop_model.pkl" ]; then
    echo "Model not found. Running training pipeline..."
    python run_pipeline.py
fi

# Run the application
gunicorn main:app \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:$PORT \
    --timeout 120 \
    --graceful-timeout 30 \
    --access-logfile - \
    --error-logfile -
