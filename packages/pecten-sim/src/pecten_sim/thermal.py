"""Minimal thermal simulator for the thin end-to-end slice (ROADMAP M1.1).

A Lepton-class radiometric core (160 x 120 pixels at 8.7 Hz) looks at a uniform sky. One warm
disc, the stand-in for a bird, crosses the view on a straight line at constant speed. Each pixel
holds the scene temperature it sees, mixed by the fraction of the pixel the disc covers, plus
Gaussian noise whose standard deviation is the camera's NETD. Later milestones (M3) replace the
sky, the disc and the noise model with physics-based ones.

Frames are float32 temperatures in kelvin. The Lepton's integer output resolution is confirmed
against real hardware in M22, so the simulator does not commit to one yet.

Two channels never mix (ADR-0003):

* **frames** go to the edge as an Arrow IPC stream (:func:`write_ipc_stream`);
* **ground truth** goes to a separate JSON Lines file (:mod:`pecten_sim.truth`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final

import numpy as np
import pyarrow as pa

from pecten_sim.truth import DiscTruth

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from typing import BinaryIO

    import numpy.typing as npt

__all__ = [
    "FRAME_SCHEMA_VERSION",
    "ThermalCamera",
    "ThermalScenario",
    "WarmDisc",
    "frame_schema",
    "write_ipc_stream",
]

FRAME_SCHEMA_VERSION: Final = "1"
"""Version of the Arrow frame schema, stored in its metadata."""

_SUPERSAMPLING: Final = 4
"""Sub-pixel samples per axis used to compute how much of a pixel the disc covers."""

_NS_PER_S: Final = 1_000_000_000


@dataclass(frozen=True, slots=True)
class ThermalCamera:
    """A radiometric thermal core.

    Attributes:
        camera_id: Identifier carried by every frame.
        width_px: Columns.
        height_px: Rows.
        frame_rate_hz: Frames per second.
        netd_k: Noise-equivalent temperature difference, the per-pixel noise in kelvin.
        sky_temp_k: Apparent temperature of the uniform sky.
    """

    camera_id: str = "thermal-1"
    width_px: int = 160
    height_px: int = 120
    frame_rate_hz: float = 8.7
    netd_k: float = 0.05
    sky_temp_k: float = 253.15

    @property
    def frame_period_ns(self) -> int:
        """Time between frames in nanoseconds."""
        return round(_NS_PER_S / self.frame_rate_hz)


@dataclass(frozen=True, slots=True)
class WarmDisc:
    """A disc of uniform temperature moving at constant velocity across the image.

    Attributes:
        start_px: Centre ``(x, y)`` at the start, in pixels (x to the right, y down).
        velocity_px_s: Velocity ``(vx, vy)`` in pixels per second.
        radius_px: Disc radius in pixels.
        temp_k: Apparent temperature of the disc.
    """

    start_px: tuple[float, float]
    velocity_px_s: tuple[float, float]
    radius_px: float = 2.0
    temp_k: float = 303.15

    def centre_at(self, t_s: float) -> tuple[float, float]:
        """Centre at ``t_s`` seconds after the start."""
        return (
            self.start_px[0] + self.velocity_px_s[0] * t_s,
            self.start_px[1] + self.velocity_px_s[1] * t_s,
        )


def frame_schema(camera: ThermalCamera) -> pa.Schema:
    """Arrow schema of the frame stream: one row per frame, the image in row-major order."""
    pixels = camera.width_px * camera.height_px
    return pa.schema(
        [
            pa.field("frame_id", pa.uint64(), nullable=False),
            pa.field("timestamp", pa.timestamp("ns", tz="UTC"), nullable=False),
            pa.field("temp_k", pa.list_(pa.float32(), pixels), nullable=False),
        ],
        metadata={
            "pecten.schema_version": FRAME_SCHEMA_VERSION,
            "pecten.camera_id": camera.camera_id,
            "pecten.width_px": str(camera.width_px),
            "pecten.height_px": str(camera.height_px),
            "pecten.frame_rate_hz": str(camera.frame_rate_hz),
            "pecten.netd_k": str(camera.netd_k),
        },
    )


@dataclass(frozen=True, slots=True)
class ThermalScenario:
    """A seeded scenario: one camera, one warm disc, a start time.

    Attributes:
        disc: The disc and its flight line.
        seed: Seed of the noise generator.
        camera: The camera.
        start_time_ns: UTC time of the first frame, ns since the Unix epoch.
    """

    disc: WarmDisc
    seed: int = 0
    camera: ThermalCamera = field(default_factory=ThermalCamera)
    start_time_ns: int = 1_777_593_600 * _NS_PER_S  # 2026-05-01T00:00:00Z

    @classmethod
    def from_seed(cls, seed: int, *, duration_s: float = 60.0) -> ThermalScenario:
        """A disc that enters at the left edge and leaves at the right edge in ``duration_s``.

        The seed picks the height at which the disc enters and leaves (rows 20 to 100), so the
        line may slope, and the noise.
        """
        camera = ThermalCamera()
        rng = np.random.default_rng(seed)
        y_in, y_out = rng.uniform(20.0, 100.0, size=2)
        radius = 2.0
        x_in, x_out = -radius, camera.width_px + radius
        velocity = ((x_out - x_in) / duration_s, (y_out - y_in) / duration_s)
        disc = WarmDisc((x_in, float(y_in)), (velocity[0], float(velocity[1])), radius)
        return cls(disc=disc, seed=seed, camera=camera)

    def frame_count(self, duration_s: float) -> int:
        """Number of whole frames in ``duration_s``."""
        return math.floor(duration_s * self.camera.frame_rate_hz + 1e-9)

    def frames(self, duration_s: float) -> Iterator[tuple[npt.NDArray[np.float32], DiscTruth]]:
        """Yield every frame, shape ``(height, width)``, with its ground truth."""
        cam = self.camera
        noise = np.random.default_rng(self.seed)
        for frame_id in range(self.frame_count(duration_s)):
            t_ns = frame_id * cam.frame_period_ns
            cx, cy = self.disc.centre_at(t_ns / _NS_PER_S)
            coverage = _disc_coverage(cam.width_px, cam.height_px, cx, cy, self.disc.radius_px)
            scene = cam.sky_temp_k + coverage * (self.disc.temp_k - cam.sky_temp_k)
            image = scene + noise.normal(0.0, cam.netd_k, scene.shape)
            truth = DiscTruth(
                frame_id=frame_id,
                time_ns=self.start_time_ns + t_ns,
                x_px=cx,
                y_px=cy,
                vx_px_s=self.disc.velocity_px_s[0],
                vy_px_s=self.disc.velocity_px_s[1],
                radius_px=self.disc.radius_px,
                visible_px=float(coverage.sum()),
            )
            yield image.astype(np.float32), truth


def _disc_coverage(
    width: int, height: int, cx: float, cy: float, radius: float
) -> npt.NDArray[np.float64]:
    """Fraction of each pixel covered by the disc, from 4 x 4 sub-pixel samples.

    Pixel ``(row, col)`` spans ``[col, col + 1) x [row, row + 1)``. Only the disc's bounding
    box is sampled.
    """
    out = np.zeros((height, width))
    x0, x1 = max(0, math.floor(cx - radius)), min(width, math.ceil(cx + radius) + 1)
    y0, y1 = max(0, math.floor(cy - radius)), min(height, math.ceil(cy + radius) + 1)
    if x0 >= x1 or y0 >= y1:
        return out
    offsets = (np.arange(_SUPERSAMPLING) + 0.5) / _SUPERSAMPLING
    xs = (np.arange(x0, x1)[:, np.newaxis] + offsets).ravel()
    ys = (np.arange(y0, y1)[:, np.newaxis] + offsets).ravel()
    inside = ((xs[np.newaxis, :] - cx) ** 2 + (ys[:, np.newaxis] - cy) ** 2) <= radius**2
    blocks = inside.reshape(y1 - y0, _SUPERSAMPLING, x1 - x0, _SUPERSAMPLING)
    out[y0:y1, x0:x1] = blocks.mean(axis=(1, 3))
    return out


def write_ipc_stream(
    sink: pa.NativeFile | BinaryIO,
    scenario: ThermalScenario,
    duration_s: float,
    *,
    on_frame: Callable[[DiscTruth], None] | None = None,
) -> list[DiscTruth]:
    """Write the scenario's frames to ``sink`` as an Arrow IPC stream, one batch per frame.

    Args:
        sink: A pyarrow output stream or a writable binary file-like object.
        scenario: What to simulate.
        duration_s: How long to simulate.
        on_frame: Optional callable invoked with each frame's ground truth before the frame is
            written (used for real-time pacing).

    Returns:
        The ground truth of every frame, in order.
    """
    schema = frame_schema(scenario.camera)
    truths: list[DiscTruth] = []
    with pa.ipc.new_stream(sink, schema) as writer:
        for image, truth in scenario.frames(duration_s):
            if on_frame is not None:
                on_frame(truth)
            batch = pa.record_batch(
                [
                    pa.array([truth.frame_id], pa.uint64()),
                    pa.array([truth.time_ns], pa.timestamp("ns", tz="UTC")),
                    pa.FixedSizeListArray.from_arrays(pa.array(image.ravel()), image.size),
                ],
                schema=schema,
            )
            writer.write_batch(batch)
            truths.append(truth)
    return truths
