import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Run
from app.sandbox import datasets
from app.sandbox import kubernetes as k8s


def parse_params(form: dict[str, str]) -> dict:
    return {
        key.removeprefix("param:"): yaml.safe_load(value)
        for key, value in form.items()
        if key.startswith("param:")
    }


def start(db: Session, module: str, params: dict) -> Run:
    kind = k8s.get_module(module).kind
    job_name = k8s.start_run(module, params)
    run = Run(
        job_name=job_name,
        module=module,
        kind=kind,
        namespace=k8s.MODULES_NAMESPACE,
        params=params,
    )
    db.add(run)
    db.commit()
    return run


def recent(db: Session, limit: int = 20, kind: str | None = None) -> list[Run]:
    query = select(Run).order_by(Run.id.desc()).limit(limit)
    if kind:
        query = query.where(Run.kind == kind)
    return list(db.scalars(query))


def after_success(run: Run) -> str:
    if run.kind != "poisoner":
        return ""
    if not (datasets.RUNS_DIR / run.job_name / "answer_key.json").exists():
        return ""
    params = {**k8s.get_module(run.module, run.namespace).params, **run.params}
    try:
        target = datasets.publish_poisoned(run.job_name, params["dataset"], params["output"])
    except (ValueError, FileNotFoundError) as error:
        return f"publish failed: {error}"
    return f"published {target.name} (answer key stored outside the sandbox)"


def status(db: Session, run: Run) -> k8s.RunStatus:
    current = k8s.run_status(run.job_name, run.namespace)
    if current.state != run.state:
        if current.state == "succeeded":
            current.detail = after_success(run)
        run.state = current.state
        db.commit()
    return current
