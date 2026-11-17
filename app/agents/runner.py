import threading
import traceback
import uuid

from langgraph.types import Command

from app.agents.graph import pipeline
from app.db.models import AgentRun
from app.db.session import SessionLocal


def config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}, "recursion_limit": 60}


def state(run: AgentRun) -> dict:
    return pipeline.get_state(config(run.thread_id)).values


def _execute(run_id: int, payload) -> None:
    with SessionLocal() as db:
        run = db.get(AgentRun, run_id)
        try:
            pipeline.invoke(payload, config(run.thread_id))
            snapshot = pipeline.get_state(config(run.thread_id))
            finished = snapshot.values.get("status", "done")
            run.status = "awaiting_approval" if snapshot.next else finished
            run.detail = ""
        except Exception as error:
            run.status = "error"
            run.detail = f"{type(error).__name__}: {error}"
            traceback.print_exc()
        db.commit()


def _background(run_id: int, payload) -> None:
    threading.Thread(target=_execute, args=(run_id, payload), daemon=True).start()


def start(request: str) -> int:
    with SessionLocal() as db:
        run = AgentRun(request=request, thread_id=str(uuid.uuid4()))
        db.add(run)
        db.commit()
        payload = {"request": request, "thread_id": run.thread_id, "events": []}
        run_id = run.id
    _background(run_id, payload)
    return run_id


def _set_running(run_id: int) -> None:
    with SessionLocal() as db:
        run = db.get(AgentRun, run_id)
        run.status = "running"
        db.commit()


def decide(run_id: int, approved: bool) -> None:
    _set_running(run_id)
    _background(run_id, Command(resume={"approved": approved}))


def resume(run_id: int) -> None:
    _set_running(run_id)
    _background(run_id, None)


def mark_interrupted() -> None:
    with SessionLocal() as db:
        for run in db.query(AgentRun).filter(AgentRun.status == "running"):
            run.status = "interrupted"
        db.commit()
