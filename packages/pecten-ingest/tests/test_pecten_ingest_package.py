"""Smoke tests for the pecten-ingest package."""

from importlib.metadata import version

import pecten_ingest


def test_version_matches_distribution_metadata() -> None:
    assert pecten_ingest.__version__ == version("pecten-ingest")
