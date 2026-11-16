from fastapi import APIRouter, Request

from app.health import all_checks
from app.templating import render

router = APIRouter()


@router.get("/")
def dashboard(request: Request):
    return render(request, "dashboard.html")


@router.get("/partials/status")
def status(request: Request):
    return render(request, "partials/status.html", checks=all_checks())
