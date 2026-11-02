# ADR-0010: Transformations with SQLMesh on Trino, unit-tested on DuckDB

- **Status:** accepted
- **Date:** 2026-11-02

## Context and problem statement

Silver and gold models (tracks, passage rates, rotor-zone flux, collision-risk estimates, diel
activity, colony counts) must be incremental by time, testable without a cluster, reviewable per
pull request, and documented down to column-level lineage.

## Considered options

1. dbt-core with dbt-trino: the most common choice; still Apache-2.0, but the dbt Labs and
   Fivetran merger (closed June 2026) put new engine work into the proprietary Fusion engine.
2. **SQLMesh**: virtual data environments, plan and apply, native incremental-by-time models,
   unit tests, audits and column-level lineage; contributed to the Linux Foundation in March 2026
   (chosen).

## Decision outcome

- Gateway `lake`: Trino with the Iceberg connector on Lakekeeper (an Iceberg REST catalog, which
  SQLMesh requires because it uses views).
- Gateway `test`: DuckDB for SQLMesh unit tests; SQLGlot transpiles the models.
- Each pull request gets a virtual environment (`sqlmesh plan pr_<n>`) on the CI stack; `main`
  promotes to `prod` without recomputing unchanged models.
- Physical formulas that need Python (Band collision-risk options, sun position) are SQLMesh
  Python models or macros with their own unit tests.

## Consequences

- Positive: safe per-PR changes, cheap promotion, lineage for the docs site.
- Negative: smaller ecosystem than dbt; fewer people know it. The project documents its
  conventions in `transform/README.md`.

## Confirmation

- `sqlmesh test` and `sqlmesh plan` run in CI; audits block promotion.
