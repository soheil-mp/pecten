"""Smoke tests for the pecten-api package."""

from importlib.metadata import version

import pecten_api


def test_version_matches_distribution_metadata() -> None:
    assert pecten_api.__version__ == version("pecten-api")
