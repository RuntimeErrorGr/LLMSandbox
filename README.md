# LLM Sandbox

A vulnerability scanner for LLM training data.

AI agents write **detectors** that find poisoned samples (Label Flipping, Clean Label) in datasets used to train LLMs.
Every new detector is benchmarked on deliberately poisoned data before it is approved and deployed through GitOps
(GitHub + ArgoCD) into an isolated Kubernetes sandbox. A guard blocks prompt-injection attempts against the agents.

```
 YOU ─► Guard ─► AI agents write a detector ─► exam on poisoned data ─► you approve
     ─► GitHub PR ─► CI ─► merge ─► ArgoCD installs it ─► scan any dataset
```

## Quick start

```bash
cp .env.example .env
make sync
make models
```

## Learning notes

Each build step has a short note with diagrams in [docs/](docs/).
