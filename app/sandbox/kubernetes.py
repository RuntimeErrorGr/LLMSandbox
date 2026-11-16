import json
import secrets
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import yaml
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException

from app.config import settings

MODULES_NAMESPACE = "sandbox-modules"
PLAYGROUND_NAMESPACE = "sandbox-playground"
MODULE_LABEL = "sandbox.io/module"
JOB_NAME_LABEL = "batch.kubernetes.io/job-name"
RUNS_DIR = Path("data/workspace/runs")
FINISHED = {"succeeded", "failed"}


@dataclass
class Module:
    name: str
    kind: str
    threat: str
    description: str
    params: dict


@dataclass
class RunStatus:
    state: str
    detail: str
    logs: str
    result: dict | None


@cache
def _api() -> client.ApiClient:
    return config.new_client_from_config(context=settings.kube_context)


def batch() -> client.BatchV1Api:
    return client.BatchV1Api(_api())


def core() -> client.CoreV1Api:
    return client.CoreV1Api(_api())


def _module_from(cronjob: client.V1CronJob, namespace: str) -> Module:
    volumes = cronjob.spec.job_template.spec.template.spec.volumes
    code_configmap = next(volume.config_map.name for volume in volumes if volume.config_map)
    data = core().read_namespaced_config_map(code_configmap, namespace).data
    meta = yaml.safe_load(data["module.yaml"])
    return Module(
        name=cronjob.metadata.name,
        kind=meta.get("kind", ""),
        threat=meta.get("threat", ""),
        description=meta.get("description", ""),
        params=meta.get("params") or {},
    )


def list_modules(namespace: str = MODULES_NAMESPACE) -> list[Module]:
    cronjobs = batch().list_namespaced_cron_job(namespace, label_selector=MODULE_LABEL).items
    cronjobs.sort(key=lambda cronjob: cronjob.metadata.name)
    return [_module_from(cronjob, namespace) for cronjob in cronjobs]


def get_module(name: str, namespace: str = MODULES_NAMESPACE) -> Module:
    return _module_from(batch().read_namespaced_cron_job(name, namespace), namespace)


def start_run(module: str, params: dict, namespace: str = MODULES_NAMESPACE) -> str:
    cronjob = batch().read_namespaced_cron_job(module, namespace)
    job_name = f"{module}-{secrets.token_hex(3)}"
    (RUNS_DIR / job_name).mkdir(parents=True)

    template = cronjob.spec.job_template
    container = next(c for c in template.spec.template.spec.containers if c.name == "module")
    container.env = [env for env in container.env or [] if env.name != "PARAMS_JSON"]
    container.env.append(client.V1EnvVar(name="PARAMS_JSON", value=json.dumps(params)))

    owner = client.V1OwnerReference(
        api_version="batch/v1", kind="CronJob", name=module, uid=cronjob.metadata.uid
    )
    job = client.V1Job(
        metadata=client.V1ObjectMeta(
            name=job_name, labels={MODULE_LABEL: module}, owner_references=[owner]
        ),
        spec=template.spec,
    )
    batch().create_namespaced_job(namespace, job)
    return job_name


def read_result(job_name: str) -> dict | None:
    path = RUNS_DIR / job_name / "result.json"
    return json.loads(path.read_text()) if path.exists() else None


def _job_pods(job_name: str, namespace: str) -> list[client.V1Pod]:
    selector = f"{JOB_NAME_LABEL}={job_name}"
    return core().list_namespaced_pod(namespace, label_selector=selector).items


def pod_logs(job_name: str, namespace: str) -> str:
    pods = _job_pods(job_name, namespace)
    if not pods:
        return ""
    pod = pods[0].metadata.name
    parts = []
    for container in ("network-lock-check", "module"):
        try:
            text = core().read_namespaced_pod_log(pod, namespace, container=container)
            parts.append(f"── {container} ──\n{text}")
        except ApiException:
            continue
    return "\n".join(parts)


def _waiting_reason(job_name: str, namespace: str) -> str:
    for pod in _job_pods(job_name, namespace):
        init = pod.status.init_container_statuses or []
        statuses = [*init, *(pod.status.container_statuses or [])]
        for status in statuses:
            if status.state and status.state.waiting and status.state.waiting.reason:
                return f"{status.name}: {status.state.waiting.reason}"
    return ""


def run_status(job_name: str, namespace: str) -> RunStatus:
    result = read_result(job_name)
    try:
        job = batch().read_namespaced_job_status(job_name, namespace)
    except ApiException as error:
        if error.status == 404:
            state = "succeeded" if result else "failed"
            return RunStatus(state, "job expired from the cluster", "", result)
        raise

    failed_condition = next(
        (c for c in job.status.conditions or [] if c.type == "Failed" and c.status == "True"), None
    )
    if job.status.succeeded:
        state, detail = "succeeded", ""
    elif failed_condition:
        state, detail = "failed", f"{failed_condition.reason}: {failed_condition.message}"
    elif job.status.active:
        state, detail = "running", _waiting_reason(job_name, namespace)
    else:
        state, detail = "pending", _waiting_reason(job_name, namespace)
    return RunStatus(state, detail, pod_logs(job_name, namespace), result)


def cluster_summary() -> str:
    core().read_namespace(MODULES_NAMESPACE)
    modules = batch().list_namespaced_cron_job(MODULES_NAMESPACE, label_selector=MODULE_LABEL).items
    return f"{settings.kube_context}, {len(modules)} module(s) in {MODULES_NAMESPACE}"
