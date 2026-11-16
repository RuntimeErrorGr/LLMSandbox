# Sandbox security rules

These rules are enforced by the policy checker (`scripts/check_module.py`) in the agent pipeline and again in CI.
A module that breaks any rule is rejected.

## Code rules for main.py

- Use `sandbox_sdk` for all input and output.
- Forbidden imports: subprocess, socket, requests, urllib, http, ftplib, smtplib, ctypes, multiprocessing.
- Forbidden calls: eval, exec, compile, `__import__`, os.system, os.popen, os.exec*, os.spawn*.
- No network access of any kind; models must be loaded with `sdk.model_path`.
- Do not write outside `sdk.run_dir()` or `/tmp`.
- Maximum file size: 400 lines.

## Kubernetes rules for cronjob.yaml

- The image must be the shared runner image `sandbox-runner`.
- The CronJob must be suspended (`suspend: true`); runs are created by the platform.
- Pod security context: `runAsNonRoot: true`, `runAsUser: 1000`, `seccompProfile: RuntimeDefault`.
- Container security context: `allowPrivilegeEscalation: false`, `readOnlyRootFilesystem: true`, `capabilities.drop: [ALL]`.
- `automountServiceAccountToken: false`.
- CPU and memory requests and limits must be set; limits at most 4 CPU and 6Gi memory.
- `activeDeadlineSeconds` must be set (at most 1800) and `backoffLimit: 0`.
- Forbidden: hostPath volumes, privileged containers, hostNetwork, hostPID, extra capabilities.

## Namespace protections (set once by the platform)

- Pod Security Admission level `restricted` on sandbox namespaces.
- A default-deny NetworkPolicy: no ingress and no egress, so modules cannot reach the internet.
- ResourceQuota and LimitRange cap the total CPU and memory a namespace can use.
- Datasets and models are mounted read-only; only the run folder is writable.
