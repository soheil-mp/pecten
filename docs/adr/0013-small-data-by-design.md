# ADR-0013: Small data by design

- **Status:** accepted
- **Date:** 2026-11-02

## Context and problem statement

Cameras produce enormous volumes: one 640 × 512 thermal stream at 30 Hz with 16-bit pixels is
about 19.7 MB per second, or 1.7 TB per day. Storage for the project is limited, and storing
frames would also create privacy obligations.

## Decision outcome

1. **Reduce at the edge.** Frames become detections, tracks and counts on the device; only those
   leave it. A night of tracks for one camera is a few megabytes.
2. **Regenerate, don't store.** Synthetic frames are reproduced from a scenario file and a seed;
   only scenario files are versioned.
3. **Budget every dataset.** Each contract declares a byte budget; ingestion fails closed when a
   table would exceed it, and a daily report shows usage
   ([data sources §10](../research/02-data-sources.md#10-data-budget)).
4. **Retain briefly.** Bronze keeps 14 days; evidence crops (synthetic only, off by default)
   expire after 7 days; aggregates are kept.
5. **Read windows, not archives.** Public sources are queried by bounding box and date range.

## Consequences

- Positive: the whole lakehouse fits in 2 GB; CI runs end to end in under 100 MB.
- Negative: raw frames cannot be re-analysed later; re-analysis means re-running a scenario.

## Confirmation

- Budget checks run in ingestion and in a daily Airflow job; CI asserts the end-to-end footprint.
