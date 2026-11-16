# Step 4 — GitOps with ArgoCD

## The idea

Git is the single blueprint of the cluster. ArgoCD, a program running inside the cluster,
keeps the cluster equal to the blueprint. Nobody (and no AI agent) changes the cluster by hand:
changes go through a pull request, CI checks and a merge.

```mermaid
flowchart LR
    dev[you / AI agent] -->|pull request| gh[(GitHub repo<br/>main branch)]
    ci[GitHub Actions CI] -->|checks the PR| gh
    subgraph cluster[kind cluster]
        argo[ArgoCD] -->|applies the difference| res[namespaces, policies, modules]
    end
    argo -->|pulls every 30 s| gh
```

| Git vs cluster | ArgoCD status | What ArgoCD does |
|---|---|---|
| equal | Synced | nothing |
| git changed (PR merged) | OutOfSync | applies git |
| cluster changed by hand | OutOfSync | restores git (self-heal) |

Push vs pull:

| By hand (Steps 0–3) | GitOps (from Step 4) |
|---|---|
| `kubectl apply` from a laptop | ArgoCD pulls from git |
| no record of who changed what | git history is the audit log |
| manual changes go unnoticed | drift is detected and repaired |
| the AI agents would need cluster admin | the AI agents only open pull requests |

## 4.1 Installing ArgoCD

`gitops/argocd/kustomization.yaml` pins ArgoCD v3.6.1 and lowers the git check interval
from 3 minutes to 30 seconds (`argocd-cm.yaml`).

```bash
make argocd      # install
make argocd-ui   # prints the admin password, then https://localhost:8080 (user admin)
```

| Pod | Job |
|---|---|
| argocd-server | web UI and API |
| argocd-repo-server | clones the git repo and runs kustomize: "what git wants" |
| argocd-application-controller | compares git with the cluster and applies the difference |
| argocd-applicationset-controller | creates Applications automatically (one per module) |
| redis, dex, notifications | cache, login, alerts |
