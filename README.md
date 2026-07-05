# IncidentIQ

An agentic SRE Incident Investigation and Troubleshooting dashboard powered by LangGraph, Claude, and FAISS.

## Running with Docker

### Prerequisites
* [Docker](https://www.docker.com/) and Docker Compose installed on your system.

### Steps to Run
1. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and fill in your API keys (e.g., Anthropic API key, OpenAI API key):
   ```bash
   cp .env.example .env
   ```

2. **Build and Start Container**:
   Build the Docker image and start the service:
   ```bash
   docker compose up --build
   ```

3. **Access Dashboard**:
   Open [http://localhost:8501](http://localhost:8501) in your browser.

---

### Managing search stores (FAISS index)

By default, the container mounts `stores/` and `data/` as named volumes so that FAISS indexes and ingested postmortems/runbooks persist across container restarts.

#### How to Force a Rebuild of the FAISS Store
If you modify data files and want to recreate the indexes, you can force a rebuild in one of two ways:

* **Method A (Environment Variable)**:
  Set `REBUILD_STORE=true` when running compose:
  ```bash
  REBUILD_STORE=true docker compose up
  ```

* **Method B (Manual Command Execution)**:
  Run the builder script directly inside a temporary container instance:
  ```bash
  docker compose run --rm incidentiq python build_stores.py
  ```
