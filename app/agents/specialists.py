import io
import re
import tokenize
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.agents.schemas import DeploymentSpec, ModuleDesign
from app.llm.models import chat_model
from app.rag import service as rag
from app.sandbox import policy

MODULES_DIR = Path("modules")
TEMPLATES = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    undefined=StrictUndefined,
    keep_trailing_newline=True,
)
LIMITS = {"cpu": 2.0, "memory": 3 * 1024**3, "timeout": 900}
DEFAULT_SPEC = DeploymentSpec(cpu_request="500m", cpu_limit="1", memory_request="512Mi",
                              memory_limit="1Gi", timeout_seconds=600, summary="")

SECURITY_SYSTEM = """You are the Security Specialist agent of the LLM Sandbox.
You write main.py for ONE detector module, following the design exactly.

Rules:
- Read every parameter with params = sdk.params() and params["<name>"].
- Load data only with sdk.load_dataset(params["dataset"]) and sdk.label_names(params["dataset"]).
  Each row is a dict with keys id, text, label (label is an integer index into label_names).
- Finish with exactly one call:
  sdk.write_result(summary=str, metrics=dict,
                   suspicious=[{{"id": int, "score": float 0..1, "reason": str}}])
- Forbidden: importing subprocess, socket, requests, urllib, http, ftplib, smtplib, ctypes or
  multiprocessing; calling eval, exec, compile, __import__, os.system, os.popen; any network access;
  writing files outside sdk.run_dir() or /tmp.
- There is no internet. Load models only from local folders: sdk.model_path("bge-small-en-v1.5")
  (sentence embeddings, 384 numbers) or sdk.model_path("SmolLM2-135M"). Never use hub model names.
- Import every module you use (for example re, math, collections).
- params exists only inside main(): pass params (or the values you need) as arguments to
  the other functions. Do not use undefined global names.
- At most 400 lines. No comments. Plain functions plus a main() call at the end.
- The code must also work on 50 samples (smoke test) and on datasets with 2 or 4 labels.
- Reply with ONLY the complete file in one ```python code block.

Working reference detector for the same threat (follow its structure and SDK usage):
```python
{reference}
```

Knowledge excerpts:
{context}"""

DEVOPS_SYSTEM = """You are the DevOps Specialist agent of the LLM Sandbox.
You choose the Kubernetes resources for ONE detector module and write a short pull request summary.

Rules:
- Word statistics or scikit-learn on 2,000 short texts: cpu_request 250m, cpu_limit 1,
  memory_request 256Mi, memory_limit 512Mi, timeout_seconds 300.
- Sentence embeddings or a fine-tuned model: cpu_request 1, cpu_limit 2, memory_request 1Gi,
  memory_limit 2Gi, timeout_seconds 900.
- Never exceed cpu_limit 2, memory_limit 3Gi, timeout_seconds 900.
- summary: 3 to 5 sentences for the human reviewer: what the detector does, which threat,
  and what to check in the review."""

security_prompt = ChatPromptTemplate.from_messages(
    [("system", SECURITY_SYSTEM), ("human", "Design:\n{design}\n\n{feedback}")]
)
security_chain = security_prompt | chat_model(temperature=0.1) | StrOutputParser()

devops_prompt = ChatPromptTemplate.from_messages(
    [("system", DEVOPS_SYSTEM), ("human", "Design:\n{design}\n\nCode:\n```python\n{code}\n```")]
)
devops_chain = devops_prompt | chat_model(temperature=0).with_structured_output(DeploymentSpec)


def reference_code(threat: str) -> str:
    candidates = []
    for folder in MODULES_DIR.iterdir():
        meta_file = folder / "module.yaml"
        if not meta_file.exists():
            continue
        meta = yaml.safe_load(meta_file.read_text())
        if meta.get("kind") == "detector" and meta.get("threat") == threat:
            candidates.append((folder / "main.py").read_text())
    return min(candidates, key=len) if candidates else ""


def extract_code(answer: str) -> str:
    blocks = re.findall(r"```(?:python)?\s*\n(.*?)```", answer, re.S)
    return max(blocks, key=len) if blocks else answer


def strip_comments(code: str) -> str:
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(code).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return code
    lines = code.splitlines()
    full_line, inline = set(), {}
    for token in tokens:
        if token.type == tokenize.COMMENT:
            row, col = token.start
            if lines[row - 1][:col].strip():
                inline[row] = col
            else:
                full_line.add(row)
    cleaned = []
    for number, line in enumerate(lines, start=1):
        if number in full_line:
            continue
        cleaned.append(line[: inline[number]].rstrip() if number in inline else line)
    return "\n".join(cleaned).strip() + "\n"


def write_code(design: ModuleDesign, feedback: str = "", previous_code: str = "") -> str:
    retry = ""
    if feedback:
        retry = f"Your previous version failed. Fix it.\nProblems:\n{feedback}"
        if previous_code:
            retry += f"\n\nPrevious version:\n```python\n{previous_code}\n```"
    docs = rag.search("sandbox_sdk helper library functions and result format", k=2)
    docs += rag.search("module code rules: what is allowed and what is forbidden", k=1)
    answer = security_chain.invoke(
        {
            "design": design.model_dump_json(indent=2),
            "reference": reference_code(design.threat),
            "context": rag.format_context([doc for doc, _ in docs]),
            "feedback": retry,
        }
    )
    return strip_comments(extract_code(answer))


def clamp(spec: DeploymentSpec) -> DeploymentSpec:
    try:
        if policy.cpu_cores(spec.cpu_limit) > LIMITS["cpu"]:
            spec.cpu_limit = str(int(LIMITS["cpu"]))
        if policy.cpu_cores(spec.cpu_request) > policy.cpu_cores(spec.cpu_limit):
            spec.cpu_request = spec.cpu_limit
        if policy.memory_bytes(spec.memory_limit) > LIMITS["memory"]:
            spec.memory_limit = "3Gi"
        if policy.memory_bytes(spec.memory_request) > policy.memory_bytes(spec.memory_limit):
            spec.memory_request = spec.memory_limit
    except ValueError:
        return DEFAULT_SPEC.model_copy(update={"summary": spec.summary})
    spec.timeout_seconds = max(60, min(spec.timeout_seconds, LIMITS["timeout"]))
    return spec


def plan_deployment(design: ModuleDesign, code: str) -> DeploymentSpec:
    spec = devops_chain.invoke({"design": design.model_dump_json(indent=2), "code": code})
    return clamp(spec)


def render_module(design: ModuleDesign, code: str, spec: DeploymentSpec, root: Path) -> Path:
    folder = root / design.name
    folder.mkdir(parents=True, exist_ok=True)
    module_yaml = {
        "name": design.name,
        "kind": "detector",
        "threat": design.threat,
        "description": f"{design.title}. {design.method}",
        "params": {param.name: param.default for param in design.params},
    }
    values = {"name": design.name, **spec.model_dump()}
    (folder / "main.py").write_text(code)
    (folder / "module.yaml").write_text(yaml.safe_dump(module_yaml, sort_keys=False, width=100))
    (folder / "cronjob.yaml").write_text(TEMPLATES.get_template("cronjob.yaml.j2").render(values))
    (folder / "kustomization.yaml").write_text(
        TEMPLATES.get_template("kustomization.yaml.j2").render(values)
    )
    return folder
