from dataclasses import dataclass

from app.db.models import Run
from app.sandbox import datasets
from app.sandbox.scoring import Grade, grade

MAX_ROWS = 200


@dataclass
class Finding:
    id: int
    score: float
    text: str
    label: str
    reason: str
    poisoned: bool | None


@dataclass
class Report:
    dataset: str
    suspect: bool
    findings: list[Finding]
    total_findings: int
    grade: Grade | None


def build_report(run: Run, result: dict) -> Report:
    name = run.params["dataset"]
    rows = datasets.load_rows(name)
    labels = datasets.label_names(name)
    key = datasets.answer_key(name)
    poisoned_ids = set(key["poisoned_ids"]) if key else None
    suspicious = result.get("suspicious", [])

    findings = [
        Finding(
            id=item["id"],
            score=item["score"],
            text=rows[item["id"]]["text"],
            label=labels[rows[item["id"]]["label"]],
            reason=item["reason"],
            poisoned=None if poisoned_ids is None else item["id"] in poisoned_ids,
        )
        for item in suspicious[:MAX_ROWS]
    ]
    flagged = {item["id"] for item in suspicious}
    return Report(
        dataset=name,
        suspect=key is not None,
        findings=findings,
        total_findings=len(suspicious),
        grade=grade(flagged, poisoned_ids) if poisoned_ids is not None else None,
    )
