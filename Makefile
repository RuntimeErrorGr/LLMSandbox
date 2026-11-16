.PHONY: help sync dev migrate migration ingest ollama-up ollama-down models cluster cluster-delete runner-image test argocd bootstrap argocd-ui

WORKSPACE := $(CURDIR)/data/workspace
RUNNER_IMAGE := sandbox-runner:0.1
ARGOCD_PASSWORD = kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d

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
	@echo "make runner-image    build the module toolbox image and load it into kind"
	@echo "make test            run the test suite"
	@echo "make argocd          install ArgoCD into the cluster"
	@echo "make bootstrap       hand gitops/apps over to ArgoCD (the only manual apply)"
	@echo "make argocd-ui       print the admin password and open the ArgoCD UI on https://localhost:8080"

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

runner-image:
	docker build -t $(RUNNER_IMAGE) runner/
	kind load docker-image $(RUNNER_IMAGE) --name sandbox

test:
	uv run pytest -q

argocd:
	kubectl apply --server-side --force-conflicts -k gitops/argocd
	kubectl -n argocd rollout status deploy/argocd-server --timeout=300s

bootstrap:
	kubectl apply -f gitops/bootstrap/root.yaml

argocd-ui:
	@echo "user: admin   password: $(shell $(ARGOCD_PASSWORD))"
	kubectl -n argocd port-forward svc/argocd-server 8080:443
