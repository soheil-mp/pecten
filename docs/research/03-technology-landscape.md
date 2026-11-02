# Technology landscape and selection

> Versions, licences and activity were read from each project's GitHub releases and repository
> metadata on 2 November 2026. Versions are pinned when each component is introduced; Renovate
> keeps them current afterwards.

## 1. Selection criteria

A tool is chosen when it:

1. has an **OSI-approved licence** compatible with an MIT project (§4);
2. is **actively maintained** (a release in the last six months, or a clearly stable project);
3. is an **industry standard or a credible successor** to one, so the skills transfer;
4. **runs on a laptop** (16 cores, 30 GB RAM) next to everything else, and in GitHub Actions;
5. contains **no machine learning** and does not pull in inference runtimes.

## 2. The chosen stack

### 2.1 Edge, simulation and shared algorithms

| Concern | Choice | Version | Licence | Why |
| :-- | :-- | :-- | :-- | :-- |
| Edge and gateway language | Rust (edition 2024) | 1.99.1 | MIT/Apache-2.0 | Predictable latency, small static binaries for arm64 devices, memory safety |
| Async runtime | tokio | 1.54 | MIT | De-facto standard |
| Linear algebra | nalgebra | 0.35 | Apache-2.0 | Kalman filters, camera geometry |
| Image primitives | imageproc | 0.27 | MIT | Morphology and filters; Pecten writes its own connected components and thresholds |
| FFT | rustfft | 6.4 | MIT/Apache-2.0 | Wingbeat spectra |
| Assignment | pathfinding (Kuhn–Munkres) | 4.16 | MIT/Apache-2.0 | Global track-to-detection assignment |
| Frame transport | Apache Arrow IPC (arrow-rs, pyarrow) | arrow 60.1 | Apache-2.0 | Typed, zero-copy frames between simulator and edge |
| MQTT client | rumqttc | 0.25 | Apache-2.0 | MQTT 5, TLS |
| Outbox | SQLite via rusqlite | 0.41 | MIT | Store-and-forward when offline |
| Protobuf | prost | 0.14 | Apache-2.0 | Edge event payloads |
| Camera input | v4l | 0.14 | MIT | UVC devices, including Y16 radiometric thermal (M22) |
| Python bindings | PyO3 + maturin | 0.30 / latest | MIT/Apache-2.0 | One algorithm implementation, used by the edge and the simulator's tests |
| Simulator language | Python | 3.14 | PSF-2.0 | NumPy rendering, fast iteration |
| Dataframes | Polars | 2.1 | MIT | Typed, fast, Arrow-native |

### 2.2 Transport and streaming

| Concern | Choice | Version | Licence | Why |
| :-- | :-- | :-- | :-- | :-- |
| Edge broker | Eclipse Mosquitto | 2.1.2 | EPL-2.0 or BSD-3-Clause | The reference MQTT 5 broker; small; mTLS and ACLs |
| Event envelope | CloudEvents 1.0.2 with the MQTT and Kafka bindings | spec | Apache-2.0 | Standard metadata, binary mode over MQTT 5 user properties |
| Platform log | Apache Kafka (KRaft) | 4.4.0 | Apache-2.0 | Durable, replayable backbone with many consumers |
| Kafka on Kubernetes | Strimzi | 1.3.0 | Apache-2.0 | Operator-managed Kafka node pools |
| Schema registry | Apicurio Registry | 3.3.3 | Apache-2.0 | Protobuf schemas; Confluent-compatible API used by RisingWave |
| Schema tooling | buf + protovalidate | latest / 1.2 | Apache-2.0 | Lint, breaking-change checks, validation rules |
| Stream processing | RisingWave | 3.1.0 | Apache-2.0 | Streaming SQL, materialised views, exactly-once Iceberg sink, Postgres wire protocol for live queries |

### 2.3 Lakehouse, batch and quality

| Concern | Choice | Version | Licence | Why |
| :-- | :-- | :-- | :-- | :-- |
| Table format | Apache Iceberg (format v3) | 1.12.0 | Apache-2.0 | The open table standard; deletion vectors, row lineage, geometry types |
| Catalog | Lakekeeper (Iceberg REST) | 0.14.2 | Apache-2.0 | Rust REST catalog with Postgres backend, credential vending |
| Object storage | SeaweedFS (S3 API) | 4.52 | Apache-2.0 | Mature, light; MinIO's repository was archived in 2026 |
| Catalog database | PostgreSQL via CloudNativePG | 1.30.1 | Apache-2.0 | Backups to object storage, failover drills |
| Python Iceberg client | PyIceberg | 0.12.0 | Apache-2.0 | Commits from ingestion connectors, maintenance |
| Query engine | Trino | 484 | Apache-2.0 | Iceberg REST connector; SQLMesh's supported Iceberg engine |
| Embedded engine | DuckDB | 2.0.0 | MIT | Unit tests, local analysis, the static web demo (DuckDB-WASM) |
| Transformations | SQLMesh | 0.236 | Apache-2.0 | Virtual data environments, column-level lineage, unit tests and audits; Linux Foundation project since March 2026 |
| Orchestration | Apache Airflow | 3.3.2 | Apache-2.0 | Industry standard; asset partitions (3.2), event-driven scheduling with asset watchers, state store (3.3) |
| In-pipeline validation | Pandera (Polars backend) | 0.35 | MIT | Typed dataframe schemas in connectors |
| Data contracts | Open Data Contract Standard (ODCS) + datacontract-cli | 3.2.0 / 1.2.9 | Apache-2.0 / MIT | Contracts as code, linted and tested in CI |
| Package validation | frictionless-py | 5.21 | MIT | Camtrap DP validation on ingest and export |
| Lineage | OpenLineage | 1.55 | Apache-2.0 | Standard lineage events from Airflow and Pecten's services |
| Imagery catalogue | STAC 1.1 with pystac and STAC Browser | 1.15 / 5.1 | Apache-2.0 | Drone survey imagery metadata |
| Spatial index | H3 | 4.x | Apache-2.0 | Colony density grids |

### 2.4 Product surface

| Concern | Choice | Version | Licence | Why |
| :-- | :-- | :-- | :-- | :-- |
| API | FastAPI + Pydantic v2 | latest | MIT | OpenAPI 3.1, typed models |
| Track standard | OGC API – Moving Features Part 1, MF-JSON 1.0 | standard | OGC | Standard trajectories |
| Event API docs | AsyncAPI 3 | standard | Apache-2.0 | MQTT and Kafka channels documented like REST |
| Web app | SvelteKit + Svelte 5 + TypeScript | Svelte 5.57 | MIT | Small bundles, static export for GitHub Pages |
| Maps and tracks | MapLibre GL JS + deck.gl | 6.16 / 9.3 | BSD-3-Clause / MIT | Vector maps; trips and H3 layers |
| Browser analytics | DuckDB-WASM | 1.33 | MIT | Backend-free demo over Parquet |
| Front-end tooling | Vite, pnpm, Biome, Playwright | 9 / 12 / 2.6 / 1.64 | MIT / MIT / MIT / Apache-2.0 | Fast, strict, tested |

### 2.5 DevOps and operations

| Concern | Choice | Version | Licence | Why |
| :-- | :-- | :-- | :-- | :-- |
| Python toolchain | uv, Ruff, mypy (strict), pytest, Hypothesis | uv 0.13.6, Ruff 0.17.3 | MIT/Apache-2.0 | Fast, reproducible |
| Rust toolchain | rustfmt, Clippy, cargo-nextest, cargo-llvm-cov, cargo-deny, proptest, criterion | nextest 0.9.150 | MIT/Apache-2.0 | Lint, test, coverage, licence and source policy |
| Tool pinning | mise + devcontainer | 2026.10.25 | MIT | One place for CLI tool versions |
| Task runner | just | latest | CC0-1.0 | Same commands locally and in CI |
| Containers | Docker Buildx, distroless bases | 29.x | Apache-2.0 | Multi-arch amd64 and arm64 |
| Supply chain | Syft (SBOM), cosign (keyless), GitHub artifact attestations, OpenSSF Scorecard | 2.5 (Scorecard action) | Apache-2.0 | Signed, attested, inspectable images |
| Kubernetes | k3d (local), kind (CI), K3s (edge) | 5.9 / 0.33 / 1.37 | MIT / Apache-2.0 / Apache-2.0 | Light, CI-friendly, real edge distribution |
| Packaging | Helm | 4.3.1 | Apache-2.0 | Charts per service |
| GitOps | Argo CD (ApplicationSets, progressive sync) + Argo Rollouts | 3.5.7 / 1.10.1 | Apache-2.0 | Declarative fleet rollout with health-gated promotion |
| Policy | Kyverno, Pod Security Admission | 1.19.2 | Apache-2.0 | Signed images only, non-root, limits |
| Certificates | cert-manager + trust-manager; smallstep step-ca for device enrolment | 1.21 / 0.26 / 0.30 | Apache-2.0 | Short-lived device certificates for mTLS |
| Secrets | SOPS with age | 3.13 | MPL-2.0 | Encrypted secrets in Git, decrypted in-cluster |
| Infrastructure as code | OpenTofu | 1.13.2 | MPL-2.0 | Repository settings, local clusters, optional cloud demo |
| Telemetry | OpenTelemetry SDKs and Collector | collector 0.164 | Apache-2.0 | One standard for metrics, logs and traces |
| Metrics, logs, traces | Prometheus 3, Loki 3, Tempo 3 | 3.15 / 3.7 / 3.1 | Apache-2.0 / AGPL-3.0 / AGPL-3.0 | Run as unmodified services |
| Dashboards | Grafana (dashboards as code) | 13.3 | AGPL-3.0 | Run as an unmodified service |
| SLOs | Pyrra | latest | Apache-2.0 | SLOs and burn-rate alerts from declarative specs |
| Docs | Zensical (by the Material for MkDocs team), Diátaxis, Mermaid, LikeC4 | 0.0.74 / 1.60 | MIT | Static docs site on GitHub Pages; architecture as code |
| Releases | release-please, Conventional Commits | 17.11 | Apache-2.0 | Versioned, changelogged releases |
| Dependencies | Renovate | 44.x | AGPL-3.0 (hosted app) | Grouped, scheduled updates; digests pinned |
| Integration tests | Testcontainers (Python and Rust), Toxiproxy | 4.15 / 0.28 | Apache-2.0 / MIT | Real brokers in tests; network faults |

## 3. Alternatives considered

| Layer | Alternative | Decision |
| :-- | :-- | :-- |
| Edge language | Python with NumPy | Too slow and heavy for 30 fps VGA on a single arm64 core; kept for the simulator |
| Edge vision | OpenCV | Rejected: bundles a neural-network inference module (`dnn`); Pecten's operators are few and written in Rust |
| Edge transport | NATS JetStream, Zenoh | Both good; MQTT 5 is the IoT standard with a CloudEvents binding and the widest device support |
| MQTT broker | EMQX | Recent releases are under the Business Source License 1.1, so not allowed |
| MQTT broker | NanoMQ | MIT and fast, but a smaller ecosystem for ACLs and mTLS identity mapping |
| Backbone | Redpanda | Business Source License for the community edition; Kafka 4.x is KRaft-only and simple enough now |
| Stream processing | Apache Flink 2.x | The industry reference, but JVM-heavy for a laptop next to Trino and Airflow; RisingWave's SQL and Postgres protocol fit better. Revisit if exactly-once Iceberg sinks or watermark semantics fall short |
| Stream processing | Kafka Connect Iceberg sink | Landing only, no streaming analytics; kept as the fallback for landing |
| Stream processing | Quix Streams | Good for Python stream jobs; RisingWave covers SQL MVs and serving in one component |
| Lakehouse | DuckLake | Elegant, but Iceberg is the cross-engine standard (Trino, DuckDB, RisingWave, PyIceberg all read and write it) |
| Catalog | Apache Polaris, Nessie | Polaris is heavier (JVM); Nessie's Iceberg REST mode is an option. Lakekeeper is light and Rust-based |
| Object storage | RustFS | Apache-2.0 and generally available since 16 September 2026, with an integrated Iceberg REST catalogue; too new to be the default. A CI conformance test runs against both, so switching is configuration |
| Object storage | MinIO | Repository archived (April 2026) and AGPL-3.0 |
| Orchestration | Dagster, Prefect, Kestra | Dagster's asset model is excellent, but Airflow 3 now has assets, partitions and event-driven scheduling and is what most teams run |
| Transformations | dbt-core | Still Apache-2.0, but dbt Labs and Fivetran merged (closed June 2026) and the Fusion engine is proprietary; SQLMesh's virtual environments and lineage suit per-PR plans, and it is now community-governed |
| Ingestion | dlt | Its Iceberg REST-catalogue destination is documented under the commercially licensed dltHub toolkit, so connectors use PyIceberg directly |
| Data quality | Great Expectations (GX Core 1.x) | Capable but heavy; Pandera, SQLMesh audits and ODCS contracts cover the same ground with less machinery |
| Lineage backend | Marquez | Last release October 2024 and slow activity since; OpenLineage events go to Kafka and an Iceberg table, Marquez stays an optional viewer |
| Docs | Material for MkDocs | Its team now builds Zensical as the successor; starting on Zensical avoids a migration |
| Dashboards | Perses | Apache-2.0 and promising; Grafana's ecosystem and alerting are more complete today |

## 4. Licence policy for dependencies

Pecten is MIT-licensed. Dependencies that are **linked or vendored** must use one of:

- MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, Zlib, 0BSD, Unicode-3.0, BSL-1.0 (Boost),
  PSF-2.0, CC0-1.0, Unlicense;
- MPL-2.0 (file-level copyleft; allowed unmodified).

Services that run as **separate, unmodified processes** (for example Mosquitto under EPL-2.0, or
Grafana, Loki and Tempo under AGPL-3.0) are allowed because Pecten neither links nor
redistributes modified versions of them. They are listed in the deployment documentation.

**Never allowed:** source-available licences (Business Source License, SSPL, Elastic License,
Commons Clause, PolyForm), non-commercial or no-derivatives terms, and unlicensed code.

**Machine-learning deny list.** CI fails if any of these appear, directly or transitively:

- *Python:* `torch`, `tensorflow`, `jax`, `keras`, `onnx`, `onnxruntime`, `scikit-learn`,
  `xgboost`, `lightgbm`, `catboost`, `transformers`, `sentence-transformers`, `ultralytics`,
  `opencv-python`, `opencv-python-headless`, `opencv-contrib-python`, `mediapipe`, `openai`,
  `anthropic`, `google-generativeai`, `ollama`, `langchain*`, `llama*`, `birdnet*`;
- *Rust:* `tch`, `ort`, `onnxruntime*`, `candle-*`, `burn*`, `tract-*`, `linfa*`, `smartcore`,
  `rust-bert`;
- *JavaScript:* `@tensorflow/*`, `onnxruntime-web`, `@xenova/transformers`,
  `@huggingface/*`, `ml5`.

The checks are `tools/dependency_policy.py` (Python and JavaScript lock files) and
`cargo deny check licenses bans sources` (Rust), run in pre-commit, `just lint` and CI (M0.8).

## 5. Landscape notes that shaped these choices

- **MinIO:** the `minio/minio` repository was archived in April 2026.
- **RustFS:** reached general availability on 16 September 2026 (1.0.4 on 25 October 2026).
- **DuckDB 2.0** (21 October 2026): the Iceberg extension writes to attached REST catalogues
  (`INSERT`, `UPDATE`, `DELETE`, `MERGE INTO`, merge-on-read, deletion vectors for v3 tables);
  `GEOGRAPHY` is not yet supported.
- **Airflow:** 3.2 (April 2026) added asset partitioning; 3.3 (July 2026) added a task and asset
  state store and experimental non-Python task SDKs. Python 3.10–3.14 is supported.
- **dbt and SQLMesh:** dbt Labs and Fivetran completed their merger on 1 June 2026; Fivetran
  contributed SQLMesh to the Linux Foundation on 25 March 2026.
- **Kafka 4.x** runs only in KRaft mode; ZooKeeper is gone.
- **RisingWave 3.x** added Iceberg compaction scheduling, sort-order keys and Iceberg v3 tables
  with a primary-key index for its sink, and Protobuf for its MQTT source.
- **Marquez:** last release 0.50.0 (October 2024); commits continued into April 2026.
- **ODCS 3.2.0** was released on 8 September 2026; **Camtrap DP 1.0.2** on 10 June 2025.

## 6. Resource budget on a laptop

Compose profiles keep the full stack within about 12 GB of RAM: `core` (Mosquitto, Kafka,
Apicurio, SeaweedFS, Postgres, Lakekeeper, about 3 GB), `stream` (RisingWave, about 2 GB),
`batch` (Trino and Airflow, about 5 GB) and `obs` (OpenTelemetry Collector, Prometheus, Loki,
Tempo and Grafana, about 2 GB). These figures are planning estimates, measured in M18.4.
