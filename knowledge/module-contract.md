# Module contract

Every module (detector, poisoner, trainer) follows the same contract so the platform can run, test and benchmark it.

## Folder layout

A module lives in `modules/<name>/` and contains exactly these files:

- `main.py`: the program. It is mounted into the container and run with `python /module/main.py`.
- `module.yaml`: metadata (name, kind, threat, description, params with defaults).
- `cronjob.yaml`: the Kubernetes job template (suspended CronJob).
- `kustomization.yaml`: tells Kustomize to package `main.py` and `module.yaml` into a ConfigMap mounted at `/module`.

Module names use lowercase letters, digits and dashes, for example `detect-label-flip-knn`.

## module.yaml example

```yaml
name: detect-label-flip-knn
kind: detector
threat: label_flip
description: Flags samples whose nearest neighbours mostly have a different label.
params:
  dataset: sst2_suspect_A
  k: 10
  threshold: 0.6
```

## Dataset format

Datasets are JSON Lines files in `/workspace/datasets/<name>.jsonl`, one sample per line:

```json
{"id": 17, "text": "a wonderful, moving film", "label": 1}
```

- `id`: unique integer inside the dataset.
- `text`: the input sentence.
- `label`: integer class id.

Label names are in `/workspace/datasets/<name>.meta.json`, for example `{"labels": ["negative", "positive"]}`.

## The sandbox_sdk helper library

Modules must use `sandbox_sdk` for all input and output:

```python
import sandbox_sdk as sdk

params = sdk.params()
rows = sdk.load_dataset(params["dataset"])
labels = sdk.label_names(params["dataset"])
sdk.log(f"loaded {len(rows)} samples")

suspicious = [{"id": 17, "score": 0.93, "reason": "9 of 10 neighbours disagree"}]
sdk.write_result(
    summary=f"{len(suspicious)} suspicious samples found",
    metrics={"scanned": len(rows), "flagged": len(suspicious)},
    suspicious=suspicious,
)
```

| function | what it does |
|---|---|
| `sdk.params()` | returns the run parameters (defaults from module.yaml merged with the values chosen in the UI) |
| `sdk.load_dataset(name)` | returns a list of dicts with keys id, text, label |
| `sdk.label_names(name)` | returns the list of label names |
| `sdk.is_smoke_test()` | True during the smoke test; `load_dataset` then returns only the first 50 samples, so the module must also work on small data |
| `sdk.model_path(name)` | local folder of a pre-downloaded model, for example `sdk.model_path("bge-small-en-v1.5")` |
| `sdk.run_dir()` | folder of this run (`/workspace/run`), the only writable place besides `/tmp`; it is created by the platform before the run starts |
| `sdk.log(message)` | prints a progress line visible in the UI |
| `sdk.write_result(summary, metrics, suspicious)` | writes `result.json`; must be called exactly once at the end |

## Result format

`write_result` creates `result.json` in the run folder:

```json
{
  "summary": "38 suspicious samples found",
  "metrics": {"scanned": 2000, "flagged": 38},
  "suspicious": [{"id": 17, "score": 0.93, "reason": "9 of 10 neighbours disagree"}]
}
```

- A detector must fill `suspicious`, sorted by score from highest to lowest. Score is between 0 and 1.
- Poisoners and trainers leave `suspicious` empty and report their numbers in `metrics`.
- A module exits with code 0 on success. Any exception means the run failed.

## Available libraries

The runner image provides: numpy, pandas, scikit-learn, torch (CPU), transformers, sentence-transformers, chromadb, and the Python standard library.

Available models (offline, via `sdk.model_path`): `bge-small-en-v1.5` (sentence embeddings, 384 numbers), `SmolLM2-135M` (victim LLM).

## Code style

Every module is reviewed by a human before it is merged, so the code must read like the method it
implements. All reference modules in `modules/` follow this layout:

```python
import sandbox_sdk as sdk

MIN_COUNT = 20


def main() -> None:
    params = sdk.params()
    rows = sdk.load_dataset(params["dataset"])
    signal = compute_signal(rows)
    suspicious = flag_suspicious_rows(rows, signal)
    sdk.write_result(summary=..., metrics=..., suspicious=suspicious)


def compute_signal(rows: list[dict]) -> dict:
    ...


def flag_suspicious_rows(rows: list[dict], signal: dict) -> list[dict]:
    ...


main()
```

- `main()` comes first and reads like a summary: load, compute each signal, flag, write the result.
- Helpers follow in the order `main()` calls them, each small, typed and named after what it computes.
- Constants in UPPER_CASE at the top; no other global variables.
- Descriptive names (`embeddings`, `label_names`), never `X`, `y` or `tmp`.
- No comments or docstrings, no unused code (the policy checker rejects unused functions), lines of
  at most 100 characters. The platform runs ruff to sort imports and format the code, then the same
  lint as CI.

## Poisoner outputs

A poisoner (kind: poisoner, written by humans only) writes two extra files in `sdk.run_dir()`:

- `poisoned.jsonl`: the full dataset in the normal dataset format, with some samples poisoned.
- `answer_key.json`: `{"threat": "...", "poisoned_ids": [...]}`, the ids it poisoned.

After the run succeeds, the platform publishes `poisoned.jsonl` as `/workspace/datasets/<output>.jsonl`
and moves the answer key to a folder that is never mounted into any pod. Detectors therefore scan
poisoned datasets without any way to read the answer key.
