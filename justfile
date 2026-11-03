# Pecten task runner. Every CI job runs one of these recipes, so `just check`
# locally means the same as a green CI run. List recipes with `just`.

set shell := ["bash", "-euo", "pipefail", "-c"]

compose_file := "deploy/compose/compose.yaml"

# List the available recipes.
default:
    @just --list --unsorted

# Install dependencies, Git hooks and (when mise is available) pinned CLI tools.
setup:
    uv sync --all-packages --all-groups --locked
    uv run pre-commit install --hook-type pre-commit --hook-type commit-msg
    cargo fetch --locked
    if command -v mise >/dev/null; then mise install; else echo "mise not found; install it from https://mise.jdx.dev for the pinned CLI tools in mise.toml"; fi

# Format Python and Rust code in place.
fmt:
    uv run ruff format .
    uv run ruff check --fix .
    cargo fmt --all

# Run all linters without changing files.
lint:
    uv run ruff format --check .
    uv run ruff check .
    uv run lint-imports
    cargo fmt --all -- --check
    cargo clippy --workspace --all-targets --locked -- -D warnings
    just deps

# Check dependency licences and the machine-learning deny list.
deps:
    uv run python tools/dependency_policy.py
    uv run python tools/crate_boundaries.py
    if command -v cargo-deny >/dev/null; then cargo deny check licenses bans sources; else echo "cargo-deny not found (install with mise); CI runs it"; fi

# Type-check the Python packages (mypy, strict).
typecheck:
    uv run mypy

# Run every test suite.
test: test-py test-rs

# Python tests with branch coverage (fails under 85 %).
test-py:
    uv run pytest --cov --cov-report=term

# Rust tests (nextest when installed, otherwise cargo test).
test-rs:
    if command -v cargo-nextest >/dev/null; then cargo nextest run --workspace --locked; else cargo test --workspace --locked; fi

# Rust coverage summary (needs cargo-llvm-cov and cargo-nextest from mise).
coverage-rs:
    cargo llvm-cov nextest --workspace --locked --summary-only

# Run Rust benchmarks.
bench:
    cargo bench --workspace --locked

# Everything CI checks: lint, types and tests.
check: lint typecheck test

# Run every pre-commit hook on all files.
hooks:
    uv run pre-commit run --all-files

# Preview the documentation site at http://localhost:8000 with live reload.
docs:
    uv run --group docs zensical serve

# Build the documentation site into site/ (warnings fail the build).
docs-build:
    uv run --group docs zensical build --clean --strict

# Start the local stack with a Compose profile (core, stream, batch, obs, full).
up profile="core":
    @test -f {{compose_file}} || { echo "The Compose stack arrives with roadmap item M1.4." >&2; exit 1; }
    docker compose -f {{compose_file}} --profile {{profile}} up --detach --wait

# Stop the local stack and remove its containers.
down:
    @test -f {{compose_file}} || { echo "The Compose stack arrives with roadmap item M1.4." >&2; exit 1; }
    docker compose -f {{compose_file}} --profile full down --remove-orphans

# Run the end-to-end scenario test against the local stack.
e2e:
    @test -f tests/e2e/test_walking_skeleton.py || { echo "The end-to-end test arrives with roadmap item M1.10." >&2; exit 1; }
    uv run pytest tests/e2e

# Mirror ROADMAP.md onto GitHub milestones and issues (dry run; pass --apply to change).
sync-issues *args:
    uv run python tools/sync_roadmap_issues.py {{args}}

# Remove build outputs and caches.
clean:
    cargo clean
    rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage site
