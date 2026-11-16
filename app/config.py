from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ollama_base_url: str = "http://localhost:11434"
    agent_model: str = "qwen2.5-coder:7b"
    embed_model: str = "nomic-embed-text"
    github_repo: str = "RuntimeErrorGr/LLMSandbox"
    github_token: str = ""


settings = Settings()
