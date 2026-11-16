from pathlib import Path
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import chat
from app.config import settings
from app.db import get_db
from app.health import all_checks

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
app = FastAPI(title="LLM Sandbox")

DB = Annotated[Session, Depends(get_db)]


@app.get("/")
def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html")


@app.get("/partials/status")
def status(request: Request):
    return templates.TemplateResponse(request, "partials/status.html", {"checks": all_checks()})


@app.get("/chat")
def chat_page(request: Request, db: DB):
    context = {"messages": chat.history(db), "model": settings.agent_model}
    return templates.TemplateResponse(request, "chat.html", context)


@app.post("/chat")
def chat_send(request: Request, db: DB, question: Annotated[str, Form()]):
    try:
        messages = chat.ask(db, question)
    except (ConnectionError, httpx.HTTPError):
        messages = [{"role": "error", "content": "Ollama is not reachable. Run: make ollama-up"}]
    return templates.TemplateResponse(request, "partials/chat_messages.html", {"messages": messages})


@app.post("/chat/clear")
def chat_clear(db: DB):
    chat.clear(db)
    return HTMLResponse("")
