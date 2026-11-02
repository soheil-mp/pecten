# Architecture decision records

Decisions are recorded with the [MADR 4](https://adr.github.io/madr/) structure, as described in
[ADR-0001](0001-record-architecture-decisions.md). Superseded records stay in place and point to
their successor.

| ADR | Decision | Status |
| :-- | :-- | :-- |
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | accepted |
| [0002](0002-deterministic-explainable-perception.md) | Deterministic, explainable perception with no machine learning | accepted |
| [0003](0003-physics-based-sensor-twin.md) | A physics-based sensor twin as the primary data source | accepted |
| [0004](0004-privacy-by-design-for-cameras.md) | Privacy by design for cameras | accepted |
| [0005](0005-rust-edge-python-platform.md) | Rust on the edge, Python for the simulator and platform, one monorepo | accepted |
| [0006](0006-mqtt-cloudevents-protobuf-kafka.md) | MQTT 5 with CloudEvents and Protobuf at the edge, Kafka as the backbone | accepted |
| [0007](0007-stream-processing-risingwave.md) | Stream processing with RisingWave | accepted |
| [0008](0008-iceberg-lakehouse-lakekeeper.md) | An Apache Iceberg lakehouse with Lakekeeper and S3-compatible storage | accepted |
| [0009](0009-orchestration-airflow-3.md) | Orchestration with Apache Airflow 3 | accepted |
| [0010](0010-transformations-sqlmesh-trino.md) | Transformations with SQLMesh on Trino, unit-tested on DuckDB | accepted |
| [0011](0011-contracts-first.md) | Contracts first: Protobuf, a schema registry and ODCS data contracts | accepted |
| [0012](0012-ingestion-connectors-pyiceberg.md) | Public-source ingestion with small, idempotent connectors on PyIceberg | accepted |
| [0013](0013-small-data-by-design.md) | Small data by design | accepted |
| [0014](0014-gitops-kubernetes-supply-chain.md) | Kubernetes with GitOps, and a signed software supply chain | accepted |
| [0015](0015-observability-opentelemetry.md) | Observability with OpenTelemetry, and data treated as a monitored service | accepted |
| [0016](0016-standards-based-outputs.md) | Standards-based outputs | accepted |
