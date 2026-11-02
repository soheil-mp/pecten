//! `pecten-gateway`: the bridge from MQTT to Kafka.
//!
//! It validates `CloudEvents` from edge devices, de-duplicates them and produces
//! them to Kafka (ADR-0006). It is built in roadmap items M1.5 and M9.3.

use std::process::ExitCode;

fn main() -> ExitCode {
    println!("{}", version_line());
    let asked_for_version = std::env::args()
        .skip(1)
        .any(|arg| arg == "--version" || arg == "-V");
    if asked_for_version {
        ExitCode::SUCCESS
    } else {
        println!("The gateway is not implemented yet (roadmap M1.5).");
        ExitCode::FAILURE
    }
}

fn version_line() -> String {
    format!(
        "pecten-gateway {} (vision {}, schemas {})",
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
        assert!(line.starts_with("pecten-gateway "));
        assert!(line.contains("pecten.edge.v1"));
    }
}
