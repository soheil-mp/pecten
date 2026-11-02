# ADR-0008: An Apache Iceberg lakehouse with Lakekeeper and S3-compatible storage

- **Status:** accepted
- **Date:** 2026-11-02

## Context and problem statement

Several engines must read and write the same tables: RisingWave (streaming sink), PyIceberg
(ingestion and maintenance), Trino (SQLMesh models and ad-hoc queries) and DuckDB (tests, local
analysis and the static demo). Tables need schema evolution, time travel and geometry columns.

## Considered options

1. Plain Parquet in object storage (no transactions or schema evolution).
2. DuckLake (elegant, but fewer engines read and write it).
3. Delta Lake (strong, but weaker support in the chosen engines).
4. **Apache Iceberg format v3 with an Iceberg REST catalog** (chosen).

## Decision outcome

- **Format:** Iceberg v3 where every engine in the path supports it, v2 otherwise; the choice is
  per table and recorded in its contract.
- **Catalog:** Lakekeeper (Rust, Apache-2.0) backed by PostgreSQL, with credential vending so
  engines never hold long-lived storage keys.
- **Storage:** SeaweedFS through its S3 API. A conformance smoke test runs the same suite against
  RustFS, so the backend is replaceable by configuration.
- **Layout:** namespaces `raw`, `bronze`, `silver`, `gold`, `ref` and `ops`; partitioning by event
  day and a device bucket; sort orders for common filters; per-table retention.
- **Maintenance:** snapshot expiry, orphan-file removal and manifest rewrites on a schedule; tags
  on snapshots for every release so results stay reproducible.

## Consequences

- Positive: an open standard with time travel and multi-engine access; skills that transfer.
- Negative: more moving parts than a single-file database; maintenance must be automated.

## Confirmation

- Integration tests write with one engine and read with the others.
- Iceberg metadata (snapshot counts, file counts, average file size) is exported as metrics and
  alerted on (M20).
