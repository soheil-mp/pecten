"""Smoke tests for the pecten-survey package."""

from importlib.metadata import version

import pecten_survey


def test_version_matches_distribution_metadata() -> None:
    assert pecten_survey.__version__ == version("pecten-survey")
