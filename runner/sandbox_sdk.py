import json
import os
import re
from datetime import datetime
from pathlib import Path

SMOKE_TEST_LIMIT = 50
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")

_result_written = False


def _dir(env_name: str, default: str) -> Path:
    return Path(os.environ.get(env_name, default))


def _safe(name: str) -> str:
    if not SAFE_NAME.match(name) or ".." in name:
        raise ValueError(f"invalid name: {name!r}")
    return name


def params() -> dict:
    return json.loads(os.environ.get("PARAMS_JSON", "{}"))


def is_smoke_test() -> bool:
    return os.environ.get("SMOKE_TEST") == "1"


def load_dataset(name: str) -> list[dict]:
    path = _dir("SANDBOX_DATASETS", "/workspace/datasets") / f"{_safe(name)}.jsonl"
    rows = []
    with path.open() as file:
        for line in file:
            if line.strip():
                row = json.loads(line)
                rows.append(
                    {"id": int(row["id"]), "text": str(row["text"]), "label": int(row["label"])}
                )
            if is_smoke_test() and len(rows) >= SMOKE_TEST_LIMIT:
                break
    return rows


def label_names(name: str) -> list[str]:
    path = _dir("SANDBOX_DATASETS", "/workspace/datasets") / f"{_safe(name)}.meta.json"
    return json.loads(path.read_text())["labels"]


def model_path(name: str) -> str:
    path = _dir("SANDBOX_MODELS", "/workspace/models") / _safe(name)
    if not path.is_dir():
        raise FileNotFoundError(f"model not available offline: {name}")
    return str(path)


def run_dir() -> Path:
    path = _dir("SANDBOX_RUN_DIR", "/workspace/run")
    path.mkdir(parents=True, exist_ok=True)
    return path


def log(message: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {message}", flush=True)


def _clean_suspicious(suspicious: list[dict]) -> list[dict]:
    cleaned = []
    for item in suspicious:
        score = float(item["score"])
        if not 0.0 <= score <= 1.0:
            raise ValueError(f"score must be between 0 and 1, got {score} for id {item['id']}")
        reason = str(item.get("reason", ""))
        cleaned.append({"id": int(item["id"]), "score": round(score, 4), "reason": reason})
    return sorted(cleaned, key=lambda item: item["score"], reverse=True)


def write_result(summary: str, metrics: dict, suspicious: list[dict] | None = None) -> Path:
    global _result_written
    if _result_written:
        raise RuntimeError("write_result must be called exactly once")

    result = {
        "summary": str(summary),
        "metrics": json.loads(json.dumps(metrics)),
        "suspicious": _clean_suspicious(suspicious or []),
    }
    path = run_dir() / "result.json"
    path.write_text(json.dumps(result, indent=2))
    _result_written = True
    log(f"result written: {result['summary']}")
    return path
