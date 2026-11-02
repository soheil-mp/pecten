#!/usr/bin/env bash
# Runs once when the devcontainer is created. Installs mise, the tools pinned in
# mise.toml, the Rust toolchain from rust-toolchain.toml, then the workspace.
set -euo pipefail

curl -fsSL https://mise.run | sh
export PATH="$HOME/.local/bin:$PATH"
mise trust --yes mise.toml
mise install --yes
rustup show active-toolchain
mise exec -- just setup
