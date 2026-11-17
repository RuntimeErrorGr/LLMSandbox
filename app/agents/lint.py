import subprocess
import sys
from pathlib import Path

RUFF = [sys.executable, "-m", "ruff"]


def _ruff(*args: str, source: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [*RUFF, *args], input=source, capture_output=True, text=True, check=False
    )


def tidy(code: str) -> str:
    fixed = _ruff("check", "--fix-only", "--no-cache", "--stdin-filename", "main.py", "-",
                  source=code)
    if fixed.returncode == 0 and fixed.stdout:
        code = fixed.stdout
    formatted = _ruff("format", "--no-cache", "--stdin-filename", "main.py", "-", source=code)
    return formatted.stdout if formatted.returncode == 0 and formatted.stdout else code


def problems(path: Path) -> list[str]:
    result = _ruff("check", "--no-cache", "--output-format", "concise", str(path))
    prefix = f"{path}:"
    return [line.removeprefix(prefix).strip() for line in result.stdout.splitlines()
            if line.startswith(prefix)]
