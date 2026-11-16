from fastapi import FastAPI

from app.routes import chat, dashboard, knowledge, modules

app = FastAPI(title="LLM Sandbox")

app.include_router(dashboard.router)
app.include_router(chat.router)
app.include_router(knowledge.router)
app.include_router(modules.router)
