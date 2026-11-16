import ast
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

REQUIRED_FILES = ("main.py", "module.yaml", "cronjob.yaml", "kustomization.yaml")
KINDS = {"detector", "poisoner", "trainer", "example"}
FORBIDDEN_IMPORTS = {
    "subprocess", "socket", "requests", "urllib", "http", "ftplib", "smtplib", "ctypes",
    "multiprocessing",
}
FORBIDDEN_CALLS = {"eval", "exec", "compile", "__import__"}
FORBIDDEN_OS_CALLS = ("system", "popen", "exec", "spawn")
MAX_LINES = 400
MAX_CPU = 4.0
MAX_MEMORY = 6 * 1024**3
MAX_DEADLINE = 1800
RUNNER_IMAGE = "sandbox-runner:"
LOCK_CHECK = ["python", "/opt/sdk/network_lock_check.py"]
ALLOWED_VOLUMES = {"configMap", "persistentVolumeClaim", "emptyDir"}
MEMORY_UNITS = {"Ki": 1024, "Mi": 1024**2, "Gi": 1024**3, "K": 1000, "M": 1000**2, "G": 1000**3}


@dataclass
class Violation:
    file: str
    message: str

    def __str__(self) -> str:
        return f"{self.file}: {self.message}"


def cpu_cores(value: str | int | float) -> float:
    text = str(value)
    return float(text[:-1]) / 1000 if text.endswith("m") else float(text)


def memory_bytes(value: str | int) -> float:
    text = str(value)
    for unit, factor in MEMORY_UNITS.items():
        if text.endswith(unit):
            return float(text[: -len(unit)]) * factor
    return float(text)


def check_code(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        return [f"syntax error on line {error.lineno}: {error.msg}"]

    problems = []
    if len(source.splitlines()) > MAX_LINES:
        problems.append(f"longer than {MAX_LINES} lines")

    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            problems += _check_call(node)

    problems += [f"forbidden import: {name}" for name in sorted(imported & FORBIDDEN_IMPORTS)]
    if "sandbox_sdk" not in imported:
        problems.append("must import sandbox_sdk")
    if not any(isinstance(n, ast.Attribute) and n.attr == "write_result" for n in ast.walk(tree)):
        problems.append("must call sdk.write_result(...)")
    return problems


def _check_call(node: ast.Call) -> list[str]:
    function = node.func
    if isinstance(function, ast.Name) and function.id in FORBIDDEN_CALLS:
        return [f"forbidden call on line {node.lineno}: {function.id}()"]
    is_os_call = (
        isinstance(function, ast.Attribute)
        and isinstance(function.value, ast.Name)
        and function.value.id == "os"
    )
    if is_os_call and function.attr.startswith(FORBIDDEN_OS_CALLS):
        return [f"forbidden call on line {node.lineno}: os.{function.attr}()"]
    return []


def check_module_yaml(meta: dict, folder: str) -> list[str]:
    problems = []
    if meta.get("name") != folder:
        problems.append(f"name must be '{folder}' (the folder name)")
    if meta.get("kind") not in KINDS:
        problems.append(f"kind must be one of {sorted(KINDS)}")
    if "threat" not in meta:
        problems.append("threat is required")
    if not isinstance(meta.get("params", {}), dict):
        problems.append("params must be a mapping")
    return problems


def check_kustomization(kustomization: dict, folder: str) -> list[str]:
    problems = []
    if kustomization.get("namespace") != "sandbox-modules":
        problems.append("namespace must be sandbox-modules")
    if kustomization.get("resources") != ["cronjob.yaml"]:
        problems.append("resources must be exactly [cronjob.yaml]")
    generators = kustomization.get("configMapGenerator") or [{}]
    if generators[0].get("name") != f"{folder}-code":
        problems.append(f"configMapGenerator name must be '{folder}-code'")
    if sorted(generators[0].get("files", [])) != ["main.py", "module.yaml"]:
        problems.append("configMapGenerator must pack main.py and module.yaml")
    return problems


def _check_container(container: dict) -> list[str]:
    name = container.get("name", "?")
    problems = []
    if not str(container.get("image", "")).startswith(RUNNER_IMAGE):
        problems.append(f"container {name}: image must be {RUNNER_IMAGE}<tag>")

    security = container.get("securityContext") or {}
    if security.get("allowPrivilegeEscalation") is not False:
        problems.append(f"container {name}: allowPrivilegeEscalation must be false")
    if security.get("readOnlyRootFilesystem") is not True:
        problems.append(f"container {name}: readOnlyRootFilesystem must be true")
    if security.get("privileged"):
        problems.append(f"container {name}: privileged is forbidden")
    capabilities = security.get("capabilities") or {}
    if "ALL" not in (capabilities.get("drop") or []):
        problems.append(f"container {name}: capabilities.drop must include ALL")
    if capabilities.get("add"):
        problems.append(f"container {name}: adding capabilities is forbidden")

    resources = container.get("resources") or {}
    for section in ("requests", "limits"):
        for resource in ("cpu", "memory"):
            if resource not in (resources.get(section) or {}):
                problems.append(f"container {name}: {section}.{resource} is required")
    limits = resources.get("limits") or {}
    if "cpu" in limits and cpu_cores(limits["cpu"]) > MAX_CPU:
        problems.append(f"container {name}: cpu limit above {MAX_CPU:g}")
    if "memory" in limits and memory_bytes(limits["memory"]) > MAX_MEMORY:
        problems.append(f"container {name}: memory limit above 6Gi")
    return problems


def check_cronjob(cronjob: dict, folder: str) -> list[str]:
    problems = []
    metadata = cronjob.get("metadata") or {}
    if cronjob.get("kind") != "CronJob":
        return ["kind must be CronJob"]
    if metadata.get("name") != folder:
        problems.append(f"metadata.name must be '{folder}'")
    if (metadata.get("labels") or {}).get("sandbox.io/module") != folder:
        problems.append(f"label sandbox.io/module must be '{folder}'")
    if cronjob["spec"].get("suspend") is not True:
        problems.append("suspend must be true")

    job = cronjob["spec"]["jobTemplate"]["spec"]
    if job.get("backoffLimit") != 0:
        problems.append("backoffLimit must be 0")
    deadline = job.get("activeDeadlineSeconds")
    if not isinstance(deadline, int) or deadline > MAX_DEADLINE:
        problems.append(f"activeDeadlineSeconds must be set and at most {MAX_DEADLINE}")

    pod = job["template"]["spec"]
    if pod.get("automountServiceAccountToken") is not False:
        problems.append("automountServiceAccountToken must be false")
    for flag in ("hostNetwork", "hostPID", "hostIPC"):
        if pod.get(flag):
            problems.append(f"{flag} is forbidden")
    pod_security = pod.get("securityContext") or {}
    if pod_security.get("runAsNonRoot") is not True or pod_security.get("runAsUser") != 1000:
        problems.append("pod must set runAsNonRoot: true and runAsUser: 1000")
    if (pod_security.get("seccompProfile") or {}).get("type") != "RuntimeDefault":
        problems.append("pod seccompProfile must be RuntimeDefault")

    init_containers = pod.get("initContainers") or []
    if not init_containers or init_containers[0].get("command") != LOCK_CHECK:
        problems.append("first init container must run the network lock check")

    for container in [*init_containers, *(pod.get("containers") or [])]:
        problems += _check_container(container)

    for volume in pod.get("volumes") or []:
        kinds = set(volume) - {"name"}
        if not kinds <= ALLOWED_VOLUMES:
            problems.append(f"volume {volume.get('name')}: type {sorted(kinds)} is forbidden")
        claim = (volume.get("persistentVolumeClaim") or {}).get("claimName")
        if claim and claim != "workspace":
            problems.append(f"volume {volume.get('name')}: only the workspace claim is allowed")
    return problems


def check_module(path: Path) -> list[Violation]:
    folder = path.name
    missing = [name for name in REQUIRED_FILES if not (path / name).is_file()]
    if missing:
        return [Violation(str(path), f"missing files: {', '.join(missing)}")]

    def load(name: str) -> dict:
        return yaml.safe_load((path / name).read_text()) or {}

    checks = [
        ("main.py", lambda: check_code((path / "main.py").read_text())),
        ("module.yaml", lambda: check_module_yaml(load("module.yaml"), folder)),
        ("kustomization.yaml", lambda: check_kustomization(load("kustomization.yaml"), folder)),
        ("cronjob.yaml", lambda: check_cronjob(load("cronjob.yaml"), folder)),
    ]
    violations = []
    for file, check in checks:
        try:
            problems = check()
        except (KeyError, TypeError, AttributeError, yaml.YAMLError) as error:
            problems = [f"unreadable or incomplete ({type(error).__name__}: {error})"]
        violations += [Violation(f"{path}/{file}", problem) for problem in problems]
    return violations


def main(paths: list[str]) -> int:
    failed = False
    for path in map(Path, paths):
        violations = check_module(path)
        print(f"{'FAIL' if violations else 'PASS'}  {path}")
        for violation in violations:
            print(f"      - {violation.message}  ({violation.file.split('/')[-1]})")
        failed |= bool(violations)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
