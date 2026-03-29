"""GitStrategy implementation (default, Dulwich pure-Python for delta backups).

PEP 8 compliant: single class per file in strategies subpackage.
Efficient VCS deltas; no host Git/subprocess; extensible base.

Storage Optimizations:
- Retention policy: Limits number of commits to prevent unbounded growth
- Garbage collection: Periodic GC to reclaim space from old objects
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union

# Dulwich for pure-Python Git (no host binary/subprocess dep)
import dulwich.porcelain as porcelain
from dulwich.repo import Repo

# Internal imports refactored to absolute for Bazel compatibility.
# Dulwich GitStrategy (default delta backend) now importable under Bazel.
# See base.py for details; no change to pure-Python VCS logic.
from gamesave_vcs.config import get_backups_dir, get_game_path
from gamesave_vcs.strategies.base import BackupStrategy

logger = logging.getLogger(__name__)


class GitStrategy(BackupStrategy):
    """Git-based strategy (default, powered by Dulwich pure-Python lib): efficient delta backups.

    No subprocess or host Git binary required--Dulwich provides full Git impl in Python.
    Figures delta between previous save and now (stores diffs, compression, history).
    Much better than full copy-paste for repeated saves. Keeps full history, cheap restore.
    Per-game repo at ~/.gamesave-vcs/backups/<game>/
    
    Storage Optimizations:
    - retention_count: Maximum number of commits to keep (0 = unlimited)
    - gc_interval: Run GC every N backups (0 = never)
    """
    
    DEFAULT_RETENTION_COUNT = 20  # Keep last 20 backups by default
    DEFAULT_GC_INTERVAL = 10  # GC every 10 backups
    
    def __init__(
        self,
        retention_count: int = DEFAULT_RETENTION_COUNT,
        gc_interval: int = DEFAULT_GC_INTERVAL
    ) -> None:
        """Initialize GitStrategy with storage optimization settings.
        
        Args:
            retention_count: Maximum commits to keep (0 = unlimited)
            gc_interval: Run GC every N backups (0 = never)
        """
        self.retention_count = retention_count
        self.gc_interval = gc_interval
        self._backup_count = 0  # Track backups for GC interval
        logger.debug(
            f"GitStrategy initialized: retention={retention_count}, gc_interval={gc_interval}"
        )

    def _ensure_repo(self, repo_dir: Path) -> Path:
        """Init repo if needed using Dulwich porcelain; set user config for author/commit."""
        repo_dir.mkdir(parents=True, exist_ok=True)
        if not (repo_dir / ".git").exists():
            porcelain.init(str(repo_dir))
            # Dulwich repo to set config (avoids author errors , headless/CI)
            r = Repo(str(repo_dir))
            c = r.get_config()
            c.set(("user",), "email", "gamesave-vcs@example.com")
            c.set(("user",), "name", "GameSave-VCS")
            c.write_to_path()
            # Default branch handling by Dulwich ok (main/master compat)
        return repo_dir

    def _get_content_path(self, repo_dir: Path, save_path: Path) -> Path:
        """Save content stored under repo/<original_save_basename> to mirror structure."""
        return repo_dir / save_path.name

    def _apply_retention(self, repo_dir: Path, keep_count: int) -> None:
        """Apply retention policy - keep only the most recent N commits.
        
        Args:
            repo_dir: Path to git repository
            keep_count: Number of commits to keep
        """
        if keep_count <= 0:
            return
        
        try:
            r = Repo(str(repo_dir))
            commits = list(r.get_walker(max_entries=None))
            
            total_commits = len(commits)
            if total_commits <= keep_count:
                logger.debug(
                    f"Retention: {total_commits} commits, keeping all (limit: {keep_count})"
                )
                return
            
            # Get the commit to reset to (the keep_count-th most recent)
            # commits are returned newest first
            target_commit = commits[keep_count - 1].commit
            target_id = target_commit.id
            
            logger.info(
                f"Applying retention: {total_commits} commits -> {keep_count} commits"
            )
            
            # Reset to the target commit (discarding newer commits)
            # This effectively prunes the history
            porcelain.reset(
                str(repo_dir),
                treeish=target_id,
                mode="hard"
            )
            
            logger.info(f"Retention applied: kept last {keep_count} commits")
            
        except Exception as e:
            logger.warning(f"Retention policy failed: {e}")
            # Don't fail the backup if retention fails

    def _prune_old_commits(self, repo_dir: Path) -> None:
        """Public method to prune old commits based on retention policy."""
        if self.retention_count > 0:
            self._apply_retention(repo_dir, self.retention_count)

    def _run_gc(self, repo_dir: Path, aggressive: bool = False) -> None:
        """Run git garbage collection to reclaim space.
        
        Args:
            repo_dir: Path to git repository
            aggressive: If True, run aggressive GC for better compression
        """
        try:
            logger.debug(f"Running git gc (aggressive={aggressive})")
            
            # Use dulwich's gc command
            # gc() prunes loose objects and repacks for efficiency
            porcelain.gc(str(repo_dir))
            
            logger.info("Git garbage collection completed")
        except Exception as e:
            logger.warning(f"Git GC failed: {e}")
            # Don't fail the backup if GC fails

    def _maybe_run_gc(self, repo_dir: Path) -> None:
        """Run GC if backup count interval is reached."""
        if self.gc_interval <= 0:
            return
        
        self._backup_count += 1
        
        if self._backup_count >= self.gc_interval:
            logger.debug(f"GC interval reached ({self.gc_interval}), running gc")
            self._run_gc(repo_dir, aggressive=False)
            self._backup_count = 0

    def backup_save(self, game_name: str) -> Optional[Path]:
        """Backup via Dulwich: sync save to repo working tree, commit delta.
        Pure-Python: no subprocess; Dulwich porcelain handles add/commit.
        Delta efficiency: stores only changes vs previous.
        """
        save_path_str = get_game_path(game_name)
        if not save_path_str or not Path(save_path_str).exists():
            print(
                f"Backup skipped for {game_name}: save path not found (nothing to backup yet)"
            )
            return None
        save_path = Path(save_path_str)
        repo_dir = get_backups_dir() / game_name
        self._ensure_repo(repo_dir)
        content_path = self._get_content_path(repo_dir, save_path)
        # Sync to repo working tree (file/dir; Dulwich will delta it)
        if save_path.is_file():
            shutil.copy2(save_path, content_path)
        elif save_path.is_dir():
            if content_path.exists():
                shutil.rmtree(content_path)
            shutil.copytree(save_path, content_path)
        # Dulwich porcelain: stage all , commit (handles add/update/delete; pure Python)
        try:
            # Add all ('.' or list; Dulwich accepts repo path)
            porcelain.add(str(repo_dir))
        except Exception:
            pass  # no-op if no changes
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        commit_msg = f"Backup {timestamp} for {game_name}"
        # Commit with explicit author (Dulwich requires to avoid defaults/errors)
        try:
            porcelain.commit(
                str(repo_dir),
                message=commit_msg.encode(),
                author=b"GameSave-VCS <gamesave-vcs@example.com>",
            )
        except Exception as e:
            # Graceful for no changes (Dulwich raises specific)
            if "no changes" in str(e).lower() or "unchanged" in str(e).lower():
                pass
            else:
                raise
        # Get current commit hash (via Repo)
        r = Repo(str(repo_dir))
        commit_hash = r.head().decode()
        
        # Apply retention policy after backup
        self._prune_old_commits(repo_dir)
        
        # Maybe run GC
        self._maybe_run_gc(repo_dir)
        
        # backup_spec = f"{repo_dir}@{commit_hash}"  # for doc
        print(
            f"Backed up {game_name} save to git repo {repo_dir} at commit {commit_hash} (git strategy)"
        )
        logger.info(
            f"Backup complete for {game_name}: commit={commit_hash}, "
            f"retention={self.retention_count}, gc_interval={self.gc_interval}"
        )
        return repo_dir  # API compat (repo Path)

    def list_saves(
        self, game_name: Optional[str] = None
    ) -> List[tuple[datetime, Union[Path, str], str]]:
        """List git commits as "saves": use Dulwich log walker for ts/hash.
        backup_spec='repo@commit' encodes for restore dispatch.
        Pure-Python replacement for git log.
        """
        if game_name is None:
            # Per-game only; aggregate in top-level
            return []
        saves: List[tuple[datetime, Union[Path, str], str]] = []
        repo_dir = get_backups_dir() / game_name
        if not (repo_dir / ".git").exists():
            return saves
        try:
            # Dulwich: use Repo.get_walker() for commits (porcelain.log walker sometimes empty post-consume; low-level reliable)
            # Oldest first , limit
            r = Repo(str(repo_dir))
            for entry in r.get_walker(max_entries=100):
                if entry.commit:
                    commit = entry.commit
                    ts_unix = commit.commit_time  # unix timestamp
                    commit_hash = commit.id.decode()
                    ts = datetime.fromtimestamp(ts_unix)
                    backup_spec = f"{repo_dir}@{commit_hash}"
                    saves.append((ts, backup_spec, game_name))
        except Exception:
            # Empty repo/no commits or Dulwich err: graceful
            pass
        return saves

    def restore_save(self, backup_spec: Union[str, Path]) -> bool:
        """Restore: parse repo@commit , Dulwich reset --hard to snapshot , then copy to save_path.
        Pure-Python: no subprocess; Dulwich reconstructs state from history.
        """
        # Expect str 'repo@commit' from list/git backup
        spec_str = str(backup_spec)
        if "@" not in spec_str:
            print("Invalid git backup spec (expected repo@commit)")
            return False
        repo_str, commit_hash = spec_str.split("@", 1)
        repo_dir = Path(repo_str)
        game_name = repo_dir.name
        if not (repo_dir / ".git").exists():
            print("Git repo not found")
            return False
        save_path_str = get_game_path(game_name)
        if not save_path_str:
            print("Game not found")
            return False
        save_path = Path(save_path_str)
        try:
            # Dulwich porcelain.reset hard: applies historical delta state to working tree
            porcelain.reset(
                str(repo_dir), treeish=commit_hash.encode(), mode="hard"
            )
            # Content now at content_path in repo
            content_path = self._get_content_path(repo_dir, save_path)
            if not content_path.exists():
                print(f"No content at {content_path} for restore")
                return False
            # Copy to live save (unified file/dir logic , same as full-copy)
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
            print(
                f"Restored commit {commit_hash} from {repo_dir} to {save_path} (git strategy)"
            )
            return True
        except Exception as e:
            print(f"Git restore failed: {e}")
            return False
