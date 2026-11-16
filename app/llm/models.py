from langchain_ollama import ChatOllama, OllamaEmbeddings

from app.config import settings


def chat_model(temperature: float = 0.2) -> ChatOllama:
    return ChatOllama(
        base_url=settings.ollama_base_url,
        model=settings.agent_model,
        temperature=temperature,
    )


def embeddings() -> OllamaEmbeddings:
    return OllamaEmbeddings(base_url=settings.ollama_base_url, model=settings.embed_model)
