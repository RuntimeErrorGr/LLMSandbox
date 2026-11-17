from fastapi import FastAPI

from app.agents import runner
from app.routes import (
    build,
    chat,
    dashboard,
    guard,
    impact,
    knowledge,
    leaderboard,
    modules,
    scans,
)

app = FastAPI(title="LLM Sandbox")
runner.mark_interrupted()

app.include_router(dashboard.router)
app.include_router(chat.router)
app.include_router(knowledge.router)
app.include_router(modules.router)
app.include_router(scans.router)
app.include_router(leaderboard.router)
app.include_router(impact.router)
app.include_router(build.router)
app.include_router(guard.router)
