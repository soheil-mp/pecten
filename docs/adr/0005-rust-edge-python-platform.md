# ADR-0005: Rust on the edge, Python for the simulator and platform, one monorepo

- **Status:** accepted
- **Date:** 2026-11-02

## Context and problem statement

The edge must process a 640 × 512 thermal stream at 30 frames per second on one arm64 core of a
Raspberry Pi 5-class device, with bounded memory and latency. The simulator, ingestion, pipelines
and API benefit from Python's data ecosystem.

## Considered options

1. Python everywhere (rejected for the edge: too slow and heavy).
2. C++ on the edge (rejected: weaker memory safety and packaging).
3. **Rust for edge, gateway and shared algorithms; Python for the rest** (chosen).

## Decision outcome

- Cargo workspace under `crates/`: `pecten-vision` (pure algorithms, no I/O), `pecten-edge`,
  `pecten-gateway`, `pecten-proto`, and `pecten-py` (PyO3 bindings of `pecten-vision`).
- uv workspace under `packages/`: `pecten-sim`, `pecten-ingest`, `pecten-pipelines`,
  `pecten-survey`, `pecten-api`, `pecten-contracts`.
- The simulator's verification tests call the Rust algorithms through `pecten-py`, so there is
  one implementation of each algorithm.
- Python 3.14 (supported by Airflow 3.3, SQLMesh and the rest of the stack); Rust edition 2024
  with a pinned toolchain.

## Consequences

- Positive: fast, safe edge binaries; one algorithm implementation; Python where it shines.
- Negative: two toolchains in CI and for contributors. `just` and `mise` hide most of this.

## Confirmation

- Criterion benchmarks on an arm64 CI runner enforce the frame-rate budget (M6.9).
- `cargo deny` and import-linter enforce the dependency direction between packages.
