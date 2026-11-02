# Pecten

Pecten is an open platform for monitoring birds with cameras: fixed visible-light cameras at nest
boxes and feeders, thermal and stereo-thermal cameras for night migration and wind turbines, and
drone surveys of colonies. Edge software turns frames into tracks, counts and flight measurements
with deterministic, explainable image processing, and a data platform turns those events into
analysis-ready, standards-based datasets.

It is named after the *pecten oculi*, the comb-shaped structure found in every bird's eye.

> **Status:** planning is complete and building starts with the walking skeleton. Nothing is
> runnable yet. See [Status and plans](#status-and-plans).

## What makes it different

- **No machine learning.** Detection, tracking and classification use classical signal
  processing and estimation (background models, connected components, Kalman filters,
  Kuhn–Munkres assignment, spectral wingbeat analysis, stereo geometry). Every result carries the
  reasons behind it.
- **A physics-based sensor twin.** A simulator renders thermal, visible-light, stereo and drone
  imagery from radiometry, optics, weather and bird-flight allometry, with exact ground truth. It
  is the test reference for the whole system, and frames are regenerated instead of stored.
- **Privacy by architecture.** Frames never leave the camera's edge device; privacy masks apply
  before processing; a rule-based guard suppresses people; third-party data is stripped of
  personal fields before it is stored.
- **Standards in and out.** Camtrap DP, OGC Moving Features, STAC, GeoParquet, CloudEvents,
  AsyncAPI, OpenLineage and Open Data Contract Standard contracts.
- **Production-grade data engineering.** MQTT 5 with mutual TLS, Kafka, streaming SQL, an Apache
  Iceberg lakehouse, Airflow 3, SQLMesh, data contracts, physics-aware data-quality checks, byte
  budgets, GitOps for an edge fleet, a signed supply chain and SLOs.

## Who it's for

- **Ecologists and conservation practitioners** who want transparent, reproducible camera-based
  measurements: flight heights near turbines, passage rates, nest-box activity and colony counts.
- **Data and platform engineers** who want a complete, realistic reference for edge-to-lakehouse
  pipelines, built with current open-source tools and strict engineering practice.
- **Anyone curious** about what cameras can measure about birds without machine learning.

## Built with

| Layer | Tools |
| :-- | :-- |
| Edge and gateway | Rust 1.99 (tokio, nalgebra, Arrow IPC, rumqttc, prost), MQTT 5 |
| Sensor twin | Python 3.14, NumPy, Polars; AVONET and AviList reference data; Open-Meteo weather |
| Transport | Eclipse Mosquitto, CloudEvents, Protobuf with buf, Apache Kafka 4, Apicurio Registry |
| Streaming | RisingWave |
| Lakehouse | Apache Iceberg, Lakekeeper (REST catalog), SeaweedFS, PostgreSQL, Trino, DuckDB |
| Batch | Apache Airflow 3, SQLMesh, PyIceberg, Pandera, ODCS contracts, OpenLineage |
| Product | FastAPI, OGC API – Moving Features, STAC, SvelteKit, MapLibre GL, deck.gl, DuckDB-WASM |
| Operations | Docker, Kubernetes (k3d, kind, K3s), Helm, Argo CD, Kyverno, SOPS, OpenTofu, OpenTelemetry, Prometheus, Grafana |
| Engineering | uv, Ruff, mypy, pytest, Hypothesis, Clippy, proptest, criterion, pre-commit, GitHub Actions, Renovate, release-please |

Why each was chosen, with versions checked on 2 November 2026:
[technology landscape](docs/research/03-technology-landscape.md).

## How to run it

There is no runnable code yet. What works on a fresh clone today:

```sh
git clone https://github.com/soheil-mp/pecten.git
cd pecten
pre-commit install --hook-type pre-commit --hook-type commit-msg
pre-commit run --all-files
```

Requirements: Git and [pre-commit](https://pre-commit.com/). The hooks check for secrets
(gitleaks), spelling, Markdown style and commit-message format.

Once the walking skeleton (milestone M1) lands, the full local stack will start with
`just up core` and an end-to-end test with `just e2e`, using Docker Compose and the toolchain
pinned in `mise.toml`.

## Documentation

- [Domain research](docs/research/01-domain.md): camera physics, bird flight, metrics, methods,
  privacy and law.
- [Data sources](docs/research/02-data-sources.md): what real data is used, verified live, and how
  personal fields are removed.
- [Technology landscape](docs/research/03-technology-landscape.md): the stack, alternatives and the
  licence policy.
- [Architecture](docs/architecture.md) and [architecture decision records](docs/adr/README.md).

## Status and plans

Planning is done: research, data sources checked against the live services, sixteen ADRs and the
target architecture. The work ahead, 24 milestones and about 1,060 hours from the walking
skeleton to 1.0, is in [ROADMAP.md](ROADMAP.md). The next item is M0.3, the Rust workspace.

All data in this repository is synthetic or comes from the public, non-personal sources listed
in the data-sources document.

## License

MIT, see [LICENSE](LICENSE). Third-party data keeps its own licence; attribution is listed in
[data sources §11](docs/research/02-data-sources.md#11-attribution).
