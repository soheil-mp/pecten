# Pecten

Pecten is an open platform for monitoring birds with cameras: fixed visible-light cameras at
nest boxes and feeders, thermal and stereo-thermal cameras for night migration and wind turbines,
and drone surveys of colonies. Edge software turns frames into tracks, counts and flight
measurements with deterministic, explainable image processing, and a data platform turns those
events into analysis-ready, standards-based datasets.

!!! note "Project status"
    Planning is complete and the engineering foundations are being built. The product is not
    runnable yet; the [roadmap](https://github.com/soheil-mp/pecten/blob/main/ROADMAP.md) shows
    what comes next.

## Where to start

| You want to… | Read |
| :-- | :-- |
| Understand what cameras can measure about birds | [Domain research](research/01-domain.md) |
| See how the system fits together | [Architecture](architecture.md) |
| Know which real data is used and how personal fields are removed | [Data sources](research/02-data-sources.md) |
| Know why each tool was chosen | [Technology landscape](research/03-technology-landscape.md) and the [ADRs](adr/README.md) |
| Set up a development environment | [Development setup](how-to/development-setup.md) |
| Check what is stable and how versions change | [Versioning policy](reference/versioning.md) |

## How these docs are organised

The site follows the [Diátaxis](https://diataxis.fr/) framework:

- **Tutorials** teach by walking through a complete task, starting with the first run of the
  walking skeleton.
- **How-to guides** solve one specific problem, such as setting up the workspace.
- **Reference** describes interfaces, schemas, contracts and policies precisely.
- **Explanation** covers the background: research, architecture and decisions.

## Principles

Pecten uses no machine learning, keeps camera frames on the device, works with synthetic or
public non-personal data only, and verifies everything against a physics-based sensor twin. The
reasons are recorded in [ADR-0002](adr/0002-deterministic-explainable-perception.md),
[ADR-0003](adr/0003-physics-based-sensor-twin.md) and
[ADR-0004](adr/0004-privacy-by-design-for-cameras.md).
