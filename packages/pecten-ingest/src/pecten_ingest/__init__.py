"""Small, idempotent connectors for public, non-personal data sources."""

from importlib.metadata import version as _version

__all__ = ["__version__"]

__version__: str = _version("pecten-ingest")
