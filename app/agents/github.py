import shutil
import subprocess
from pathlib import Path

import httpx

from app.config import settings

REPO_DIR = Path("data/agent-repo")
AUTHOR = ["-c", "user.name=LLM Sandbox Agents", "-c", "user.email=agents@llm-sandbox.local"]


class PublishError(Exception):
    pass


def git(*args: str) -> str:
    result = subprocess.run(["git", "-C", str(REPO_DIR), *args],
                            capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise PublishError(f"git {args[0]} failed: {result.stderr.strip()[:300]}")
    return result.stdout


def pull_request_body(state: dict) -> str:
    design, scores = state["design"], state["benchmark"]["scores"]
    rows = "\n".join(f"| `{exam}` | {score} |" for exam, score in scores.items())
    steps = "\n".join(f"{i}. {step}" for i, step in enumerate(design["steps"], start=1))
    return f"""## {design["title"]}

Threat: `{design["threat"]}` · module `modules/{design["name"]}/`

{state["spec"]["summary"]}

### Method
{design["method"]}

{steps}

### Quality gates passed in the sandbox
- policy checker and lint (ruff)
- smoke test on 50 samples (playground run #{state["smoke"]["run_id"]})
- benchmark on the threat's exams:

| Exam | F1 |
|---|---|
{rows}

### Request
> {state["request"]}

Built by the LLM Sandbox agents (Architect, Security Specialist, DevOps Specialist)
after {state["attempt"]} attempt(s).
Review `main.py` before merging: after the merge ArgoCD deploys it to `sandbox-modules`.
"""


def open_pull_request(folder: Path, state: dict) -> str:
    if not settings.github_token:
        raise PublishError("GITHUB_TOKEN is not set in .env, so no pull request was opened")

    remote = f"https://github.com/{settings.github_repo}.git"
    if not (REPO_DIR / ".git").exists():
        subprocess.run(["git", "clone", "--quiet", remote, str(REPO_DIR)], check=True)
    git("fetch", "--quiet", "origin", "main")
    branch = f"agent/{folder.name}-{state['thread_id'][:8]}"
    git("checkout", "--quiet", "-B", branch, "origin/main")
    git("reset", "--quiet", "--hard", "origin/main")
    git("clean", "--quiet", "-fd")

    if git("ls-tree", "--name-only", "origin/main", f"modules/{folder.name}").strip():
        raise PublishError(f"modules/{folder.name} already exists on main")
    shutil.copytree(folder, REPO_DIR / "modules" / folder.name)
    git("add", f"modules/{folder.name}")
    git(*AUTHOR, "commit", "--quiet", "-m", f"Add {folder.name} detector built by the agents")

    push_url = f"https://x-access-token:{settings.github_token}@github.com/{settings.github_repo}.git"
    git("push", "--quiet", push_url, f"{branch}:{branch}")

    response = httpx.post(
        f"https://api.github.com/repos/{settings.github_repo}/pulls",
        headers={"Authorization": f"Bearer {settings.github_token}",
                 "Accept": "application/vnd.github+json"},
        json={"title": f"Add detector {folder.name}", "head": branch, "base": "main",
              "body": pull_request_body(state)},
        timeout=30,
    )
    if response.status_code >= 300:
        raise PublishError(f"GitHub API error {response.status_code}: {response.text[:200]}")
    return response.json()["html_url"]
