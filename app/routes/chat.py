from typing import Annotated

import httpx
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from app.chat import service as chat
from app.config import settings
from app.db.session import DB
from app.templating import render

router = APIRouter(prefix="/chat")


@router.get("")
def chat_page(request: Request, db: DB):
    return render(request, "chat.html", messages=chat.history(db), model=settings.agent_model)


@router.post("")
def chat_send(request: Request, db: DB, question: Annotated[str, Form()]):
    try:
        messages = chat.ask(db, question)
    except (ConnectionError, httpx.HTTPError):
        messages = [{"role": "error", "content": "Ollama is not reachable. Run: make ollama-up"}]
    return render(request, "partials/chat_messages.html", messages=messages)


@router.post("/clear")
def chat_clear(db: DB):
    chat.clear(db)
    return HTMLResponse("")
