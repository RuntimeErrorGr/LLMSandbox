.PHONY: help sync ollama-up ollama-down models

help:
	@echo "make sync         install Python dependencies"
	@echo "make ollama-up    start the local LLM server"
	@echo "make ollama-down  stop the local LLM server"
	@echo "make models       download the LLM models"

sync:
	uv sync

ollama-up:
	docker compose up -d ollama

ollama-down:
	docker compose down

models: ollama-up
	docker exec ollama ollama pull qwen2.5-coder:7b
	docker exec ollama ollama pull nomic-embed-text
