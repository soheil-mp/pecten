# Security policy

## Supported versions

Pecten has not had a release yet. Until 1.0, security fixes are made on `main` only.

## Reporting a vulnerability

Please report vulnerabilities privately, not in public issues:

1. Go to the repository's **Security** tab.
2. Choose **Report a vulnerability** to open a private advisory.

Include what is affected, how to reproduce it and the impact you expect. You can expect an
acknowledgement within a week. Once a fix is available, the advisory is published with credit to
the reporter unless you prefer otherwise.

## Scope

In scope: code in this repository, its container images and its deployment configuration once
they exist. Out of scope: the third-party services and public data sources Pecten reads from;
please report those to their owners.

## Practices

- Secrets never enter the repository: gitleaks runs before every commit, and GitHub secret
  scanning with push protection is enabled.
- Devices authenticate with short-lived client certificates; the public API is read-only.
- Camera frames never leave the edge device, and personal fields in third-party data are dropped
  before storage (see [ADR-0004](docs/adr/0004-privacy-by-design-for-cameras.md)).
- Dependencies are kept current by Renovate and checked against a licence policy in CI; GitHub
  Actions are pinned by commit SHA and run with read-only permissions by default.
