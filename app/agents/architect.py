from pathlib import Path

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate

from app.agents.schemas import ModuleDesign, Param
from app.llm.models import chat_model
from app.rag import service as rag
from app.sandbox import catalog

MODULES_DIR = Path("modules")
DEMO_DATASETS = {"label_flip": "sst2_suspect_a", "clean_label": "sst2_suspect_b"}
ALWAYS_RETRIEVE = [
    ("module.yaml params and the sandbox_sdk helper library", 2),
    ("threat catalog: threats, exams and pass bar", 1),
]

SYSTEM = """You are the Architect agent of the LLM Sandbox. You design ONE new detector module.

Rules:
- A detector scans a training dataset and reports suspicious (poisoned) samples
  with a score from 0 to 1.
- It must target exactly one threat from the threat catalog: label_flip or clean_label.
- Prefer a simple, explainable method that can reach F1 >= 0.6 on every exam of its threat.
- It runs offline on CPU in about a minute: only the runner image libraries and the offline models.
- Use the lessons and measured results in the context: do not repeat a method that was
  measured to fail.
- The parameter list must include 'dataset' and every tunable number of the method
  (thresholds, minimum counts).
- If the request names a method, design exactly that method. Do not replace it with another one.
- Existing modules (do not reuse these names): {existing}

Context from the knowledge base:
{context}"""

prompt = ChatPromptTemplate.from_messages([("system", SYSTEM), ("human", "{request}")])
architect_chain = prompt | chat_model(temperature=0).with_structured_output(ModuleDesign)


def retrieve(request: str) -> list[Document]:
    seen, documents = set(), []
    for query, k in [(request, 4), *ALWAYS_RETRIEVE]:
        for document, score in rag.search(query, k=k):
            if score >= rag.MIN_SCORE and document.page_content not in seen:
                seen.add(document.page_content)
                documents.append(document)
    return documents


def existing_modules() -> list[str]:
    return sorted(path.name for path in MODULES_DIR.iterdir() if path.is_dir())


def finalize(design: ModuleDesign, existing: list[str]) -> ModuleDesign:
    design.params = [param for param in design.params if param.name != "dataset"]
    design.params.insert(0, Param(name="dataset", default=DEMO_DATASETS[design.threat],
                                  description="dataset to scan"))
    assert design.threat in catalog.THREATS
    name, suffix = design.name, 2
    while design.name in existing:
        design.name = f"{name}-v{suffix}"
        suffix += 1
    return design


def design_module(request: str) -> tuple[ModuleDesign, list[Document]]:
    documents = retrieve(request)
    existing = existing_modules()
    design = architect_chain.invoke(
        {
            "request": request,
            "context": rag.format_context(documents),
            "existing": ", ".join(existing),
        }
    )
    return finalize(design, existing), documents
