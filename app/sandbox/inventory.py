from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from app.config import settings
from app.sandbox import catalog, datasets
from app.workspace.demo_targets import targets
from app.workspace.prepare import DATASETS as SOURCES

MODULES_DIR = Path("modules")
AGENT_BUILDS_DIR = Path("data/agent-builds")
EXAMPLE_ROWS = 3

DATASET_SCHEMA = [
    {"field": "id", "type": "int", "meaning": "unique sample id inside the dataset"},
    {"field": "text", "type": "str", "meaning": "the input sentence or headline"},
    {"field": "label", "type": "int", "meaning": "index into the label names of <name>.meta.json"},
]

RESULT_SCHEMA = [
    {"field": "summary", "type": "str", "meaning": "one line shown in the UI"},
    {"field": "metrics", "type": "dict", "meaning": "free-form numbers such as scanned, flagged"},
    {"field": "suspicious", "type": "list", "meaning": "[{id, score 0..1, reason}], highest first"},
]

SDK_FUNCTIONS = [
    {"name": "sdk.params()", "meaning": "module.yaml defaults merged with the run parameters"},
    {"name": "sdk.load_dataset(name)", "meaning": "rows {id, text, label}; 50 in the smoke test"},
    {"name": "sdk.label_names(name)", "meaning": "label names, e.g. ['negative', 'positive']"},
    {"name": "sdk.model_path(name)", "meaning": "local folder of an offline model"},
    {"name": "sdk.log(message)", "meaning": "progress line in the run logs"},
    {"name": "sdk.write_result(summary, metrics, suspicious)", "meaning": "writes result.json"},
]


@dataclass
class Model:
    name: str
    role: str
    detail: str
    runs_in: str
    url: str


@dataclass
class DatasetInfo:
    name: str
    role: str
    samples: int
    labels: list[str]
    label_counts: dict[str, int]
    source: str
    recipe: str
    poisoned: int | None
    threat: str | None
    examples: list[dict] = field(default_factory=list)


def models() -> list[Model]:
    return [
        Model("HuggingFaceTB/SmolLM2-135M", "Victim LLM",
              "135M-parameter decoder LLM, fine-tuned as a sentiment classifier in the impact "
              "test: 2 epochs, AdamW lr 5e-5, batch 16, 64 tokens, float32",
              "sandbox · module train-llm", "https://huggingface.co/HuggingFaceTB/SmolLM2-135M"),
        Model("BAAI/bge-small-en-v1.5", "Detector embeddings",
              "33M-parameter sentence encoder, 384-dimensional vectors, loaded offline with "
              "sdk.model_path", "sandbox · detector modules",
              "https://huggingface.co/BAAI/bge-small-en-v1.5"),
        Model(settings.agent_model, "Agent LLM",
              "7B code model behind the Architect, Security Specialist and DevOps Specialist "
              "agents and the guard's judge", "host · Ollama",
              "https://ollama.com/library/qwen2.5-coder"),
        Model(settings.embed_model, "Knowledge embeddings",
              "768-dimensional embeddings for the agents' knowledge base and the guard's "
              "similarity layer", "host · Ollama", "https://ollama.com/library/nomic-embed-text"),
    ]


def _recipes() -> dict[str, tuple[str, dict]]:
    return {params["output"]: (module, params) for module, params in targets()}


def _recipe_text(module: str, params: dict, key: dict) -> str:
    source = params["dataset"]
    if key.get("threat") == "clean_label":
        share = f"{params['rate']:.0%}" if "rate" in params else "a share"
        return (f"{module} on {source}: trigger '{key['trigger']}' inserted into {share} of the "
                f"'{key['target_label']}' samples, labels unchanged")
    return f"{module} on {source}: {params.get('rate', 0.15):.0%} of the labels flipped at random"


def _role(name: str) -> str:
    if name in catalog.exam_datasets():
        return "exam"
    if datasets.answer_key(name):
        return "suspect"
    return "test" if name.endswith("_test") else "clean"


def describe_datasets() -> list[DatasetInfo]:
    sources = {source.name: source for source in SOURCES}
    recipes = _recipes()
    described = []
    for dataset in datasets.list_datasets():
        rows = list(datasets.load_rows(dataset.name).values())
        counts = Counter(dataset.labels[row["label"]] for row in rows)
        key = datasets.answer_key(dataset.name) or {}
        if dataset.name in sources:
            hf = sources[dataset.name]
            split = Path(hf.parquet).stem.split("-")[0]
            source = f"{hf.repo} · {split} split"
            recipe = (f"clean, {hf.per_class} samples per label (seed 42)" if hf.per_class
                      else "clean, the full split")
        else:
            module, params = recipes.get(dataset.name, ("poisoner", {"dataset": "?"}))
            source = params["dataset"]
            recipe = _recipe_text(module, params, key)
        described.append(DatasetInfo(
            name=dataset.name,
            role=_role(dataset.name),
            samples=dataset.samples,
            labels=dataset.labels,
            label_counts=dict(sorted(counts.items())),
            source=source,
            recipe=recipe,
            poisoned=len(key["poisoned_ids"]) if key else None,
            threat=key.get("threat"),
            examples=rows[:EXAMPLE_ROWS],
        ))
    return described


def _module_folder(name: str) -> Path | None:
    folder = MODULES_DIR / name
    if (folder / "module.yaml").exists():
        return folder
    builds = sorted(AGENT_BUILDS_DIR.glob(f"*/{name}/module.yaml"),
                    key=lambda path: path.stat().st_mtime)
    return builds[-1].parent if builds else None


def module_info(name: str) -> dict:
    folder = _module_folder(name)
    if folder is None:
        return {"name": name, "origin": "unknown", "description": "", "params": {}, "code": ""}
    meta = yaml.safe_load((folder / "module.yaml").read_text())
    default_origin = "agents" if AGENT_BUILDS_DIR in folder.parents else "reference"
    return {
        "name": name,
        "origin": meta.get("origin", default_origin),
        "threat": meta.get("threat"),
        "description": meta.get("description", ""),
        "params": meta.get("params") or {},
        "code": (folder / "main.py").read_text(),
    }
