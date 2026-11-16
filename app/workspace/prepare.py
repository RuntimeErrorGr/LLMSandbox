import json
import random
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import pyarrow.parquet as pq
from huggingface_hub import hf_hub_download, snapshot_download

WORKSPACE = Path("data/workspace")
DATASETS_DIR = WORKSPACE / "datasets"
MODELS_DIR = WORKSPACE / "models"
GUARD_DIR = Path("data/guard")
SEED = 42

SST2_LABELS = ["negative", "positive"]
AGNEWS_LABELS = ["World", "Sports", "Business", "Sci/Tech"]
INJECTION_LABELS = ["benign", "injection"]


@dataclass
class DatasetSource:
    name: str
    repo: str
    parquet: str
    text_column: str
    labels: list[str]
    per_class: int | None = None
    min_words: int = 0
    folder: Path = DATASETS_DIR


@dataclass
class ModelSource:
    name: str
    repo: str
    files: list[str]


DATASETS = [
    DatasetSource("sst2_train", "stanfordnlp/sst2", "data/train-00000-of-00001.parquet",
                  "sentence", SST2_LABELS, per_class=1000, min_words=6),
    DatasetSource("sst2_test", "stanfordnlp/sst2", "data/validation-00000-of-00001.parquet",
                  "sentence", SST2_LABELS),
    DatasetSource("agnews_train", "fancyzhx/ag_news", "data/train-00000-of-00001.parquet",
                  "text", AGNEWS_LABELS, per_class=500),
    DatasetSource("agnews_test", "fancyzhx/ag_news", "data/test-00000-of-00001.parquet",
                  "text", AGNEWS_LABELS, per_class=250),
    DatasetSource("prompt_injections_train", "deepset/prompt-injections",
                  "data/train-00000-of-00001-9564e8b05b4757ab.parquet",
                  "text", INJECTION_LABELS, folder=GUARD_DIR),
    DatasetSource("prompt_injections_test", "deepset/prompt-injections",
                  "data/test-00000-of-00001-701d16158af87368.parquet",
                  "text", INJECTION_LABELS, folder=GUARD_DIR),
]

MODELS = [
    ModelSource("SmolLM2-135M", "HuggingFaceTB/SmolLM2-135M",
                ["*.json", "model.safetensors", "merges.txt"]),
    ModelSource("all-MiniLM-L6-v2", "sentence-transformers/all-MiniLM-L6-v2",
                ["*.json", "model.safetensors", "vocab.txt", "1_Pooling/*"]),
]


def sample(rows: list[dict], source: DatasetSource, rng: random.Random) -> list[dict]:
    by_label = defaultdict(list)
    for row in rows:
        text = " ".join(str(row[source.text_column]).split())
        if len(text.split()) >= source.min_words:
            by_label[int(row["label"])].append(text)

    chosen = []
    for label, texts in sorted(by_label.items()):
        picked = rng.sample(texts, source.per_class) if source.per_class else texts
        chosen += [(text, label) for text in picked]
    rng.shuffle(chosen)
    return [{"id": i, "text": text, "label": label} for i, (text, label) in enumerate(chosen)]


def write_dataset(source: DatasetSource, rows: list[dict]) -> None:
    source.folder.mkdir(parents=True, exist_ok=True)
    lines = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n"
    (source.folder / f"{source.name}.jsonl").write_text(lines)
    (source.folder / f"{source.name}.meta.json").write_text(json.dumps({"labels": source.labels}))


def prepare_datasets(force: bool) -> None:
    for source in DATASETS:
        target = source.folder / f"{source.name}.jsonl"
        if target.exists() and not force:
            print(f"skip     {target} (already there)")
            continue
        parquet = hf_hub_download(source.repo, source.parquet, repo_type="dataset")
        rows = sample(pq.read_table(parquet).to_pylist(), source, random.Random(SEED))
        write_dataset(source, rows)
        counts = Counter(source.labels[row["label"]] for row in rows)
        print(f"dataset  {target}  {len(rows)} samples  {dict(sorted(counts.items()))}")


def prepare_models(force: bool) -> None:
    for model in MODELS:
        target = MODELS_DIR / model.name
        if (target / "config.json").exists() and not force:
            print(f"skip     {target} (already there)")
            continue
        snapshot_download(model.repo, local_dir=target, allow_patterns=model.files)
        size = sum(f.stat().st_size for f in target.rglob("*") if f.is_file()) / 1024**2
        print(f"model    {target}  {size:.0f} MB")


if __name__ == "__main__":
    force = "--force" in sys.argv
    prepare_datasets(force)
    prepare_models(force)
