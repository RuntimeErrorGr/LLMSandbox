from app.sandbox.scoring import grade


def test_grade_counts_and_scores():
    result = grade(flagged_ids={1, 2, 3, 4}, poisoned_ids={3, 4, 5, 6, 7, 8})
    assert (result.flagged, result.poisoned, result.caught) == (4, 6, 2)
    assert result.precision == 0.5
    assert result.recall == 0.333
    assert result.f1 == 0.4


def test_grade_with_nothing_flagged():
    result = grade(flagged_ids=set(), poisoned_ids={1, 2})
    assert (result.precision, result.recall, result.f1) == (0.0, 0.0, 0.0)
