# ADR-0012: Public-source ingestion with small, idempotent connectors on PyIceberg

- **Status:** accepted
- **Date:** 2026-11-02

## Context and problem statement

Pecten ingests a handful of small public sources in different shapes: a Frictionless data package
(Camtrap DP), JSON APIs (Open-Meteo, GBIF), spreadsheets (AviList, AVONET) and OGC API – Features
(Natura 2000). Each needs minimisation of personal fields **before** the first write.

## Considered options

1. dlt: a capable ingestion library, but its Iceberg REST-catalog destination is documented under
   the commercially licensed dltHub toolkit.
2. Airbyte or Meltano: heavy for five small sources.
3. **A small in-house framework (`pecten-ingest`) on httpx, Polars, Pandera and PyIceberg**
   (chosen).

## Decision outcome

Every connector follows the same steps:

1. **Fetch** with conditional requests (ETag, Last-Modified), retries with jittered backoff, and a
   per-source rate governor.
2. **Minimise** in memory: drop person-identifying fields and rows (ADR-0004).
3. **Land** the minimised payload in the raw zone, content-addressed by SHA-256, with a manifest
   (source URL, retrieval time, licence, original checksum).
4. **Parse and validate** into typed Polars frames checked by Pandera schemas generated from the
   table's contract.
5. **Commit** to Iceberg with PyIceberg; the snapshot summary records the manifest checksum so a
   re-run with unchanged input is a no-op.

## Consequences

- Positive: full control of minimisation, idempotency and licensing; very little code per source.
- Negative: the framework must be built and maintained (about 8 hours, M11.1).

## Confirmation

- Recorded HTTP fixtures (synthetic or trimmed public samples without personal fields) drive
  connector tests offline.
- Re-running a connector twice yields one Iceberg snapshot.
