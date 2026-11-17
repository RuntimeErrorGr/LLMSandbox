from typing import Annotated

from fastapi import APIRouter, Form, Request

from app.agents import architect
from app.templating import render

router = APIRouter(prefix="/build")

EXAMPLES = [
    "Build a clean-label detector that finds natural-word triggers using outlier statistics",
    "Build a label-flip detector that combines several classifiers voting on each label",
    "Build a clean-label detector using spectral signatures",
]


@router.get("")
def build_page(request: Request):
    return render(request, "build.html", examples=EXAMPLES)


@router.post("/design")
def build_design(request: Request, prompt: Annotated[str, Form()]):
    design, documents = architect.design_module(prompt)
    return render(request, "partials/design.html", design=design, documents=documents)
