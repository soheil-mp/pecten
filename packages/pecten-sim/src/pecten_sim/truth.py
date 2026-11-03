"""Ground truth: what the simulator knows and the edge must never see (ADR-0003).

Only tests, evaluation and the end-to-end check read this module; import-linter contracts in
``pyproject.toml`` keep every platform package from importing it. Ground truth travels on its own
channel, a JSON Lines file, never inside the frame stream.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import TextIO

__all__ = ["DiscTruth", "read_truth", "write_truth"]


@dataclass(frozen=True, slots=True)
class DiscTruth:
    """The true state of the warm disc in one frame.

    Attributes:
        frame_id: Frame the state belongs to.
        time_ns: UTC time of the frame, ns since the Unix epoch.
        x_px, y_px: Disc centre in pixels (x to the right, y down); may lie outside the image.
        vx_px_s, vy_px_s: Velocity in pixels per second.
        radius_px: Disc radius in pixels.
        visible_px: Pixel area of the disc inside the image (0 when it is outside).
    """

    frame_id: int
    time_ns: int
    x_px: float
    y_px: float
    vx_px_s: float
    vy_px_s: float
    radius_px: float
    visible_px: float


def write_truth(records: Iterable[DiscTruth], stream: TextIO) -> int:
    """Write records as JSON Lines; returns how many were written."""
    count = 0
    for record in records:
        stream.write(json.dumps(asdict(record), separators=(",", ":")) + "\n")
        count += 1
    return count


def read_truth(stream: TextIO) -> list[DiscTruth]:
    """Read JSON Lines written by :func:`write_truth`."""
    return [DiscTruth(**json.loads(line)) for line in stream if line.strip()]
