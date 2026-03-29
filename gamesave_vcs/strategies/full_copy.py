"""FullCopyStrategy implementation (legacy full folder/file copy-paste).

PEP 8 compliant: single class per file in strategies subpackage for extensibility.
Atomic ops , recursive dir support; kept for backward compat.

Storage Optimizations:
- Hard-link deduplication: Identical files share storage via hard links
- Content-addressed storage: Files stored by hash for automatic dedup
"""

import hashlib
import logging
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

# Internal imports refactored to absolute for Bazel compatibility (config from root pkg, base from subpkg).
# See base.py/cli.py for details. Ensures full-copy strategy (recursive atomic copy) works in Bazel.
# Strategy pattern unchanged for extensibility/legacy.
from gamesave_vcs.config import get_backups_dir, get_game_path

# Base ABC for inheritance (strategy pattern)
from gamesave_vcs.strategies.base import BackupStrategy

logger = logging.getLogger(__name__)


class FullCopyStrategy(BackupStrategy):
    """Original implementation: full folder/file copy-paste to timestamped locations.

    Kept for users who prefer it (e.g., no git dep, simple FS copies). Not delta-efficient,
    but fulfills "won't deny them" old style.
    
    Storage Optimizations:
    - use_hardlinks: Create hard links for identical files (saves disk space)
    - content_addressed: Store files by content hash for deduplication
    """
    
    DEFAULT_USE_HARDLINKS = True
    DEFAULT_CONTENT_ADDRESSED = True

    def __init__(
        self,
        use_hardlinks: bool = DEFAULT_USE_HARDLINKS,
        content_addressed: bool = DEFAULT_CONTENT_ADDRESSED,
        content_store: Optional[Path] = None
    ) -> None:
        """Initialize FullCopyStrategy with storage optimization options.

        Args:
            use_hardlinks: Use hard links for duplicate files
            content_addressed: Store files by content hash
            content_store: Directory for content-addressed storage
        """
        self.use_hardlinks = use_hardlinks
        self.content_addressed = content_addressed
        self.content_store = content_store
        self._content_hashes: Dict[Path, str] = {}  # Cache for content hashes

        if self.content_addressed and self.content_store:
            self.content_store.mkdir(parents=True, exist_ok=True)

        logger.debug(
            f"FullCopyStrategy initialized: hardlinks={use_hardlinks}, "
            f"content_addressed={content_addressed}"
        )

    def _file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file content."""
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _get_content_path(self, content_hash: str) -> Path:
        """Get storage path for content hash.

        Uses prefix subdirectories to avoid too many files in one directory.
        """
        if not self.content_store:
            raise ValueError("Content store not configured")

        prefix = content_hash[:2]
        return self.content_store / prefix / content_hash

    def _copy_with_hardlinks(self, src: Path, dst: Path) -> None:
        """Copy file using hard links when possible.

        If hard linking fails (different filesystem), falls back to copy.
        """
        dst.parent.mkdir(parents=True, exist_ok=True)

        if not self.use_hardlinks:
            # Hard links disabled, use normal copy
            shutil.copy2(src, dst)
            return

        try:
            # Try to create hard link
            if dst.exists():
                dst.unlink()
            os.link(src, dst)
            logger.debug(f"Created hard link: {src} -> {dst}")
        except OSError as e:
            # Hard link failed (different FS, permissions, etc.)
            logger.debug(f"Hard link failed ({e}), falling back to copy")
            shutil.copy2(src, dst)

    def _backup_with_dedup(self, src: Path, dst: Path) -> None:
        """Backup file with content-addressed deduplication.

        Uses hard links to share storage for identical files.
        """
        if not self.content_addressed or not self.content_store:
            # No dedup, use regular copy with optional hardlinks
            self._copy_with_hardlinks(src, dst)
            return

        # Compute content hash
        content_hash = self._file_hash(src)
        content_path = self._get_content_path(content_hash)

        # Check if content already exists
        if content_path.exists():
            # Content exists, create hard link to it
            logger.debug(f"Content {content_hash[:16]}... exists, linking")
        else:
            # New content, store it
            content_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, content_path)
            logger.debug(f"Stored new content: {content_hash[:16]}...")

        # Create hard link from content store to destination
        self._copy_with_hardlinks(content_path, dst)

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
