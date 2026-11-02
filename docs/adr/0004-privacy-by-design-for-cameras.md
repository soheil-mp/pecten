# ADR-0004: Privacy by design for cameras

- **Status:** accepted
- **Date:** 2026-11-02

## Context and problem statement

Outdoor cameras capture people. Images of identifiable people are personal data, and the European
Data Protection Board's Guidelines 3/2019 on video devices call for minimisation, short retention
and masking. Third-party camera-trap metadata also names the people who set up cameras and
classified images. Pecten must be safe to run and to publish.

## Decision

Privacy is enforced by the architecture, in this order:

1. **Frames stay on the edge device.** Only derived events are transmitted. Optional evidence
   crops are off by default, allowed only for synthetic sources, and expire after seven days.
2. **Static privacy masks** (per camera, versioned in the device registry) zero pixels before any
   processing.
3. **Human-signature guard:** a rule-based check (ground-level, warm, large for its range, slow)
   suppresses events in that region and emits only a `PrivacySuppression` count.
4. **Minimisation at ingestion:** person-identifying fields of third-party data are dropped before
   the first write; observations of people and all media links are discarded
   ([data sources §1.3](../research/02-data-sources.md#13-personal-data-in-camtrap-dp-and-how-pecten-handles-it)).
5. **Synthetic data only** in the repository, fixtures, screenshots and demos.
6. **No user accounts.** The API is read-only for anonymous clients; operators authenticate with
   infrastructure credentials, not application accounts.

## Consequences

- Positive: personal data never reaches storage, so there is nothing to protect, retain or
  delete downstream.
- Negative: no image-based review of detections in the platform. The web app shows tracks, plots
  and synthetic replays instead.

## Confirmation

- Privacy scenarios in the simulator (synthetic walkers on paths) must produce zero person-like
  events beyond suppression counts (M14.7).
- Column-name and pattern checks reject person-identifying columns in every contract.
- Contracts carry a `privacy` classification per field; anything other than `none` fails CI.
