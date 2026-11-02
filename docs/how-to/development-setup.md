# Set up a development environment

This guide gets a working checkout in which every check CI runs also passes locally.

## Prerequisites

| Tool | Why | Install |
| :-- | :-- | :-- |
| Git | Version control | Your package manager |
| [uv](https://docs.astral.sh/uv/) | Python 3.14 and the Python workspace | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| [rustup](https://rustup.rs/) | The pinned Rust toolchain from `rust-toolchain.toml` | See rustup.rs |
| [just](https://just.systems/) | Task runner | `uv tool install rust-just` |
| [mise](https://mise.jdx.dev/) (optional) | Pinned CLI tools from `mise.toml` (nextest, cargo-deny, buf, linters, Kubernetes tools) | See mise.jdx.dev |
| Docker (later) | The local stack from milestone M1 | Docker Engine or Docker Desktop |

Alternatively, open the repository in the devcontainer (`.devcontainer/`), which installs all of
the above.

## Steps

1. Clone the repository and enter it:

    ```sh
    git clone https://github.com/soheil-mp/pecten.git
    cd pecten
    ```

2. Install everything:

    ```sh
    just setup
    ```

    This syncs the uv workspace (installing Python 3.14 if needed), installs the Git hooks,
    fetches the Rust crates (rustup installs the pinned toolchain on first use) and, if mise is
    present, installs the pinned CLI tools.

3. Run every check:

    ```sh
    just check
    ```

    This runs Ruff, `mypy --strict`, import-linter, the dependency policy, rustfmt, Clippy and
    all tests. A green `just check` means CI will pass the same checks.

## Everyday commands

| Command | What it does |
| :-- | :-- |
| `just` | List all recipes |
| `just fmt` | Format Python and Rust code |
| `just lint` | Linters, import boundaries and the dependency policy |
| `just typecheck` | Strict type checking |
| `just test` | Python and Rust tests with coverage for Python |
| `just hooks` | All pre-commit hooks on all files |
| `just docs` | Preview this documentation site at <http://localhost:8000> |

## Troubleshooting

- **`cargo-deny not found`:** install it with `mise install`; CI runs it regardless.
- **A hook fails on a file you did not touch:** run `just fmt`, then `just hooks`, and commit the
  fixes separately.
