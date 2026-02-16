"""Strategies subpackage for backup backends.

PEP 8: one class per file (base ABC , full_copy.py , git.py impls).
Provides extensibility: add new strategy/*.py + register in base.py dispatch.
Re-exports only base/dispatch ; impl direct import to avoid cycle.
"""

# Re-export for compat and extensibility (from gamesave_vcs.strategies import ...)
# Impl direct: from gamesave_vcs.strategies.full_copy import ...
from .base import BackupStrategy, detect_strategy, get_strategy

__all__ = [
    "BackupStrategy",
    "detect_strategy",
    "get_strategy",
]
