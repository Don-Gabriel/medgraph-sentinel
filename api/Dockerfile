# Shared image for the api and seed services (compose pins it as
# medgraph-api:demo; DEMO_RUNBOOK's docker-save references that name).
# Build context is the REPO ROOT (seed needs data/ and graph/ too).
FROM python:3.11-slim

WORKDIR /app

# Install dependencies first so code edits don't bust the dependency layer.
COPY pyproject.toml README.md LICENSE ./
COPY generator ./generator
COPY loader ./loader
COPY detection ./detection
COPY api ./api
COPY graph ./graph
COPY data ./data
RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
