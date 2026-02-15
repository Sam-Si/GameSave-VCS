#!/bin/bash
# Run all tests with coverage AND type checking with pyright (updated for full type hints).
# Pyright added to verify refactor; fails build on type errors.
set -e

echo "Installing test deps (if needed)..."
pip install -e .[test]

echo "Running pyright for type checking (strict-ish via pyproject.toml)..."
pyright

echo "Running tests with coverage..."
pytest --cov=gamesave_vcs --cov-report=term-missing --cov-report=html --cov-fail-under=90

echo "Tests and type checks passed! See htmlcov/ for detailed coverage report."
