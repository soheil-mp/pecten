"""Check Python and JavaScript dependencies against Pecten's dependency policy.

The policy (``tools/dependency-policy.toml``) has two parts:

* a licence allowlist of SPDX identifiers, checked against the metadata of every
  installed Python distribution (and every installed JavaScript package once the
  web app exists);
* a deny list of machine-learning, model-inference and model-API packages,
  checked against every package in ``uv.lock`` and ``pnpm-lock.yaml``, including
  packages not installed on this platform.

Rust crates are checked by ``cargo deny`` with ``deny.toml``. Run this script
inside the workspace environment::

    uv run python tools/dependency_policy.py
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
import tomllib
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping, Sequence

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_POLICY = ROOT / "tools" / "dependency-policy.toml"

# Trove classifiers and free-text licence fields mapped to SPDX identifiers.
LICENCE_ALIASES: dict[str, str] = {
    "apache 2.0": "Apache-2.0",
    "apache license 2.0": "Apache-2.0",
    "apache software license": "Apache-2.0",
    "apache-2.0": "Apache-2.0",
    "bsd": "BSD-3-Clause",
    "bsd license": "BSD-3-Clause",
    "bsd 2-clause license": "BSD-2-Clause",
    "bsd 3-clause license": "BSD-3-Clause",
    "bsd-2-clause": "BSD-2-Clause",
    "bsd-3-clause": "BSD-3-Clause",
    "the mit license": "MIT",
    "isc license (iscl)": "ISC",
    "isc": "ISC",
    "mit license": "MIT",
    "mit": "MIT",
    "mit no attribution license (mit-0)": "MIT-0",
    "mozilla public license 2.0 (mpl 2.0)": "MPL-2.0",
    "mpl-2.0": "MPL-2.0",
    "psf-2.0": "PSF-2.0",
    "python software foundation license": "PSF-2.0",
    "the unlicense (unlicense)": "Unlicense",
    "unlicense": "Unlicense",
    "zlib/libpng license": "Zlib",
    "cc0 1.0 universal (cc0 1.0) public domain dedication": "CC0-1.0",
}

_TOKEN = re.compile(r"\(|\)|[^\s()]+")
# Longer free-text "License" fields are usually the full licence text.
_MAX_FREE_TEXT = 80


@dataclass(frozen=True)
class Policy:
    """The allowlist, deny lists and reviewed overrides from the policy file."""

    allowed_licences: frozenset[str]
    deny_python: tuple[str, ...]
    deny_javascript: tuple[str, ...]
    overrides_python: Mapping[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> Policy:
        """Read the policy from a TOML file."""
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        overrides = data.get("overrides", {}).get("python", {})
        return cls(
            allowed_licences=frozenset(data["licences"]["allow"]),
            deny_python=tuple(data["deny"]["python"]),
            deny_javascript=tuple(data["deny"]["javascript"]),
            overrides_python={normalise(k): v["licence"] for k, v in overrides.items()},
        )


@dataclass(frozen=True)
class Violation:
    """One dependency that breaks the policy."""

    ecosystem: str
    package: str
    problem: str


def normalise(name: str) -> str:
    """Normalise a Python distribution name as PEP 503 describes."""
    return re.sub(r"[-_.]+", "-", name).lower()


def is_denied(name: str, patterns: Iterable[str]) -> bool:
    """Return whether a package name matches any deny-list pattern."""
    candidate = normalise(name) if not name.startswith("@") else name.lower()
    return any(fnmatch.fnmatchcase(candidate, pattern.lower()) for pattern in patterns)


class _SpdxParser:
    """Recursive-descent evaluator for SPDX licence expressions."""

    _OPERATORS = frozenset({"AND", "OR", "WITH", ")"})

    def __init__(self, expression: str, allowed: frozenset[str]) -> None:
        self.expression = expression
        self.allowed = allowed
        self.symbols: list[str] = _TOKEN.findall(expression)
        self.position = 0

    def evaluate(self) -> bool:
        result = self._or()
        if self.position != len(self.symbols):
            self._fail(f"unexpected token {self.symbols[self.position]!r}")
        return result

    def _peek(self) -> str:
        return self.symbols[self.position].upper() if self.position < len(self.symbols) else ""

    def _take(self) -> str:
        if self.position >= len(self.symbols):
            self._fail("unexpected end of licence expression")
        symbol = self.symbols[self.position]
        self.position += 1
        return symbol

    def _or(self) -> bool:
        result = self._and()
        while self._peek() == "OR":
            self._take()
            result = self._and() or result
        return result

    def _and(self) -> bool:
        result = self._atom()
        while self._peek() == "AND":
            self._take()
            result = self._atom() and result
        return result

    def _atom(self) -> bool:
        symbol = self._take()
        if symbol == "(":
            result = self._or()
            if self._take() != ")":
                self._fail("unbalanced parentheses")
            return result
        if symbol.upper() in self._OPERATORS:
            self._fail(f"unexpected operator {symbol!r}")
        if self._peek() == "WITH":
            self._take()
            self._take()  # the exception identifier
        return symbol.removesuffix("+") in self.allowed

    def _fail(self, problem: str) -> NoReturn:
        message = f"{problem} in licence expression {self.expression!r}"
        raise ValueError(message)


def spdx_allowed(expression: str, allowed: frozenset[str]) -> bool:
    """Evaluate an SPDX licence expression against the allowlist.

    ``OR`` needs one allowed side, ``AND`` needs both, and ``WITH`` exceptions are
    accepted when the licence they modify is allowed.

    Raises:
        ValueError: If the expression cannot be parsed.
    """
    return _SpdxParser(expression, allowed).evaluate()


def licence_of(dist_metadata: metadata.PackageMetadata) -> str | None:
    """Return the SPDX licence expression a distribution declares, if any."""
    expression = dist_metadata.get("License-Expression")
    if expression:
        return expression.strip()
    free_text = (dist_metadata.get("License") or "").strip()
    if free_text and "\n" not in free_text and len(free_text) < _MAX_FREE_TEXT:
        alias = LICENCE_ALIASES.get(free_text.lower(), free_text)
        if _looks_like_spdx(alias):
            return alias
    classifiers = [
        c.split("::")[-1].strip()
        for c in dist_metadata.get_all("Classifier") or []
        if c.startswith("License ::")
    ]
    spdx = [LICENCE_ALIASES[c.lower()] for c in classifiers if c.lower() in LICENCE_ALIASES]
    return " OR ".join(sorted(set(spdx))) or None


def _looks_like_spdx(text: str) -> bool:
    """Return whether free text parses as an SPDX expression."""
    try:
        spdx_allowed(text, frozenset())
    except ValueError:
        return False
    return True


def locked_python_packages(lock_path: Path) -> list[str]:
    """Return every package name recorded in a uv lock file."""
    data = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    return [package["name"] for package in data.get("package", [])]


def locked_javascript_packages(lock_text: str) -> list[str]:
    """Return package names from the ``packages:`` section of a pnpm lock file."""
    names: list[str] = []
    in_packages = False
    for line in lock_text.splitlines():
        if not line.startswith(" "):
            in_packages = line.rstrip() == "packages:"
            continue
        match = re.match(r"^  '?(@?[^@\s'/][^@\s']*(?:/[^@\s']+)?)@", line)
        if in_packages and match:
            names.append(match.group(1))
    return sorted(set(names))


def installed_python(
    distributions: Iterable[metadata.Distribution] | None = None,
) -> Iterator[tuple[str, str | None]]:
    """Yield ``(name, licence expression)`` for every installed distribution."""
    for dist in distributions if distributions is not None else metadata.distributions():
        name = dist.metadata["Name"]
        if name:
            yield name, licence_of(dist.metadata)


_NODE_MANIFESTS = (
    "*/package.json",
    "@*/*/package.json",
    ".pnpm/*/node_modules/*/package.json",
    ".pnpm/*/node_modules/@*/*/package.json",
)


def installed_javascript(node_modules: Path) -> Iterator[tuple[str, str | None]]:
    """Yield ``(name, licence)`` for packages installed under ``node_modules``."""
    seen: set[tuple[str, str]] = set()
    for pattern in _NODE_MANIFESTS:
        for manifest in sorted(node_modules.glob(pattern)):
            data = json.loads(manifest.read_text(encoding="utf-8"))
            key = (str(data.get("name", manifest.parent.name)), str(data.get("version", "")))
            if key in seen:
                continue
            seen.add(key)
            licence = data.get("license")
            yield key[0], licence if isinstance(licence, str) else None


def check(  # noqa: PLR0913 - each input is an explicit, testable source
    policy: Policy,
    *,
    python_installed: Iterable[tuple[str, str | None]],
    python_locked: Sequence[str],
    javascript_installed: Iterable[tuple[str, str | None]] = (),
    javascript_locked: Sequence[str] = (),
    workspace_prefix: str = "pecten-",
) -> list[Violation]:
    """Return every policy violation in the given dependency sets."""
    denied = "on the machine-learning deny list"
    violations = [
        Violation("python", name, denied)
        for name in python_locked
        if is_denied(name, policy.deny_python)
    ]
    violations.extend(
        Violation("javascript", name, denied)
        for name in javascript_locked
        if is_denied(name, policy.deny_javascript)
    )
    for name, licence in python_installed:
        if normalise(name).startswith(workspace_prefix):
            continue
        effective = policy.overrides_python.get(normalise(name), licence)
        violations.extend(_licence_violation("python", name, effective, policy))
    for name, licence in javascript_installed:
        violations.extend(_licence_violation("javascript", name, licence, policy))
    return violations


def _licence_violation(
    ecosystem: str, name: str, licence: str | None, policy: Policy
) -> list[Violation]:
    if not licence:
        return [Violation(ecosystem, name, "declares no recognisable licence")]
    try:
        allowed = spdx_allowed(licence, policy.allowed_licences)
    except ValueError:
        return [Violation(ecosystem, name, f"has an unparsable licence: {licence!r}")]
    if not allowed:
        return [Violation(ecosystem, name, f"licence {licence!r} is not on the allowlist")]
    return []


def main(argv: Sequence[str] | None = None) -> int:
    """Run the policy check and print a report; return a process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)

    policy = Policy.load(args.policy)
    root: Path = args.root
    pnpm_lock = root / "web" / "pnpm-lock.yaml"
    node_modules = root / "web" / "node_modules"
    python_installed = list(installed_python())
    violations = check(
        policy,
        python_installed=python_installed,
        python_locked=locked_python_packages(root / "uv.lock"),
        javascript_installed=list(installed_javascript(node_modules))
        if node_modules.is_dir()
        else [],
        javascript_locked=locked_javascript_packages(pnpm_lock.read_text(encoding="utf-8"))
        if pnpm_lock.is_file()
        else [],
    )
    for violation in violations:
        print(f"{violation.ecosystem}: {violation.package} {violation.problem}")  # noqa: T201
    summary = (
        f"dependency policy: {len(python_installed)} Python distributions checked, "
        f"{len(violations)} violation(s)"
    )
    print(summary)  # noqa: T201
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
