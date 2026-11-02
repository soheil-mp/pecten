# Domain research: monitoring birds with cameras

> Researched on 2 November 2026. Numbers that drive design decisions are worked out in the text so
> they can be checked. Where a source could not be verified first-hand, the text says so.

This document explains what cameras can and cannot tell us about birds, the physics behind each
camera type, the quantities ecologists actually use, the classical (non-learned) image-processing
methods that turn pixels into those quantities, and the privacy, welfare and legal rules that
shape the design. The last sections list the design implications and the open questions.

## Contents

1. [Why cameras](#1-why-cameras)
2. [Camera modalities](#2-camera-modalities)
3. [Physics of thermal detection](#3-physics-of-thermal-detection)
4. [Bird flight and morphology](#4-bird-flight-and-morphology)
5. [Quantities and metrics](#5-quantities-and-metrics)
6. [Classical computer-vision toolkit](#6-classical-computer-vision-toolkit)
7. [Privacy, animal welfare and law](#7-privacy-animal-welfare-and-law)
8. [Prior art and the gap Pecten fills](#8-prior-art-and-the-gap-pecten-fills)
9. [Design implications](#9-design-implications)
10. [Open questions and known limitations](#10-open-questions-and-known-limitations)
11. [References](#11-references)

---

## 1. Why cameras

Birds are monitored with radar (weather and dedicated bird radars), acoustics, direct counts and
cameras. Each sees a different slice:

| Method | Strength | Weakness |
| :-- | :-- | :-- |
| Weather radar | Continental coverage, altitude profiles | Coarse (km), no individuals, insects mixed in |
| Bird radar | Individual tracks to several km | Expensive, no shape detail, ground clutter |
| Acoustics | Species-rich, cheap | Only vocalising birds; nocturnal calls are sparse |
| Human counts | Species, behaviour | Daylight, observer effects, does not scale |
| **Cameras** | Geometry: size, shape, wingbeat, exact position; cheap; day and night (thermal) | Short range; weather-sensitive; they can capture people |

Cameras are the only cheap sensor that resolves individual birds in space with enough detail to
measure wingbeat, flight mode and, with two cameras, altitude. That makes them the sensor of choice
for three concrete jobs:

1. **Near-field behaviour** at nest boxes, feeders and roosts (visible-light cameras, often with
   infrared illumination at night) and in camera-trap surveys.
2. **Flight-path and collision-risk monitoring** around structures such as wind turbines, where
   altitude and flux through the rotor-swept zone matter (thermal and stereo thermal cameras).
3. **Colony and flock counts** from above (drone surveys with visible-light or thermal cameras).

Pecten covers all three with one data model and one platform.

## 2. Camera modalities

### 2.1 Visible-light (RGB) fixed cameras

- **Nest-box and feeder cameras.** Close range (decimetres to a few metres), fixed background,
  motion-triggered recording. At night they need near-infrared illumination, which makes the image
  effectively monochrome. Useful quantities: visit counts, visit durations, diel activity.
- **Camera traps.** Passive-infrared (PIR) triggered still or burst cameras. They are a mature
  survey method with an open data standard, **Camtrap DP** (§5.4), and public datasets on GBIF
  ([data sources](02-data-sources.md#1-camera-trap-data-camtrap-dp)).
- **Sky-facing cameras** for diurnal migration ("visible migration") counts: birds appear as
  dark silhouettes against a bright, slowly varying sky. Clouds, sun glare and exposure changes are
  the main nuisances.

### 2.2 Thermal (long-wave infrared) cameras

Thermal cameras image emitted radiation in the 8–14 µm atmospheric window, so they work in
darkness and do not need illumination. Two classes matter here:

| Core class | Example | Resolution | NETD | Frame rate | Use in Pecten |
| :-- | :-- | :-- | :-- | :-- | :-- |
| Micro core | Teledyne FLIR Lepton 3.5 (radiometric) | 160 × 120 | < 50 mK | < 9 Hz (export-compliant) | Near field: nest boxes, feeders, close turbine view |
| Uncooled VGA core | Generic 640 × 512 microbolometer | 640 × 512 | 30–50 mK typical | 9 Hz export, 30–60 Hz otherwise | Migration and turbine monitoring |

Lepton figures are from the Teledyne FLIR datasheets ([Lepton 3/3.5 datasheet][lepton-ds]); the
TLinear radiometric output (per-pixel temperatures) is documented in the engineering datasheet,
whose TLinear section could not be read in full during this research, so the exact output
resolution (0.1 K or 0.01 K per count) is confirmed in M22 against real hardware. The 640 × 512
row is a generic class, not a specific product.

Things every thermal pipeline must handle:

- **Flat-field correction (FFC).** Microbolometers periodically close a shutter to recalibrate.
  The stream freezes for a fraction of a second and the background shifts slightly afterwards.
- **Non-uniformity and fixed-pattern noise**, dead pixels, vignetting and slow drift with the
  camera's own temperature.
- **Radiometric vs. non-radiometric output.** Radiometric cores report scene temperatures; others
  report relative intensity with automatic gain control (AGC), which destroys absolute contrast.
  Pecten always works on linear radiometric values, never on AGC-processed video.

Thermal cameras have a long record in bird-migration work: Gauthreaux and Livingston (2006)
combined a fixed-beam radar with a vertically pointing thermal camera; Weisshaupt, Maruri and
Arizaga (2016) estimated altitudes of nocturnal migrants from long-range thermal footage in
northern Spain, with most tracks clustered around 2 km; Pacific Northwest National Laboratory's
**ThermalTracker** extracted flight tracks from offshore thermal video (Matzner, Cullinan and
Duberstein 2015) and is open source ([pnnl/ThermalTracker][thermaltracker], BSD-style licence for
the library, C++ with OpenCV, offline processing).

### 2.3 Stereo thermal

A single camera measures angles, not distances. Range must then be guessed from an assumed body
size, which is wrong by the full size spread of the species mix. Two synchronised cameras with a
known baseline `B` measure range `Z` from the disparity `d` (in pixels) between the two images:

```text
Z = f·B / d        δZ ≈ Z² · δd / (f·B)
```

`f` is the focal length in pixels. Worked example, 640-pixel-wide camera with a 25° horizontal field
of view and a 2 m baseline:

- `f = 320 / tan(12.5°) ≈ 1443 px`, so `f·B ≈ 2886 px·m`.
- At 200 m: `d ≈ 14.4 px`. With a quarter-pixel centroid error, `δZ ≈ 3.5 m`.
- At 500 m: `d ≈ 5.8 px` and `δZ ≈ 22 m`.

Range error grows with the square of range, so stereo is accurate exactly where collision risk is
decided (tens to a few hundred metres) and degrades smoothly beyond. Synchronisation matters too: a
bird at 15 m/s moves 1.5 cm in 1 ms, so frame timestamps must be matched to the millisecond.
Huang et al. (2016) used upward-looking stereo cameras (near-infrared, lit by urban light
pollution) to detect night migrants and rejected implausible hypotheses by disparity, timing and
extreme speed or altitude, which is the same family of geometric checks Pecten uses.

### 2.4 Drone (UAS) surveys

Drones carry visible-light or thermal cameras looking straight down (nadir) over colonies, roosts
or wetlands. The ground sampling distance (GSD) follows from the camera and altitude `H`:

```text
GSD = (sensor width × H) / (focal length × image width in pixels)
```

Example: a 1-inch sensor (13.2 mm wide) with an 8.8 mm lens and 5472-pixel images gives
`GSD ≈ 1.4 cm/px` at 50 m and `≈ 3.3 cm/px` at 120 m. Studies on replica seabird colonies found no
loss of count accuracy at GSDs finer than about 3.3 cm/px when birds covered at least about 17
pixels (as reported in the review literature on drone counts; Hodgson et al. 2018 is the primary
study). Thermal nadir imagery finds occupied nests and burrows by their heat signature: a survey of
burrow-nesting shearwaters captured a thermal response from every occupied burrow in the colony
([Drones 2023, 7(11):674][shearwater-thermal]).

Drones disturb birds, so altitude and approach are constrained by welfare, not only by image
quality (§7.2). The design consequence is a trade-off the mission planner must make explicit:
lower altitude gives finer GSD but more disturbance.

## 3. Physics of thermal detection

### 3.1 What the camera measures

A pixel integrates radiance over the 8–14 µm band. For a target of emissivity `ε` at temperature
`T`, seen through an atmosphere of transmittance `τ` against a background, the in-band radiance is

```text
L_pixel = τ·[ε·L(T_target) + (1−ε)·L(T_reflected)] + (1−τ)·L(T_atm)
```

where `L(T)` is Planck's law integrated over the band. The detector converts radiance to counts;
radiometric cores invert this to a temperature assuming an emissivity. Pecten's simulator
implements this forward model, and the edge pipeline works on the resulting temperature-like
values (§9).

### 3.2 Emissivity and bird surface temperature

- Biological surfaces, including feathers, are commonly assigned an emissivity of about **0.95**
  in thermography; apparent emissivity falls at grazing angles, and distance and spot size
  strongly affect measured surface temperatures in field conditions
  ([Dryad dataset on emissivity and distance errors][emissivity-dryad]).
- Plumage insulates. The outer surface of a resting bird is only a few kelvin above ambient; eyes,
  bill, legs and the thinly feathered areas under the wings are warmer. In flight, heat is shed
  through the wings and legs (thermal imaging of starlings in a wind tunnel: Ward et al. 1999).
- Surface temperature is not core temperature; recent work warns against inferring one from the
  other ([dove thermoregulation study][dove-thermo]).

### 3.3 The sky is cold: where contrast comes from

The surprising part is that a flying bird is visible mostly because the **clear sky is much colder
than the air**. Swinbank's (1963) clear-sky formula gives the effective sky temperature

```text
T_sky ≈ 0.0552 · T_air^1.5      (kelvin)
```

At `T_air = 283 K` (10 °C) this is `≈ 263 K`, about 20 K colder than the air, while the bird's
outer surface is near or slightly above air temperature. Clouds radiate at roughly their base
temperature and shrink that contrast to a few kelvin; fog and rain also attenuate the signal.
Berdahl and Martin (1984) refine the clear-sky emissivity with dew point. Open-Meteo supplies air
temperature, dew point, cloud cover and visibility per hour
([data sources](02-data-sources.md#2-weather-open-meteo)), so the simulator can compute contrast
per scene, and the platform can flag nights when detection probability drops (§5.1).

### 3.4 Atmospheric transmission

Transmittance in the LWIR window falls with water vapour, fog and rain. Pecten uses a documented
first-order model (Beer–Lambert extinction parameterised by humidity and visibility) rather than a
full radiative-transfer code. This is accurate enough to make detection range vary realistically
with weather and is stated as a limitation (§10).

### 3.5 Pixels on target and detection range

A target of size `L` at range `R` subtends `L/R` radians. Dividing by the instantaneous field of
view (IFOV) gives its size in pixels:

| Camera | IFOV | Starling (wingspan ≈ 0.38 m) at 100 m | At 400 m |
| :-- | :-- | :-- | :-- |
| Lepton 3.5 (57° / 160 px) | ≈ 6.2 mrad | ≈ 0.6 px | ≈ 0.15 px |
| VGA core (25° / 640 px) | ≈ 0.68 mrad | ≈ 5.6 px | ≈ 1.4 px |

The Johnson criteria put *detection* at about one line pair (two pixels) across the critical
dimension. But a hot point source can be detected even when it covers less than a pixel: the pixel
sees the target's contrast diluted by its fill factor. With 20 K of contrast, 50 mK of NETD and a
5σ threshold, a target covering about 1.3 % of a pixel is still above threshold. Range is then
limited by optics blur, atmosphere and clutter rather than by resolution. Two consequences:

- A Lepton is a near-field sensor (metres to tens of metres for small birds).
- A VGA core detects small birds at hundreds of metres, but only as a few pixels, so shape-based
  rules are unusable at range and **motion and wingbeat** carry the information.

## 4. Bird flight and morphology

### 4.1 Speed

Across 138 species measured by tracking radar, airspeeds ranged from about 8 to 23 m/s and scaled
only weakly with body mass, much more weakly than the classical aerodynamic prediction of
`M^(1/6)` (Alerstam et al. 2007). Ground speed adds wind, which can double or halve it, so
wind-corrected airspeed is the meaningful feature (wind from Open-Meteo, §5).

### 4.2 Wingbeat frequency

Pennycuick (1990) derived, from 32 species of 20 g to 5 kg, the prediction

```text
f = 1.08 · m^(1/3) · g^(1/2) · b^(−1) · S^(−1/4) · ρ^(−1/3)
```

with body mass `m`, gravity `g`, wingspan `b`, wing area `S` and air density `ρ`; later work
revised the exponents and added wing moment of inertia (Pennycuick 1996). For a herring-gull-sized
bird (1 kg, 1.4 m span, 0.2 m² wing area) the 1990 formula gives about 3.4 Hz, consistent with
field values near 3 Hz. Small passerines flap at 10–20 Hz and often use bounding flight
(bursts of flapping between closed-wing phases).

**Design constraint: aliasing.** A camera at frame rate `F` can only measure wingbeats below
`F/2`. A Lepton at 8.7 Hz cannot resolve anything above about 4.3 Hz, so a passerine's 15 Hz
wingbeat aliases to a false low frequency. Pecten must record the Nyquist limit with every
wingbeat estimate and report "above Nyquist" instead of a wrong number. Wingbeat-based rules need
30–60 Hz cameras.

### 4.3 Flight modes

Flapping, flap-gliding, bounding, gliding, and soaring (circling in thermals, typical of raptors,
storks and gulls). Geese fly in V or line formations, starlings in dense flocks. In image
sequences these modes appear as periodic or aperiodic modulation of the silhouette's area and
brightness, and as straight or circling trajectories. Flocks create merged blobs that split and
rejoin, which the tracker must handle explicitly.

### 4.4 Morphology data

The simulator and the explainable rules need body mass, wing length and wing shape per species.
**AVONET** (Tobias et al. 2022) provides morphological measurements for 11,009 species,
including the hand-wing index, under CC BY 4.0; **AviList v2025** provides the unified global
taxonomy (11,131 species), also under CC BY 4.0
([data sources](02-data-sources.md#3-taxonomy-and-traits)). Wingspan and wing area are not AVONET
fields and are derived from wing length with documented allometries, recorded as approximations.

## 5. Quantities and metrics

### 5.1 Counts and passage rates

Radar ornithology reports the **migration traffic rate (MTR)**: birds crossing a 1 km line
perpendicular to the flight direction per hour. A vertically pointing camera observes a strip
whose width grows with altitude, `W(h) = 2·h·tan(FOV/2)`, so raw counts must be divided by the
observed width per altitude band and corrected for detection probability, which falls with range
and weather. Schmaljohann et al. (2008) treat this as a detection-probability problem for radar,
and the same reasoning applies to cameras. Pecten reports camera-based passage rates per altitude
band with the detection model's assumptions attached, never as a bare number.

### 5.2 Flight-height distributions and collision risk

Collision risk at wind farms is usually estimated with the **Band (2012)** model, developed for
the UK Strategic Ornithological Support Services programme. It offers four options: basic or
extended model, each with a site-specific or generic flight-height distribution. The basic model
assumes birds are spread uniformly through the rotor's height range; the extended model uses the
actual height distribution (generic distributions for seabirds come from Johnston et al. 2014).
Masden (2015) made the model stochastic so that input uncertainty produces a distribution of
predicted collisions; the stochLAB R package implements it and matches the original spreadsheet.
The model needs exactly what stereo thermal cameras measure: flux, flight height, speed and body
size. Pecten implements the deterministic Band options with parameter sweeps for uncertainty. It
is a research demonstration, not an assessment tool, and says so.

### 5.3 Behaviour at nest boxes and feeders

Visits per hour, visit duration, first and last activity relative to sunrise and sunset, and
diel activity curves, all joined to sun elevation (computed) and weather.

### 5.4 Camera-trap metrics and Camtrap DP

Camera-trap surveys report trap rates (detections per 100 camera-days) and activity patterns.
**Camtrap DP** (Bubnicki et al. 2024; current version 1.0.2, June 2025) is the TDWG standard for
exchanging such data, built on the Frictionless Data Package specification with three tables:
`deployments`, `media` and `observations`. GBIF ingests Camtrap DP directly. Pecten both
**ingests** public Camtrap DP packages and **exports** its own camera observations as Camtrap DP.

### 5.5 Colony counts

Drone counts produce individuals or nests per survey area. Converting counted individuals to
breeding pairs needs species- and date-specific factors (one Wadden Sea-related source reports a
factor of 0.7 for gulls counted from 25 m imagery; [Monitoring colonies of large gulls using
UAVs][gulls-uav]). Overlapping images must be de-duplicated geometrically before counting. Pecten
reports counts with their uncertainty sources (overlap de-duplication, occlusion, GSD).

## 6. Classical computer-vision toolkit

Everything below is deterministic signal processing or estimation with parameters written down in
configuration. Nothing is trained on data.

| Stage | Method | Reference |
| :-- | :-- | :-- |
| Noise estimate | Median absolute deviation of temporal differences | Standard robust statistics |
| Background | Frame differencing; exponential moving average with selective update; approximate running median | McFarlane & Schofield 1995 |
| Foreground | Hysteresis (dual) thresholding on contrast-to-noise | Canny 1986 |
| Clean-up | Binary morphology (opening, closing) | Serra 1982 |
| Grouping | Connected-component labelling with union–find | Rosenfeld & Pfaltz 1966 |
| Small blobs in stills | Difference of Gaussians / Laplacian of Gaussian at the GSD-derived scale; white top-hat | Lindeberg 1998 |
| Tracking | Kalman filter, Mahalanobis gating, global assignment (Kuhn–Munkres), M-of-N track confirmation | Kalman 1960; Kuhn 1955; Munkres 1957 |
| Smoothing | Rauch–Tung–Striebel smoother on closed tracks | Rauch, Tung & Striebel 1965 |
| Wingbeat | FFT of the detrended silhouette-area signal; Lomb–Scargle for uneven sampling | Lomb 1976; Scargle 1982 |
| Geometry | Pinhole model with Brown–Conrady distortion; calibration from planar targets; triangulation | Brown 1966; Zhang 2000; Hartley & Zisserman 2004 |

Deliberately **excluded**: Gaussian-mixture background models (fitted by expectation–maximisation,
a learning procedure), neural detectors and classifiers of any kind (for example YOLO-family
detectors, MegaDetector, SpeciesNet, BirdNET), clustering algorithms such as DBSCAN or k-means
(overlap de-duplication uses explicit geometric rules instead), and libraries that bundle model
inference (OpenCV's `dnn` module is one reason Pecten does not depend on OpenCV). See
[ADR-0002](../adr/0002-deterministic-explainable-perception.md).

## 7. Privacy, animal welfare and law

### 7.1 People in the frame

Any camera outdoors can capture people, and images of identifiable people are personal data
under the GDPR. The European Data Protection Board's Guidelines 3/2019 on processing personal data
through video devices stress purpose limitation, data minimisation, short retention and technical
measures such as masking. Pecten's response is structural:

- **Frames never leave the edge device.** Only derived events (detections, tracks, counts) are
  transmitted.
- **Static privacy masks** (paths, roads, windows) are applied to pixels before any processing.
- A **rule-based human-signature guard** (warm, large, slow, ground-level blob) suppresses events
  and records only a suppression count.
- **Synthetic data only** in the repository, fixtures, screenshots and demos. Synthetic people
  exist solely to test the guard.
- **Third-party data is minimised at the door**: contributor names and e-mail addresses, the
  `setupBy` and `classifiedBy` fields, observations of type `human`, bounding boxes and media
  links are dropped before anything is stored
  ([data sources](02-data-sources.md#1-camera-trap-data-camtrap-dp)).

### 7.2 Disturbance by drones

- Vas et al. (2015) ran controlled drone approaches towards mallards, flamingos and greenshanks:
  most approaches caused no visible reaction, but vertical (overhead) approaches did, and the
  authors proposed ethical guidelines (launch far from birds, approach obliquely, keep
  distances).
- Reported thresholds vary by species and site: a goose-monitoring study recommends about 100 m
  altitude with take-off about 500 m from flocks ([Cambridge Core][geese-uav]); a tern colony
  showed disturbance below about 60 m ([DBCA PDF][terns-uav]); one study found that no take-off
  closer than 100 m and no flight within 100 m prevented most escape responses
  ([BES resource][bes-uav]).
- Mulero-Pázmány et al. (2017) reviewed drone disturbance of wildlife systematically.

Pecten encodes these as a **cited rule table** in the mission planner (minimum altitude, minimum
take-off distance, approach rules per species group) and refuses to plan flights that violate it.
The table is a starting point, not authority, and must be checked against local rules and permits.

### 7.3 Drone regulation

Under Regulation (EU) 2019/947 the open category limits flights to 120 m above ground within
visual line of sight. Member states publish **UAS geographical zones** (Article 15) in a common
data model based on EUROCAE ED-269. In the Netherlands, flying over protected nature areas of the
Wadden Sea is prohibited ([government.nl][nl-drones]). The Dutch no-fly-zone API on PDOK returned
HTTP 404 on 2 November 2026, so the current Dutch publication is a research spike (M11.6).

## 8. Prior art and the gap Pecten fills

| Kind | Examples | What is missing for Pecten's goals |
| :-- | :-- | :-- |
| Research software | ThermalTracker (PNNL), stereo night-migration detection (Huang et al. 2016) | Single modality, offline, no data platform or operations |
| Camera-trap platforms | Agouti, Trapper, Wildlife Insights | Still images of terrestrial wildlife; increasingly built on learned classifiers |
| Commercial wind-farm systems | Camera-based detection and curtailment products | Closed, proprietary and often model-based |
| Collision-risk tooling | Band (2012) spreadsheet, stochLAB | Needs flight-height and flux inputs from somewhere |

No open project combines several camera modalities with deterministic, explainable perception,
privacy by design, standards-based outputs (Camtrap DP, OGC Moving Features, STAC) and a
production-grade data platform, and verifies all of it against a physics-based simulator with
known ground truth. That combination is Pecten's contribution.

## 9. Design implications

1. **Work on radiometric values**, never on AGC video; detect contrast-to-noise, not brightness.
2. **Make detection weather-aware.** Compute expected thermal contrast from sky-temperature
   models and Open-Meteo data, and attach a detection-probability context to every count.
3. **Carry the Nyquist limit** with every wingbeat estimate; demand 30–60 Hz for wingbeat rules.
4. **Use stereo for altitude** and report range-dependent uncertainty (`δZ ∝ Z²`).
5. **Size classes, not species,** for Pecten's own sensors, with every classification carrying
   its reasons. Species appear only where a third party annotated them (Camtrap DP).
6. **Verify against a twin.** A physics-based simulator with ground truth makes detection,
   tracking and counting testable to stated tolerances in CI.
7. **Privacy is an architecture property**, not a feature: frames stay on the device; masks
   before processing; suppression before transmission; minimisation at ingestion.
8. **Disturbance rules are first-class data** for drone planning.
9. **Standards out:** Camtrap DP for camera observations, MF-JSON and OGC API – Moving Features for
   tracks, STAC and GeoParquet for survey imagery and detections.

## 10. Open questions and known limitations

- The atmospheric model is first-order; long-range performance in fog or rain is approximate.
- Bird surface-temperature models are simplified; real birds vary with posture, wetness and sun.
- Wingspan and wing area are derived from AVONET wing length by allometry, which adds error.
- The detection-probability model for passage rates needs field validation that the project
  cannot do with synthetic data alone; M22 compares simulator statistics with a real recording
  (kept locally, never committed).
- Drone disturbance thresholds are species- and context-specific; the rule table will be
  incomplete.
- The Dutch UAS geozone source must be re-located (§7.3).

## 11. References

- Alerstam T., Rosén M., Bäckman J., Ericson P. G. P., Hellgren O. (2007). Flight speeds among
  bird species: allometric and phylogenetic effects. *PLoS Biology* 5(8): e197.
- AviList Core Team (2025). AviList: The Global Avian Checklist, v2025.
  <https://doi.org/10.2173/avilist.v2025>
- Band W. (2012). Using a collision risk model to assess bird collision risks for offshore
  windfarms. SOSS report. [PDF][band-2012]
- Berdahl P., Martin M. (1984). Emissivity of clear skies. *Solar Energy* 32(5): 663–664.
- Brown D. C. (1966). Decentering distortion of lenses. *Photogrammetric Engineering* 32(3).
- Bubnicki J. W. et al. (2024). Camtrap DP: an open standard for the FAIR exchange and archiving
  of camera trap data. *Remote Sensing in Ecology and Conservation* 10(3): 283–295.
  <https://doi.org/10.1002/rse2.374>
- Canny J. (1986). A computational approach to edge detection. *IEEE TPAMI* 8(6): 679–698.
- European Data Protection Board (2020). Guidelines 3/2019 on processing of personal data through
  video devices, version 2.0.
- Evans J. et al. (2024). Data paper for the Amsterdamse Waterleidingduinen camera-trap pilots.
  *Data in Brief*. <https://doi.org/10.1016/j.dib.2024.110544>
- Gauthreaux S. A., Livingston J. W. (2006). Monitoring bird migration with a fixed-beam radar and
  a thermal-imaging camera. *Journal of Field Ornithology* 77(3): 319–328.
- Hartley R., Zisserman A. (2004). *Multiple View Geometry in Computer Vision*, 2nd ed.
- Hodgson J. C. et al. (2018). Drones count wildlife more accurately and precisely than humans.
  *Methods in Ecology and Evolution* 9(5): 1160–1167.
- Huang J.-B., Caruana R., Farnsworth A., Kelling S., Ahuja N. (2016). Detecting migrating birds
  at night. *CVPR 2016*. [PDF][huang-2016]
- Johnston A. et al. (2014). Modelling flight heights of marine birds to more accurately assess
  collision risk with offshore wind turbines. *Journal of Applied Ecology* 51(1): 31–41.
- Kalman R. E. (1960). A new approach to linear filtering and prediction problems. *Journal of
  Basic Engineering* 82(1): 35–45.
- Kuhn H. W. (1955). The Hungarian method for the assignment problem. *Naval Research Logistics
  Quarterly* 2: 83–97.
- Lindeberg T. (1998). Feature detection with automatic scale selection. *IJCV* 30(2): 79–116.
- Lomb N. R. (1976). Least-squares frequency analysis of unequally spaced data. *Astrophysics and
  Space Science* 39: 447–462.
- Masden E. (2015). Developing an avian collision risk model to incorporate variability and
  uncertainty. *Scottish Marine and Freshwater Science* 6(14).
- Matzner S., Cullinan V. I., Duberstein C. A. (2015). Two-dimensional thermal video analysis of
  offshore bird and bat flight. *Ecological Informatics* 30: 20–28. [PDF][matzner-2015]
- McFarlane N. J. B., Schofield C. P. (1995). Segmentation and tracking of piglets in images.
  *Machine Vision and Applications* 8: 187–193.
- Mulero-Pázmány M. et al. (2017). Unmanned aircraft systems as a new source of disturbance for
  wildlife: a systematic review. *PLoS ONE* 12(6): e0178448.
- Munkres J. (1957). Algorithms for the assignment and transportation problems. *Journal of SIAM*
  5(1): 32–38.
- Pennycuick C. J. (1990). Predicting wingbeat frequency and wavelength of birds. *Journal of
  Experimental Biology* 150: 171–185.
- Pennycuick C. J. (1996). Wingbeat frequency of birds in steady cruising flight: new data and
  improved predictions. *Journal of Experimental Biology* 199: 1613–1618.
- Rauch H. E., Tung F., Striebel C. T. (1965). Maximum likelihood estimates of linear dynamic
  systems. *AIAA Journal* 3(8): 1445–1450.
- Regulation (EU) 2019/947 on the rules and procedures for the operation of unmanned aircraft.
- Rosenfeld A., Pfaltz J. L. (1966). Sequential operations in digital picture processing.
  *Journal of the ACM* 13(4): 471–494.
- Scargle J. D. (1982). Studies in astronomical time series analysis II. *Astrophysical Journal*
  263: 835–853.
- Schmaljohann H., Liechti F., Bächler E., Steuri T., Bruderer B. (2008). Quantification of bird
  migration by radar: a detection probability problem. *Ibis* 150: 342–355.
- Serra J. (1982). *Image Analysis and Mathematical Morphology*. Academic Press.
- Swinbank W. C. (1963). Long-wave radiation from clear skies. *Quarterly Journal of the Royal
  Meteorological Society* 89: 339–348.
- Tobias J. A. et al. (2022). AVONET: morphological, ecological and geographical data for all
  birds. *Ecology Letters* 25(3): 581–597. <https://doi.org/10.1111/ele.13898>
- Vas E., Lescroël A., Duriez O., Boguszewski G., Grémillet D. (2015). Approaching birds with
  drones: first experiments and ethical guidelines. *Biology Letters* 11: 20140754.
- Ward S., Rayner J. M. V., Möller U., Jackson D. M., Nachtigall W., Speakman J. R. (1999). Heat
  transfer from starlings *Sturnus vulgaris* during flight. *Journal of Experimental Biology*
  202: 1589–1602.
- Weisshaupt N., Maruri M., Arizaga J. (2016). Long-range thermal imaging of nocturnal migrants
  in northern Spain (article in *Bird Study*; title not verified here). [BOU summary][weisshaupt-2016]
- Zhang Z. (2000). A flexible new technique for camera calibration. *IEEE TPAMI* 22(11):
  1330–1334.

[lepton-ds]: https://www.mouser.com/datasheet/2/227/Lepton3_3_5_Data_Sheet-2580086.pdf
[thermaltracker]: https://github.com/pnnl/ThermalTracker
[shearwater-thermal]: https://www.mdpi.com/2504-446X/7/11/674
[emissivity-dryad]: https://datadryad.org/dataset/doi:10.5061/dryad.bk3j9kdb0
[dove-thermo]: https://umimpact.umt.edu/en/publications/the-role-of-plumage-and-heat-dissipation-areas-in-thermoregulatio/
[gulls-uav]: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9698304/
[geese-uav]: https://www.cambridge.org/core/product/4A17F4A9B1CAE94572B3BAD285D9DCC8/core-reader
[terns-uav]: https://library.dbca.wa.gov.au/static/Journals/080292/080292-13.002.pdf
[bes-uav]: https://www.britishecologicalsociety.org/applied-ecology-resources/document/20203534087/
[nl-drones]: https://www.government.nl/faq/aviation/where-can-i-fly-a-drone
[band-2012]: https://tethys.pnnl.gov/sites/default/files/publications/Band%202012.pdf
[huang-2016]: https://openaccess.thecvf.com/content_cvpr_2016/papers/Huang_Detecting_Migrating_Birds_CVPR_2016_paper.pdf
[matzner-2015]: https://mhk.pnl.gov/sites/default/files/publications/Matzner-et-al-2015.pdf
[weisshaupt-2016]: https://bou.org.uk/blog-weisshaupt-infrared-migration/
