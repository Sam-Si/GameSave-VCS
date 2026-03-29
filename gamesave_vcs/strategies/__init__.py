"""Strategies subpackage for backup backends.

PEP 8: one class per file (base ABC , full_copy.py , git.py impls).
Provides extensibility: add new strategy/*.py + register in base.py dispatch.
Re-exports only base/dispatch ; impl direct import to avoid cycle.
"""

# Re-export for compat and extensibility (from gamesave_vcs.strategies import ...)
# Impl direct: from gamesave_vcs.strategies.full_copy import ...
# Import refactored to absolute for Bazel (though re-export; used in tests/backup).
# Enables `from gamesave_vcs.strategies import get_strategy` in Bazel context.
from gamesave_vcs.strategies.base import BackupStrategy, detect_strategy, get_strategy

__all__ = [
    "BackupStrategy",
    "detect_strategy",
    "get_strategy",
]
