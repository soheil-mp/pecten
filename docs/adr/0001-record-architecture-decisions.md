# ADR-0001: Record architecture decisions

- **Status:** accepted
- **Date:** 2026-11-02

## Context and problem statement

Pecten spans edge software, a simulator, a streaming and batch data platform and its operations.
Decisions in one part constrain the others, and the reasons behind them are easy to lose.

## Decision

Record every significant decision as an Architecture Decision Record in `docs/adr/`, using the
[MADR 4](https://adr.github.io/madr/) structure: context, drivers, options, outcome, consequences
and how compliance is confirmed.

- Files are numbered `NNNN-title.md` and never renumbered.
- An ADR is changed only to fix typos or to mark it **superseded by** a newer ADR.
- A pull request that changes a recorded decision must add or supersede an ADR; the pull-request
  template asks this question.

## Consequences

- Reviewers can see why the system looks the way it does.
- Writing an ADR costs about an hour; small, reversible choices do not need one.
