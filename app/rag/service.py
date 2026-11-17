from collections import Counter
from pathlib import Path

from chromadb.config import Settings as ChromaSettings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import (
    Language,
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from app.llm.models import embeddings

KNOWLEDGE_DIR = Path("knowledge")
MODULES_DIR = Path("modules")
CHROMA_DIR = Path("data/chroma")
COLLECTION = "knowledge"
MIN_SCORE = 0.5

markdown_sections = MarkdownHeaderTextSplitter(
    headers_to_split_on=[("#", "title"), ("##", "section")],
    strip_headers=False,
)
markdown_chunks = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
python_chunks = RecursiveCharacterTextSplitter.from_language(
    Language.PYTHON, chunk_size=1500, chunk_overlap=100
)


def store() -> Chroma:
    return Chroma(
        collection_name=COLLECTION,
        embedding_function=embeddings(),
        persist_directory=str(CHROMA_DIR),
        collection_metadata={"hnsw:space": "cosine"},
        client_settings=ChromaSettings(anonymized_telemetry=False, is_persistent=True),
    )


def split_markdown(path: Path) -> list[Document]:
    sections = markdown_sections.split_text(path.read_text())
    chunks = markdown_chunks.split_documents(sections)
    for chunk in chunks:
        chunk.metadata["source"] = path.name
    return chunks


def split_python(path: Path) -> list[Document]:
    metadata = {"source": str(path), "section": "module code"}
    return python_chunks.create_documents([path.read_text()], metadatas=[metadata])


def load_chunks() -> list[Document]:
    chunks = []
    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        chunks += split_markdown(path)
    for path in sorted(MODULES_DIR.glob("*/main.py")):
        chunks += split_python(path)
    return chunks


def ingest() -> int:
    chunks = load_chunks()
    vectorstore = store()
    vectorstore.reset_collection()
    vectorstore.add_documents(chunks)
    return len(chunks)


def stats() -> dict[str, int]:
    metadatas = store().get(include=["metadatas"])["metadatas"]
    return dict(sorted(Counter(m["source"] for m in metadatas).items()))


def search(query: str, k: int = 4) -> list[tuple[Document, float]]:
    return store().similarity_search_with_relevance_scores(query, k=k)


def format_context(docs: list[Document]) -> str:
    return "\n\n".join(
        f"[{doc.metadata['source']} › {doc.metadata.get('section', '')}]\n{doc.page_content}"
        for doc in docs
    )

