"""Check the dependency boundaries between Pecten's Rust crates (ADR-0003, ROADMAP M1.11).

cargo-deny keeps Python (PyO3) out of every crate except the bindings, but it cannot say that no
workspace crate may depend on the bindings themselves. This script reads the workspace manifests
and enforces the rules below, so the edge and gateway binaries can never pull in the simulator
side of the project:

* No crate depends on ``pecten-py`` (the Python bindings are a leaf).
* ``pecten-vision`` and ``pecten-proto`` depend on no other workspace crate.
* ``pecten-edge`` and ``pecten-gateway`` depend only on ``pecten-vision`` and ``pecten-proto``.

Run it with ``uv run python tools/crate_boundaries.py``; it exits with status 1 on a violation.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECTIONS = ("dependencies", "dev-dependencies", "build-dependencies")
LEAVES = frozenset({"pecten-vision", "pecten-proto"})
BINARIES = frozenset({"pecten-edge", "pecten-gateway"})
BINDINGS = "pecten-py"


def workspace_dependencies(root: Path = ROOT) -> dict[str, set[str]]:
    """Map every workspace crate to the workspace crates it depends on (any section)."""
    manifests = sorted((root / "crates").glob("*/Cargo.toml"))
    crates = {tomllib.loads(m.read_text(encoding="utf-8"))["package"]["name"]: m for m in manifests}
    graph: dict[str, set[str]] = {}
    for name, manifest in crates.items():
        data = tomllib.loads(manifest.read_text(encoding="utf-8"))
        deps: set[str] = set()
        for section in SECTIONS:
            deps |= {d for d in data.get(section, {}) if d in crates}
        for target in data.get("target", {}).values():
            for section in SECTIONS:
                deps |= {d for d in target.get(section, {}) if d in crates}
        graph[name] = deps
    return graph


def violations(graph: dict[str, set[str]]) -> list[str]:
    """Human-readable rule violations in a workspace dependency graph."""
    found = [f"{name} depends on {BINDINGS}" for name, deps in graph.items() if BINDINGS in deps]
    found += [
        f"{name} must not depend on {sorted(deps)}"
        for name, deps in graph.items()
        if name in LEAVES and deps
    ]
    found += [
        f"{name} may depend only on {sorted(LEAVES)}, not {sorted(deps - LEAVES)}"
        for name, deps in graph.items()
        if name in BINARIES and deps - LEAVES
    ]
    return sorted(found)


def main() -> int:
    """Print violations and return the exit status."""
    problems = violations(workspace_dependencies())
    for problem in problems:
        print(f"crate boundary violated: {problem}")  # noqa: T201
    print(f"crate boundaries: {len(problems)} violation(s)")  # noqa: T201
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
