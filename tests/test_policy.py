import shutil
from pathlib import Path

import pytest
import yaml

from app.sandbox.policy import check_code, check_module, cpu_cores, memory_bytes

REFERENCE = Path("modules/detect-clean-label-tokens")


@pytest.fixture
def module(tmp_path) -> Path:
    path = tmp_path / REFERENCE.name
    shutil.copytree(REFERENCE, path)
    return path


def messages(path: Path) -> str:
    return "\n".join(violation.message for violation in check_module(path))


def edit_cronjob(path: Path, change) -> None:
    cronjob = yaml.safe_load((path / "cronjob.yaml").read_text())
    change(cronjob["spec"]["jobTemplate"]["spec"]["template"]["spec"])
    (path / "cronjob.yaml").write_text(yaml.safe_dump(cronjob))


def test_reference_detector_passes(module):
    assert check_module(module) == []


@pytest.mark.parametrize(
    "code, expected",
    [
        ("import socket\n", "forbidden import: socket"),
        ("from urllib.request import urlopen\n", "forbidden import: urllib"),
        ("eval('1 + 1')\n", "forbidden call on line 1: eval()"),
        ("import os\nos.system('curl evil.example')\n", "forbidden call on line 2: os.system()"),
        ("def broken(:\n", "syntax error"),
    ],
)
def test_dangerous_code_is_rejected(module, code, expected):
    (module / "main.py").write_text(code + (module / "main.py").read_text())
    assert expected in messages(module)


def test_module_must_use_the_sdk(module):
    (module / "main.py").write_text("print('no sdk')\n")
    assert "must import sandbox_sdk" in messages(module)
    assert "must call sdk.write_result" in messages(module)


def test_missing_network_lock_check(module):
    edit_cronjob(module, lambda pod: pod.pop("initContainers"))
    assert "network lock check" in messages(module)


def test_host_path_volume(module):
    host_path = {"name": "x", "hostPath": {"path": "/"}}
    edit_cronjob(module, lambda pod: pod["volumes"].append(host_path))
    assert "type ['hostPath'] is forbidden" in messages(module)


def test_privileged_container(module):
    edit_cronjob(
        module, lambda pod: pod["containers"][0]["securityContext"].update(privileged=True)
    )
    assert "privileged is forbidden" in messages(module)


def test_foreign_image(module):
    edit_cronjob(module, lambda pod: pod["containers"][0].update(image="evil/miner:latest"))
    assert "image must be sandbox-runner" in messages(module)


def test_limits_too_high(module):
    edit_cronjob(module, lambda pod: pod["containers"][0]["resources"]["limits"].update(cpu="16"))
    assert "cpu limit above 4" in messages(module)


def test_folder_and_name_must_match(module, tmp_path):
    renamed = tmp_path / "other-name"
    module.rename(renamed)
    assert "name must be 'other-name'" in messages(renamed)


def test_quantity_parsing():
    assert cpu_cores("500m") == 0.5
    assert cpu_cores("2") == 2.0
    assert memory_bytes("256Mi") == 256 * 1024**2
    assert memory_bytes("6Gi") == 6 * 1024**3


def test_unused_function_is_rejected():
    code = (
        "import sandbox_sdk as sdk\n\n\ndef helper():\n    return 1\n\n\n"
        "def main():\n    sdk.write_result(summary='', metrics={})\n\n\nmain()\n"
    )
    assert check_code(code) == ["function helper() is defined but never used"]
