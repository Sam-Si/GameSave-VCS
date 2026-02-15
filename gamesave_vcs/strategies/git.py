"""GitStrategy implementation (default, Dulwich pure-Python for delta backups).

PEP 8 compliant: single class per file in strategies subpackage.
Efficient VCS deltas; no host Git/subprocess; extensible base.
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union

# Dulwich for pure-Python Git (no host binary/subprocess dep)
import dulwich.porcelain as porcelain
from dulwich.repo import Repo

# Internal: base ABC , config (relative in subpkg)
from ..config import get_backups_dir, get_game_path
from .base import BackupStrategy


class GitStrategy(BackupStrategy):
    """Git-based strategy (default, powered by Dulwich pure-Python lib): efficient delta backups.

    No subprocess or host Git binary required--Dulwich provides full Git impl in Python.
    Figures delta between previous save and now (stores diffs, compression, history).
    Much better than full copy-paste for repeated saves. Keeps full history, cheap restore.
    Per-game repo at ~/.gamesave-vcs/backups/<game>/
    """

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
        # backup_spec = f"{repo_dir}@{commit_hash}"  # for doc
        print(
            f"Backed up {game_name} save to git repo {repo_dir} at commit {commit_hash} (git strategy)"
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
