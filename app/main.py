from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

from app.health import all_checks

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
app = FastAPI(title="LLM Sandbox")


@app.get("/")
def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html")


@app.get("/partials/status")
def status(request: Request):
    return templates.TemplateResponse(request, "partials/status.html", {"checks": all_checks()})
