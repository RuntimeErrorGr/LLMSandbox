from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.db.models import Run
from app.db.session import DB
from app.sandbox import kubernetes as k8s
from app.sandbox import runs
from app.templating import render

router = APIRouter()


def get_run(db: Session, run_id: int) -> Run:
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404)
    return run


@router.get("/modules")
def modules_page(request: Request, db: DB):
    return render(request, "modules.html", modules=k8s.list_modules(), runs=runs.recent(db))


@router.post("/modules/{module}/run")
async def module_run(module: str, request: Request, db: DB):
    form = await request.form()
    run = runs.start(db, module, runs.parse_params(dict(form)))
    return HTMLResponse(headers={"HX-Redirect": f"/runs/{run.id}"})


@router.get("/partials/runs")
def runs_table(request: Request, db: DB):
    recent = runs.recent(db)
    for run in recent:
        if run.state not in k8s.FINISHED:
            runs.status(db, run)
    return render(request, "partials/runs_table.html", runs=recent)


@router.get("/runs/{run_id}")
def run_page(run_id: int, request: Request, db: DB):
    run = get_run(db, run_id)
    return render(request, "run.html", run=run, status=runs.status(db, run))


@router.get("/partials/runs/{run_id}")
def run_status(run_id: int, request: Request, db: DB):
    run = get_run(db, run_id)
    return render(request, "partials/run_status.html", run=run, status=runs.status(db, run))
