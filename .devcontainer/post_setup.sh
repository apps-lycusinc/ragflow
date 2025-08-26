#!/bin/bash
set -e

# Install pipx and ensure path
pip install pipx
pipx ensurepath

# Install uv and pre-commit using pipx
pipx install uv
pipx install pre-commit

# Sync Python dependencies and run setup scripts
uv sync --python 3.10 --all-extras
uv run download_deps.py

# Install pre-commit hooks
pre-commit install
