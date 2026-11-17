import operator
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Annotated, TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app import guard
from app.agents import architect, github, specialists
from app.agents.schemas import DeploymentSpec, ModuleDesign
from app.db.session import SessionLocal
from app.sandbox import benchmark, catalog, policy, runs
from app.sandbox import kubernetes as k8s

BUILDS_DIR = Path("data/agent-builds")
MAX_ATTEMPTS = 3


class BuildState(TypedDict, total=False):
    request: str
    thread_id: str
    guard: dict
    design: dict
    code: str
    spec: dict
    folder: str
    attempt: int
    feedback: str
    checks: list[str]
    smoke: dict
    benchmark: dict
    status: str
    pr_url: str
    events: Annotated[list[dict], operator.add]


def event(stage: str, message: str, ok: bool | None = True) -> list[dict]:
    return [{"stage": stage, "message": message, "ok": ok, "time": f"{datetime.now():%H:%M:%S}"}]


def guard_node(state: BuildState) -> BuildState:
    verdict = guard.check(state["request"], source="agent-request")
    if verdict.blocked:
        return {"guard": verdict.as_dict(), "status": "blocked",
                "events": event("guard", f"blocked: {verdict.reason}", ok=False)}
    return {"guard": verdict.as_dict(), "events": event("guard", "request allowed")}


def architect_node(state: BuildState) -> BuildState:
    design, documents = architect.design_module(state["request"])
    message = f"designed {design.name} ({design.threat}) from {len(documents)} knowledge chunks"
    return {"design": design.model_dump(), "attempt": 0, "feedback": "",
            "events": event("architect", message)}


def security_node(state: BuildState) -> BuildState:
    attempt = state.get("attempt", 0) + 1
    design = ModuleDesign(**state["design"])
    code = specialists.write_code(design, state.get("feedback", ""), state.get("code", ""))
    message = f"attempt {attempt}: wrote main.py ({len(code.splitlines())} lines)"
    return {"code": code, "attempt": attempt, "events": event("security", message)}


def devops_node(state: BuildState) -> BuildState:
    design = ModuleDesign(**state["design"])
    spec = state.get("spec")
    spec = DeploymentSpec(**spec) if spec else specialists.plan_deployment(design, state["code"])
    folder = specialists.render_module(design, state["code"], spec, BUILDS_DIR / state["thread_id"])
    message = f"packaged {folder.name}: cpu {spec.cpu_limit}, memory {spec.memory_limit}"
    return {"spec": spec.model_dump(), "folder": str(folder), "events": event("devops", message)}


def static_problems(folder: Path) -> list[str]:
    problems = [f"policy: {violation.message}" for violation in policy.check_module(folder)]
    lint = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--select", "F,E9", "--no-cache",
         "--output-format", "concise", str(folder / "main.py")],
        capture_output=True, text=True, check=False,
    )
    problems += [f"lint: {line.split(':', 1)[1].strip()}" for line in lint.stdout.splitlines()
                 if line.startswith(str(folder))]
    return problems


def checks_node(state: BuildState) -> BuildState:
    problems = static_problems(Path(state["folder"]))
    if problems:
        return {"checks": problems, "feedback": "\n".join(problems),
                "events": event("checks", f"{len(problems)} problem(s): {problems[0]}", ok=False)}
    return {"checks": [], "events": event("checks", "policy and static checks passed")}


def smoke_node(state: BuildState) -> BuildState:
    folder = Path(state["folder"])
    k8s.deploy_playground(folder)
    dataset = architect.DEMO_DATASETS[state["design"]["threat"]]
    with SessionLocal() as db:
        run = runs.start(db, folder.name, {"dataset": dataset}, k8s.PLAYGROUND_NAMESPACE,
                         env={"SMOKE_TEST": "1"})
        status = runs.wait(db, run, timeout=600)
    smoke = {"run_id": run.id, "state": status.state}
    if status.state != "succeeded" or not status.result:
        logs = status.logs[-1500:] or status.detail
        return {"smoke": smoke, "feedback": f"The smoke test (50 samples) failed. Logs:\n{logs}",
                "events": event("smoke", "smoke test failed, logs sent back", ok=False)}
    message = f"smoke test passed: {status.result['summary']}"
    return {"smoke": smoke, "events": event("smoke", message)}


def benchmark_node(state: BuildState) -> BuildState:
    name = Path(state["folder"]).name
    threat = catalog.THREATS[state["design"]["threat"]]
    results = benchmark.run_benchmark(name, k8s.PLAYGROUND_NAMESPACE)
    scores = {result.exam: result.f1 for result in results}
    passed = all(score is not None and score >= threat.pass_f1 for score in scores.values())
    summary = ", ".join(f"{exam} F1 {score}" for exam, score in scores.items())
    if passed:
        return {"benchmark": {"scores": scores, "passed": True},
                "events": event("benchmark", f"passed: {summary}")}
    details = "\n".join(
        f"- {r.exam}: F1 {r.f1}, caught {r.caught} of {r.poisoned} poisoned, flagged {r.flagged}"
        for r in results
    )
    feedback = (f"The detector runs but fails the benchmark (needs F1 >= {threat.pass_f1} on every "
                f"exam).\n{details}\nRe-read the design steps and fix the logic.")
    return {"benchmark": {"scores": scores, "passed": False}, "feedback": feedback,
            "events": event("benchmark", f"failed: {summary}", ok=False)}


def approval_node(state: BuildState) -> BuildState:
    decision = interrupt({"question": "Approve this detector and open a pull request?"})
    if decision.get("approved"):
        return {"status": "approved", "events": event("approval", "approved by a human")}
    return {"status": "rejected", "events": event("approval", "rejected by a human", ok=False)}


def publish_node(state: BuildState) -> BuildState:
    try:
        url = github.open_pull_request(Path(state["folder"]), state)
    except github.PublishError as error:
        return {"status": "publish_failed", "events": event("publish", str(error), ok=False)}
    return {"status": "pr_opened", "pr_url": url,
            "events": event("publish", f"pull request: {url}")}


def after_guard(state: BuildState) -> str:
    return END if state.get("status") == "blocked" else "architect"


def retry_or_give_up(state: BuildState) -> str:
    return "security" if state["attempt"] < MAX_ATTEMPTS else "give_up"


def after_checks(state: BuildState) -> str:
    return "smoke" if not state["checks"] else retry_or_give_up(state)


def after_smoke(state: BuildState) -> str:
    return "benchmark" if state["smoke"]["state"] == "succeeded" else retry_or_give_up(state)


def after_benchmark(state: BuildState) -> str:
    return "approval" if state["benchmark"]["passed"] else retry_or_give_up(state)


def after_approval(state: BuildState) -> str:
    return "publish" if state["status"] == "approved" else END


def after_publish(state: BuildState) -> str:
    return "approval" if state["status"] == "publish_failed" else END


def give_up_node(state: BuildState) -> BuildState:
    message = f"gave up after {state['attempt']} attempts; nothing was published"
    return {"status": "failed", "events": event("security", message, ok=False)}


def build_graph() -> StateGraph:
    graph = StateGraph(BuildState)
    for name, node in [
        ("guard", guard_node), ("architect", architect_node), ("security", security_node),
        ("devops", devops_node), ("checks", checks_node), ("smoke", smoke_node),
        ("benchmark", benchmark_node), ("approval", approval_node), ("publish", publish_node),
        ("give_up", give_up_node),
    ]:
        graph.add_node(name, node)
    graph.add_edge(START, "guard")
    graph.add_conditional_edges("guard", after_guard)
    graph.add_edge("architect", "security")
    graph.add_edge("security", "devops")
    graph.add_edge("devops", "checks")
    graph.add_conditional_edges("checks", after_checks)
    graph.add_conditional_edges("smoke", after_smoke)
    graph.add_conditional_edges("benchmark", after_benchmark)
    graph.add_conditional_edges("approval", after_approval)
    graph.add_conditional_edges("publish", after_publish)
    graph.add_edge("give_up", END)
    return graph


checkpointer = SqliteSaver(sqlite3.connect("data/agents.db", check_same_thread=False))
pipeline = build_graph().compile(checkpointer=checkpointer)
