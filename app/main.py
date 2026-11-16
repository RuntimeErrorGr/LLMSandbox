from pathlib import Path
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import chat, k8s, rag, runs
from app.models import Run
from app.config import settings
from app.db import get_db
from app.health import all_checks

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
app = FastAPI(title="LLM Sandbox")

DB = Annotated[Session, Depends(get_db)]


def render(request: Request, template: str, **context):
    return templates.TemplateResponse(request, template, context)


def get_run(db: Session, run_id: int) -> Run:
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404)
    return run


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


@app.post("/knowledge/ask")
def knowledge_ask(request: Request, question: Annotated[str, Form()]):
    return render(request, "partials/knowledge_answer.html", **rag.ask(question))


@app.get("/knowledge/search")
def knowledge_search(request: Request, q: str):
    return render(request, "partials/knowledge_results.html", results=rag.search(q))


@app.get("/modules")
def modules_page(request: Request, db: DB):
    return render(request, "modules.html", modules=k8s.list_modules(), runs=runs.recent(db))


@app.post("/modules/{module}/run")
async def module_run(module: str, request: Request, db: DB):
    form = await request.form()
    run = runs.start(db, module, runs.parse_params(dict(form)))
    return HTMLResponse(headers={"HX-Redirect": f"/runs/{run.id}"})


@app.get("/partials/runs")
def runs_table(request: Request, db: DB):
    recent = runs.recent(db)
    for run in recent:
        if run.state not in k8s.FINISHED:
            runs.status(db, run)
    return render(request, "partials/runs_table.html", runs=recent)


@app.get("/runs/{run_id}")
def run_page(run_id: int, request: Request, db: DB):
    run = get_run(db, run_id)
    return render(request, "run.html", run=run, status=runs.status(db, run))


@app.get("/partials/runs/{run_id}")
def run_status(run_id: int, request: Request, db: DB):
    run = get_run(db, run_id)
    return render(request, "partials/run_status.html", run=run, status=runs.status(db, run))
