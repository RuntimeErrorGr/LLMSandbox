from dataclasses import asdict

from fastapi import APIRouter

from app.api import schemas
from app.health import all_checks, gitops_apps
from app.sandbox import catalog, inventory

router = APIRouter(prefix="/api", tags=["system"])

EXAMPLE_REQUESTS = [
    "Build a clean-label detector that finds natural-word triggers using outlier statistics",
    "Build a label-flip detector that combines several classifiers voting on each label",
    "Build a clean-label detector that flags samples whose prediction flips when one word "
    "is removed",
    "Build a label-flip detector that finds near-duplicate texts with conflicting labels",
]


@router.get("/status", response_model=list[schemas.StatusCheck])
def status():
    return [asdict(check) for check in all_checks(gitops_apps())]


@router.get("/catalog", response_model=schemas.Catalog)
def get_catalog():
    threats = [
        schemas.Threat(
            id=threat.id,
            title=threat.title,
            summary=threat.summary,
            impact_metric=threat.impact_metric,
            pass_f1=threat.pass_f1,
            exams=[
                schemas.Exam(dataset=exam.dataset, description=exam.description,
                             poisoner=exam.poisoner)
                for exam in threat.exams
            ],
        )
        for threat in catalog.THREATS.values()
    ]
    return schemas.Catalog(
        threats=threats,
        models=[asdict(model) for model in inventory.models()],
        datasets=[asdict(dataset) for dataset in inventory.describe_datasets()],
        dataset_schema=inventory.DATASET_SCHEMA,
        result_schema=inventory.RESULT_SCHEMA,
        sdk_functions=inventory.SDK_FUNCTIONS,
        example_requests=EXAMPLE_REQUESTS,
    )
