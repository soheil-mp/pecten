//! Protobuf types for Pecten's edge events.
//!
//! The schemas live in `proto/` and are the source of truth (ADR-0011). Code
//! generation with `prost` is added in roadmap item M1.2; until then this crate
//! only exposes the schema package name that every event uses.

/// Protobuf package that every Pecten edge event belongs to.
pub const SCHEMA_PACKAGE: &str = "pecten.edge.v1";

#[cfg(test)]
mod tests {
    use super::SCHEMA_PACKAGE;

    #[test]
    fn schema_package_is_versioned() {
        assert_eq!(SCHEMA_PACKAGE.rsplit('.').next(), Some("v1"));
    }
}
