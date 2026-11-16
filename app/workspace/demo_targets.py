import time

from app.db.session import SessionLocal
from app.sandbox import kubernetes as k8s
from app.sandbox import runs

TIMEOUT_SECONDS = 600

TARGETS = [
    ("poison-label-flip", {"dataset": "sst2_train", "output": "sst2_suspect_a", "rate": 0.15}),
    ("poison-label-flip", {"dataset": "agnews_train", "output": "agnews_suspect_c", "rate": 0.10}),
]


def run_and_wait(module: str, params: dict) -> None:
    with SessionLocal() as db:
        run = runs.start(db, module, params)
        print(f"started  {run.job_name}  {params}")
        deadline = time.time() + TIMEOUT_SECONDS
        while time.time() < deadline:
            status = runs.status(db, run)
            if status.state in k8s.FINISHED:
                summary = (status.result or {}).get("summary", "")
                print(f"{status.state:9}{run.job_name}  {summary}  {status.detail}")
                return
            time.sleep(2)
        print(f"timeout  {run.job_name}")


if __name__ == "__main__":
    for module, params in TARGETS:
        run_and_wait(module, params)
