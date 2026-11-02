# Working on Pecten

Context for coding assistants and contributors. Read [ROADMAP.md](ROADMAP.md) for what to build
next and [docs/architecture.md](docs/architecture.md) for how the parts fit.

## Scope boundaries

Every change must stay inside these boundaries:

- **No machine learning or AI in the product.** No calls to model APIs, no local models,
  embeddings or ML libraries, and no datasets for training or evaluating models. Perception is
  deterministic signal processing and estimation
  ([ADR-0002](docs/adr/0002-deterministic-explainable-perception.md)). Do not add OpenCV; it
  bundles a neural-network inference module.
- **No personal data.** Only synthetic data and public data about nature (weather, taxonomy,
  traits, protected areas, minimised camera-trap observations). Fixtures, seeds, examples and
  screenshots are synthetic. Never fetch third-party images. No scraping of data about people.
  No health or financial records.
- **No user accounts** and no storing of other people's data.
- **No security tooling** that finds or exploits vulnerabilities.
- **No secrets in code or history.** Read keys from environment variables; `.env` stays ignored;
  every new variable goes into `.env.example` with a placeholder value.
- **Licences.** The project is MIT. Only add dependencies whose licences allow that (see
  [technology landscape §4](docs/research/03-technology-landscape.md#4-licence-policy-for-dependencies)),
  and never copy code we do not have the right to share.

## Git workflow

- Commit after each working step with a Conventional Commit message (`feat:`, `fix:`, `docs:`,
  `chore:`, `test:`, `refactor:`, `ci:`, `build:`, `perf:`).
- Never rewrite published history: no squashing, amending or rebasing of pushed commits, no
  force-pushing, and no changing of commit dates.
- Keep README.md and ROADMAP.md current when a change affects them; tick roadmap items when they
  are merged and add a progress-log row.

## Engineering conventions

- Rust (edition 2024, pinned toolchain) for `crates/`; Python 3.14 with uv for `packages/`.
- Ruff, `mypy --strict`, rustfmt and Clippy with warnings as errors.
- SI units in storage with unit suffixes in names (`speed_mps`, `altitude_agl_m`, `temp_k`).
- Seed every random number generator; identical inputs must give identical outputs.
- Schemas and data contracts change before the code that uses them.
- Significant decisions get an ADR in `docs/adr/`.
- Data never goes into Git; tests use tiny synthetic fixtures. Respect the byte budgets.
