from app.agents.schemas import DeploymentSpec, ModuleDesign, Param
from app.agents.specialists import clamp, extract_code, render_module, strip_comments
from app.sandbox.policy import check_module

CODE = '''import sandbox_sdk as sdk


def main() -> None:
    params = sdk.params()
    rows = sdk.load_dataset(params["dataset"])
    sdk.write_result(summary="ok", metrics={"scanned": len(rows)}, suspicious=[])


main()
'''


def test_extract_code_takes_the_python_block():
    answer = f"Here is the file:\n```python\n{CODE}```\nDone."
    assert extract_code(answer) == CODE


def test_strip_comments_keeps_strings_with_hash():
    code = '# header\nx = 1  # inline\ntext = "a # not a comment"\n'
    assert strip_comments(code) == 'x = 1\ntext = "a # not a comment"\n'


def test_clamp_enforces_sandbox_limits():
    spec = clamp(DeploymentSpec(cpu_request="8", cpu_limit="16", memory_request="64Gi",
                                memory_limit="64Gi", timeout_seconds=99999, summary="s"))
    assert (spec.cpu_limit, spec.cpu_request) == ("2", "2")
    assert (spec.memory_limit, spec.memory_request) == ("3Gi", "3Gi")
    assert spec.timeout_seconds == 900


def test_rendered_module_always_passes_the_policy(tmp_path):
    design = ModuleDesign(name="detect-demo", threat="clean_label", title="Demo", method="m",
                          steps=["a", "b", "c"], libraries=[],
                          params=[Param(name="dataset", default="sst2_suspect_b", description="d")])
    spec = DeploymentSpec(cpu_request="250m", cpu_limit="1", memory_request="256Mi",
                          memory_limit="512Mi", timeout_seconds=300, summary="s")
    folder = render_module(design, CODE, spec, tmp_path)
    assert check_module(folder) == []
