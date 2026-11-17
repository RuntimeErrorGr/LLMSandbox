from sqlalchemy.orm import Session

from app.db.models import ImpactTest
from app.db.session import SessionLocal
from app.sandbox import datasets, runs, scoring

TRAINER = "train-llm"
VARIANTS = (
    ("clean", "A · clean data"),
    ("poisoned", "B · poisoned data"),
    ("cleaned", "C · poisoned data cleaned by the detector"),
)


def save(db: Session, test: ImpactTest, **changes) -> None:
    for name, value in changes.items():
        setattr(test, name, value)
    db.commit()


def scan(db: Session, test: ImpactTest) -> list[int] | None:
    save(db, test, step=f"① scanning {test.suspect} with {test.detector}")
    run = runs.start(db, test.detector, {"dataset": test.suspect})
    status = runs.wait(db, run)
    if status.state != "succeeded" or not status.result:
        return None
    flagged = [item["id"] for item in status.result["suspicious"]]
    key = datasets.answer_key(test.suspect)
    removed = {"count": len(flagged), "scan_run_id": run.id}
    if key:
        grade = scoring.grade(set(flagged), set(key["poisoned_ids"]))
        removed |= {"caught": grade.caught, "poisoned": grade.poisoned}
    save(db, test, removed=removed)
    return flagged


def train(db: Session, test: ImpactTest, variants: dict[str, dict]) -> None:
    started = {name: runs.start(db, TRAINER, params) for name, params in variants.items()}
    for name, run in started.items():
        save(db, test, results={**test.results, name: {"run_id": run.id, "state": "running"}})
    for name, run in started.items():
        status = runs.wait(db, run, timeout=2400)
        metrics = (status.result or {}).get("metrics", {})
        entry = {"run_id": run.id, "state": status.state, **metrics}
        save(db, test, results={**test.results, name: entry})


def run_impact(test_id: int) -> None:
    with SessionLocal() as db:
        test = db.get(ImpactTest, test_id)
        key = datasets.answer_key(test.suspect) or {}
        attack = {"trigger": key.get("trigger"), "target_label": key.get("target_label")}

        flagged = scan(db, test)
        if flagged is None:
            save(db, test, state="failed", step="the scan failed")
            return

        save(db, test, step="② training models A (clean) and B (poisoned) in parallel")
        train(db, test, {
            "clean": {"train_dataset": test.clean, **attack},
            "poisoned": {"train_dataset": test.suspect, **attack},
        })
        save(db, test, step=f"③ training model C without the {len(flagged)} flagged samples")
        train(db, test, {
            "cleaned": {"train_dataset": test.suspect, "exclude_ids": flagged, **attack},
        })

        failed = any(result["state"] != "succeeded" for result in test.results.values())
        save(db, test, state="failed" if failed else "succeeded", step="④ done")
