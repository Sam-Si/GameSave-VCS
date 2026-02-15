#!/bin/bash
# Run all tests with coverage AND type checking with pyright (updated for full type hints).
# Pyright added to verify refactor; fails build on type errors.
set -e

echo "Installing test deps (if needed)..."
pip install -e .[test]

echo "Running pyright for type checking (strict-ish via pyproject.toml)..."
pyright

echo "Checking PEP 8 compliance (isort/black/flake8 via pyproject.toml)..."
# isort/black enforce import/order/spacing/naming/line ; flake8 for rest (ignore E501 long doc/test , F401/F841 test code common)
isort --check-only --diff .
black --check --line-length 79 --diff .
flake8 --ignore=E501,F401,F841,W503 .

echo "Running tests with coverage..."
pytest --cov=gamesave_vcs --cov-report=term-missing --cov-report=html --cov-fail-under=90

echo "Tests and type checks passed! See htmlcov/ for detailed coverage report."
