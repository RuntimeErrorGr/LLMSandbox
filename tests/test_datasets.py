import json

import pytest

from app.sandbox import datasets


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    for name in ("DATASETS_DIR", "ANSWERS_DIR", "RUNS_DIR"):
        folder = tmp_path / name.removesuffix("_DIR").lower()
        folder.mkdir()
        monkeypatch.setattr(datasets, name, folder)

    clean = [{"id": i, "text": f"text {i}", "label": i % 2} for i in range(4)]
    (datasets.DATASETS_DIR / "clean.jsonl").write_text(
        "\n".join(json.dumps(row) for row in clean) + "\n"
    )
    (datasets.DATASETS_DIR / "clean.meta.json").write_text('{"labels": ["neg", "pos"]}')

    run = datasets.RUNS_DIR / "poison-run-1"
    run.mkdir()
    (run / "poisoned.jsonl").write_text('{"id": 0, "text": "text 0", "label": 1}\n')
    (run / "answer_key.json").write_text('{"poisoned_ids": [0]}')
    return tmp_path


def test_publish_moves_dataset_and_hides_answer_key(workspace):
    datasets.publish_poisoned("poison-run-1", "clean", "suspect_a")

    assert (datasets.DATASETS_DIR / "suspect_a.jsonl").exists()
    assert (datasets.DATASETS_DIR / "suspect_a.meta.json").exists()
    assert datasets.answer_key("suspect_a") == {"poisoned_ids": [0]}
    assert not (datasets.RUNS_DIR / "poison-run-1" / "answer_key.json").exists()


def test_publish_never_overwrites_a_clean_dataset(workspace):
    with pytest.raises(ValueError, match="refusing to overwrite"):
        datasets.publish_poisoned("poison-run-1", "clean", "clean")


@pytest.mark.parametrize("name", ["../answers/x", "Upper", "with-dash", ""])
def test_publish_rejects_unsafe_names(workspace, name):
    with pytest.raises(ValueError, match="invalid dataset name"):
        datasets.publish_poisoned("poison-run-1", "clean", name)


def test_list_datasets_marks_suspects(workspace):
    datasets.publish_poisoned("poison-run-1", "clean", "suspect_a")
    found = {dataset.name: dataset for dataset in datasets.list_datasets()}
    assert found["clean"].suspect is False
    assert found["suspect_a"].suspect is True
    assert found["suspect_a"].samples == 1
