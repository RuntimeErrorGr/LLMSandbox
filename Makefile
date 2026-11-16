.PHONY: help sync dev migrate migration ingest ollama-up ollama-down models cluster cluster-delete infra runner-image test

WORKSPACE := $(CURDIR)/data/workspace
RUNNER_IMAGE := sandbox-runner:0.1

help:
	@echo "make dev             start the web app on http://localhost:8000"
	@echo "make migrate         apply database migrations"
	@echo "make migration id=0002 m=\"add scans\"  create a migration from models.py"
	@echo "make ingest          load knowledge/ into the Chroma vector database"
	@echo "make sync            install Python dependencies"
	@echo "make ollama-up       start the local LLM server"
	@echo "make ollama-down     stop the local LLM server"
	@echo "make models          download the LLM models"
	@echo "make cluster         create the kind Kubernetes cluster"
	@echo "make cluster-delete  delete the kind cluster (data/workspace is kept)"
	@echo "make infra           apply the sandbox rooms and rules (gitops/infra)"
	@echo "make runner-image    build the module toolbox image and load it into kind"
	@echo "make test            run the test suite"

sync:
	uv sync

dev: migrate
	uv run uvicorn app.main:app --reload --port 8000

migrate:
	uv run alembic upgrade head

ingest:
	uv run python -m app.rag

migration:
	uv run alembic revision --autogenerate --rev-id $(id) -m "$(m)"
	sed -i '/# ###/d' migrations/versions/$(id)_*.py

ollama-up:
	docker compose up -d ollama

ollama-down:
	docker compose down

models: ollama-up
	docker exec ollama ollama pull qwen2.5-coder:7b
	docker exec ollama ollama pull nomic-embed-text

cluster:
	mkdir -p $(WORKSPACE)/datasets $(WORKSPACE)/answers $(WORKSPACE)/models $(WORKSPACE)/runs
	sed "s|__WORKSPACE__|$(WORKSPACE)|" cluster/kind-config.yaml > data/kind-config.yaml
	kind get clusters | grep -qx sandbox || kind create cluster --config data/kind-config.yaml
	kubectl cluster-info --context kind-sandbox

cluster-delete:
	kind delete cluster --name sandbox

infra:
	kubectl apply -k gitops/infra

runner-image:
	docker build -t $(RUNNER_IMAGE) runner/
	kind load docker-image $(RUNNER_IMAGE) --name sandbox

test:
	uv run pytest -q
