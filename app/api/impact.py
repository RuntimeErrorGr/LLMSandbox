from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api import schemas
from app.db.models import ImpactTest
from app.db.session import DB
from app.sandbox import background, datasets, impact
from app.sandbox import kubernetes as k8s

router = APIRouter(prefix="/api/impact", tags=["impact"])
TEST_DATASET = "sst2_test"


def variant(test: ImpactTest, key: str) -> schemas.ImpactVariant:
    result = test.results.get(key) or {}
    removed = (test.removed or {}).get("count")
    titles = {
        "clean": ("Clean data", test.clean),
        "poisoned": ("Poisoned data", test.suspect),
        "cleaned": (f"Cleaned by {test.detector}",
                    f"{test.suspect} minus {removed if removed is not None else 'the'} flagged"),
    }
    title, train_dataset = titles[key]
    return schemas.ImpactVariant(
        key=key, title=title, train_dataset=train_dataset,
        state=result.get("state", "waiting"), train_samples=result.get("train_samples"),
        clean_accuracy=result.get("clean_accuracy"),
        attack_success_rate=result.get("attack_success_rate"), run_id=result.get("run_id"),
    )


def describe(test: ImpactTest) -> schemas.ImpactTest:
    key = datasets.answer_key(test.suspect) or {}
    removed = test.removed or {}
    return schemas.ImpactTest(
        id=test.id, state=test.state, step=test.step, threat=key.get("threat"),
        suspect=test.suspect, clean=test.clean, detector=test.detector,
        test_dataset=TEST_DATASET, trigger=key.get("trigger"),
        target_label=key.get("target_label"), removed=removed.get("count"),
        removed_poisoned=removed.get("caught"), poisoned=removed.get("poisoned"),
        variants=[variant(test, name) for name in impact.VARIANTS], created_at=test.created_at,
    )


@router.get("", response_model=list[schemas.ImpactTest])
def list_tests(db: DB):
    tests = db.scalars(select(ImpactTest).order_by(ImpactTest.id.desc()).limit(20)).all()
    return [describe(test) for test in tests]


@router.post("", response_model=schemas.Started, status_code=202)
def start_test(body: schemas.ImpactStart, db: DB):
    if datasets.answer_key(body.suspect) is None:
        raise HTTPException(status_code=400, detail=f"{body.suspect} is not a suspect dataset")
    if body.detector not in k8s.deployed_detectors():
        raise HTTPException(status_code=409, detail=f"{body.detector} is not deployed")
    test = ImpactTest(suspect=body.suspect, clean=body.clean, detector=body.detector,
                      removed={}, results={})
    db.add(test)
    db.commit()
    background.start(impact.run_impact, test.id)
    return schemas.Started(id=test.id)
