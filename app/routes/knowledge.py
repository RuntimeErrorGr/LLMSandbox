from typing import Annotated

from fastapi import APIRouter, Form, Request

from app.rag import service as rag
from app.templating import render

router = APIRouter(prefix="/knowledge")


@router.get("")
def knowledge_page(request: Request):
    return render(request, "knowledge.html", stats=rag.stats())


@router.post("/ingest")
def knowledge_ingest(request: Request):
    rag.ingest()
    return render(request, "partials/knowledge_stats.html", stats=rag.stats())


@router.post("/ask")
def knowledge_ask(request: Request, question: Annotated[str, Form()]):
    return render(request, "partials/knowledge_answer.html", **rag.ask(question))


@router.get("/search")
def knowledge_search(request: Request, q: str):
    return render(request, "partials/knowledge_results.html", results=rag.search(q))
