#!/bin/bash
set -e

# Determine if the FAISS store index directory is missing or empty
STORES_EMPTY=true
if [ -d "/app/stores/code_chunks" ] && [ "$(ls -A /app/stores/code_chunks 2>/dev/null)" ]; then
    STORES_EMPTY=false
fi

if [ "$REBUILD_STORE" = "true" ] || [ "$STORES_EMPTY" = "true" ]; then
    echo "Running build_stores.py to generate FAISS stores..."
    python build_stores.py
else
    echo "FAISS stores already exist. Skipping build."
fi

echo "Starting Streamlit..."
exec streamlit run app.py --server.port=8501 --server.address=0.0.0.0
