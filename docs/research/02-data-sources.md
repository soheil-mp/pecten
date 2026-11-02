# Data sources

> Verified against the live services on 2 November 2026 unless marked otherwise. Sizes and counts
> are what the services returned that day.

Pecten's main data source is its own **sensor twin**: a physics-based simulator that renders
visible-light, thermal, stereo-thermal and drone imagery with known ground truth (see
[ADR-0003](../adr/0003-physics-based-sensor-twin.md)). Real data plays a supporting role. Every
real source must be **public, about nature rather than people, clearly licensed, and small**.

## Rules every source must pass

1. **No personal data at rest.** Fields that identify people are dropped before anything is
   written, including to the raw landing zone (see §1.3).
2. **No media from third parties.** Pecten never downloads third-party images or video.
3. **No machine-learning datasets.** Benchmarks built for training or evaluating models are out
   of scope, as are labels such as bounding boxes in otherwise acceptable data.
4. **Small by design.** Every source has a byte budget (§10) enforced in code.
5. **Licence and attribution recorded** with every raw file and shown wherever data is displayed.

## Summary

| # | Source | What Pecten uses | Format and access | Licence | Size | Milestone |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| 1 | Camtrap DP package `awd_pilot1` (NLBIF IPT) | Bird observations from three dune camera traps | Zipped Frictionless data package (CSV + JSON) | CC BY 4.0 | 2.2 MB | M11.2 |
| 2 | Open-Meteo forecast and archive APIs | Hourly weather for sites and deployments | JSON over HTTPS, no key | CC BY 4.0 data; free API for non-commercial use | KB per site-day | M11.3 |
| 3a | AviList v2025 | Global bird taxonomy | XLSX | CC BY 4.0 | small (measured in M11.4) | M11.4 |
| 3b | AVONET | Species morphology for the simulator and rules | XLSX on Figshare | CC BY 4.0 | 20.5 MB raw; < 1 MB derived | M3.2, M11.4 |
| 4 | Natura 2000 via PDOK | Protected-area polygons for sites and surveys | OGC API – Features (GeoJSON) | Public Domain Mark 1.0 | < 1 MB per bounding box | M11.5 |
| 5 | Dutch UAS geozones (LVNL via PDOK) | Drone no-fly zones for mission planning | OGC API – Features (when found) | PDM 1.0 (listed) | small | M11.6 (spike) |
| 6 | GBIF API | Finding datasets; monthly aggregate counts as context | JSON over HTTPS | Per dataset (CC0 / CC BY) | KB | M11.7 |
| 7 | Computed | Sun and moon position, twilight, sky temperature | Code | n/a | none | M3, M4 |
| 8 | Sensor twin | Frames, events and ground truth | Generated from seeds | MIT (this repository) | regenerated, not stored | M3, M4 |

## 1. Camera-trap data (Camtrap DP)

### 1.1 Primary package: Amsterdamse Waterleidingduinen pilot 1

- **Where:** GBIF dataset `74196cd9-7ebc-4b20-bc27-3c2d22e31ed7`, endpoint type `CAMTRAP_DP`,
  archive `https://ipt.nlbif.nl/archive.do?r=awd_pilot1` (version 2, file
  `datapackage-awd_pilot1-v2.zip`).
- **What:** three cameras (Snyper Commander 4G) set 30 cm above ground inside exclosures in the
  Amsterdam Water Supply Dunes, August 2021 to December 2022, annotated by people (data paper:
  Evans et al. 2024, *Data in Brief*).
- **Profile:** `https://rs.gbif.org/data-packages/camtrap-dp/1.0/profile/camtrap-dp-profile.json`.
  The current TDWG release is Camtrap DP **1.0.2** (10 June 2025); the IPT export references the
  1.0 profile, so validation must accept both.
- **Contents measured on 2026-11-02:**

  | Table | Rows | Notes |
  | :-- | --: | :-- |
  | `deployments.csv` | 3 | coordinates, start and end, camera model and height, `setupBy` |
  | `media.csv` | 30,431 | one row per image, `filePath` links to images on `multimedia.agouti.eu` |
  | `observations.csv` | 6,741 | 4,454 blank, 2,148 animal, 118 unknown, 18 human, 3 unclassified |

- **Birds:** 48 of the animal observations are birds (GBIF agrees): carrion crow 13, magpie 9,
  woodlark 8, starling 7, wood pigeon 4, woodcock 3, buzzard 2, barn owl 1, stonechat 1. Small,
  but enough to build and test the whole Camtrap DP path, diel-activity analytics and the joins
  with weather, sun and protected areas.
- **Location:** a bounding box around the deployments intersects exactly one Natura 2000 site,
  *Kennemerland-Zuid* (`NL1000012`); the point-in-polygon check is part of M11.5.

### 1.2 Larger packages (not used by default)

The Research Institute for Nature and Forest (INBO, Belgium) publishes Camtrap DP packages under
CC0 that contain birds as by-catch. They exceed the default budget and would only be used through
aggregated GBIF counts or a single-deployment subset:

| Package | Archive size | Bird occurrences on GBIF |
| :-- | --: | --: |
| `gmu8_leuven` | 95 MB | 4,957 |
| `nphk1` (National Park Hoge Kempen) | 68 MB | 1,248 |
| `muntjac_antwerp` | not measured | 1,278 |
| `mica-agouti` (Belgium, Netherlands, Germany) | not measured | 78,178 |

### 1.3 Personal data in Camtrap DP and how Pecten handles it

| Where | Field | Contains | Handling |
| :-- | :-- | :-- | :-- |
| `datapackage.json` | `contributors` | names, e-mail addresses, organisations | dropped; only the dataset citation and licence are kept |
| `deployments.csv` | `setupBy` | a person's name | dropped |
| `observations.csv` | `classifiedBy` | a person's name | dropped; `classificationMethod` is kept |
| `observations.csv` | rows with `observationType = human` | people in the images | rows dropped, with their linked `media` rows |
| `media.csv` | `filePath`, `fileName`, `exifData` | links to images that may show people | dropped; images are never fetched |
| `observations.csv` | `bboxX`, `bboxY`, `bboxWidth`, `bboxHeight`, `classificationProbability` | annotation geometry and model scores | dropped (not needed, and they are labelling data) |

The drop happens in the connector **before** the raw landing write: the raw zone stores a
re-serialised, minimised package plus the SHA-256 of the original archive, never the original
archive itself. Tests assert that none of these columns or rows can reach storage (M14.7).

## 2. Weather (Open-Meteo)

- **Endpoints:** forecast `https://api.open-meteo.com/v1/forecast` and historical archive
  `https://archive-api.open-meteo.com/v1/archive`. Both answered without a key on 2026-11-02; a
  request for 52.32 N, 4.50 E snapped to the grid point 52.337 N, 4.5 E at 9 m elevation.
- **Variables Pecten needs:** `temperature_2m`, `dew_point_2m`, `relative_humidity_2m`,
  `cloud_cover` (and its low, mid and high layers), `visibility`, `precipitation`,
  `shortwave_radiation`, wind speed and direction at 10 m and 100 m, and pressure-level winds for
  drift at altitude. Availability of each variable in the archive is checked in M11.3.
- **Terms:** data under CC BY 4.0 with the credit "Weather data by Open-Meteo.com" linked wherever
  it is shown. The free API is for non-commercial use without guarantees. Third-party summaries
  quote fair-use limits of 10,000 calls a day, 5,000 an hour and 600 a minute; these were not
  confirmed on Open-Meteo's own terms page, so Pecten's rate governor stays far below them
  (default one request per second, cached by ETag and date range). Some summaries place the
  historical API in paid tiers; the terms are re-checked in M11.3 before the connector ships.
- **Use:** simulator scenes (contrast, visibility, wind drift), wind-corrected airspeed,
  weather context on every count, drone go/no-go checks.

## 3. Taxonomy and traits

### 3.1 AviList v2025

The unified global checklist that replaces the IOC and Clements lists, released on 12 June 2025:
11,131 species, 19,879 subspecies, 2,376 genera, 252 families and 46 orders, updated yearly.
Licence CC BY 4.0; cite as *AviList Core Team (2025), doi:10.2173/avilist.v2025*. The official
download is XLSX (a CSV version is reported by press coverage but was not confirmed). Pecten uses
it as the reference taxonomy for every species name, including those in Camtrap DP observations.

### 3.2 AVONET

Morphological, ecological and geographical data for all birds (Tobias et al. 2022): measurements
of 90,020 individuals of 11,009 species, with species averages under three taxonomies. The main
file is *AVONET Supplementary dataset 1.xlsx* (20.53 MB on Figshare), CC BY 4.0. Pecten reads
body mass, wing length, Kipp's distance and the hand-wing index (`100 × Kipp's distance / wing
length`) for the simulator's species list and the size-class rules, keeps a derived table of
under 1 MB, and records the derivation of span and wing area as approximations.

**Reconciliation:** AVONET's taxonomies differ from AviList. Names are matched with documented
rules (exact, then accepted synonym, then manual mapping file reviewed in a pull request); the
unmatched list is a data-quality output, not silently dropped.

## 4. Protected areas (Natura 2000 via PDOK)

- **Endpoint:** `https://api.pdok.nl/rvo/natura2000/ogc/v1`, collection `natura2000`
  (OGC API – Features, GeoJSON). Licence: Public Domain Mark 1.0.
- **Fields seen:** `naam_n2k` (name), `sitecode_h`, `beschermin` (directive: habitats or birds),
  `status`, `staatscour`, area and perimeter. The Netherlands has 162 Natura 2000 sites.
- **Use:** survey areas for the drone planner, context joins for sites and deployments. Requests
  are always bounding-box limited. The pan-European EEA release is distributed as large yearly
  GeoPackage files and is not used.

## 5. Drone geozones

EU member states publish UAS geographical zones in the common ED-269-based model (Regulation (EU)
2019/947, Article 15). Search indexes list a PDOK OGC API for LVNL's drone no-fly zones
(`api.pdok.nl/lvnl/drone-no-flyzones/ogc/v1`, collections `luchtvaartgebieden` and `landingsite`,
PDM 1.0), but the endpoint returned **HTTP 404 on 2 November 2026**. M11.6 is a research spike to
find the current publication. Until then, the planner uses a synthetic geozone fixture and marks
every plan "geozones not checked against an official source".

## 6. GBIF API

- Used to discover datasets (for example, endpoint type `CAMTRAP_DP` and bird class key `212`) and
  for monthly aggregate counts around a site as context.
- Pecten requests facets and counts only. Fields that name people, such as `recordedBy` and
  `identifiedBy`, are never requested or stored.

## 7. Computed rather than downloaded

- **Sun position and twilight** with the NOAA solar-position algorithm; moon phase and
  illumination for night-time visible-light scenes.
- **Sky brightness temperature** from Swinbank (1963) and Berdahl and Martin (1984) with
  Open-Meteo inputs ([domain research §3.3](01-domain.md#33-the-sky-is-cold-where-contrast-comes-from)).
- **Wind turbine geometry** (hub height, rotor diameter, rotation speed) from a synthetic
  specification, so no turbine database is needed.
- **Terrain:** flat ground in v1; an optional small digital elevation tile for georeferencing
  drone detections later (M15.5).

## 8. Synthetic data: the sensor twin

All frames, events and ground truth come from seeded scenarios. They are regenerated rather than
stored: a scenario file plus a seed reproduces the same frames bit for bit. Only derived events
reach the lakehouse. Synthetic data is never published as a dataset and is never exported in
formats designed for training models.

## 9. Sources considered and rejected

| Source | Why not |
| :-- | :-- |
| Citizen-science observation platforms (for example eBird, observation.org) | Observer identities and restrictive terms |
| Public live bird webcams | Terms usually forbid recording; footage can show people |
| Thermal, drone or camera-trap benchmark datasets built for model training | Excluded by design (machine-learning data) |
| Outputs of automated species classifiers | Model outputs; Pecten keeps human-classified observations only |
| The full EEA Natura 2000 release | Size; PDOK bounding-box queries are enough |
| Large Camtrap DP packages (§1.2) | Size; aggregated GBIF counts instead |
| OpenStreetMap wind turbines | Not needed with a synthetic turbine; ODbL share-alike on derived databases |

## 10. Data budget

Budgets are enforced by the platform (M10.7): ingestion fails closed when a table would exceed
its budget, and a daily report lists usage.

| Zone | Content | Budget |
| :-- | :-- | --: |
| Raw landing | Minimised third-party files, content-addressed | 50 MB |
| Bronze | Edge events (estimated at about 10 MB a day for three simulated devices) | 14 days, 500 MB |
| Silver and gold | Tracks, counts, marts, reference tables | 500 MB |
| Ops | Data-quality results, lineage events, budget reports | 100 MB |
| Evidence crops | Synthetic only, off by default | 100 MB, 7-day expiry |
| Whole local lakehouse | | **2 GB** |
| CI end-to-end run | | **100 MB** |

## 11. Attribution

| Source | Credit line |
| :-- | :-- |
| Camtrap DP `awd_pilot1` | Evans J., Zilber R., Kissling W. D. et al., University of Amsterdam, CC BY 4.0, via NLBIF/GBIF |
| Open-Meteo | "Weather data by Open-Meteo.com" (linked) |
| AviList | AviList Core Team (2025), AviList v2025, CC BY 4.0 |
| AVONET | Tobias J. A. et al. (2022), *Ecology Letters* 25: 581–597, CC BY 4.0 |
| Natura 2000 | Rijksdienst voor Ondernemend Nederland via PDOK, Public Domain Mark 1.0 |

Citations name dataset authors because the licences require attribution. Author names appear in
citations and the generated `ATTRIBUTION.md` only; they are never stored in data tables.
