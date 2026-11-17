from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api import schemas
from app.db.models import ExamResult, Run
from app.db.session import DB
from app.sandbox import background, benchmark, catalog, inventory, scans
from app.sandbox import kubernetes as k8s

router = APIRouter(prefix="/api", tags=["leaderboard"])
TOP_FINDINGS = 25


def score(result: ExamResult | None, exam: str) -> schemas.ExamScore | None:
    if result is None:
        return None
    return schemas.ExamScore(
        exam=exam, state=result.state, f1=result.f1, precision=result.precision,
        recall=result.recall, caught=result.caught, poisoned=result.poisoned,
        flagged=result.flagged, run_id=result.run_id,
    )


def mean_f1(scores: list[schemas.ExamScore], exams: int) -> float | None:
    values = [item.f1 for item in scores if item.f1 is not None]
    return round(sum(values) / exams, 3) if values else None


@router.get("/leaderboard", response_model=list[schemas.ThreatBoard])
def get_leaderboard():
    deployed = k8s.deployed_detectors()
    boards = []
    for threat_id, rows in benchmark.leaderboard(list(deployed.values())).items():
        threat = catalog.THREATS[threat_id]
        detectors = []
        for row in rows:
            info = inventory.module_info(row.detector)
            scores = [s for exam in threat.exams
                      if (s := score(row.results.get(exam.dataset), exam.dataset))]
            detectors.append(schemas.DetectorRow(
                name=row.detector, origin=info["origin"], deployed=row.detector in deployed,
                description=info["description"], verdict=row.verdict(threat),
                mean_f1=mean_f1(scores, len(threat.exams)), scores=scores,
            ))
        detectors.sort(key=lambda d: (d.verdict != "pass", -(d.mean_f1 or 0)))
        boards.append(schemas.ThreatBoard(
            threat=threat.id, title=threat.title, pass_f1=threat.pass_f1,
            exams=[exam.dataset for exam in threat.exams], detectors=detectors,
        ))
    return boards


@router.get("/detectors/{name}", response_model=schemas.Detector)
def get_detector(name: str, db: DB):
    info = inventory.module_info(name)
    results = db.scalars(
        select(ExamResult).where(ExamResult.detector == name).order_by(ExamResult.id.desc())
    ).all()
    if info["origin"] == "unknown" and not results:
        raise HTTPException(status_code=404, detail=f"unknown detector {name}")

    threat = catalog.THREATS.get(info.get("threat") or (results[0].threat if results else ""))
    latest = {}
    for result in results:
        latest.setdefault(result.exam, result)

    exams = []
    for exam in threat.exams if threat else []:
        result = latest.get(exam.dataset)
        if result is None:
            continue
        run = db.get(Run, result.run_id)
        output = k8s.read_result(run.job_name) if run else None
        report = scans.build_report(run, output) if output else None
        top = report.findings[:TOP_FINDINGS] if report else []
        findings = [schemas.Finding(**vars(item)) for item in top]
        exams.append(schemas.ExamDetail(
            **score(result, exam.dataset).model_dump(), findings=findings,
            total_findings=report.total_findings if report else 0,
        ))

    row = benchmark.Row(name, latest)
    return schemas.Detector(
        name=name, threat=threat.id if threat else None, origin=info["origin"],
        deployed=name in k8s.deployed_detectors(), description=info["description"],
        params=info["params"], code=info["code"],
        verdict=row.verdict(threat) if threat else "not benchmarked", exams=exams,
    )


@router.post("/detectors/{name}/benchmark", status_code=202)
def start_benchmark(name: str):
    if name not in k8s.deployed_detectors():
        raise HTTPException(status_code=409, detail=f"{name} is not deployed in sandbox-modules")
    background.start(benchmark.run_benchmark, name)
    return {"detector": name}
