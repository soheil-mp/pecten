# ADR-0016: Standards-based outputs

- **Status:** accepted
- **Date:** 2026-11-02

## Context and problem statement

Pecten's results are only useful if other tools can read them without custom glue. Ecology,
geospatial and data communities each have established standards.

## Decision outcome

| Output | Standard |
| :-- | :-- |
| Camera observations (Pecten's own and ingested) | Camtrap DP 1.0.x, validated with frictionless-py |
| Trajectories | OGC Moving Features JSON (MF-JSON 1.0) and an OGC API – Moving Features Part 1 subset |
| Drone survey imagery | STAC 1.1 Items and Collections (`eo`, `view`, `proj` extensions) |
| Spatial detections and counts | GeoParquet and Iceberg geometry columns |
| Drone missions | QGroundControl `.plan` (MAVLink mission items) and GeoJSON |
| Device and sensor metadata | JSON-LD using the W3C SOSA/SSN vocabulary |
| REST API | OpenAPI 3.1, errors as RFC 9457 problem details |
| Event API | AsyncAPI 3 |
| Events | CloudEvents 1.0 |
| Lineage | OpenLineage |
| Data contracts | Open Data Contract Standard v3.2 |

Every export pins an Iceberg snapshot ID so it can be reproduced later.

## Consequences

- Positive: results drop into GBIF-style tooling, GIS, STAC browsers and lineage viewers.
- Negative: each standard brings validation work; validators run in CI for each format.

## Confirmation

- Export tests validate against the official schemas or validators for each standard.
