//! Deterministic image-processing and estimation algorithms for Pecten.
//!
//! This crate holds the pure algorithms shared by the edge runtime and, through
//! `pecten-py`, by the simulator's verification tests: background models,
//! thresholds, connected components, tracking filters and camera geometry. It
//! performs no I/O and contains no learned models (see ADR-0002).

pub mod components;
pub mod tracking;

/// The crate version, as recorded in `Cargo.toml`.
#[must_use]
pub const fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

#[cfg(test)]
mod tests {
    use super::version;

    #[test]
    fn version_matches_the_manifest() {
        assert_eq!(version(), env!("CARGO_PKG_VERSION"));
    }
}
