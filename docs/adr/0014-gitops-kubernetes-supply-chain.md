# ADR-0014: Kubernetes with GitOps, and a signed software supply chain

- **Status:** accepted
- **Date:** 2026-11-02

## Context and problem statement

Pecten has two deployment targets: a central platform and a fleet of edge devices at several
sites. Both must be reproducible, auditable and safe to roll out and roll back.

## Decision outcome

- **Local development:** Docker Compose profiles for speed.
- **Clusters:** a k3d `platform` cluster and a k3d `edge` cluster that simulates several sites
  locally; kind in CI; K3s on real arm64 devices (M22).
- **Packaging:** one Helm 4 chart per Pecten service; upstream operators for Kafka (Strimzi),
  PostgreSQL (CloudNativePG) and certificates (cert-manager, trust-manager).
- **GitOps:** Argo CD app-of-apps; ApplicationSets generate one application per site from the
  fleet registry; progressive syncs and Argo Rollouts analysis gate promotion from a canary site
  to the rest.
- **Secrets:** SOPS with age; nothing in plain text in Git.
- **Policy:** Kyverno admits only signed images from the project's registry, non-root containers
  with resource limits and no `latest` tags; Pod Security Admission `restricted`; default-deny
  NetworkPolicies.
- **Supply chain:** multi-arch images (amd64, arm64) built in GitHub Actions; SBOMs with Syft;
  keyless cosign signatures and GitHub artifact attestations (SLSA build provenance); actions
  pinned by commit SHA; OpenSSF Scorecard.
- **Infrastructure as code:** OpenTofu manages GitHub repository settings, the local clusters and
  an optional, disposable cloud demo.

## Consequences

- Positive: production-grade practices end to end, all reviewable in Git.
- Negative: a steep local setup, mitigated by `just up` and Compose for everyday work.

## Confirmation

- `helm lint`, `kubeconform` and chart tests in CI; a kind-based end-to-end job deploys the
  platform and runs a scenario.
- Kyverno policy tests run in CI with the Kyverno CLI.
