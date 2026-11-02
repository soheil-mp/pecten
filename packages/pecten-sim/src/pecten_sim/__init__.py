"""Physics-based sensor twin.

Renders thermal, visible-light, stereo and drone imagery with ground truth on a
separate channel (ADR-0003).
"""

from importlib.metadata import version as _version

__all__ = ["__version__"]

__version__: str = _version("pecten-sim")
