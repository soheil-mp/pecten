"""Mirror ROADMAP.md onto GitHub: labels, milestones and one issue per open item.

ROADMAP.md stays the source of truth. The sync is idempotent:

* missing labels and milestones are created, and milestone descriptions follow
  the roadmap;
* every open roadmap item without an issue gets one, titled ``<ID> <summary>``;
* issues of items that are ticked (``[x]``) in the roadmap are closed;
* issues whose item is open in the roadmap but closed on GitHub are reported,
  not reopened, so a person can decide.

It runs as a dry run unless ``--apply`` is given::

    uv run python tools/sync_roadmap_issues.py            # show the plan
    uv run python tools/sync_roadmap_issues.py --apply    # make the changes

GitHub is reached through the ``gh`` CLI, which must be authenticated.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

ROOT = Path(__file__).resolve().parent.parent
REPO = "soheil-mp/pecten"
ROADMAP_URL = f"https://github.com/{REPO}/blob/main/ROADMAP.md"
STRETCH_MILESTONE = "Stretch goals"

_MILESTONE = re.compile(r"^### (M(\d+)) · (.+)$", re.MULTILINE)
_ITEM = re.compile(
    r"^- \[(?P<state>[ x])\] \*\*(?P<id>(?:M\d+\.\d+|S\d+))\*\* \((?P<hours>\d+) h\) "
    r"(?P<text>.+?)(?=\n- \[|\n\n|\Z)",
    re.MULTILINE | re.DOTALL,
)
_ISSUE_ID = re.compile(r"^(M\d+\.\d+|S\d+) ")
MAX_TITLE = 80  # characters; GitHub titles stay readable below this

# Summaries that read better written by hand than derived from the item text.
TITLE_OVERRIDES: dict[str, str] = {
    "M0.13": "Roadmap-to-issues sync script",
    "M1.2": "First Protobuf schemas and code generation",
    "M1.4": "Compose profile core",
    "M1.6": "RisingWave Kafka source and Iceberg sink",
    "M1.7": "SQLMesh project on Trino",
    "M1.8": "Airflow 3.3 with an asset-scheduled DAG",
    "M1.10": "End-to-end test (just e2e) in CI",
    "M1.11": "Architecture boundary checks",
    "M2.5": "Protobuf catalogue v1 for every edge event",
    "M2.6": "CloudEvents conventions and a shared conformance suite",
    "M2.7": "MQTT topic namespace, QoS, retention and ACL templates",
    "M5.4": "Calibration and privacy masks applied before processing",
    "M7.1": "Kalman filters with kinematics-derived process noise",
    "M9.4": "Event-ID de-duplication and per-device ordering",
    "M10.2": "RisingWave sources, watermarks and lateness policy",
    "M10.5": "Curtailment advisory rules with hysteresis",
    "M11.6": "Spike: locate the current Dutch UAS geozone publication",
    "M13.1": "SQLMesh project structure and gateways",
    "M14.4": "Data-quality results store and quarantine tables",
    "M15.5": "Georeferencing of detections",
    "M15.9": "Static STAC catalogue, STAC Browser and STAC search",
    "M16.5": "Camtrap DP export of Pecten's camera observations",
    "M17.1": "SvelteKit scaffold with strict TypeScript and tests",
    "M18.4": "Compose profiles with measured resource limits",
    "M22.1": "UVC webcam adapter with mandatory privacy masks",
    "M22.4": "Field deployment checklist and privacy note",
}

# Default area per milestone number, with per-item exceptions.
MILESTONE_AREAS: dict[int, str] = {
    0: "tooling",
    1: "platform",
    2: "contracts",
    3: "sim",
    4: "sim",
    5: "edge",
    6: "edge",
    7: "edge",
    8: "edge",
    9: "platform",
    10: "platform",
    11: "data",
    12: "data",
    13: "data",
    14: "data",
    15: "survey",
    16: "api",
    17: "web",
    18: "ci",
    19: "ops",
    20: "ops",
    21: "ops",
    22: "edge",
    23: "docs",
}
ITEM_AREAS: dict[str, str] = {
    "M0.7": "ci",
    "M0.8": "ci",
    "M0.9": "docs",
    "M0.10": "ci",
    "M0.11": "docs",
    "M0.12": "ops",
    "M1.1": "sim",
    "M1.2": "contracts",
    "M1.3": "edge",
    "M1.7": "data",
    "M1.8": "data",
    "M1.9": "api",
    "M1.10": "ci",
    "M1.11": "tooling",
    "M2.2": "edge",
    "M2.9": "data",
    "M16.5": "data",
}
DOCS_ITEMS = frozenset({"M0.9", "M0.11", "M14.6", "M22.4", "M23.1", "M23.2", "M23.3", "M23.4"})

LABELS: dict[str, tuple[str, str]] = {
    "roadmap": ("0e8a16", "Item from ROADMAP.md"),
    "stretch": ("c2e0c6", "Optional stretch goal"),
    "type:feature": ("1d76db", "New capability"),
    "type:chore": ("c5def5", "Tooling, CI or maintenance"),
    "type:docs": ("0075ca", "Documentation"),
    "type:spike": ("fbca04", "Time-boxed research"),
    "size:S": ("ededed", "Up to 2 hours"),
    "size:M": ("d4c5f9", "3 to 5 hours"),
    "size:L": ("bfd4f2", "6 to 8 hours"),
    "size:XL": ("5319e7", "10 hours or more"),
    "area:sim": ("f9d0c4", "Sensor twin (pecten-sim)"),
    "area:edge": ("f9d0c4", "Edge runtime and perception"),
    "area:platform": ("f9d0c4", "Transport, streaming, lakehouse services"),
    "area:data": ("f9d0c4", "Ingestion, orchestration, transformations, quality"),
    "area:api": ("f9d0c4", "Read API and exports"),
    "area:web": ("f9d0c4", "Web application"),
    "area:ops": ("f9d0c4", "Deployment, GitOps, observability, IaC"),
    "area:ci": ("f9d0c4", "CI, releases, supply chain"),
    "area:docs": ("f9d0c4", "Documentation site and guides"),
    "area:tooling": ("f9d0c4", "Workspaces, tasks, developer tooling"),
    "area:contracts": ("f9d0c4", "Schemas and data contracts"),
    "area:survey": ("f9d0c4", "Drone survey planning and processing"),
}


@dataclass(frozen=True)
class Item:
    """One roadmap item."""

    id: str
    hours: int
    done: bool
    text: str


@dataclass(frozen=True)
class Milestone:
    """One roadmap milestone with its items."""

    id: str
    title: str
    anchor: str
    goal: str
    exit_criteria: str
    items: tuple[Item, ...]

    @property
    def hours(self) -> int:
        """Planned hours of all items in the milestone."""
        return sum(item.hours for item in self.items)

    @property
    def description(self) -> str:
        """Milestone description shown on GitHub (at most 1,000 characters)."""
        text = f"{self.goal} ({self.hours} h planned). Exit criteria: {self.exit_criteria}"
        return text[:1000]


@dataclass(frozen=True)
class Issue:
    """The parts of a GitHub issue the sync needs."""

    number: int
    title: str
    state: str

    @property
    def item_id(self) -> str | None:
        """Roadmap ID at the start of the title, if any."""
        match = _ISSUE_ID.match(self.title)
        return match.group(1) if match else None


@dataclass
class Plan:
    """Changes the sync would make."""

    labels: list[str] = field(default_factory=list)
    milestones: list[Milestone] = field(default_factory=list)
    milestone_updates: list[Milestone] = field(default_factory=list)
    create: list[tuple[Item, Milestone]] = field(default_factory=list)
    close: list[tuple[Issue, Item]] = field(default_factory=list)
    closed_but_open: list[tuple[Issue, Item]] = field(default_factory=list)

    def is_empty(self) -> bool:
        """Return whether the plan changes nothing on GitHub."""
        return not (
            self.labels or self.milestones or self.milestone_updates or self.create or self.close
        )


def slug(heading: str) -> str:
    """Return GitHub's anchor for a Markdown heading."""
    text = re.sub(r"[^\w\- ]", "", heading.strip().lower())
    return text.replace(" ", "-")


def _section(text: str, start: int) -> str:
    following = re.search(r"^#{2,3} ", text[start:], re.MULTILINE)
    return text[start : start + following.start()] if following else text[start:]


def _items(block: str) -> tuple[Item, ...]:
    return tuple(
        Item(
            id=match["id"],
            hours=int(match["hours"]),
            done=match["state"] == "x",
            text=" ".join(match["text"].split()),
        )
        for match in _ITEM.finditer(block)
    )


def parse_roadmap(text: str) -> list[Milestone]:
    """Parse milestones and items (including stretch goals) from ROADMAP.md."""
    milestones: list[Milestone] = []
    for match in _MILESTONE.finditer(text):
        block = _section(text, match.end())
        goal = re.search(r"\*\*Goal:\*\* (.+?)\n\n", block, re.DOTALL)
        exit_criteria = re.search(r"\*\*Exit criteria:\*\* (.+?)(?:\n\n|\Z)", block, re.DOTALL)
        milestones.append(
            Milestone(
                id=match.group(1),
                title=f"{match.group(1)} · {match.group(3)}",
                anchor=slug(match.group(0).removeprefix("### ")),
                goal=" ".join(goal.group(1).split()) if goal else "",
                exit_criteria=" ".join(exit_criteria.group(1).split()) if exit_criteria else "",
                items=_items(block),
            )
        )
    stretch = re.search(r"^## Stretch goals$", text, re.MULTILINE)
    if stretch:
        milestones.append(
            Milestone(
                id="S",
                title=STRETCH_MILESTONE,
                anchor="stretch-goals",
                goal="Optional work beyond the core roadmap",
                exit_criteria="Each goal is optional and closes on its own.",
                items=_items(_section(text, stretch.end())),
            )
        )
    return milestones


def summary(item: Item) -> str:
    """Return a short issue title summary for an item."""
    if item.id in TITLE_OVERRIDES:
        return TITLE_OVERRIDES[item.id]
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", item.text)  # Markdown links to their text
    spike = text.startswith("Spike: ")
    text = text.removeprefix("Spike: ")
    head = text.split(": ", 1)[0] if ": " in text[:90] else text.split(". ", 1)[0]
    head = head.split("; ", 1)[0]
    while (stripped := re.sub(r"\s*\([^()]*\)", "", head)) != head:
        head = stripped
    head = head.replace("`", "").rstrip(".")
    if len(head) > MAX_TITLE:
        cut = head[: MAX_TITLE - 3]
        head = (cut.rsplit(", ", 1)[0] if ", " in cut else cut.rsplit(" ", 1)[0]) + "…"
    first_word = head.split(" ", 1)[0]
    if not spike and first_word.isalpha():
        head = head[:1].upper() + head[1:]
    return f"Spike: {head}" if spike else head


def size_label(hours: int) -> str:
    """Return the size label for an estimate in hours."""
    if hours <= 2:  # noqa: PLR2004
        return "size:S"
    if hours <= 5:  # noqa: PLR2004
        return "size:M"
    if hours <= 8:  # noqa: PLR2004
        return "size:L"
    return "size:XL"


def labels_for(item: Item, milestone: Milestone) -> list[str]:
    """Return the labels an item's issue carries."""
    if item.id.startswith("S"):
        return ["roadmap", "stretch", "type:feature", size_label(item.hours)]
    number = int(milestone.id.removeprefix("M"))
    if item.text.startswith("Spike:"):
        kind = "type:spike"
    elif item.id in DOCS_ITEMS:
        kind = "type:docs"
    elif number == 0:
        kind = "type:chore"
    else:
        kind = "type:feature"
    area = ITEM_AREAS.get(item.id, MILESTONE_AREAS.get(number, "tooling"))
    return ["roadmap", kind, size_label(item.hours), f"area:{area}"]


def issue_body(item: Item, milestone: Milestone) -> str:
    """Return the Markdown body of an item's issue."""
    lines = [
        (
            f"**Roadmap item {item.id}** · estimate **{item.hours} h** · milestone "
            f"[{milestone.title}]({ROADMAP_URL}#{milestone.anchor})"
        ),
        "",
        item.text,
        "",
        f"**Milestone goal:** {milestone.goal}",
        "",
        f"**Milestone exit criteria:** {milestone.exit_criteria}",
        "",
        (
            f"Done means the [definition of done]({ROADMAP_URL}#definition-of-done-every-item) "
            f"holds and `{item.id}` is ticked in ROADMAP.md in the same change."
        ),
    ]
    return "\n".join(lines)


def plan_sync(
    milestones: Sequence[Milestone],
    *,
    existing_labels: Iterable[str],
    existing_milestones: dict[str, str],
    issues: Iterable[Issue],
) -> Plan:
    """Compare the roadmap with GitHub's state and return the changes to make."""
    plan = Plan()
    known_labels = set(existing_labels)
    plan.labels = [name for name in LABELS if name not in known_labels]
    for milestone in milestones:
        if milestone.title not in existing_milestones:
            plan.milestones.append(milestone)
        elif existing_milestones[milestone.title] != milestone.description:
            plan.milestone_updates.append(milestone)
    _plan_issues(plan, milestones, _issues_by_item(issues))
    return plan


def _issues_by_item(issues: Iterable[Issue]) -> dict[str, Issue]:
    """Map roadmap IDs to issues, preferring an open issue when there are several."""
    by_item: dict[str, Issue] = {}
    for issue in issues:
        if issue.item_id and (issue.item_id not in by_item or issue.state == "open"):
            by_item[issue.item_id] = issue
    return by_item


def _plan_issues(plan: Plan, milestones: Sequence[Milestone], by_item: dict[str, Issue]) -> None:
    for milestone in milestones:
        for item in milestone.items:
            existing = by_item.get(item.id)
            if existing is None:
                if not item.done:
                    plan.create.append((item, milestone))
            elif item.done and existing.state == "open":
                plan.close.append((existing, item))
            elif not item.done and existing.state == "closed":
                plan.closed_but_open.append((existing, item))


class Runner(Protocol):
    """Calls the GitHub API (``gh api``) and returns decoded JSON."""

    def __call__(self, args: Sequence[str], payload: dict[str, Any] | None = None) -> Any:  # noqa: ANN401
        """Run one API call."""
        ...


def gh_api(args: Sequence[str], payload: dict[str, Any] | None = None) -> Any:  # noqa: ANN401
    """Run ``gh api`` with optional JSON input and return the decoded response."""
    command = ["gh", "api", *args]
    if payload is not None:
        command += ["--input", "-"]
    result = subprocess.run(  # noqa: S603 - fixed executable, arguments built by this module
        command,
        input=json.dumps(payload) if payload is not None else None,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        message = f"gh api {' '.join(args)} failed: {result.stderr.strip()}"
        raise RuntimeError(message)
    if "--jq" in args:  # one compact JSON value per line
        return [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    return json.loads(result.stdout) if result.stdout.strip() else None


def _paged(run: Runner, path: str) -> list[dict[str, Any]]:
    """Fetch every page of a list endpoint and flatten the result."""
    entries: list[dict[str, Any]] = run([path, "--paginate", "--jq", ".[]"])
    return entries


def fetch_state(
    run: Runner, repo: str
) -> tuple[list[str], dict[str, tuple[int, str]], list[Issue]]:
    """Read labels, milestones and issues from GitHub."""
    labels = [label["name"] for label in _paged(run, f"repos/{repo}/labels?per_page=100")]
    milestones = {
        m["title"]: (m["number"], m["description"] or "")
        for m in _paged(run, f"repos/{repo}/milestones?state=all&per_page=100")
    }
    issues = [
        Issue(number=i["number"], title=i["title"], state=i["state"])
        for i in _paged(run, f"repos/{repo}/issues?state=all&per_page=100")
        if "pull_request" not in i
    ]
    return labels, milestones, issues


def apply(
    plan: Plan, run: Runner, repo: str, milestone_numbers: dict[str, int], pause: float
) -> None:
    """Make the planned changes on GitHub."""
    for name in plan.labels:
        color, description = LABELS[name]
        run([f"repos/{repo}/labels"], {"name": name, "color": color, "description": description})
    for milestone in plan.milestones:
        created = run(
            [f"repos/{repo}/milestones"],
            {"title": milestone.title, "description": milestone.description},
        )
        milestone_numbers[milestone.title] = created["number"]
    for milestone in plan.milestone_updates:
        number = milestone_numbers[milestone.title]
        run(
            ["-X", "PATCH", f"repos/{repo}/milestones/{number}"],
            {"description": milestone.description},
        )
    for item, milestone in plan.create:
        run(
            [f"repos/{repo}/issues"],
            {
                "title": f"{item.id} {summary(item)}",
                "body": issue_body(item, milestone),
                "labels": labels_for(item, milestone),
                "milestone": milestone_numbers[milestone.title],
            },
        )
        time.sleep(pause)  # stay well below GitHub's secondary rate limits
    for issue, item in plan.close:
        run(
            [f"repos/{repo}/issues/{issue.number}/comments"],
            {"body": f"`{item.id}` is ticked in ROADMAP.md; closing."},
        )
        run(
            ["-X", "PATCH", f"repos/{repo}/issues/{issue.number}"],
            {"state": "closed", "state_reason": "completed"},
        )


def describe(plan: Plan) -> list[str]:
    """Return a human-readable list of the planned changes."""
    lines = [f"create label {name}" for name in plan.labels]
    lines += [f"create milestone {m.title}" for m in plan.milestones]
    lines += [f"update milestone {m.title}" for m in plan.milestone_updates]
    lines += [f"create issue {item.id} {summary(item)}" for item, _ in plan.create]
    lines += [f"close #{issue.number} ({item.id} is ticked)" for issue, item in plan.close]
    lines += [
        f"note: #{issue.number} is closed but {item.id} is still open in ROADMAP.md"
        for issue, item in plan.closed_but_open
    ]
    return lines


def main(argv: Sequence[str] | None = None, run: Runner = gh_api) -> int:
    """Run the sync; return a process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--apply", action="store_true", help="make the changes on GitHub")
    parser.add_argument("--repo", default=REPO)
    parser.add_argument("--roadmap", type=Path, default=ROOT / "ROADMAP.md")
    parser.add_argument("--pause", type=float, default=1.5, help="seconds between new issues")
    args = parser.parse_args(argv)

    milestones = parse_roadmap(args.roadmap.read_text(encoding="utf-8"))
    labels, remote_milestones, issues = fetch_state(run, args.repo)
    plan = plan_sync(
        milestones,
        existing_labels=labels,
        existing_milestones={title: desc for title, (_, desc) in remote_milestones.items()},
        issues=issues,
    )
    for line in describe(plan) or ["nothing to do"]:
        print(line)  # noqa: T201
    if args.apply and not plan.is_empty():
        numbers = {title: number for title, (number, _) in remote_milestones.items()}
        apply(plan, run, args.repo, numbers, args.pause)
        print("applied")  # noqa: T201
    elif not plan.is_empty():
        print("dry run: pass --apply to make these changes")  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main())
