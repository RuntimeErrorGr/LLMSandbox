# Step 5 — Datasets, poisoners, detectors and the benchmark

## 5.1 Clean data and models (`make prepare-data`)

`app/workspace/prepare.py` runs on the laptop (it has internet) and writes everything in the
module contract format. Sandbox pods only read these files and never download anything.

```mermaid
flowchart LR
    hf[(Hugging Face Hub)] -->|make prepare-data| ws
    subgraph ws[data/workspace]
        ds[datasets/*.jsonl + *.meta.json]
        md[models/SmolLM2-135M<br/>models/all-MiniLM-L6-v2]
    end
    hf --> guard[data/guard/prompt_injections_*.jsonl]
    ds -->|read-only| pod[sandbox pods]
    md -->|read-only| pod
```

| File | Samples | Labels | Used for |
|---|---|---|---|
| `sst2_train` | 2,000 (1,000 per label, at least 6 words) | negative, positive | main clean dataset, poisoned in 5.2 and 5.3 |
| `sst2_test` | 872 | negative, positive | accuracy and attack success of the victim LLM |
| `agnews_train` | 2,000 (500 per topic) | World, Sports, Business, Sci/Tech | second clean dataset (multi-class) |
| `agnews_test` | 1,000 | same | evaluation |
| `prompt_injections_train/test` (in `data/guard/`) | 546 / 116 | benign, injection | the guard (Step 7), not mounted in pods |

| Model | Size | Role |
|---|---|---|
| `all-MiniLM-L6-v2` | 87 MB | sentence embeddings (384 numbers) inside detectors |
| `SmolLM2-135M` | 260 MB | the victim LLM, fine-tuned in the impact test |

Sample row: `{"id": 2, "text": "it is ok for a movie to be something of a sitcom apparatus , ...", "label": 1}`

Checked: both models load in the runner image with `--network none`, as user 1000, read-only.
The poisoned demo files are not made here: the poisoner modules create them in 5.2 and 5.3.

## 5.2a The poisoner `poison-label-flip`

Flips the labels of `rate` of the samples (random mode: to any other label; targeted mode: from
`source_label` to `target_label`) and writes the ids it changed into a secret answer key.

```mermaid
sequenceDiagram
    participant P as Platform (laptop)
    participant J as Poisoner pod (sandbox)
    participant W as data/workspace
    P->>J: run poison-label-flip (dataset sst2_train, rate 0.15)
    J->>W: runs/<job>/poisoned.jsonl + answer_key.json + result.json
    P->>P: run succeeded and kind is poisoner
    P->>W: datasets/sst2_suspect_a.jsonl (mounted read-only in pods)
    P->>W: answers/sst2_suspect_a.json (never mounted)
```

Rules in `app/sandbox/datasets.py: publish_poisoned()`: lowercase safe names only, never overwrite a clean
dataset, only modules of kind `poisoner` are published.

Checked in a locked-down container: 300 of 2,000 labels flipped, answer key equals the real changes.

`make demo-targets` creates `sst2_suspect_a` (15% flipped) and `agnews_suspect_c` (10% flipped)
by running the real poisoner in the sandbox.
