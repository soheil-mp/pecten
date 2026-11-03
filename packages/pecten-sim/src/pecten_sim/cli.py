"""Command-line interface: ``pecten-sim``.

Examples::

    pecten-sim thermal --seed 7 --duration-s 60 --target 127.0.0.1:7600 --truth truth.jsonl
    pecten-sim thermal --seed 7 --duration-s 5 --out frames.arrows --truth truth.jsonl
"""

from __future__ import annotations

import argparse
import socket
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

from pecten_sim.thermal import ThermalScenario, write_ipc_stream
from pecten_sim.truth import write_truth

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pecten_sim.truth import DiscTruth

__all__ = ["main", "parse_address", "run_thermal"]

_PORTS = range(1, 65_536)


def parse_address(value: str) -> tuple[str, int]:
    """Parse ``host:port``."""
    host, sep, port = value.rpartition(":")
    if not sep or not host or not port.isdigit() or int(port) not in _PORTS:
        msg = f"expected host:port, got {value!r}"
        raise argparse.ArgumentTypeError(msg)
    return host, int(port)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pecten-sim", description="Pecten sensor twin.")
    commands = parser.add_subparsers(dest="command", required=True)
    thermal = commands.add_parser("thermal", help="one warm disc crossing a thermal camera")
    thermal.add_argument("--seed", type=int, default=0)
    thermal.add_argument("--duration-s", type=float, default=60.0)
    where = thermal.add_mutually_exclusive_group(required=True)
    where.add_argument("--target", type=parse_address, help="stream frames over TCP to host:port")
    where.add_argument("--out", type=Path, help="write frames to an Arrow IPC stream file")
    thermal.add_argument("--truth", type=Path, required=True, help="ground-truth JSON Lines file")
    thermal.add_argument(
        "--speed", type=float, default=1.0, help="1 is real time, 0 as fast as possible"
    )
    return parser


def run_thermal(  # noqa: PLR0913 - one argument per CLI option
    *,
    seed: int,
    duration_s: float,
    truth: Path,
    target: tuple[str, int] | None = None,
    out: Path | None = None,
    speed: float = 1.0,
) -> list[DiscTruth]:
    """Run the thermal scenario into a TCP connection or a file; returns the ground truth."""
    scenario = ThermalScenario.from_seed(seed, duration_s=duration_s)
    period_s = scenario.camera.frame_period_ns / 1e9
    started = time.monotonic()

    def pace(record: DiscTruth) -> None:
        if speed > 0:
            delay = started + record.frame_id * period_s / speed - time.monotonic()
            if delay > 0:
                time.sleep(delay)

    if target is not None:
        with (
            socket.create_connection(target, timeout=10.0) as conn,
            conn.makefile("wb") as sink,
        ):
            records = write_ipc_stream(sink, scenario, duration_s, on_frame=pace)
    elif out is not None:
        with out.open("wb") as sink:
            records = write_ipc_stream(sink, scenario, duration_s, on_frame=pace)
    else:
        msg = "give a TCP target or an output file"
        raise ValueError(msg)
    with truth.open("w", encoding="utf-8") as truth_file:
        write_truth(records, truth_file)
    return records


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point of ``pecten-sim``."""
    args = _parser().parse_args(argv)
    records = run_thermal(
        seed=args.seed,
        duration_s=args.duration_s,
        truth=args.truth,
        target=args.target,
        out=args.out,
        speed=args.speed,
    )
    where = f"{args.target[0]}:{args.target[1]}" if args.target else str(args.out)
    sys.stdout.write(f"wrote {len(records)} frames to {where}\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
