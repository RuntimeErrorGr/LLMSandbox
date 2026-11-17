from app.api.agents import next_stage, stages
from app.db.models import AgentRun


def event(stage: str, ok: bool = True) -> dict:
    return {"stage": stage, "message": f"{stage} message", "ok": ok, "time": "12:00:00"}


def states(status: str, events: list[dict]) -> dict[str, str]:
    run = AgentRun(request="r", thread_id="t", status=status)
    return {stage.key: stage.state for stage in stages(run, events)}


def test_next_stage_follows_the_pipeline_and_retries_from_security():
    assert next_stage([]) == "guard"
    assert next_stage([event("guard"), event("architect")]) == "security"
    assert next_stage([event("checks", ok=False)]) == "security"
    assert next_stage([event("benchmark", ok=False)]) == "security"
    assert next_stage([event("publish")]) is None


def test_running_run_marks_the_next_stage_running():
    result = states("running", [event("guard"), event("architect")])
    assert (result["guard"], result["architect"], result["security"]) == ("done", "done", "running")
    assert result["benchmark"] == "pending"


def test_retry_resets_the_stages_after_security():
    events = [event("guard"), event("architect"), event("security"), event("devops"),
              event("checks", ok=False), event("security")]
    result = states("running", events)
    assert result["security"] == "done"
    assert result["devops"] == "running"
    assert result["checks"] == "pending"


def test_awaiting_approval_is_waiting():
    events = [event(key) for key in ("guard", "architect", "security", "devops", "checks",
                                     "smoke", "benchmark")]
    result = states("awaiting_approval", events)
    assert result["benchmark"] == "done"
    assert result["approval"] == "waiting"
    assert result["publish"] == "pending"
