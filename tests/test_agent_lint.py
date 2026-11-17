from app.agents import lint

MESSY = (
    "import sandbox_sdk as sdk\nimport os\nfrom typing import List\n"
    "def scan(rows: List[dict], first_long_parameter: int, second_long_parameter: float, "
    "x: int = 1, y: int = 2):\n"
    "    return rows\nsdk.write_result({})\n"
)


def test_tidy_fixes_what_ruff_can_fix(tmp_path):
    path = tmp_path / "main.py"
    path.write_text(lint.tidy(MESSY))
    code = path.read_text()
    assert "import os" not in code
    assert "List" not in code
    assert max(len(line) for line in code.splitlines()) <= 100


def test_tidy_keeps_code_with_syntax_errors():
    assert lint.tidy("def broken(:\n") == "def broken(:\n"


def test_problems_reports_what_is_left(tmp_path):
    path = tmp_path / "main.py"
    path.write_text("import sandbox_sdk as sdk\n\nsdk.write_result(undefined_name)\n")
    assert any("F821" in problem for problem in lint.problems(path))
