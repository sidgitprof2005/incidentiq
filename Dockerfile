# Base image
FROM python:3.11-slim

# Install system dependencies (build-essential for compiling libraries, curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements.txt and install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY app.py build_stores.py entrypoint.sh ./
COPY agent/ ./agent/
COPY data/ ./data/
COPY ingestion/ ./ingestion/
COPY stores/ ./stores/
COPY .streamlit/ ./.streamlit/

# Make entrypoint.sh executable
RUN chmod +x entrypoint.sh

# Expose port
EXPOSE 8501

# Set the entrypoint script
ENTRYPOINT ["./entrypoint.sh"]
