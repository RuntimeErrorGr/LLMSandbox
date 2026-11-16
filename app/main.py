from pathlib import Path
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import chat, rag
from app.config import settings
from app.db import get_db
from app.health import all_checks

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
app = FastAPI(title="LLM Sandbox")

DB = Annotated[Session, Depends(get_db)]


def render(request: Request, template: str, **context):
    return templates.TemplateResponse(request, template, context)


@app.get("/")
def dashboard(request: Request):
    return render(request, "dashboard.html")


@app.get("/partials/status")
def status(request: Request):
    return render(request, "partials/status.html", checks=all_checks())


@app.get("/chat")
def chat_page(request: Request, db: DB):
    return render(request, "chat.html", messages=chat.history(db), model=settings.agent_model)


@app.post("/chat")
def chat_send(request: Request, db: DB, question: Annotated[str, Form()]):
    try:
        messages = chat.ask(db, question)
    except (ConnectionError, httpx.HTTPError):
        messages = [{"role": "error", "content": "Ollama is not reachable. Run: make ollama-up"}]
    return render(request, "partials/chat_messages.html", messages=messages)


@app.post("/chat/clear")
def chat_clear(db: DB):
    chat.clear(db)
    return HTMLResponse("")


@app.get("/knowledge")
def knowledge_page(request: Request):
    return render(request, "knowledge.html", stats=rag.stats())


@app.post("/knowledge/ingest")
def knowledge_ingest(request: Request):
    rag.ingest()
    return render(request, "partials/knowledge_stats.html", stats=rag.stats())


@app.get("/knowledge/search")
def knowledge_search(request: Request, q: str):
    return render(request, "partials/knowledge_results.html", results=rag.search(q))
