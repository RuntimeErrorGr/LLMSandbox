.PHONY: help sync dev migrate migration ingest ollama-up ollama-down models

help:
	@echo "make dev          start the web app on http://localhost:8000"
	@echo "make migrate      apply database migrations"
	@echo "make migration id=0002 m=\"add scans\"  create a migration from models.py"
	@echo "make ingest       load knowledge/ into the Chroma vector database"
	@echo "make sync         install Python dependencies"
	@echo "make ollama-up    start the local LLM server"
	@echo "make ollama-down  stop the local LLM server"
	@echo "make models       download the LLM models"

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
