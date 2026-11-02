"""Schemas and data contracts shared by every Pecten package."""

from importlib.metadata import version as _version

__all__ = ["__version__"]

__version__: str = _version("pecten-contracts")
