"""Read API: REST, OGC API - Moving Features and STAC."""

from importlib.metadata import version as _version

__all__ = ["__version__"]

__version__: str = _version("pecten-api")
