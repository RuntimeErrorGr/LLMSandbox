import sys

from app.db.session import SessionLocal
from app.sandbox import catalog, datasets, runs

DEMO_TARGETS = [
    ("poison-label-flip", {"dataset": "sst2_train", "output": "sst2_suspect_a", "rate": 0.15}),
    ("poison-clean-label", {"dataset": "sst2_train", "output": "sst2_suspect_b", "rate": 0.15}),
    ("poison-label-flip", {"dataset": "agnews_train", "output": "agnews_suspect_c", "rate": 0.10}),
]


def targets() -> list[tuple[str, dict]]:
    exams = [
        (exam.poisoner, {**exam.params, "output": exam.dataset})
        for threat in catalog.THREATS.values()
        for exam in threat.exams
    ]
    return DEMO_TARGETS + exams


def main(force: bool) -> None:
    with SessionLocal() as db:
        for module, params in targets():
            if datasets.answer_key(params["output"]) and not force:
                print(f"skip     {params['output']} (already created)")
                continue
            run = runs.start(db, module, params)
            print(f"started  {run.job_name}  {params}")
            status = runs.wait(db, run)
            summary = (status.result or {}).get("summary", "")
            print(f"{status.state:9}{run.job_name}  {summary}  {status.detail}")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
