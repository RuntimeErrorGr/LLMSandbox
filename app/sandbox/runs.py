import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Run
from app.sandbox import kubernetes as k8s


def parse_params(form: dict[str, str]) -> dict:
    return {
        key.removeprefix("param:"): yaml.safe_load(value)
        for key, value in form.items()
        if key.startswith("param:")
    }


def start(db: Session, module: str, params: dict) -> Run:
    job_name = k8s.start_run(module, params)
    run = Run(job_name=job_name, module=module, namespace=k8s.MODULES_NAMESPACE, params=params)
    db.add(run)
    db.commit()
    return run


def recent(db: Session, limit: int = 20) -> list[Run]:
    return list(db.scalars(select(Run).order_by(Run.id.desc()).limit(limit)))


def status(db: Session, run: Run) -> k8s.RunStatus:
    current = k8s.run_status(run.job_name, run.namespace)
    if current.state != run.state:
        run.state = current.state
        db.commit()
    return current
