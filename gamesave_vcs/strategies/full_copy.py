"""FullCopyStrategy implementation (legacy full folder/file copy-paste).

PEP 8 compliant: single class per file in strategies subpackage for extensibility.
Atomic ops , recursive dir support; kept for backward compat.
"""

import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union

# Internal
from ..config import get_backups_dir, get_game_path

# Base ABC for inheritance (strategy pattern)
from .base import BackupStrategy


class FullCopyStrategy(BackupStrategy):
    """Original implementation: full folder/file copy-paste to timestamped locations.

    Kept for users who prefer it (e.g., no git dep, simple FS copies). Not delta-efficient,
    but fulfills "won't deny them" old style.
    """

    def backup_save(self, game_name: str) -> Optional[Path]:
        """Atomic backup for full copy: copy to temp , os.replace for all-or-nothing (POSIX atomic rename)."""
        save_path = get_game_path(game_name)
        if not save_path or not Path(save_path).exists():
            print(
                f"Backup skipped for {game_name}: save path not found (nothing to backup yet)"
            )
            return None
        save_path = Path(save_path)
        backup_dir = get_backups_dir() / game_name
        # Ensure per-game backup dir (robust for unit tests without prior add_game)
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{timestamp}_{save_path.name}"
        backup_path = backup_dir / backup_name
        # Atomic: use temp to avoid partial state on crash/interrupt
        if save_path.is_file():
            # For file: NamedTemporaryFile + replace
            fd, tmp_path = tempfile.mkstemp(dir=backup_dir, prefix=".tmp_")
            os.close(fd)
            shutil.copy2(save_path, tmp_path)
            if backup_path.exists():
                backup_path.unlink()
            os.replace(tmp_path, backup_path)  # atomic
        elif save_path.is_dir():
            # For dir: temp dir , copytree , replace (rm old)
            tmp_path = backup_path.with_suffix(
                backup_path.suffix + ".tmp" + str(os.getpid())
            )
            shutil.copytree(save_path, tmp_path)
            if backup_path.exists():
                shutil.rmtree(backup_path)
            os.replace(tmp_path, backup_path)  # atomic on POSIX
        print(
            f"Backed up {game_name} save to {backup_path} (full-copy, atomic)"
        )
        return backup_path

    def _list_saves_for_game(
        self, game_dir: Path, game_name: str
    ) -> List[tuple[datetime, Path, str]]:
        """Helper: parse timestamped files/dirs for full-copy (legacy)."""
        saves: List[tuple[datetime, Path, str]] = []
        if not game_dir.exists():
            return saves
        for f in game_dir.iterdir():
            # Skip git internals like .git to prevent parse errors
            if f.name.startswith("."):
                continue
            if f.is_file() or f.is_dir():
                try:
                    parts = f.name.split("_")
                    ts_str = "_".join(parts[:2])
                    ts = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
                    saves.append((ts, f, game_name))
                except ValueError:
                    pass
        return saves

    def list_saves(
        self, game_name: Optional[str] = None
    ) -> List[tuple[datetime, Union[Path, str], str]]:
        """Original list_saves logic, adapted to skip git dirs/files for clean legacy support.
        Handles mixed repos in aggregate.
        """
        saves: List[tuple[datetime, Union[Path, str], str]] = []
        backups_dir = get_backups_dir()
        if not backups_dir.exists():
            return saves
        if game_name:
            game_dir = backups_dir / game_name
            saves.extend(self._list_saves_for_game(game_dir, game_name))
        else:
            for game_dir in backups_dir.iterdir():
                if game_dir.is_dir():
                    # Full-copy only: .git presence handled in top-level dispatch
                    if not (game_dir / ".git").exists():
                        saves.extend(
                            self._list_saves_for_game(game_dir, game_dir.name)
                        )
        saves.sort(key=lambda x: x[0], reverse=True)
        return saves

    def restore_save(self, backup_spec: Union[str, Path]) -> bool:
        """Atomic restore for full-copy: copy to temp target , os.replace for all-or-nothing.
        Prevents partial overwrite of live save on failure/crash.
        """
        backup_path = Path(backup_spec)
        if not backup_path.exists():
            print("Backup not found")
            return False
        game_name = backup_path.parent.name
        save_path = get_game_path(game_name)
        if not save_path:
            print("Game not found")
            return False
        save_path = Path(save_path)
        # Atomic: temp for target save , replace (safe for file/dir)
        if backup_path.is_dir():
            # Dir case
            tmp_save = save_path.with_suffix(
                save_path.suffix + ".tmp" + str(os.getpid())
            )
            if save_path.exists():
                if save_path.is_dir():
                    shutil.rmtree(save_path)
                else:
                    save_path.unlink()
            save_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(backup_path, tmp_save)
            os.replace(tmp_save, save_path)  # atomic swap
        else:
            # File case
            fd, tmp_save = tempfile.mkstemp(
                dir=save_path.parent, prefix=".tmp_"
            )
            os.close(fd)
            shutil.copy2(backup_path, tmp_save)
            if save_path.exists():
                save_path.unlink()
            save_path.parent.mkdir(parents=True, exist_ok=True)
            os.replace(tmp_save, save_path)  # atomic
        print(f"Restored {backup_path} to {save_path} (full-copy, atomic)")
        return True
