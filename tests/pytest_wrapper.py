"""Pytest wrapper for Bazel.

This allows running pytest via `bazel run //:pytest -- [args]` (e.g., `tests/` or specific tests).

- Refactored build uses this to invoke pytest.main() ensuring plugins (cov), fixtures (conftest), and all tests
  (unit/integration) execute identically to pre-Bazel `pytest`.
- Deps include gamesave_vcs lib + pytest/pytest-cov for full functionality (coverage reports, fail-under).
- srcs include tests/ for discovery/execution; no changes to existing test code.
- Enables `bazel test` equiv for existing test suite (though run used for CLI compat with pyproject opts/AAA).
- See BUILD.bazel and updated run_tests.sh/README for usage.

Preserves 100% test coverage, type checks separate (pyright etc).
"""

import sys

import pytest

if __name__ == "__main__":
    # Forward args to pytest; e.g., tests/ --cov=... --tb=no
    # sys.exit ensures Bazel sees test pass/fail status.
    sys.exit(pytest.main(sys.argv[1:]))
