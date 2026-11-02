# ADR-0002: Deterministic, explainable perception with no machine learning

- **Status:** accepted
- **Date:** 2026-11-02

## Context and problem statement

Most modern camera-based wildlife systems use learned detectors and classifiers. Pecten
deliberately does not: the product must contain no models, no inference, no training or
evaluation data and no calls to model APIs. The question is how to get useful, trustworthy
measurements from cameras under that constraint.

## Decision drivers

- Every output must be reproducible from configuration and input alone.
- Every classification must state its reasons in terms a field ecologist can check.
- The physics of each camera type (see [domain research](../research/01-domain.md)) is well
  understood, so classical signal processing goes a long way.

## Considered options

1. Learned detectors and classifiers (rejected: out of scope by design).
2. Classical image processing with learned components such as Gaussian-mixture background models
   or clustering (rejected: these are fitted to data).
3. **Deterministic signal processing and estimation with explicit, cited rules** (chosen).

## Decision outcome

- Perception uses only deterministic operators: robust noise estimation, background models with
  fixed update rules (exponential moving average, approximate running median), hysteresis
  thresholds, morphology, connected components, scale-space blob detection, Kalman filtering with
  Kuhn–Munkres assignment, RTS smoothing, spectral analysis and multi-view geometry.
- Pecten reports **size classes, flight modes and behaviours, not species**, for its own sensors.
  Each result carries **reason codes** (for example `wingbeat_2_4_hz`, `airspeed_15_20_mps`)
  that point to a versioned rule table with literature references.
- Species names appear only where a third party annotated them by hand (Camtrap DP
  observations with `classificationMethod = human`).
- Synthetic ground truth is used to **test** this code, never to fit it. Thresholds are set from
  physics and literature and reviewed in pull requests, not tuned automatically.
- No export in formats designed for training models (for example COCO or YOLO label files).

## Consequences

- Positive: transparent, auditable results; tiny compute footprint; no model supply chain.
- Negative: lower recall in clutter than a good learned detector; no species identification from
  Pecten's own cameras. Both limitations are stated in the documentation.

## Confirmation

- A dependency policy (`tools/dependency_policy.py`, `cargo deny`) fails CI on any package from
  the machine-learning deny list in
  [technology landscape §4](../research/03-technology-landscape.md#4-licence-policy-for-dependencies).
- Rule tables are data files with a schema; every rule needs a `reference` field.
- Code review checks that no parameter is fitted from data.
