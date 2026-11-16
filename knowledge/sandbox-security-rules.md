# Sandbox security rules

These rules are enforced by the policy checker (`scripts/check_module.py`) in the agent pipeline and again in CI.
A module that breaks any rule is rejected.

## Module code rules (main.py): what is allowed and what is forbidden

What module code is allowed (permitted) to do:

- Read inputs and write results only through `sandbox_sdk`.
- Import the libraries of the runner image: numpy, pandas, scikit-learn, torch, transformers, sentence-transformers, chromadb, and the Python standard library (except the forbidden modules below).
- Load models only from local folders with `sdk.model_path`.
- Write files only in `sdk.run_dir()` or `/tmp`.

What module code is forbidden to do:

- Import subprocess, socket, requests, urllib, http, ftplib, smtplib, ctypes or multiprocessing.
- Call eval, exec, compile, `__import__`, os.system, os.popen, os.exec* or os.spawn*.
- Open any network connection or download anything.
- Be longer than 400 lines.

## Kubernetes rules for cronjob.yaml

- The image must be the shared runner image `sandbox-runner`.
- The CronJob must be suspended (`suspend: true`); runs are created by the platform.
- Pod security context: `runAsNonRoot: true`, `runAsUser: 1000`, `seccompProfile: RuntimeDefault`.
- Container security context: `allowPrivilegeEscalation: false`, `readOnlyRootFilesystem: true`, `capabilities.drop: [ALL]`.
- `automountServiceAccountToken: false`.
- An init container `network-lock-check` must run first: it waits until outbound traffic is blocked and fails the pod if it is not blocked after 30 seconds. The NetworkPolicy engine needs a moment to see a new pod, and this check closes that gap.
- CPU and memory requests and limits must be set; limits at most 4 CPU and 6Gi memory.
- `activeDeadlineSeconds` must be set (at most 1800) and `backoffLimit: 0`.
- Forbidden: hostPath volumes, privileged containers, hostNetwork, hostPID, extra capabilities.

## Namespace protections (set once by the platform)

- Pod Security Admission level `restricted` on sandbox namespaces.
- A default-deny NetworkPolicy: no ingress and no egress, so modules cannot reach the internet.
- ResourceQuota and LimitRange cap the total CPU and memory a namespace can use.
- Datasets and models are mounted read-only; only the run folder is writable.
