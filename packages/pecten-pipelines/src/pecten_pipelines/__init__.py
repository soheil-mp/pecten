"""Airflow 3 DAGs and the task code they run."""

from importlib.metadata import version as _version

__all__ = ["__version__"]

__version__: str = _version("pecten-pipelines")
