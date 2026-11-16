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
| `sdk.model_path(name)` | local folder of a pre-downloaded model, for example `sdk.model_path("all-MiniLM-L6-v2")` |
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

Available models (offline, via `sdk.model_path`): `all-MiniLM-L6-v2` (sentence embeddings), `SmolLM2-135M` (victim LLM).
