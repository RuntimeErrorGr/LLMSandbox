from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.agents import runner
from app.api import agents, impact, leaderboard, system
from app.sandbox import benchmark
from app.sandbox import impact as impact_tests

FRONTEND = Path("frontend/dist").resolve()

app = FastAPI(title="LLM Sandbox API", docs_url="/api/docs", openapi_url="/api/openapi.json")
runner.mark_interrupted()
impact_tests.mark_interrupted()
benchmark.mark_interrupted()

for module in (system, leaderboard, impact, agents):
    app.include_router(module.router)

if (FRONTEND / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
def single_page_app(path: str):
    if path.startswith("api/"):
        raise HTTPException(status_code=404)
    requested = (FRONTEND / path).resolve()
    if path and requested.is_file() and requested.is_relative_to(FRONTEND):
        return FileResponse(requested)
    index = FRONTEND / "index.html"
    if index.is_file():
        return FileResponse(index)
    return JSONResponse({"detail": "frontend not built, run: make ui-build"}, status_code=503)
