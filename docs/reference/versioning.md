# Versioning policy

Pecten has several things that other code depends on: the repository as a whole, event schemas,
Kafka topics, data contracts, tables and the REST API. Each is versioned on its own terms, and
this page states the rules.

## Releases

- One version for the whole repository, following [Semantic Versioning](https://semver.org/):
  every Rust crate, Python package and (later) the web app carry the same number. Tags are
  `vX.Y.Z`.
- release-please opens a release pull request from Conventional Commit messages; merging it
  updates `CHANGELOG.md`, the version in every `Cargo.toml` and `pyproject.toml`, both lock files
  and `CITATION.cff`, then tags the release.
- `feat:` bumps the minor version, `fix:` and `perf:` the patch version, and `!` or a
  `BREAKING CHANGE:` footer the major version. Other types (`docs:`, `build:`, `ci:`, `test:`,
  `refactor:`, `chore:`) do not trigger a release on their own. Before 1.0, breaking changes
  bump the minor version and are called out in the changelog.
- Releases follow milestones: v0.1.0 after M1, and so on up to v1.0.0 after M23 (see the
  [release plan](https://github.com/soheil-mp/pecten/blob/main/ROADMAP.md#release-plan)).

## Event schemas (Protobuf)

- Packages are versioned in their name: `pecten.edge.v1`. Within a major version, only
  backward-compatible changes are allowed: new optional fields, new enum values, new messages.
- `buf breaking` runs on every pull request against `main`, and the schema registry enforces
  backward-transitive compatibility.
- A breaking change creates `pecten.edge.v2` alongside `v1`; both are produced until every
  consumer has moved, and the overlap is announced in the changelog.

## CloudEvents types and Kafka topics

- Event types end in the schema's major version (`org.pecten.track.closed.v1`), and topics carry
  it too (`pecten.tracks.v1`). A new major version means a new type and a new topic, never a
  reinterpretation of an old one.

## Data contracts (ODCS)

- Every contract has its own SemVer `version`.
- **Patch:** documentation, descriptions, tightened quality thresholds that existing data
  already meets.
- **Minor:** new optional columns, new quality rules, relaxed service levels.
- **Major:** removed or renamed columns, type changes, changed meaning or units, stricter
  service levels. A major change needs a migration note and, for tables, a new table version or
  a dual-write period.
- CI compares each changed contract with the version on `main` and fails if the version bump is
  smaller than the change requires.

## Iceberg tables

- Additive schema evolution (new nullable columns) happens in place.
- Anything else creates a new table (`silver.tracks_v2`) that is backfilled before consumers
  switch; the old table is kept read-only for one release.
- Every release tags the Iceberg snapshots it was verified against, so results can be
  reproduced.

## REST API

- The URL carries the major version (`/v1/...`). Within `v1`, changes are additive: new
  endpoints, new optional parameters and new response fields.
- Removals and behaviour changes go into `/v2/`; `/v1/` stays available for at least one minor
  release afterwards and returns `Deprecation` and `Sunset` headers.
- The OpenAPI document is versioned with the release, and Schemathesis tests run against it.

## Deprecation

Anything deprecated is listed in the changelog with the release that deprecated it, the
replacement, and the release in which it will be removed (at least one minor release later).
