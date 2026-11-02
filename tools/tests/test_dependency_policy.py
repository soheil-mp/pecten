from __future__ import annotations

from email.message import Message
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

import dependency_policy as dp

if TYPE_CHECKING:
    from importlib.metadata import PackageMetadata

ALLOWED = frozenset({"MIT", "Apache-2.0", "BSD-3-Clause"})
POLICY_FILE = Path(__file__).resolve().parents[1] / "dependency-policy.toml"


def make_metadata(
    *, expression: str | None = None, licence: str | None = None, classifiers: tuple[str, ...] = ()
) -> PackageMetadata:
    message = Message()
    message["Name"] = "example"
    if expression is not None:
        message["License-Expression"] = expression
    if licence is not None:
        message["License"] = licence
    for classifier in classifiers:
        message["Classifier"] = classifier
    return cast("PackageMetadata", message)


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("MIT", True),
        ("GPL-3.0-only", False),
        ("MIT OR GPL-3.0-only", True),
        ("MIT AND GPL-3.0-only", False),
        ("(MIT OR GPL-3.0-only) AND Apache-2.0", True),
        ("Apache-2.0 WITH LLVM-exception", True),
        ("apache-2.0", False),
        ("BSD-3-Clause+", True),
    ],
)
def test_spdx_expressions(expression: str, *, expected: bool) -> None:
    assert dp.spdx_allowed(expression, ALLOWED) is expected


@pytest.mark.parametrize("expression", ["", "MIT OR", "(MIT", "MIT)", "MIT Apache-2.0", "OR MIT"])
def test_malformed_spdx_expressions_raise(expression: str) -> None:
    with pytest.raises(ValueError, match=r"in licence expression"):
        dp.spdx_allowed(expression, ALLOWED)


@given(st.sampled_from(sorted(ALLOWED)), st.sampled_from(["GPL-3.0-only", "SSPL-1.0"]))
def test_or_is_permissive_and_and_is_strict(good: str, bad: str) -> None:
    assert dp.spdx_allowed(f"{bad} OR {good}", ALLOWED)
    assert not dp.spdx_allowed(f"{bad} AND {good}", ALLOWED)


def test_licence_prefers_the_pep_639_expression() -> None:
    meta = make_metadata(expression="MIT", licence="Proprietary")
    assert dp.licence_of(meta) == "MIT"


def test_licence_maps_free_text_aliases() -> None:
    assert dp.licence_of(make_metadata(licence="BSD 2-Clause License")) == "BSD-2-Clause"


def test_licence_falls_back_to_classifiers() -> None:
    meta = make_metadata(
        licence="See LICENSE file for details",
        classifiers=(
            "License :: OSI Approved :: MIT License",
            "License :: OSI Approved :: Apache Software License",
        ),
    )
    assert dp.licence_of(meta) == "Apache-2.0 OR MIT"


def test_licence_is_none_without_any_information() -> None:
    assert dp.licence_of(make_metadata()) is None


@pytest.mark.parametrize(
    ("name", "denied"),
    [
        ("torch", True),
        ("Torch_Vision", True),
        ("opencv-python-headless", True),
        ("scikit_learn", True),
        ("scikit-image", False),
        ("numpy", False),
        ("@tensorflow/tfjs", True),
    ],
)
def test_deny_list_matching(name: str, *, denied: bool) -> None:
    policy = dp.Policy.load(POLICY_FILE)
    patterns = policy.deny_javascript if name.startswith("@") else policy.deny_python
    assert dp.is_denied(name, patterns) is denied


def test_check_reports_denied_and_unlicensed_packages() -> None:
    policy = dp.Policy(
        allowed_licences=ALLOWED,
        deny_python=("torch*",),
        deny_javascript=("ml5",),
        overrides_python={"reviewed-pkg": "MIT"},
    )
    violations = dp.check(
        policy,
        python_installed=[
            ("good", "MIT"),
            ("copyleft", "GPL-3.0-only"),
            ("silent", None),
            ("reviewed_pkg", None),
            ("pecten-sim", None),
            ("broken", "MIT OR"),
        ],
        python_locked=["good", "torchvision"],
        javascript_installed=[("left-pad", "WTFPL")],
        javascript_locked=["ml5", "react"],
    )
    found = {(v.ecosystem, v.package) for v in violations}
    assert found == {
        ("python", "torchvision"),
        ("javascript", "ml5"),
        ("python", "copyleft"),
        ("python", "silent"),
        ("python", "broken"),
        ("javascript", "left-pad"),
    }


def test_locked_python_packages(tmp_path: Path) -> None:
    lock = tmp_path / "uv.lock"
    lock.write_text(
        'version = 1\n[[package]]\nname = "numpy"\n[[package]]\nname = "torch"\n', encoding="utf-8"
    )
    assert dp.locked_python_packages(lock) == ["numpy", "torch"]


def test_locked_javascript_packages() -> None:
    lock = (
        "lockfileVersion: '9.0'\n"
        "importers:\n  .:\n    dependencies: {}\n"
        "packages:\n"
        "  '@tensorflow/tfjs@4.22.0':\n    resolution: {integrity: x}\n"
        "  svelte@5.57.3:\n    resolution: {integrity: y}\n"
        "snapshots:\n  ml5@1.0.0: {}\n"
    )
    assert dp.locked_javascript_packages(lock) == ["@tensorflow/tfjs", "svelte"]


def test_installed_javascript_reads_manifests(tmp_path: Path) -> None:
    for relative, body in {
        "svelte/package.json": '{"name": "svelte", "version": "5.0.0", "license": "MIT"}',
        "@scope/pkg/package.json": '{"name": "@scope/pkg", "version": "1.0.0"}',
        ".pnpm/x@1/node_modules/svelte/package.json": (
            '{"name": "svelte", "version": "5.0.0", "license": "MIT"}'
        ),
    }.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True)
        path.write_text(body, encoding="utf-8")
    assert sorted(dp.installed_javascript(tmp_path)) == [("@scope/pkg", None), ("svelte", "MIT")]


def test_the_workspace_environment_passes(capsys: pytest.CaptureFixture[str]) -> None:
    assert dp.main([]) == 0
    assert "0 violation(s)" in capsys.readouterr().out


def test_main_reports_violations(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    policy = tmp_path / "policy.toml"
    policy.write_text(
        '[licences]\nallow = ["Apache-2.0"]\n[deny]\npython = ["pytest"]\njavascript = []\n',
        encoding="utf-8",
    )
    (tmp_path / "uv.lock").write_text('[[package]]\nname = "pytest"\n', encoding="utf-8")
    assert dp.main(["--policy", str(policy), "--root", str(tmp_path)]) == 1
    assert "pytest on the machine-learning deny list" in capsys.readouterr().out
