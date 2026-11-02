"""Smoke tests for the pecten-contracts package."""

from importlib.metadata import version

import pecten_contracts


def test_version_matches_distribution_metadata() -> None:
    assert pecten_contracts.__version__ == version("pecten-contracts")
