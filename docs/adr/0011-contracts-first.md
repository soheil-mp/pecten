# ADR-0011: Contracts first: Protobuf, a schema registry and ODCS data contracts

- **Status:** accepted
- **Date:** 2026-11-02

## Context and problem statement

Events cross four technologies (Rust edge, MQTT, Kafka, RisingWave) before they become tables
that SQLMesh, the API and the web app read. Uncoordinated changes would break consumers silently.

## Decision outcome

- **Events:** Protobuf schemas in `proto/` are the source of truth. `buf lint` and
  `buf breaking` run in CI; protovalidate rules express field constraints (ranges, required
  fields). Schemas are registered in Apicurio with backward-transitive compatibility.
- **Tables:** every bronze, silver, gold and reference table has an Open Data Contract Standard
  (ODCS v3.2) document in `contracts/` with schema, quality rules, freshness and completeness
  service levels, ownership, retention, byte budget and a per-field privacy classification.
- **Order of change:** schemas and contracts change first, in the same pull request as the code
  that needs them; breaking changes require a new major version and a migration note.
- **Generated artefacts:** Rust and Python types from Protobuf, JSON Schemas from Pydantic
  models, and reference documentation for all of them.

## Consequences

- Positive: breaking changes are caught in CI, not in production; one documented truth.
- Negative: more ceremony for small changes, which is accepted.

## Confirmation

- `datacontract lint` and `datacontract test` (against the end-to-end stack) run in CI.
- Schema-evolution drills (M10.8) add a field end to end without downtime.
