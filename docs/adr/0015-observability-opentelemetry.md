# ADR-0015: Observability with OpenTelemetry, and data treated as a monitored service

- **Status:** accepted
- **Date:** 2026-11-02

## Context and problem statement

A detection travels from a camera through an edge process, MQTT, the gateway, Kafka, RisingWave,
Iceberg, SQLMesh and the API. When numbers look wrong, operators need to see where and why, for
both the software and the data.

## Decision outcome

- **One standard:** OpenTelemetry SDKs in Rust and Python; the W3C `traceparent` travels inside
  CloudEvents over MQTT and as Kafka headers, so one trace spans edge to lakehouse.
- **Back ends:** OpenTelemetry Collector → Prometheus 3 (metrics over OTLP), Loki (logs), Tempo
  (traces); Grafana dashboards and alerts provisioned as code.
- **Service-level objectives** declared with Pyrra, with multi-window burn-rate alerts:
  edge-to-lake latency, data freshness, completeness (frames processed versus expected from
  heartbeats) and API availability.
- **Data observability:** Iceberg metadata, contract-check results, reconciliation drift and
  budget usage are exported as metrics next to service metrics.
- **Runbooks:** every alert links to a runbook in `docs/runbooks/`.

## Consequences

- Positive: one place to debug both software and data.
- Negative: telemetry has its own resource cost; the `obs` Compose profile is optional.

## Confirmation

- An end-to-end test asserts that one trace contains spans from edge, gateway and API.
- Alert rules are unit-tested with `promtool test rules`.
