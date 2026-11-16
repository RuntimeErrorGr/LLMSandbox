from dataclasses import dataclass

import httpx
import urllib3
from kubernetes.client.exceptions import ApiException
from kubernetes.config import ConfigException

from app import k8s
from app.config import settings


@dataclass
class Check:
    name: str
    state: str
    detail: str


def _with_tag(model: str) -> str:
    return model if ":" in model else f"{model}:latest"


def ollama_check() -> Check:
    name = "Ollama (local LLM server)"
    try:
        response = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=2)
        response.raise_for_status()
    except httpx.HTTPError:
        return Check(name, "down", "not reachable, run: make ollama-up")

    installed = {model["name"] for model in response.json()["models"]}
    wanted = {_with_tag(settings.agent_model), _with_tag(settings.embed_model)}
    missing = wanted - installed
    if missing:
        names = ", ".join(sorted(missing))
        return Check(name, "down", f"missing models: {names}, run: make models")
    return Check(name, "ok", ", ".join(sorted(wanted)))


def kubernetes_check() -> Check:
    name = "Kubernetes sandbox"
    try:
        return Check(name, "ok", k8s.cluster_summary())
    except (ApiException, ConfigException, urllib3.exceptions.HTTPError) as error:
        reason = type(error).__name__
        return Check(name, "down", f"not reachable ({reason}), run: make cluster infra")


def all_checks() -> list[Check]:
    return [
        ollama_check(),
        kubernetes_check(),
        Check("ArgoCD (GitOps)", "todo", "coming in Step 4"),
    ]
