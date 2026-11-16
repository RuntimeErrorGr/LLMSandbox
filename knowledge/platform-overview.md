# LLM Sandbox: platform overview

## What the platform does

The LLM Sandbox is a vulnerability scanner for LLM training data.
A training dataset is a list of examples (a text and its label) used to fine-tune an LLM.
An attacker who can modify that dataset can make the LLM learn wrong or hidden behaviour. This is called data poisoning.

The platform runs security modules called detectors. A detector reads a dataset and reports which samples look poisoned, each with a suspicion score.

## Main flow

1. A user asks the AI agents for a new detector, for example "a label flipping detector using kNN".
2. The guard checks the request for prompt injection or abuse.
3. The Architect agent plans the detector, the Security Specialist agent writes the code, the DevOps Specialist agent writes the deployment settings.
4. The detector passes a policy check, a smoke test and an automatic benchmark inside the sandbox.
5. A human approves it, a GitHub pull request is opened, CI checks it, and after merge ArgoCD deploys it.
6. The detector can then scan any dataset from the Scan page and appears on the Leaderboard.

## Module kinds

- detector: scans a dataset and reports suspicious samples. Agents may write detectors.
- poisoner: poisons a clean dataset on purpose and writes an answer key. Only humans write poisoners.
- trainer: fine-tunes the victim LLM (SmolLM2-135M) to measure the impact of an attack.

## Threat catalog

Every detector must target one threat from the catalog:

| threat | poisoner | benchmark datasets | pass bar |
|---|---|---|---|
| label_flip | poison-label-flip | sst2, agnews | F1 >= 0.6 |
| clean_label | poison-clean-label | sst2 | F1 >= 0.6 |

## Where things run

- The platform web app runs on the laptop.
- Modules run as Kubernetes Jobs inside the kind cluster, in the namespaces sandbox-playground (tests of new detectors) and sandbox-modules (approved modules).
- Modules have no internet access and no access to the platform or to Ollama.
