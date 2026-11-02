from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

import sync_roadmap_issues as sync

if TYPE_CHECKING:
    from collections.abc import Sequence

ROADMAP = Path(__file__).resolve().parents[2] / "ROADMAP.md"

SAMPLE = """# Roadmap

### M0 · Engineering foundations

**Goal:** a repository where every change is checked.

- [x] **M0.1** (2 h) Repository bootstrap: licence and hooks.
- [ ] **M0.2** (6 h) GitHub Actions CI: path filters, caches and
  an aggregate check.

**Exit criteria:** CI is green on `main`.

---

### M9 · Thin end-to-end slice (thermal)

**Goal:** one synthetic bird becomes a gold row.

- [ ] **M9.1** (5 h) Spike: find the current publication (the old endpoint returned 404).
- [ ] **M9.2** (12 h) Minimal edge with a fixed threshold; more detail later.

**Exit criteria:** `just e2e` passes. **Release v0.1.0.**

## Stretch goals

- [ ] **S1** (8 h) Mutation testing: cargo-mutants on the vision crate.

## Release plan
"""


def item(item_id: str, text: str, hours: int = 3, *, done: bool = False) -> sync.Item:
    return sync.Item(id=item_id, hours=hours, done=done, text=text)


@pytest.fixture
def milestones() -> list[sync.Milestone]:
    return sync.parse_roadmap(SAMPLE)


def test_parse_sample(milestones: list[sync.Milestone]) -> None:
    assert [m.title for m in milestones] == [
        "M0 · Engineering foundations",
        "M9 · Thin end-to-end slice (thermal)",
        "Stretch goals",
    ]
    m0, m1, stretch = milestones
    assert m0.anchor == "m0--engineering-foundations"
    assert m1.anchor == "m9--thin-end-to-end-slice-thermal"
    assert m0.goal == "a repository where every change is checked."
    assert m1.exit_criteria == "`just e2e` passes. **Release v0.1.0.**"
    assert [(i.id, i.hours, i.done) for i in m0.items] == [("M0.1", 2, True), ("M0.2", 6, False)]
    assert m0.items[1].text == "GitHub Actions CI: path filters, caches and an aggregate check."
    assert m0.hours == 8
    assert [i.id for i in stretch.items] == ["S1"]
    assert "(8 h planned)" in m0.description


def test_parse_the_real_roadmap() -> None:
    milestones = sync.parse_roadmap(ROADMAP.read_text(encoding="utf-8"))
    core = [m for m in milestones if m.id != "S"]
    assert len(core) == 24
    assert sum(len(m.items) for m in core) == 194
    assert sum(m.hours for m in core) == 1067
    assert milestones[-1].title == sync.STRETCH_MILESTONE
    assert len(milestones[-1].items) == 10
    ids = [i.id for m in milestones for i in m.items]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Repository bootstrap: licence and hooks.", "Repository bootstrap"),
        (
            "Minimal edge with a fixed threshold; more detail later.",
            "Minimal edge with a fixed threshold",
        ),
        (
            "Protobuf catalogue v1 ([architecture §4](docs/architecture.md#4-events)) with rules.",
            "Protobuf catalogue v1 with rules",
        ),
        ("Nested (outer (inner) part) removed. Rest.", "Nested removed"),
        ("`ops.dq_results`, quarantine tables.", "ops.dq_results, quarantine tables"),
        (
            "Spike: find the current publication (old endpoint).",
            "Spike: find the current publication",
        ),
        ("lowercase start: rest", "Lowercase start"),
    ],
)
def test_summary(text: str, expected: str) -> None:
    assert sync.summary(item("M9.9", text)) == expected


def test_summary_truncates_long_titles_on_a_boundary() -> None:
    text = "Alpha bravo charlie delta echo foxtrot golf, hotel india juliet kilo lima mike, " * 2
    title = sync.summary(item("M9.9", text))
    assert len(title) <= sync.MAX_TITLE
    assert title.endswith("…")


def test_summary_uses_overrides() -> None:
    assert sync.summary(item("M0.13", "anything")) == "Roadmap-to-issues sync script"


@pytest.mark.parametrize(
    ("hours", "label"),
    [(1, "size:S"), (2, "size:S"), (3, "size:M"), (5, "size:M"), (8, "size:L"), (9, "size:XL")],
)
def test_size_labels(hours: int, label: str) -> None:
    assert sync.size_label(hours) == label


def test_labels(milestones: list[sync.Milestone]) -> None:
    m0, m1, stretch = milestones
    assert sync.labels_for(m0.items[1], m0) == ["roadmap", "type:chore", "size:L", "area:tooling"]
    assert sync.labels_for(m1.items[0], m1)[1] == "type:spike"
    assert sync.labels_for(m1.items[1], m1) == [
        "roadmap",
        "type:feature",
        "size:XL",
        "area:platform",
    ]
    assert sync.labels_for(stretch.items[0], stretch) == [
        "roadmap",
        "stretch",
        "type:feature",
        "size:L",
    ]
    assert sync.labels_for(item("M0.9", "Community files: x"), m0)[1] == "type:docs"
    assert sync.labels_for(item("M0.7", "CI: x"), m0)[3] == "area:ci"


def test_issue_body_links_the_milestone(milestones: list[sync.Milestone]) -> None:
    m0 = milestones[0]
    body = sync.issue_body(m0.items[1], m0)
    assert f"{sync.ROADMAP_URL}#m0--engineering-foundations" in body
    assert "estimate **6 h**" in body
    assert "`M0.2` is ticked" in body


def test_issue_item_id() -> None:
    assert sync.Issue(1, "M3.10 Determinism and speed", "open").item_id == "M3.10"
    assert sync.Issue(2, "S4 Zarr cubes", "open").item_id == "S4"
    assert sync.Issue(3, "Unrelated bug", "open").item_id is None


def test_plan_sync(milestones: list[sync.Milestone]) -> None:
    m0, m1, stretch = milestones
    plan = sync.plan_sync(
        milestones,
        existing_labels=[name for name in sync.LABELS if name != "stretch"],
        existing_milestones={m0.title: m0.description, m1.title: "stale description"},
        issues=[
            sync.Issue(1, "M0.1 Repository bootstrap", "open"),  # ticked, so it closes
            sync.Issue(2, "M0.2 GitHub Actions CI", "closed"),  # an older duplicate
            sync.Issue(3, "M0.2 GitHub Actions CI", "open"),  # the open one wins
            sync.Issue(4, "M9.1 Spike", "closed"),  # closed although still open
            sync.Issue(5, "A bug report", "open"),
        ],
    )
    assert plan.labels == ["stretch"]
    assert [m.title for m in plan.milestones] == [stretch.title]
    assert [m.title for m in plan.milestone_updates] == [m1.title]
    assert [i.id for i, _ in plan.create] == ["M9.2", "S1"]
    assert [(issue.number, i.id) for issue, i in plan.close] == [(1, "M0.1")]
    assert [(issue.number, i.id) for issue, i in plan.closed_but_open] == [(4, "M9.1")]
    assert not plan.is_empty()
    assert "close #1 (M0.1 is ticked)" in sync.describe(plan)


def test_plan_is_empty_when_in_sync(milestones: list[sync.Milestone]) -> None:
    issues = [
        sync.Issue(n, f"{i.id} x", "closed" if i.done else "open")
        for n, i in enumerate((i for m in milestones for i in m.items), start=1)
    ]
    plan = sync.plan_sync(
        milestones,
        existing_labels=sync.LABELS,
        existing_milestones={m.title: m.description for m in milestones},
        issues=issues,
    )
    assert plan.is_empty()
    assert sync.describe(plan) == []


class FakeGitHub:
    """Records calls and answers like the GitHub API for a small repository."""

    def __init__(self, milestones: list[dict[str, Any]], issues: list[dict[str, Any]]) -> None:
        self.calls: list[tuple[tuple[str, ...], dict[str, Any] | None]] = []
        self.milestones = milestones
        self.issues = issues

    def __call__(self, args: Sequence[str], payload: dict[str, Any] | None = None) -> Any:  # noqa: ANN401
        self.calls.append((tuple(args), payload))
        path = args[0] if not args[0].startswith("-") else args[2]
        if path.endswith("labels?per_page=100"):
            return [{"name": name} for name in sync.LABELS]
        if "milestones?state=all" in path:
            return self.milestones
        if "issues?state=all" in path:
            return [
                *self.issues,
                {"number": 99, "title": "M0.2 PR", "state": "open", "pull_request": {}},
            ]
        if path.endswith("/milestones"):
            return {"number": 42}
        return {}


def test_main_dry_run_changes_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    roadmap = tmp_path / "ROADMAP.md"
    roadmap.write_text(SAMPLE, encoding="utf-8")
    fake = FakeGitHub(milestones=[], issues=[])
    assert sync.main(["--roadmap", str(roadmap)], run=fake) == 0
    out = capsys.readouterr().out
    assert "create milestone Stretch goals" in out
    assert "dry run" in out
    assert all(payload is None for _, payload in fake.calls)


def test_main_apply(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    roadmap = tmp_path / "ROADMAP.md"
    roadmap.write_text(SAMPLE, encoding="utf-8")
    parsed = sync.parse_roadmap(SAMPLE)
    fake = FakeGitHub(
        milestones=[
            {"title": parsed[0].title, "number": 1, "description": parsed[0].description},
            {"title": parsed[1].title, "number": 2, "description": None},
        ],
        issues=[{"number": 7, "title": "M0.1 Repository bootstrap", "state": "open"}],
    )
    assert sync.main(["--roadmap", str(roadmap), "--apply", "--pause", "0"], run=fake) == 0
    assert "applied" in capsys.readouterr().out
    writes = [(args, payload) for args, payload in fake.calls if payload is not None]
    created = [p for a, p in writes if a == ("repos/soheil-mp/pecten/issues",) and p]
    assert [p["title"] for p in created] == [
        "M0.2 GitHub Actions CI",
        "M9.1 Spike: find the current publication",
        "M9.2 Minimal edge with a fixed threshold",
        "S1 Mutation testing",
    ]
    assert created[-1]["milestone"] == 42
    assert (
        ("-X", "PATCH", "repos/soheil-mp/pecten/milestones/2"),
        {"description": parsed[1].description},
    ) in writes
    assert (
        ("-X", "PATCH", "repos/soheil-mp/pecten/issues/7"),
        {"state": "closed", "state_reason": "completed"},
    ) in writes


def test_main_reports_nothing_to_do(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    roadmap = tmp_path / "ROADMAP.md"
    roadmap.write_text("# Roadmap\n", encoding="utf-8")
    assert sync.main(["--roadmap", str(roadmap)], run=FakeGitHub([], [])) == 0
    assert capsys.readouterr().out.strip() == "nothing to do"


def test_gh_api(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[dict[str, Any]] = []

    def fake_run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:  # noqa: ANN401
        seen.append({"command": command, **kwargs})
        if "--jq" in command:
            return subprocess.CompletedProcess(command, 0, '{"a": 1}\n{"a": 2}\n', "")
        if command[-1] == "boom":
            return subprocess.CompletedProcess(command, 1, "", "HTTP 404")
        return subprocess.CompletedProcess(command, 0, json.dumps({"ok": True}), "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert sync.gh_api(["repos/x/issues", "--paginate", "--jq", ".[]"]) == [{"a": 1}, {"a": 2}]
    assert sync.gh_api(["repos/x/labels"], {"name": "n"}) == {"ok": True}
    assert seen[-1]["command"][-2:] == ["--input", "-"]
    assert json.loads(seen[-1]["input"]) == {"name": "n"}
    with pytest.raises(RuntimeError, match="HTTP 404"):
        sync.gh_api(["boom"])
