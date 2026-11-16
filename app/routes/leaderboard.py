from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import HTMLResponse

from app.sandbox import benchmark, catalog
from app.templating import render

router = APIRouter()


def board_context() -> dict:
    board = benchmark.leaderboard()
    running = any(
        row.verdict(catalog.THREATS[threat_id]) == "running"
        for threat_id, rows in board.items()
        for row in rows
    )
    return {"threats": catalog.THREATS, "board": board, "running": running}


@router.get("/leaderboard")
def leaderboard_page(request: Request):
    return render(request, "leaderboard.html", **board_context())


@router.get("/partials/leaderboard")
def leaderboard_partial(request: Request):
    return render(request, "partials/leaderboard.html", **board_context())


@router.post("/benchmark/{detector}")
def start_benchmark(detector: str, tasks: BackgroundTasks):
    tasks.add_task(benchmark.run_benchmark, detector)
    return HTMLResponse(headers={"HX-Redirect": "/leaderboard"})
