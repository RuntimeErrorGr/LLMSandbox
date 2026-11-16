import sys
from dataclasses import dataclass, field

from sqlalchemy import select

from app.db.models import ExamResult
from app.db.session import SessionLocal
from app.sandbox import catalog, datasets, runs, scoring
from app.sandbox import kubernetes as k8s


@dataclass
class Row:
    detector: str
    results: dict[str, ExamResult] = field(default_factory=dict)

    def verdict(self, threat: catalog.Threat) -> str:
        results = [self.results.get(exam.dataset) for exam in threat.exams]
        if not any(results):
            return "not benchmarked"
        if any(result and result.state == "running" for result in results):
            return "running"
        passed = all(result and result.f1 is not None and result.f1 >= threat.pass_f1
                     for result in results)
        return "pass" if passed else "fail"


def run_benchmark(detector: str, namespace: str = k8s.MODULES_NAMESPACE) -> list[ExamResult]:
    with SessionLocal() as db:
        threat = catalog.THREATS[k8s.get_module(detector, namespace).threat]
        started = []
        for exam in threat.exams:
            run = runs.start(db, detector, {"dataset": exam.dataset}, namespace)
            result = ExamResult(
                detector=detector, threat=threat.id, exam=exam.dataset, run_id=run.id
            )
            db.add(result)
            db.commit()
            started.append((run, result))

        for run, result in started:
            status = runs.wait(db, run)
            if status.state == "succeeded" and status.result:
                flagged = {item["id"] for item in status.result["suspicious"]}
                poisoned = set(datasets.answer_key(result.exam)["poisoned_ids"])
                grade = scoring.grade(flagged, poisoned)
                result.flagged, result.caught, result.poisoned = (
                    grade.flagged, grade.caught, grade.poisoned
                )
                result.precision, result.recall, result.f1 = grade.precision, grade.recall, grade.f1
            result.state = status.state
            db.commit()
        return [result for _, result in started]


def leaderboard() -> dict[str, list[Row]]:
    with SessionLocal() as db:
        results = db.scalars(select(ExamResult).order_by(ExamResult.id.desc())).all()
    detectors = [module for module in k8s.list_modules() if module.kind == "detector"]

    board = {threat_id: {} for threat_id in catalog.THREATS}
    for module in detectors:
        if module.threat in board:
            board[module.threat][module.name] = Row(module.name)
    for result in results:
        row = board[result.threat].setdefault(result.detector, Row(result.detector))
        row.results.setdefault(result.exam, result)
    return {threat_id: list(rows.values()) for threat_id, rows in board.items()}


if __name__ == "__main__":
    for exam_result in run_benchmark(sys.argv[1]):
        print(f"{exam_result.exam:17} {exam_result.state:9} F1 {exam_result.f1}  "
              f"caught {exam_result.caught}/{exam_result.poisoned}  flagged {exam_result.flagged}")
