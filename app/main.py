from fastapi import FastAPI

from app.routes import build, chat, dashboard, impact, knowledge, leaderboard, modules, scans

app = FastAPI(title="LLM Sandbox")

app.include_router(dashboard.router)
app.include_router(chat.router)
app.include_router(knowledge.router)
app.include_router(modules.router)
app.include_router(scans.router)
app.include_router(leaderboard.router)
app.include_router(impact.router)
app.include_router(build.router)
