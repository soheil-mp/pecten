"""Smoke tests for the pecten-pipelines package."""

from importlib.metadata import version

import pecten_pipelines


def test_version_matches_distribution_metadata() -> None:
    assert pecten_pipelines.__version__ == version("pecten-pipelines")
