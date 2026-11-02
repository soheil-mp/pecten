# ADR-0003: A physics-based sensor twin as the primary data source

- **Status:** accepted
- **Date:** 2026-11-02

## Context and problem statement

Real camera footage of birds is large, often licensed restrictively, can contain people, and
public labelled collections are mostly machine-learning datasets. Pecten still needs frames with
known ground truth to build and verify detection, tracking, counting and the data platform.

## Decision drivers

- Ground truth must be exact so tests can assert tolerances.
- Storage is scarce: data should be regenerated, not stored.
- Realism must come from physics and literature, not from copying real footage.

## Considered options

1. Record real footage (rejected: privacy, storage, licensing).
2. Use public benchmark datasets (rejected: machine-learning datasets, see ADR-0002).
3. **Render synthetic frames from a physics-based simulator** (chosen).

## Decision outcome

`pecten-sim` renders visible-light, thermal, stereo-thermal and drone imagery from declarative
scenario files:

- **Radiometry:** Planck band radiance, emissivity, bird surface-temperature model, sky brightness
  temperature from Swinbank and Berdahl–Martin with Open-Meteo weather, first-order atmospheric
  transmittance.
- **Sensors:** pinhole optics with Brown–Conrady distortion, point-spread blur, noise equivalent
  temperature difference, fixed-pattern noise, flat-field-correction events, dead pixels; shot
  and read noise and exposure control for visible-light cameras.
- **Birds:** AVONET morphology, airspeed and wingbeat allometries, flight modes, flocks, wind
  drift; plus distractors (insects, rain, clouds, turbine blades) and synthetic people for
  privacy tests.
- **Ground truth** is written to a separate channel that the edge cannot read.

Frames travel to the edge as Apache Arrow IPC streams, the same interface a real camera adapter
implements (M5, M22).

## Consequences

- Positive: exact, reproducible tests; zero storage for frames; any weather or failure on demand.
- Negative: a sim-to-real gap. It is measured in M22 against a real recording that is kept local
  and never committed, and the gap is documented.

## Confirmation

- Determinism tests: the same scenario and seed give identical frame hashes.
- Import and dependency boundaries (import-linter, `cargo deny` bans) stop edge code from reading
  ground-truth modules.
