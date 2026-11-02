"""Smoke tests for the pecten-sim package."""

from importlib.metadata import version

import pecten_sim


def test_version_matches_distribution_metadata() -> None:
    assert pecten_sim.__version__ == version("pecten-sim")
