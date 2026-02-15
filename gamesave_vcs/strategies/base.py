"""Base strategy classes and dispatch for extensible backup backends.

Follows PEP 8: single class (ABC) per logical file in strategies subpackage.
Enables adding new strategies (e.g., rsync) easily for maintainability/extensibility.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union

# Internal import for config/dispatch (minimal for PEP 8; unused removed)
from ..config import get_backups_dir, get_game_backend


class BackupStrategy(ABC):
    """Abstract base class for backup strategies.

    Enables supporting both full folder copy and git-style deltas (or future ones).
    """

    @abstractmethod
    def backup_save(self, game_name: str) -> Optional[Path]:
        """Backup the game's save. Returns backup location (Path) or None.
        Called by watcher/CLI on change.
        """

    @abstractmethod
    def list_saves(
        self, game_name: Optional[str] = None
    ) -> List[tuple[datetime, Union[Path, str], str]]:
        """List saves/backups. Returns list of (datetime, spec, game_name).
        spec: Path for full-copy, 'repo@commit' str for git.
        Supports game=None for aggregate.
        """

    @abstractmethod
    def restore_save(self, backup_spec: Union[str, Path]) -> bool:
        """Restore from backup_spec.
        Parses spec to apply strategy-specific restore.
        """


# Dispatch helpers for extensibility (in base as core to strategies pkg)
def detect_strategy(game_name: str) -> "BackupStrategy":
    """Detect from FS (e.g. .git dir) for legacy/mixed/backward compat.
    Full-copy if no git repo found.
    """
    backups_dir = get_backups_dir()
    game_dir = backups_dir / game_name
    # Lazy import to avoid circular (full impl in own files)
    if (game_dir / ".git").exists():
        from .git import GitStrategy

        return GitStrategy()
    from .full_copy import FullCopyStrategy

    return FullCopyStrategy()


def get_strategy(game_name: str) -> "BackupStrategy":
    """Main dispatcher: uses config backend (default 'git') or FS detect.
    Makes system extensible to future strategies (e.g., rsync, zfs).
    """
    backend = get_game_backend(game_name)
    if backend == "git":
        from .git import GitStrategy

        return GitStrategy()
    elif backend == "full-copy":
        from .full_copy import FullCopyStrategy

        return FullCopyStrategy()
    else:
        # Fallback for legacy no-config
        return detect_strategy(game_name)
