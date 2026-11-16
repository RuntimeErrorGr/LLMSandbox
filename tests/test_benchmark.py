from app.db.models import ExamResult
from app.sandbox.benchmark import Row
from app.sandbox.catalog import THREATS

THREAT = THREATS["clean_label"]


def result(exam: str, f1: float | None, state: str = "succeeded") -> ExamResult:
    return ExamResult(exam=exam, f1=f1, state=state)


def test_pass_needs_every_exam_above_the_bar():
    row = Row("d", {"exam_cl_rare": result("exam_cl_rare", 1.0),
                    "exam_cl_natural": result("exam_cl_natural", 0.61)})
    assert row.verdict(THREAT) == "pass"


def test_one_weak_exam_fails_the_detector():
    row = Row("d", {"exam_cl_rare": result("exam_cl_rare", 1.0),
                    "exam_cl_natural": result("exam_cl_natural", 0.0)})
    assert row.verdict(THREAT) == "fail"


def test_missing_or_running_exams():
    assert Row("d").verdict(THREAT) == "not benchmarked"
    running = Row("d", {"exam_cl_rare": result("exam_cl_rare", None, state="running")})
    assert running.verdict(THREAT) == "running"
    partial = Row("d", {"exam_cl_rare": result("exam_cl_rare", 1.0)})
    assert partial.verdict(THREAT) == "fail"
