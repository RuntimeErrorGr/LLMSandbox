.PHONY: help sync dev ollama-up ollama-down models

help:
	@echo "make dev          start the web app on http://localhost:8000"
	@echo "make sync         install Python dependencies"
	@echo "make ollama-up    start the local LLM server"
	@echo "make ollama-down  stop the local LLM server"
	@echo "make models       download the LLM models"

sync:
	uv sync

dev:
	uv run uvicorn app.main:app --reload --port 8000

ollama-up:
	docker compose up -d ollama

ollama-down:
	docker compose down

models: ollama-up
	docker exec ollama ollama pull qwen2.5-coder:7b
	docker exec ollama ollama pull nomic-embed-text
