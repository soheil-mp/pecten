# Contributing to Pecten

Thank you for your interest. Pecten is a personal open-source project, and contributions that
fit its scope are welcome: bug reports, documentation fixes, tests and roadmap items.

## Scope

Before you start, read the scope boundaries; pull requests outside them cannot be merged.

- **No machine learning.** Perception is deterministic signal processing and estimation; no
  models, inference, model APIs or training data
  ([ADR-0002](docs/adr/0002-deterministic-explainable-perception.md)).
- **No personal data.** Only synthetic data and public data about nature. Never commit camera
  images, recordings or data files, and never add code that fetches third-party images
  ([ADR-0004](docs/adr/0004-privacy-by-design-for-cameras.md)).
- **Licences.** Pecten is MIT. New dependencies must pass the dependency policy
  (`just deps`); see [technology landscape §4](docs/research/03-technology-landscape.md#4-licence-policy-for-dependencies).

## Getting set up

```sh
just setup   # uv workspace, Git hooks, Rust crates, pinned CLI tools via mise
just check   # everything CI checks
```

You need Git, uv, rustup and just; mise is optional. The README lists the details, and the
devcontainer in `.devcontainer/` has everything preinstalled.

## Finding work

- [ROADMAP.md](ROADMAP.md) is the source of truth for planned work. Every open item has an ID
  such as `M3.4` and, once synced, a GitHub issue with the same title.
- Issues labelled `size:S` are good first contributions.
- For anything larger than a bug fix, open an issue first so the approach can be agreed.

## Making a change

1. Create a branch from `main`.
2. Change schemas and data contracts **before** the code that uses them (ADR-0011).
3. Add tests at the right level: unit, property (Hypothesis, proptest), scenario (seeded sensor
   twin runs) or integration.
4. Run `just check`; pre-commit runs the fast checks on every commit.
5. Update the docs that your change affects, and tick the roadmap item if you complete one.
6. Open a pull request; the template has a checklist.

## Conventions

- **Commits** follow [Conventional Commits](https://www.conventionalcommits.org/): `feat:`,
  `fix:`, `docs:`, `test:`, `refactor:`, `perf:`, `build:`, `ci:` or `chore:`, with an optional
  scope such as `feat(edge):`. A commit-message hook checks this. Release notes are generated
  from these messages.
- **History** is never rewritten once pushed: no force-pushes, no squashing or rebasing of
  published commits. Pull requests are merged with merge commits.
- **Python:** 3.14, Ruff with every rule family, `mypy --strict`, Google-style docstrings.
- **Rust:** edition 2024, rustfmt, Clippy pedantic with warnings as errors, no `unsafe` outside
  `pecten-py`.
- **Units:** SI units in storage, with the unit in the name (`speed_mps`, `altitude_agl_m`,
  `temp_k`).
- **Determinism:** seed every random number generator; identical inputs give identical outputs.
- **Decisions:** anything that changes a recorded decision or adds a technology needs an ADR in
  `docs/adr/` ([ADR-0001](docs/adr/0001-record-architecture-decisions.md)).

## Reporting bugs and security problems

Use the bug-report form for bugs. Report security problems privately through the repository's
Security tab, as described in [SECURITY.md](SECURITY.md).

## Code of conduct

Everyone taking part is expected to follow the [code of conduct](CODE_OF_CONDUCT.md).
