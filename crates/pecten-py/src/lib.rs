//! Python bindings for `pecten-vision`.
//!
//! The simulator's verification tests call the same Rust algorithms the edge
//! runs, so each algorithm has exactly one implementation (ADR-0005). Bindings
//! are added alongside each algorithm, starting with camera geometry in M2.2.

use pyo3::prelude::*;

/// Native extension module `pecten_native`.
#[pymodule]
mod pecten_native {
    use pyo3::prelude::*;

    /// Version of the bundled `pecten-vision` crate.
    #[pyfunction]
    fn vision_version() -> &'static str {
        pecten_vision::version()
    }
}
