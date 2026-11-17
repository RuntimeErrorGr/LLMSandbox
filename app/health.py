from dataclasses import dataclass

import httpx

from app.config import settings
from app.sandbox import kubernetes as k8s


@dataclass
class Check:
    name: str
    state: str
    detail: str


def _with_tag(model: str) -> str:
    return model if ":" in model else f"{model}:latest"


def ollama_check() -> Check:
    name = "Ollama"
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
    name = "Kubernetes"
    try:
        return Check(name, "ok", k8s.cluster_summary())
    except k8s.CLUSTER_ERRORS as error:
        reason = type(error).__name__
        return Check(name, "down", f"not reachable ({reason}), run: make cluster argocd bootstrap")


def gitops_apps() -> list[k8s.ArgoApp]:
    try:
        return k8s.argocd_apps()
    except k8s.CLUSTER_ERRORS:
        return []


def argocd_check(apps: list[k8s.ArgoApp]) -> Check:
    name = "ArgoCD"
    if not apps:
        return Check(name, "down", "no applications found, run: make argocd bootstrap")
    broken = [app.name for app in apps if not app.ok]
    if broken:
        return Check(name, "down", f"not Synced/Healthy: {', '.join(broken)}")
    return Check(name, "ok", f"{len(apps)} apps Synced/Healthy at commit {apps[0].revision}")


def all_checks(apps: list[k8s.ArgoApp]) -> list[Check]:
    return [ollama_check(), kubernetes_check(), argocd_check(apps)]
