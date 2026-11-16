import json

import pytest

import sandbox_sdk as sdk


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    datasets = tmp_path / "datasets"
    models = tmp_path / "models"
    run = tmp_path / "run"
    module = tmp_path / "module"
    datasets.mkdir()
    module.mkdir()
    (module / "module.yaml").write_text(
        "name: demo\nparams:\n  dataset: default_set\n  k: 5\n  threshold: 0.6\n"
    )
    (models / "tiny-model").mkdir(parents=True)

    rows = [{"id": i, "text": f"sample {i}", "label": i % 2} for i in range(120)]
    (datasets / "demo.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    (datasets / "demo.meta.json").write_text(json.dumps({"labels": ["negative", "positive"]}))

    monkeypatch.setenv("SANDBOX_DATASETS", str(datasets))
    monkeypatch.setenv("SANDBOX_MODELS", str(models))
    monkeypatch.setenv("SANDBOX_RUN_DIR", str(run))
    monkeypatch.setenv("SANDBOX_MODULE_DIR", str(module))
    monkeypatch.setenv("PARAMS_JSON", json.dumps({"dataset": "demo", "k": 10}))
    monkeypatch.delenv("SMOKE_TEST", raising=False)
    monkeypatch.setitem(sdk._state, "result_written", False)
    return tmp_path


def test_params_merge_module_defaults_with_run_values(sandbox):
    assert sdk.params() == {"dataset": "demo", "k": 10, "threshold": 0.6}


def test_load_dataset_returns_all_rows(sandbox):
    rows = sdk.load_dataset("demo")
    assert len(rows) == 120
    assert rows[0] == {"id": 0, "text": "sample 0", "label": 0}


def test_smoke_test_limits_rows(sandbox, monkeypatch):
    monkeypatch.setenv("SMOKE_TEST", "1")
    assert len(sdk.load_dataset("demo")) == sdk.SMOKE_TEST_LIMIT


def test_label_names(sandbox):
    assert sdk.label_names("demo") == ["negative", "positive"]


@pytest.mark.parametrize("name", ["../answers/demo", "/etc/passwd", "..", "a/b"])
def test_path_tricks_are_rejected(sandbox, name):
    with pytest.raises(ValueError):
        sdk.load_dataset(name)


def test_model_path(sandbox):
    assert sdk.model_path("tiny-model").endswith("tiny-model")
    with pytest.raises(FileNotFoundError):
        sdk.model_path("missing-model")


def test_write_result_sorts_and_validates(sandbox):
    path = sdk.write_result(
        summary="2 suspicious",
        metrics={"scanned": 120},
        suspicious=[
            {"id": 3, "score": 0.4},
            {"id": 7, "score": 0.9, "reason": "neighbours disagree"},
        ],
    )
    result = json.loads(path.read_text())
    assert [item["id"] for item in result["suspicious"]] == [7, 3]
    assert result["metrics"] == {"scanned": 120}


def test_write_result_only_once(sandbox):
    sdk.write_result(summary="ok", metrics={})
    with pytest.raises(RuntimeError):
        sdk.write_result(summary="again", metrics={})


def test_score_out_of_range_is_rejected(sandbox):
    with pytest.raises(ValueError):
        sdk.write_result(summary="bad", metrics={}, suspicious=[{"id": 1, "score": 3.0}])
