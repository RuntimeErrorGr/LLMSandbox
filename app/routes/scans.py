from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from app.db.session import DB
from app.routes.modules import get_run
from app.sandbox import datasets, runs, scans
from app.sandbox import kubernetes as k8s
from app.templating import render

router = APIRouter()


def scan_context(db: DB, run_id: int) -> dict:
    run = get_run(db, run_id)
    status = runs.status(db, run)
    report = scans.build_report(run, status.result) if status.result else None
    return {"run": run, "status": status, "report": report}


@router.get("/scan")
def scan_page(request: Request, db: DB):
    detectors = [module for module in k8s.list_modules() if module.kind == "detector"]
    context = {
        "detectors": detectors,
        "datasets": datasets.list_datasets(),
        "scans": runs.recent(db, kind="detector"),
    }
    return render(request, "scan.html", **context)


@router.post("/scan")
def scan_start(db: DB, detector: Annotated[str, Form()], dataset: Annotated[str, Form()]):
    run = runs.start(db, detector, {"dataset": dataset})
    return HTMLResponse(headers={"HX-Redirect": f"/scans/{run.id}"})


@router.get("/scans/{run_id}")
def scan_report_page(run_id: int, request: Request, db: DB):
    return render(request, "scan_report.html", **scan_context(db, run_id))


@router.get("/partials/scans/{run_id}")
def scan_report_partial(run_id: int, request: Request, db: DB):
    return render(request, "partials/scan_report.html", **scan_context(db, run_id))
