//! `pecten-edge` command line.
//!
//! ```text
//! pecten-edge run --input frames.arrows
//! pecten-edge run --listen 127.0.0.1:7600
//! ```
//!
//! Track updates go to standard output as JSON Lines; a summary goes to standard error.

use std::fs::File;
use std::io::{BufReader, BufWriter, Read, Write};
use std::net::TcpListener;
use std::process::ExitCode;

use pecten_edge::frames::FrameReader;
use pecten_edge::pipeline::{DetectorConfig, EdgePipeline, to_json_line};
use pecten_vision::tracking::TrackerConfig;

fn version_line() -> String {
    format!(
        "pecten-edge {} (vision {}, schemas {})",
        env!("CARGO_PKG_VERSION"),
        pecten_vision::version(),
        pecten_proto::SCHEMA_PACKAGE
    )
}

const USAGE: &str = "usage: pecten-edge run (--input FILE | --listen HOST:PORT)";

enum Source {
    File(String),
    Listen(String),
}

fn parse(args: &[String]) -> Result<Source, String> {
    match args {
        [cmd, flag, value] if cmd == "run" && flag == "--input" => Ok(Source::File(value.clone())),
        [cmd, flag, value] if cmd == "run" && flag == "--listen" => {
            Ok(Source::Listen(value.clone()))
        }
        _ => Err(USAGE.to_owned()),
    }
}

fn run(input: impl Read, out: &mut impl Write) -> Result<(u64, u64), Box<dyn std::error::Error>> {
    let frames = FrameReader::new(input)?;
    let mut pipeline = EdgePipeline::new(
        frames.camera(),
        DetectorConfig::default(),
        TrackerConfig::default(),
    );
    let (mut frame_count, mut messages) = (0_u64, 0_u64);
    for frame in frames {
        let result = pipeline.process(&frame?)?;
        frame_count += 1;
        for update in &result.updates {
            writeln!(
                out,
                "{}",
                to_json_line(update, pipeline.timestamp_ns(update.time_s))
            )?;
            messages += 1;
        }
    }
    for update in &pipeline.finish() {
        writeln!(
            out,
            "{}",
            to_json_line(update, pipeline.timestamp_ns(update.time_s))
        )?;
        messages += 1;
    }
    out.flush()?;
    Ok((frame_count, messages))
}

#[expect(
    clippy::print_stderr,
    reason = "the summary goes to stderr so stdout stays JSON Lines"
)]
fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.iter().any(|a| a == "--version" || a == "-V") {
        println!("{}", version_line());
        return ExitCode::SUCCESS;
    }
    let source = match parse(&args) {
        Ok(source) => source,
        Err(usage) => {
            eprintln!("{usage}");
            return ExitCode::from(2);
        }
    };
    let mut out = BufWriter::new(std::io::stdout().lock());
    let result = match source {
        Source::File(path) => File::open(&path)
            .map_err(Into::into)
            .and_then(|file| run(BufReader::new(file), &mut out)),
        Source::Listen(address) => TcpListener::bind(&address)
            .and_then(|listener| listener.accept())
            .map_err(Into::into)
            .and_then(|(stream, _)| run(BufReader::new(stream), &mut out)),
    };
    match result {
        Ok((frames, messages)) => {
            eprintln!("frames {frames}, track updates {messages}");
            ExitCode::SUCCESS
        }
        Err(e) => {
            eprintln!("pecten-edge: {e}");
            ExitCode::FAILURE
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{Source, parse, version_line};

    #[test]
    fn version_line_names_the_binary_and_schemas() {
        let line = version_line();
        assert!(line.starts_with("pecten-edge "));
        assert!(line.contains("pecten.edge.v1"));
    }

    #[test]
    fn parses_both_sources_and_rejects_the_rest() {
        let args = |s: &str| s.split(' ').map(str::to_owned).collect::<Vec<_>>();
        assert!(
            matches!(parse(&args("run --input a.arrows")), Ok(Source::File(p)) if p == "a.arrows")
        );
        assert!(matches!(
            parse(&args("run --listen 127.0.0.1:1")),
            Ok(Source::Listen(_))
        ));
        assert!(parse(&args("run")).is_err());
        assert!(parse(&args("serve --input x")).is_err());
    }
}
