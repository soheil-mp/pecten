"""Tests for the minimal thermal simulator."""

from __future__ import annotations

import io
import socket
import threading
from typing import TYPE_CHECKING

import numpy as np
import pyarrow as pa
import pytest

from pecten_sim.cli import main, parse_address, run_thermal
from pecten_sim.thermal import (
    ThermalCamera,
    ThermalScenario,
    WarmDisc,
    frame_schema,
    write_ipc_stream,
)
from pecten_sim.truth import read_truth, write_truth

if TYPE_CHECKING:
    from pathlib import Path


def test_camera_defaults_match_a_lepton_class_core() -> None:
    camera = ThermalCamera()
    assert (camera.width_px, camera.height_px, camera.frame_rate_hz) == (160, 120, 8.7)
    assert camera.frame_period_ns == round(1e9 / 8.7)


def test_same_seed_gives_identical_frames() -> None:
    a = [image for image, _ in ThermalScenario.from_seed(3).frames(1.0)]
    b = [image for image, _ in ThermalScenario.from_seed(3).frames(1.0)]
    assert len(a) == 8
    for x, y in zip(a, b, strict=True):
        np.testing.assert_array_equal(x, y)


def test_empty_sky_shows_only_netd_noise() -> None:
    far = WarmDisc(start_px=(-100.0, -100.0), velocity_px_s=(0.0, 0.0))
    scenario = ThermalScenario(disc=far, seed=1)
    images = np.stack([image for image, _ in scenario.frames(2.0)])
    assert float(images.mean()) == pytest.approx(scenario.camera.sky_temp_k, abs=1e-3)
    assert float(images.std()) == pytest.approx(scenario.camera.netd_k, rel=0.02)


def test_disc_is_warm_and_covers_its_area() -> None:
    disc = WarmDisc(start_px=(80.0, 60.0), velocity_px_s=(0.0, 0.0), radius_px=3.0)
    scenario = ThermalScenario(disc=disc, seed=2)
    image, truth = next(scenario.frames(1.0))
    assert image[60, 80] == pytest.approx(disc.temp_k, abs=0.3)
    assert truth.visible_px == pytest.approx(np.pi * 9, rel=0.03)
    excess = (image - scenario.camera.sky_temp_k) / (disc.temp_k - scenario.camera.sky_temp_k)
    assert float(excess.sum()) == pytest.approx(truth.visible_px, rel=0.03)


def test_seeded_disc_crosses_the_whole_view() -> None:
    scenario = ThermalScenario.from_seed(5, duration_s=10.0)
    truths = [t for _, t in scenario.frames(10.0)]
    assert truths[0].x_px < 0 < truths[-1].x_px < scenario.camera.width_px + 3
    assert all(20 <= t.y_px <= 100 for t in truths)
    assert truths[0].visible_px < truths[len(truths) // 2].visible_px
    assert np.diff([t.time_ns for t in truths]).tolist() == [ThermalCamera().frame_period_ns] * (
        len(truths) - 1
    )


def test_ipc_stream_round_trip() -> None:
    scenario = ThermalScenario.from_seed(7)
    sink = io.BytesIO()
    truths = write_ipc_stream(sink, scenario, 1.0)
    table = pa.ipc.open_stream(sink.getvalue()).read_all()
    assert table.schema.equals(frame_schema(scenario.camera), check_metadata=True)
    assert table.num_rows == len(truths) == 8
    assert table.schema.metadata[b"pecten.width_px"] == b"160"
    first = np.asarray(table.column("temp_k")[0].values, dtype=np.float32).reshape(120, 160)
    np.testing.assert_array_equal(first, next(scenario.frames(1.0))[0])
    assert table.column("frame_id").to_pylist() == list(range(8))


def test_truth_round_trip() -> None:
    truths = [t for _, t in ThermalScenario.from_seed(1).frames(0.5)]
    stream = io.StringIO()
    assert write_truth(truths, stream) == len(truths)
    stream.seek(0)
    assert read_truth(stream) == truths


class TestCli:
    def test_parse_address(self) -> None:
        assert parse_address("localhost:7600") == ("localhost", 7600)
        for bad in ("7600", "host:", "host:0", "host:x"):
            with pytest.raises(Exception, match="host:port"):
                parse_address(bad)

    def test_writes_a_stream_file_and_truth(self, tmp_path: Path) -> None:
        out, truth = tmp_path / "frames.arrows", tmp_path / "truth.jsonl"
        assert (
            main(
                [
                    "thermal",
                    "--duration-s",
                    "1",
                    "--speed",
                    "0",
                    "--out",
                    str(out),
                    "--truth",
                    str(truth),
                ]
            )
            == 0
        )
        with pa.ipc.open_stream(out.read_bytes()) as reader:
            assert reader.read_all().num_rows == 8
        assert len(truth.read_text(encoding="utf-8").splitlines()) == 8

    def test_streams_over_tcp(self, tmp_path: Path) -> None:
        received = bytearray()
        with socket.create_server(("127.0.0.1", 0)) as server:

            def accept() -> None:
                conn, _ = server.accept()
                with conn:
                    while chunk := conn.recv(1 << 16):
                        received.extend(chunk)

            thread = threading.Thread(target=accept)
            thread.start()
            records = run_thermal(
                seed=4,
                duration_s=1.0,
                truth=tmp_path / "truth.jsonl",
                target=server.getsockname(),
                speed=10.0,
            )
            thread.join(timeout=10)
        table = pa.ipc.open_stream(bytes(received)).read_all()
        assert table.num_rows == len(records) == 8

    def test_needs_a_destination(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="TCP target or an output file"):
            run_thermal(seed=0, duration_s=0.5, truth=tmp_path / "t.jsonl")
