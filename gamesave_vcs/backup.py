import hashlib
import shutil
import os
import subprocess
from pathlib import Path
from datetime import datetime
from abc import ABC, abstractmethod
# Import from config for strategy dispatch and backend
from .config import (
    get_backups_dir,
    get_game_path,
    get_game_backend,
    get_game_config,
    load_config,
)

def get_save_hash(save_path):
    save_path = Path(save_path)
    hasher = hashlib.sha256()
    if save_path.is_file():
        with open(save_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hasher.update(chunk)
    elif save_path.is_dir():
        for root, dirs, files in os.walk(save_path, followlinks=False):
            for name in sorted(files):
                fpath = Path(root) / name
                rel = fpath.relative_to(save_path)
                hasher.update(str(rel).encode())
                with open(fpath, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b''):
                        hasher.update(chunk)
    return hasher.hexdigest()

# Strategy pattern for extensible backup backends
# Allows full-copy (legacy, entire copy-paste) and git (default: delta-based via commits)
# This makes implementation extensible (add more strategies easily) and efficient by default.
class BackupStrategy(ABC):
    """Abstract base class for backup strategies.
    Enables supporting both full folder copy and git-style deltas.
    """

    @abstractmethod
    def backup_save(self, game_name: str):
        """Backup the game's save. Returns backup location (Path) or None.
        Called by watcher/CLI on change.
        """
        pass

    @abstractmethod
    def list_saves(self, game_name: str = None) -> list:
        """List saves/backups. Returns list of (datetime, spec, game_name).
        spec: Path for full-copy, 'repo@commit' str for git.
        Supports game=None for aggregate.
        """
        pass

    @abstractmethod
    def restore_save(self, backup_spec) -> bool:
        """Restore from backup_spec.
        Parses spec to apply strategy-specific restore.
        """
        pass


class FullCopyStrategy(BackupStrategy):
    """Original implementation: full folder/file copy-paste to timestamped locations.
    Kept for users who prefer it (e.g., no git dep, simple FS copies). Not delta-efficient,
    but fulfills "won't deny them" old style.
    """

    def backup_save(self, game_name):
        """Exact original backup logic for full copy."""
        save_path = get_game_path(game_name)
        if not save_path or not Path(save_path).exists():
            print(f"Backup skipped for {game_name}: save path not found (nothing to backup yet)")
            return None
        save_path = Path(save_path)
        backup_dir = get_backups_dir() / game_name
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{timestamp}_{save_path.name}"
        backup_path = backup_dir / backup_name
        if save_path.is_file():
            shutil.copy2(save_path, backup_path)
        elif save_path.is_dir():
            if backup_path.exists():
                shutil.rmtree(backup_path)
            shutil.copytree(save_path, backup_path)
        print(f"Backed up {game_name} save to {backup_path} (full-copy)")
        return backup_path

    def _list_saves_for_game(self, game_dir: Path, game_name: str) -> list:
        """Helper: parse timestamped files/dirs for full-copy (legacy)."""
        saves = []
        if not game_dir.exists():
            return saves
        for f in game_dir.iterdir():
            # Skip git internals like .git to prevent parse errors
            if f.name.startswith('.'):
                continue
            if f.is_file() or f.is_dir():
                try:
                    parts = f.name.split('_')
                    ts_str = '_'.join(parts[:2])
                    ts = datetime.strptime(ts_str, '%Y%m%d_%H%M%S')
                    saves.append((ts, f, game_name))
                except ValueError:
                    pass
        return saves

    def list_saves(self, game_name=None):
        """Original list_saves logic, adapted to skip git dirs/files for clean legacy support.
        Handles mixed repos in aggregate.
        """
        saves = []
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
                    if not (game_dir / '.git').exists():
                        saves.extend(self._list_saves_for_game(game_dir, game_dir.name))
        saves.sort(key=lambda x: x[0], reverse=True)
        return saves

    def restore_save(self, backup_spec) -> bool:
        """Original restore logic, adapted for backup_spec (Path/str).
        Used for full-copy or legacy backups.
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
        if backup_path.is_dir():
            if save_path.exists():
                if save_path.is_dir():
                    shutil.rmtree(save_path)
                else:
                    save_path.unlink()
            save_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(backup_path, save_path)
        else:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup_path, save_path)
        print(f"Restored {backup_path} to {save_path} (full-copy)")
        return True


class GitStrategy(BackupStrategy):
    """Git-based strategy (default): efficient delta backups by committing changes.
    Figures delta between previous save and now via git (stores diffs, compression, history).
    Much better than full copy-paste for repeated saves. Keeps full history, cheap restore.
    Per-game repo at ~/.gamesave-vcs/backups/<game>/
    """

    def _run_git(self, repo_dir: Path, *args) -> str:
        """Run git cmd in repo cwd, return stdout. Handles 'no changes' gracefully."""
        try:
            result = subprocess.run(
                ['git', *args],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.strip() if hasattr(e, 'stderr') and e.stderr else ''
            # Robust catch for no changes (stderr may vary slightly; case/words)
            if 'nothing to commit' in stderr.lower() or 'no changes added' in stderr.lower() or 'working tree clean' in stderr.lower():
                return ''
            raise RuntimeError(f"Git failed: {' '.join(args)} -> {stderr}") from e

    def _ensure_repo(self, repo_dir: Path) -> Path:
        """Init git if needed, config user for headless/CI/tests, use main branch."""
        repo_dir.mkdir(parents=True, exist_ok=True)
        if not (repo_dir / '.git').exists():
            self._run_git(repo_dir, 'init')
            # Dummy config avoids "no author" errors
            self._run_git(repo_dir, 'config', 'user.email', 'gamesave-vcs@example.com')
            self._run_git(repo_dir, 'config', 'user.name', 'GameSave-VCS')
            # Modern git compat (init may default main/master)
            self._run_git(repo_dir, 'branch', '-M', 'main')
        return repo_dir

    def _get_content_path(self, repo_dir: Path, save_path: Path) -> Path:
        """Save content stored under repo/<original_save_basename> to mirror structure."""
        return repo_dir / save_path.name

    def backup_save(self, game_name):
        """Backup via git: sync save to repo working tree, commit.
        Delta efficiency: git stores only changes vs previous commit (binary/text diffs).
        Full copy only for initial sync; git handles versioning.
        """
        save_path_str = get_game_path(game_name)
        if not save_path_str or not Path(save_path_str).exists():
            print(f"Backup skipped for {game_name}: save path not found (nothing to backup yet)")
            return None
        save_path = Path(save_path_str)
        repo_dir = get_backups_dir() / game_name
        self._ensure_repo(repo_dir)
        content_path = self._get_content_path(repo_dir, save_path)
        # Sync to repo (file/dir copy; git will delta it)
        if save_path.is_file():
            shutil.copy2(save_path, content_path)
        elif save_path.is_dir():
            if content_path.exists():
                shutil.rmtree(content_path)
            shutil.copytree(save_path, content_path)
        # Stage all (handles add/update/delete)
        self._run_git(repo_dir, 'add', '-A')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        commit_msg = f"Backup {timestamp} for {game_name}"
        # Commit the delta (handled gracefully in _run_git if no changes)
        self._run_git(repo_dir, 'commit', '-m', commit_msg)
        commit_hash = self._run_git(repo_dir, 'rev-parse', 'HEAD')
        backup_spec = f"{repo_dir}@{commit_hash}"
        print(f"Backed up {game_name} save to git repo {repo_dir} at commit {commit_hash} (git strategy)")
        return repo_dir  # API compat (repo Path)

    def list_saves(self, game_name: str = None) -> list:
        """List git commits as "saves": parse log for ts/hash.
        backup_spec='repo@commit' encodes for restore dispatch.
        """
        if game_name is None:
            # Per-game only; aggregate in top-level
            return []
        saves = []
        repo_dir = get_backups_dir() / game_name
        if not (repo_dir / '.git').exists():
            return saves
        try:
            # Format: unix_ts hash msg ; reverse chrono? oldest first, sort top
            log_output = self._run_git(
                repo_dir, 'log', '--pretty=format:%at %H %s', '--reverse'
            )
            if log_output:
                for line in log_output.splitlines():
                    if line.strip():
                        parts = line.split(' ', 2)
                        if len(parts) >= 2:
                            ts_unix = int(parts[0])
                            commit_hash = parts[1]
                            ts = datetime.fromtimestamp(ts_unix)
                            backup_spec = f"{repo_dir}@{commit_hash}"
                            saves.append((ts, backup_spec, game_name))
        except Exception as e:
            # Empty repo/no commits or rare git err: graceful
            pass
        return saves

    def restore_save(self, backup_spec) -> bool:
        """Restore: parse repo@commit, git reset --hard to snapshot, then copy to save_path.
        Delta efficient: git reconstructs exact state from history.
        """
        # Expect str 'repo@commit' from list/git backup
        spec_str = str(backup_spec)
        if '@' not in spec_str:
            print("Invalid git backup spec (expected repo@commit)")
            return False
        repo_str, commit_hash = spec_str.split('@', 1)
        repo_dir = Path(repo_str)
        game_name = repo_dir.name
        if not (repo_dir / '.git').exists():
            print("Git repo not found")
            return False
        save_path_str = get_game_path(game_name)
        if not save_path_str:
            print("Game not found")
            return False
        save_path = Path(save_path_str)
        try:
            # Reset to commit: applies the historical delta state to working tree
            # --hard ensures clean (no merge)
            self._run_git(repo_dir, 'reset', '--hard', commit_hash)
            # Content now at content_path in repo
            content_path = self._get_content_path(repo_dir, save_path)
            if not content_path.exists():
                print(f"No content at {content_path} for restore")
                return False
            # Copy to live save (unified file/dir logic)
            if content_path.is_dir():
                if save_path.exists():
                    if save_path.is_dir():
                        shutil.rmtree(save_path)
                    else:
                        save_path.unlink()
                save_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(content_path, save_path)
            else:
                save_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(content_path, save_path)
            print(f"Restored commit {commit_hash} from {repo_dir} to {save_path} (git strategy)")
            return True
        except Exception as e:
            print(f"Git restore failed: {e}")
            return False


# Dispatch helpers for extensibility
def detect_strategy(game_name: str) -> BackupStrategy:
    """Detect from FS (e.g. .git dir) for legacy/mixed/backward compat.
    Full-copy if no git repo found.
    """
    backups_dir = get_backups_dir()
    game_dir = backups_dir / game_name
    if (game_dir / '.git').exists():
        return GitStrategy()
    return FullCopyStrategy()


def get_strategy(game_name: str) -> BackupStrategy:
    """Main dispatcher: uses config backend (default 'git') or FS detect.
    Makes system extensible to future strategies (e.g., rsync, zfs).
    """
    backend = get_game_backend(game_name)
    if backend == 'git':
        return GitStrategy()
    elif backend == 'full-copy':
        return FullCopyStrategy()
    else:
        # Fallback for legacy no-config
        return detect_strategy(game_name)


# Top-level public API - unchanged for CLI/watcher/tests compat
# Dispatches to strategy based on per-game config or detect
def backup_save(game_name):
    """Dispatch to game's backend strategy for backup.
    Default: git for delta efficiency; configurable to full-copy.
    """
    strategy = get_strategy(game_name)
    return strategy.backup_save(game_name)


def list_saves(game_name=None):
    """Aggregate list supporting mixed strategies (git/full-copy) + legacy backups.
    game=None: scan all; else dispatch to strategy.
    Ensures old full-copy backups still listable if present.
    """
    saves = []
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


def restore_save(backup_spec=None):
    """Dispatch restore to appropriate strategy based on spec/game.
    Auto-latest works across backends; parses spec (Path vs repo@commit).
    Backward compat for old backup paths.
    """
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
    if '@' in spec_str:
        # git style
        repo_str, _ = spec_str.split('@', 1)
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
