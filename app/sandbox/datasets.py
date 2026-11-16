import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

WORKSPACE = Path("data/workspace")
DATASETS_DIR = WORKSPACE / "datasets"
ANSWERS_DIR = WORKSPACE / "answers"
RUNS_DIR = WORKSPACE / "runs"
SAFE_NAME = re.compile(r"^[a-z0-9][a-z0-9_]*$")


@dataclass
class Dataset:
    name: str
    samples: int
    labels: list[str]
    suspect: bool


def list_datasets() -> list[Dataset]:
    datasets = []
    for path in sorted(DATASETS_DIR.glob("*.jsonl")):
        meta = json.loads(path.with_suffix(".meta.json").read_text())
        with path.open() as file:
            samples = sum(1 for line in file if line.strip())
        suspect = (ANSWERS_DIR / f"{path.stem}.json").exists()
        datasets.append(Dataset(path.stem, samples, meta["labels"], suspect))
    return datasets


def answer_key(name: str) -> dict | None:
    path = ANSWERS_DIR / f"{name}.json"
    return json.loads(path.read_text()) if path.exists() else None


def publish_poisoned(job_name: str, source: str, output: str) -> Path:
    if not SAFE_NAME.match(output):
        raise ValueError(f"invalid dataset name: {output!r}")
    target = DATASETS_DIR / f"{output}.jsonl"
    if target.exists() and answer_key(output) is None:
        raise ValueError(f"refusing to overwrite the clean dataset {output!r}")

    run_dir = RUNS_DIR / job_name
    ANSWERS_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(run_dir / "poisoned.jsonl", target)
    shutil.copyfile(DATASETS_DIR / f"{source}.meta.json", target.with_suffix(".meta.json"))
    shutil.move(run_dir / "answer_key.json", ANSWERS_DIR / f"{output}.json")
    (run_dir / "poisoned.jsonl").unlink()
    return target
