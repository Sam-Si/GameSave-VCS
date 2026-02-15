import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union

# PEP 8: sorted stdlib, then local.
# Strategy logic split to gamesave_vcs/strategies/ subpackage (single class/file for extensibility).
# Dispatch in base.py ; re-export here for compat.
# ensure_dirs for robustness (tests patching get_*).
from .config import ensure_dirs, get_backups_dir, get_game_path, load_config

# get_strategy re-exported from strategies; BackupStrategy unused here (internal to subpkg)
from .strategies.base import get_strategy


def get_save_hash(save_path: Union[str, Path]) -> str:
    """Compute SHA256 hash of file or recursive dir contents (sorted for determinism).
    Used by watcher for change detection.
    """
    save_path = Path(save_path)
    hasher = hashlib.sha256()
    if save_path.is_file():
        with open(save_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
    elif save_path.is_dir():
        for root, dirs, files in os.walk(save_path, followlinks=False):
            for name in sorted(files):
                fpath = Path(root) / name
                rel = fpath.relative_to(save_path)
                hasher.update(str(rel).encode())
                with open(fpath, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hasher.update(chunk)
    return hasher.hexdigest()


# Strategy pattern moved to gamesave_vcs/strategies/ subpackage (single class/file per entity per PEP 8).
# ABC in base.py; impls in full_copy.py, git.py for maintainability/extensibility.
# (See strategies/__init__.py for re-exports)


# GitStrategy and dispatch helpers moved to strategies/ subpackage (PEP 8: single class/file).
# See base.py (ABC/dispatch), full_copy.py, git.py for details.


# Top-level public API - unchanged for CLI/watcher/tests compat
# Dispatches to strategy (in subpkg) based on per-game config or detect
# Ensures extensibility/maintainability per request.
def backup_save(game_name: str) -> Optional[Path]:
    """Dispatch to game's backend strategy for backup.
    Default: git for delta efficiency; configurable to full-copy.
    Calls ensure_dirs for robustness (tests patching config funcs).
    """
    ensure_dirs()
    strategy = get_strategy(game_name)
    return strategy.backup_save(game_name)


def list_saves(
    game_name: Optional[str] = None,
) -> List[tuple[datetime, Union[Path, str], str]]:
    """Aggregate list supporting mixed strategies (git/full-copy) + legacy backups.
    game=None: scan all; else dispatch to strategy.
    Ensures old full-copy backups still listable if present.
    Calls ensure_dirs for robustness.
    """
    ensure_dirs()
    saves: List[tuple[datetime, Union[Path, str], str]] = []
    backups_dir = get_backups_dir()
    if not backups_dir.exists():
        return saves
    if game_name:
        # Dispatch for specific game
        strategy = get_strategy(game_name)
        saves = strategy.list_saves(game_name)
    else:
        # Collect games: from config + FS dirs (robust for mixed/legacy)
        config = load_config()
        game_names = set(config.keys())
        # Add dirs for legacy full-copy without config entry
        for d in backups_dir.iterdir():
            if d.is_dir():
                game_names.add(d.name)
        for gname in game_names:
            try:
                strategy = get_strategy(gname)
                saves.extend(strategy.list_saves(gname))
            except Exception:
                # Skip bad/empty to prevent test/UX break
                continue
    # Always reverse chrono sort
    saves.sort(key=lambda x: x[0], reverse=True)
    return saves


def restore_save(backup_spec: Optional[Union[str, Path]] = None) -> bool:
    """Dispatch restore to appropriate strategy based on spec/game.
    Auto-latest works across backends; parses spec (Path vs repo@commit).
    Backward compat for old backup paths.
    Calls ensure_dirs for robustness (tests patching get_*).
    """
    ensure_dirs()
    if not backup_spec:
        saves = list_saves()
        if not saves:
            print("No backups found")
            return False
        backup_spec = saves[0][1]  # Path or str spec
        game_name = saves[0][2]
        print(f"Auto-restoring latest: {backup_spec}")
    # Infer game_name from spec for dispatch
    spec_str = str(backup_spec)
    if "@" in spec_str:
        # git style
        repo_str, _ = spec_str.split("@", 1)
        game_name = Path(repo_str).name
    else:
        # full-copy: backup item path
        backup_path = Path(backup_spec)
        game_name = backup_path.parent.name
    # Game must be determinable and exist (for invalid/legacy specs)
    if not game_name or not get_game_path(game_name):
        print("Backup not found")
        return False
    strategy = get_strategy(game_name)
    return strategy.restore_save(backup_spec)
