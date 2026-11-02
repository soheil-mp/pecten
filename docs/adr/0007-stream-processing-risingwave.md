# ADR-0007: Stream processing with RisingWave

- **Status:** accepted
- **Date:** 2026-11-02

## Context and problem statement

Events must land in the lakehouse with exactly-once semantics, and some results are needed live:
per-minute activity, turbine rotor-zone passage rates, device liveness and rule-based curtailment
advisories. The stack already runs Trino and Airflow on a laptop.

## Considered options

1. Apache Flink 2.x: the industry reference, but JVM-heavy next to Trino and Airflow.
2. Kafka Connect Iceberg sink: landing only, no streaming analytics.
3. Quix Streams: Python stream jobs, but serving and SQL views would need more components.
4. **RisingWave**: streaming SQL with materialised views, an exactly-once Iceberg sink with
   compaction, and the Postgres wire protocol for live queries (chosen).

## Decision outcome

- Kafka sources with Protobuf schemas from the registry; event-time watermarks with a stated
  lateness bound.
- Materialised views for live aggregates and the advisory rules, queried by the API over the
  Postgres protocol and pushed to the web app as server-sent events.
- Iceberg sinks to Lakekeeper for bronze tables; commit intervals and file sizes tuned against
  the small-files problem; RisingWave-managed compaction where available, Airflow maintenance
  otherwise.
- Streaming SQL lives in `streaming/` as ordered, idempotent migrations applied by a small tool,
  reviewed like any other code.
- Late data beyond the watermark is handled in batch: nightly reconciliation recomputes daily
  aggregates from bronze and compares them with the streaming results (M14.5).

## Consequences

- Positive: one component for landing, live analytics and serving; SQL that analysts can read.
- Negative: smaller community than Flink; RisingWave-specific SQL in places. Kafka Connect's
  Iceberg sink remains the documented fallback for landing.

## Confirmation

- End-to-end tests assert exactly-once landing (no duplicate event IDs in bronze) across
  RisingWave restarts.
- Reconciliation drift above 0.5 % raises an alert.
