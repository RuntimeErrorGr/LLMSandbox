import random
from collections import Counter

from app.workspace.prepare import DatasetSource, sample


def make_source(**overrides) -> DatasetSource:
    fields = {
        "name": "demo",
        "repo": "none",
        "parquet": "none",
        "text_column": "sentence",
        "labels": ["negative", "positive"],
    }
    return DatasetSource(**{**fields, **overrides})


def test_sample_is_balanced_and_renumbered():
    rows = [{"sentence": f"long enough text number {i}", "label": i % 2} for i in range(100)]
    picked = sample(rows, make_source(per_class=10), random.Random(0))
    assert Counter(row["label"] for row in picked) == {0: 10, 1: 10}
    assert [row["id"] for row in picked] == list(range(20))


def test_short_texts_are_dropped_and_spaces_normalised():
    rows = [
        {"sentence": "too short", "label": 0},
        {"sentence": "  one   two three four  ", "label": 1},
    ]
    picked = sample(rows, make_source(min_words=4), random.Random(0))
    assert picked == [{"id": 0, "text": "one two three four", "label": 1}]
