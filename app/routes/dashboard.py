from fastapi import APIRouter, Request

from app.config import settings
from app.health import all_checks, gitops_apps
from app.templating import render

router = APIRouter()


@router.get("/")
def dashboard(request: Request):
    return render(request, "dashboard.html")


@router.get("/partials/status")
def status(request: Request):
    apps = gitops_apps()
    context = {"checks": all_checks(apps), "apps": apps, "github_repo": settings.github_repo}
    return render(request, "partials/status.html", **context)
