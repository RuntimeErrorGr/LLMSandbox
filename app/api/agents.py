from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.agents import runner
from app.agents.graph import MAX_ATTEMPTS
from app.api import schemas
from app.db.models import AgentRun
from app.db.session import DB
from app.sandbox import catalog

router = APIRouter(prefix="/api/agents/runs", tags=["agents"])

STAGES = [
    ("guard", "Guard", "Blocks prompt injection and requests that would weaken the sandbox"),
    ("architect", "Architect", "Designs the detector from the knowledge base"),
    ("security", "Security Specialist", "Writes main.py against the module contract"),
    ("devops", "DevOps Specialist", "Chooses resources and renders the hardened manifests"),
    ("checks", "Policy and static checks", "Sandbox policy and undefined names"),
    ("smoke", "Smoke test", "Runs on 50 samples in sandbox-playground"),
    ("benchmark", "Benchmark", "F1 on every exam of the threat"),
    ("approval", "Human approval", "Review the design, the code and the scores"),
    ("publish", "Pull request", "Branch, commit, GitHub pull request"),
]
ORDER = [key for key, _, _ in STAGES]
RETRY_FROM = {"checks", "smoke", "benchmark"}


def next_stage(events: list[dict]) -> str | None:
    if not events:
        return ORDER[0]
    last = events[-1]
    if not last["ok"] and last["stage"] in RETRY_FROM:
        return "security"
    position = ORDER.index(last["stage"])
    return ORDER[position + 1] if position + 1 < len(ORDER) else None


def stages(run: AgentRun, events: list[dict]) -> list[schemas.AgentStage]:
    latest = {}
    for index, item in enumerate(events):
        latest[item["stage"]] = (index, item)
    last_security = latest.get("security", (-1, None))[0]
    running = next_stage(events) if run.status == "running" else None

    result = []
    for key, title, description in STAGES:
        index, item = latest.get(key, (-1, None))
        stale = ORDER.index(key) > ORDER.index("security") and index < last_security
        if key == running:
            state, message, time = "running", "", ""
        elif key == "approval" and run.status == "awaiting_approval":
            state, message, time = "waiting", "Waiting for your decision", ""
        elif item is None or stale:
            state, message, time = "pending", "", ""
        else:
            state = "done" if item["ok"] else "failed"
            message, time = item["message"], item["time"]
        result.append(schemas.AgentStage(key=key, title=title, description=description,
                                         state=state, message=message, time=time))
    return result


def summary(run: AgentRun, state: dict) -> schemas.AgentRunSummary:
    design = state.get("design") or {}
    return schemas.AgentRunSummary(id=run.id, request=run.request, status=run.status,
                                   detector=design.get("name"), threat=design.get("threat"),
                                   created_at=run.created_at)


def get_agent_run(db: DB, run_id: int) -> AgentRun:
    run = db.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(status_code=404)
    return run


@router.get("", response_model=list[schemas.AgentRunSummary])
def list_runs(db: DB):
    runs = db.scalars(select(AgentRun).order_by(AgentRun.id.desc()).limit(30)).all()
    return [summary(run, runner.state(run)) for run in runs]


@router.post("", response_model=schemas.Started, status_code=202)
def start_run(body: schemas.AgentRunStart):
    return schemas.Started(id=runner.start(body.request.strip()))


@router.get("/{run_id}", response_model=schemas.AgentRun)
def get_run(run_id: int, db: DB):
    run = get_agent_run(db, run_id)
    state = runner.state(run)
    events = state.get("events", [])
    design = state.get("design")
    benchmark = None
    if state.get("benchmark"):
        threat = catalog.THREATS[design["threat"]]
        benchmark = schemas.AgentBenchmark(
            passed=state["benchmark"]["passed"], pass_f1=threat.pass_f1,
            scores=[schemas.BenchmarkScore(exam=exam, f1=f1)
                    for exam, f1 in state["benchmark"]["scores"].items()],
        )
    return schemas.AgentRun(
        **summary(run, state).model_dump(), detail=run.detail,
        attempt=state.get("attempt", 0), max_attempts=MAX_ATTEMPTS,
        stages=stages(run, events), design=design, code=state.get("code", ""),
        spec=state.get("spec"), checks=state.get("checks", []),
        feedback=state.get("feedback", ""), benchmark=benchmark, guard=state.get("guard"),
        pr_url=state.get("pr_url"), events=events,
    )


@router.post("/{run_id}/{action}", status_code=202)
def act(run_id: int, action: str, db: DB):
    run = get_agent_run(db, run_id)
    if action in {"approve", "reject"} and run.status != "awaiting_approval":
        raise HTTPException(status_code=409, detail="this run is not waiting for approval")
    if action == "approve":
        runner.decide(run_id, approved=True)
    elif action == "reject":
        runner.decide(run_id, approved=False)
    elif action == "continue" and run.status in {"interrupted", "error"}:
        runner.resume(run_id)
    else:
        raise HTTPException(status_code=409, detail=f"cannot {action} a run that is {run.status}")
    return {"id": run_id, "action": action}
