# ADR-0009: Orchestration with Apache Airflow 3

- **Status:** accepted
- **Date:** 2026-11-02

## Context and problem statement

Batch work includes public-source ingestion on schedules, SQLMesh runs per partition,
event-driven drone-survey processing, Iceberg maintenance, data-quality runs, exports and
backfills. It needs scheduling, retries, partitions, lineage and a UI.

## Considered options

1. Dagster: an excellent asset model.
2. Prefect 3 or Kestra.
3. **Apache Airflow 3** (chosen).

## Decision outcome

Airflow 3.3 is used with its modern features rather than classic task-centric DAGs:

- **Assets** for every lakehouse table, with **asset partitions** (site × day) so only the
  affected slices run.
- **Event-driven scheduling** with asset watchers on Kafka topics (`survey.uploaded`,
  `device.registered`).
- **Deadline alerts** for freshness promises made in data contracts.
- **DAG bundles** from Git; KubernetesExecutor in the cluster, LocalExecutor in Compose.
- The **OpenLineage provider** emits lineage for every run.
- A small bridge generates Airflow assets from SQLMesh's model graph so transformations appear in
  the asset graph without duplicating definitions (M12.5).

## Consequences

- Positive: the orchestrator most teams run, used in its current asset-centric form.
- Negative: heavier than Dagster locally; DAG code must stay thin, with logic in tested packages.

## Confirmation

- DAG parse and import tests, `dag.test()` runs against fixtures, and Ruff's Airflow rules in CI.
