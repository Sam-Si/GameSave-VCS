#!/bin/bash
# Run all tests with coverage AND type checking with pyright.
# Updated for Bazel refactor: tests via bazel run //:pytest (hermetic , preserves pytest/cov/fixtures/integration).
# pyright/lint kept (dev tools; assume via pip or global ; Bazel focuses build/run/test core).
# pip install -e removed (Bazel replaces via MODULE/requirements_lock).
set -e

echo "Running pyright for type checking (strict-ish via pyproject.toml)..."
pyright

echo "Checking PEP 8 compliance (isort/black/flake8 via pyproject.toml)..."
# isort/black enforce import/order/spacing/naming/line ; flake8 for rest (ignore E501 long doc/test , F401/F841 test code common)
isort --check-only --diff .
black --check --line-length 79 --diff .
flake8 --ignore=E501,F401,F841,W503 .

echo "Running tests with coverage via Bazel (all functionalities: unit/integration/CLI/backends)..."
# Uses pytest_wrapper ; --cov= absolute source path for instrumentation (Bazel runfiles otherwise miss cov data).
# Equiv to original ; report in htmlcov/ ; fail-under ensures >=90%.
# Note: Bazel hermetic , cov on src tree.
bazel run //:pytest -- tests/ --cov=/testbed/GameSave-VCS/gamesave_vcs --cov-report=term-missing --cov-report=html --cov-fail-under=90

echo "Tests and type checks passed! See htmlcov/ for detailed coverage report."
echo "Bazel build artifacts in bazel-bin/ ; run CLI: bazel run //:gamesave -- <cmd>"
