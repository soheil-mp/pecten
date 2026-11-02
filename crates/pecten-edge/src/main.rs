//! `pecten-edge`: one process per camera or camera pair.
//!
//! It turns frames into detections, tracks and counts and publishes only those
//! events (ADR-0004). The runtime is built in roadmap milestones M1 and M5.

use std::process::ExitCode;

fn main() -> ExitCode {
    println!("{}", version_line());
    let asked_for_version = std::env::args()
        .skip(1)
        .any(|arg| arg == "--version" || arg == "-V");
    if asked_for_version {
        ExitCode::SUCCESS
    } else {
        println!("The edge runtime is not implemented yet (roadmap M1.3).");
        ExitCode::FAILURE
    }
}

fn version_line() -> String {
    format!(
        "pecten-edge {} (vision {}, schemas {})",
        env!("CARGO_PKG_VERSION"),
        pecten_vision::version(),
        pecten_proto::SCHEMA_PACKAGE
    )
}

#[cfg(test)]
mod tests {
    use super::version_line;

    #[test]
    fn version_line_names_the_binary_and_schemas() {
        let line = version_line();
        assert!(line.starts_with("pecten-edge "));
        assert!(line.contains("pecten.edge.v1"));
    }
}
