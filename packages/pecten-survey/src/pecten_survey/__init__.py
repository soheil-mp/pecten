"""Drone survey planning, georeferencing and colony counting."""

from importlib.metadata import version as _version

__all__ = ["__version__"]

__version__: str = _version("pecten-survey")
