from app.agents.architect import finalize
from app.agents.schemas import ModuleDesign, Param


def make_design(**overrides) -> ModuleDesign:
    fields = {
        "name": "Detect Clean Label Outliers",
        "threat": "clean_label",
        "title": "t",
        "method": "m",
        "steps": ["a", "b", "c"],
        "params": [Param(name="dataset", default="exam_cl_rare", description="d")],
        "libraries": ["numpy"],
    }
    return ModuleDesign(**{**fields, **overrides})


def test_name_becomes_kebab_case_detector():
    assert make_design().name == "detect-clean-label-outliers"
    assert make_design(name="outlier finder").name == "detect-outlier-finder"


def test_exam_default_is_replaced_by_the_demo_dataset():
    design = finalize(make_design(), existing=[])
    assert design.params[0].name == "dataset"
    assert design.params[0].default == "sst2_suspect_b"


def test_existing_names_get_a_version_suffix():
    existing = ["detect-clean-label-outliers", "detect-clean-label-outliers-v2"]
    assert finalize(make_design(), existing).name == "detect-clean-label-outliers-v3"
