from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from app.db.models import ImpactTest
from app.db.session import DB
from app.sandbox import catalog, datasets, impact
from app.sandbox import kubernetes as k8s
from app.templating import render

router = APIRouter()


def get_test(db: DB, test_id: int) -> ImpactTest:
    test = db.get(ImpactTest, test_id)
    if test is None:
        raise HTTPException(status_code=404)
    return test


@router.get("/impact")
def impact_page(request: Request, db: DB):
    available = [d for d in datasets.list_datasets() if d.name not in catalog.exam_datasets()]
    context = {
        "suspects": [d for d in available if d.suspect],
        "cleans": [d for d in available if not d.suspect and d.name.endswith("_train")],
        "detectors": [m for m in k8s.list_modules() if m.kind == "detector"],
        "tests": db.scalars(select(ImpactTest).order_by(ImpactTest.id.desc()).limit(10)).all(),
    }
    return render(request, "impact.html", **context)


@router.post("/impact")
def impact_start(
    db: DB,
    tasks: BackgroundTasks,
    suspect: Annotated[str, Form()],
    clean: Annotated[str, Form()],
    detector: Annotated[str, Form()],
):
    test = ImpactTest(suspect=suspect, clean=clean, detector=detector, removed={}, results={})
    db.add(test)
    db.commit()
    tasks.add_task(impact.run_impact, test.id)
    return HTMLResponse(headers={"HX-Redirect": f"/impact/{test.id}"})


@router.get("/impact/{test_id}")
def impact_report(test_id: int, request: Request, db: DB):
    return render(request, "impact_report.html", test=get_test(db, test_id),
                  variants=impact.VARIANTS)


@router.get("/partials/impact/{test_id}")
def impact_partial(test_id: int, request: Request, db: DB):
    return render(request, "partials/impact_report.html", test=get_test(db, test_id),
                  variants=impact.VARIANTS)
