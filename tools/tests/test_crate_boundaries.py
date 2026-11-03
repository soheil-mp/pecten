from __future__ import annotations

from typing import TYPE_CHECKING

import crate_boundaries as cb

if TYPE_CHECKING:
    from pathlib import Path


def write_crate(root: Path, name: str, deps: dict[str, list[str]]) -> None:
    directory = root / "crates" / name
    directory.mkdir(parents=True)
    lines = [f'[package]\nname = "{name}"\n']
    for section, names in deps.items():
        lines.append(f"[{section}]")
        lines += [f'{d} = {{ path = "../{d}" }}' for d in names]
    (directory / "Cargo.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_the_real_workspace_keeps_its_boundaries() -> None:
    graph = cb.workspace_dependencies()
    assert {"pecten-edge", "pecten-py", "pecten-vision"} <= set(graph)
    assert cb.violations(graph) == []
    assert cb.main() == 0


def test_reads_every_dependency_section(tmp_path: Path) -> None:
    write_crate(tmp_path, "pecten-vision", {})
    write_crate(tmp_path, "pecten-proto", {})
    write_crate(tmp_path, "pecten-py", {"dependencies": ["pecten-vision"]})
    write_crate(
        tmp_path, "pecten-edge", {"dev-dependencies": ["pecten-py"], "dependencies": ["serde"]}
    )
    graph = cb.workspace_dependencies(tmp_path)
    assert graph["pecten-edge"] == {"pecten-py"}  # serde is not a workspace crate
    assert cb.violations(graph) == [
        "pecten-edge depends on pecten-py",
        "pecten-edge may depend only on ['pecten-proto', 'pecten-vision'], not ['pecten-py']",
    ]


def test_flags_leaves_with_workspace_dependencies() -> None:
    graph = {
        "pecten-vision": {"pecten-proto"},
        "pecten-proto": set(),
        "pecten-gateway": {"pecten-proto"},
    }
    assert cb.violations(graph) == ["pecten-vision must not depend on ['pecten-proto']"]


def test_target_specific_dependencies_count(tmp_path: Path) -> None:
    write_crate(tmp_path, "pecten-py", {})
    directory = tmp_path / "crates" / "pecten-gateway"
    directory.mkdir(parents=True)
    (directory / "Cargo.toml").write_text(
        '[package]\nname = "pecten-gateway"\n\n'
        "[target.'cfg(unix)'.dependencies]\n"
        'pecten-py = { path = "../pecten-py" }\n',
        encoding="utf-8",
    )
    assert "pecten-gateway depends on pecten-py" in cb.violations(
        cb.workspace_dependencies(tmp_path)
    )
