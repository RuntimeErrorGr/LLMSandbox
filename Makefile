.PHONY: help sync dev migrate migration ingest ollama-up ollama-down models cluster cluster-delete runner-image test lint policy validate ci argocd bootstrap argocd-ui guard-index wait-modules demo-setup ui-install ui-dev ui-build stop start

CRD_SCHEMAS := https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json
WORKSPACE := $(CURDIR)/data/workspace
RUNNER_IMAGE := sandbox-runner:0.1
ARGOCD_PASSWORD = kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d

help:
	@echo "make demo-setup      build everything from zero: models, cluster, ArgoCD, data, indexes, demo datasets"
	@echo "make dev             start the API and the built UI on http://localhost:8000"
	@echo "make stop            stop everything: API, UI dev server, ArgoCD UI, Kubernetes cluster, Ollama (data is kept)"
	@echo "make start           start the Kubernetes cluster and Ollama again after make stop (then run make dev)"
	@echo "make ui-install      install the frontend dependencies (Vue, TypeScript)"
	@echo "make ui-build        type-check and build the frontend into frontend/dist"
	@echo "make ui-dev          frontend dev server with hot reload on http://localhost:5173"
	@echo "make migrate         apply database migrations"
	@echo "make migration id=0002 m=\"add scans\"  create a migration from models.py"
	@echo "make ingest          load knowledge/ into the Chroma vector database"
	@echo "make guard-index     load the known prompts for the guard into Chroma"
	@echo "make sync            install Python dependencies"
	@echo "make ollama-up       start the local LLM server"
	@echo "make ollama-down     stop the local LLM server"
	@echo "make models          download the LLM models"
	@echo "make cluster         create the kind Kubernetes cluster"
	@echo "make cluster-delete  delete the kind cluster (data/workspace is kept)"
	@echo "make runner-image    build the module toolbox image and load it into kind"
	@echo "make prepare-data    download the clean datasets and models into data/workspace"
	@echo "make demo-targets    run the poisoners in the sandbox to create the suspect demo datasets"
	@echo "make test            run the test suite"
	@echo "make lint            check code style with ruff"
	@echo "make policy          check every module against the sandbox rules"
	@echo "make validate        check every Kubernetes and ArgoCD manifest"
	@echo "make ci              run all CI checks locally (lint, test, policy, validate)"
	@echo "make argocd          install ArgoCD into the cluster"
	@echo "make bootstrap       hand gitops/apps over to ArgoCD (the only manual apply)"
	@echo "make argocd-ui       print the admin password and open the ArgoCD UI on https://localhost:8080"

sync:
	uv sync

dev: migrate
	uv run uvicorn app.main:app --reload --reload-dir app --port 8000

stop:
	pkill -f "uvicorn[ ]app.main:app" || true
	pkill -f "node_modules/[.]bin/vite" || true
	pkill -f "port-forward[ ]svc/argocd-server" || true
	-docker stop sandbox-control-plane
	-docker compose stop ollama
	@echo "stopped: run make start, then make dev, to continue"

start:
	docker start sandbox-control-plane
	docker compose start ollama
	@until kubectl get nodes --context kind-sandbox 2>/dev/null | grep -q " Ready"; do sleep 3; done
	kubectl -n argocd annotate application --all argocd.argoproj.io/refresh=hard --overwrite
	@echo "ready: run make dev"

ui-install:
	cd frontend && npm ci

ui-build:
	cd frontend && npm run build

ui-dev:
	cd frontend && npm run dev

migrate:
	uv run alembic upgrade head

ingest:
	uv run python -m app.rag

guard-index:
	uv run python -m app.guard

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

prepare-data:
	uv run python -m app.workspace.prepare

demo-targets:
	uv run python -m app.workspace.demo_targets

test:
	uv run pytest -q

lint:
	uv run ruff check .

policy:
	uv run python -m app.sandbox.policy modules/*/

validate:
	@for dir in gitops/infra modules/*/; do \
		echo "$$dir"; kubectl kustomize $$dir | kubeconform -strict -summary || exit 1; \
	done
	kubeconform -strict -summary -schema-location default -schema-location '$(CRD_SCHEMAS)' gitops/apps gitops/bootstrap

ci: lint test policy validate

argocd:
	kubectl apply --server-side --force-conflicts -k gitops/argocd
	kubectl -n argocd rollout status deploy/argocd-server --timeout=300s

bootstrap:
	kubectl apply -f gitops/bootstrap/root.yaml

wait-modules:
	@echo "waiting for ArgoCD to deploy the modules from git"
	@until kubectl get cronjob poison-label-flip poison-clean-label -n sandbox-modules >/dev/null 2>&1; do sleep 5; done

demo-setup: sync ui-install ui-build models cluster runner-image argocd bootstrap prepare-data migrate ingest guard-index wait-modules demo-targets
	@echo "ready: run make dev and open http://localhost:8000"

argocd-ui:
	@echo "user: admin   password: $(shell $(ARGOCD_PASSWORD))"
	kubectl -n argocd port-forward svc/argocd-server 8080:443
