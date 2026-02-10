#!/bin/bash
# Run all tests with coverage (CLI-only project)
set -e

echo "Installing test deps (if needed)..."
pip install -e .[test]

echo "Running tests with coverage..."
pytest --cov=gamesave_vcs --cov-report=term-missing --cov-report=html --cov-fail-under=95

echo "Tests passed! See htmlcov/ for detailed coverage report."
