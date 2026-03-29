import os
import threading
import time
from pathlib import Path
from typing import Callable, Optional

# Local imports refactored to absolute for Bazel compatibility (see cli.py/backup.py notes).
# Ensures watcher (polling + hash-based change detect, triggers backup) works via CLI or direct.
from gamesave_vcs.backup import backup_save, get_save_hash
from gamesave_vcs.config import get_game_path
from gamesave_vcs.monitors import get_file_monitor
from gamesave_vcs.monitors.base import FileMonitor


def _get_file_metadata(path: Path) -> tuple[int, int]:
    """Get file metadata (mtime, size) for fast change detection.
    Returns (0, 0) if path doesn't exist.
    """
    try:
        # Use path.stat() for Path objects to avoid follow_symlinks issues
        st = path.stat()
        return (int(st.st_mtime), st.st_size)
    except (OSError, IOError):
        return (0, 0)


def _get_dir_metadata(path: Path) -> dict[str, tuple[int, int]]:
    """Get metadata for all files in directory recursively.
    Returns dict of relative_path -> (mtime, size).
    """
    metadata = {}
    try:
        for root, dirs, files in os.walk(path):
            # Limit walk depth for performance on large directories
            for name in files:
                try:
                    fpath = Path(root) / name
                    rel = str(fpath.relative_to(path))
                    # Use path.stat() for Path objects
                    st = fpath.stat()
                    metadata[rel] = (int(st.st_mtime), st.st_size)
                except (OSError, IOError):
                    continue
    except (OSError, IOError):
        pass
    return metadata


def _metadata_changed(save_path: Path, last_file_meta: tuple[int, int],
                      last_dir_meta: Optional[dict]) -> tuple[bool, tuple[int, int], Optional[dict]]:
    """Check if metadata changed - much faster than full hash.
    Returns (changed, new_file_meta, new_dir_meta).
    """
    if save_path.is_file():
        current_meta = _get_file_metadata(save_path)
        return (current_meta != last_file_meta, current_meta, None)
    elif save_path.is_dir():
        current_meta = _get_dir_metadata(save_path)
        # Quick check: compare dict keys first, then values
        if last_dir_meta is None:
            return (True, (0, 0), current_meta)
        if set(current_meta.keys()) != set(last_dir_meta.keys()):
            return (True, (0, 0), current_meta)
        if current_meta != last_dir_meta:
            return (True, (0, 0), current_meta)
        return (False, (0, 0), last_dir_meta)
    return (False, (0, 0), last_dir_meta)


class GameWatcher:
    """Watcher for game save changes using optimized metadata + lazy hash; triggers backup.
    
    Optimized to minimize disk I/O and prevent game stutters:
    - Uses platform-native file monitoring (inotify on Linux) when available
    - Falls back to metadata-based polling on other platforms
    - Only computes SHA256 hash when changes are confirmed
    - Uses adaptive polling intervals for fallback mode
    """

    def __init__(self, game_name: str, interval: float | int = 5) -> None:
        """Init watcher; save_path from config (may be None if game unknown)."""
        self.game_name: str = game_name
        self.interval: float | int = interval
        self.running: bool = False
        self.thread: Optional[threading.Thread] = None
        self.last_hash: Optional[str] = None
        self.save_path: Optional[str] = get_game_path(game_name)
        # Metadata-based tracking (fast, no disk reads)
        self._last_file_meta: tuple[int, int] = (0, 0)
        self._last_dir_meta: Optional[dict] = None
        self._consecutive_no_change: int = 0
        self._current_interval: float = float(interval)
        # Platform monitor (Layer 1)
        self._monitor: Optional[FileMonitor] = None
        self._use_platform_monitor: bool = True

    def _get_monitor(self) -> FileMonitor:
        """Get or create platform-specific file monitor.
        
        Layer 1: Platform-specific file system event monitoring.
        """
        if self._monitor is None:
            self._monitor = get_file_monitor()
        return self._monitor

    def _on_file_changed(self, path: Path) -> None:
        """Callback for platform monitor when file changes detected.
        
        Layer 2: Verify change with hash before triggering backup.
        """
        if not self.running:
            return

        save_path = Path(self.save_path) if self.save_path else None
        if not save_path or not save_path.exists():
            return

        # Verify with hash (Layer 2 confirmation)
        current_hash = get_save_hash(save_path)
        if current_hash != self.last_hash:
            print(f"Change detected in {self.game_name} save")
            backup_save(self.game_name)
            self.last_hash = current_hash

    def _lower_thread_priority(self) -> None:
        """Lower thread priority to reduce impact on game performance."""
        try:
            import sys
            if sys.platform == "win32":
                # Windows: lower priority class
                import ctypes
                ctypes.windll.kernel32.SetThreadPriority(
                    ctypes.windll.kernel32.GetCurrentThread(), 1
                )  # THREAD_PRIORITY_LOWEST
            else:
                # Unix/Linux/macOS: nice value
                os.nice(10)  # Lower priority (higher nice value)
        except Exception:
            pass  # Best effort - continue even if priority change fails

    def start(self) -> None:
        """Start watcher thread if save_path valid.
        
        Attempts to use platform-native monitoring (Layer 1), 
        falls back to polling loop if unavailable.
        """
        if self.save_path is None:
            print("Game not found")
            return
        
        self.running = True
        save_path = Path(self.save_path)
        
        # Try platform monitor first (Layer 1)
        if self._use_platform_monitor:
            try:
                monitor = self._get_monitor()
                # Capture initial hash
                self.last_hash = get_save_hash(save_path)
                # Start platform monitor
                monitor.start(save_path, self._on_file_changed)
                print(f"Started watcher for {self.game_name} (platform-native)")
                return
            except Exception as e:
                # Fall back to polling
                self._use_platform_monitor = False
                print(f"Platform monitor unavailable ({e}), using fallback polling")
        
        # Fallback: use polling loop
        self.thread = threading.Thread(target=self._watch_loop, daemon=True)
        self.thread.start()
        print(f"Started watcher for {self.game_name} (optimized, low-impact)")

    def stop(self) -> None:
        """Stop watcher and join thread."""
        self.running = False
        
        # Stop platform monitor if used
        if self._use_platform_monitor and self._monitor:
            self._monitor.stop()
        
        if self.thread:
            self.thread.join()
        print(f"Stopped watcher for {self.game_name}")

    def _adaptive_interval(self) -> float:
        """Calculate adaptive polling interval.
        Increases interval when no changes detected to reduce CPU/disk usage.
        """
        if self._consecutive_no_change > 10:
            # Max 4x the base interval after many no-changes
            return min(self._current_interval * 1.05, float(self.interval) * 4)
        return float(self.interval)

    def _check_change_fast(self, save_path: Path) -> bool:
        """Fast change check using metadata only (no disk reads).
        Returns True if change detected, False otherwise.
        Updates metadata state.
        """
        changed, new_file_meta, new_dir_meta = _metadata_changed(
            save_path, self._last_file_meta, self._last_dir_meta
        )
        
        if save_path.is_file():
            self._last_file_meta = new_file_meta
        else:
            self._last_dir_meta = new_dir_meta
            
        return changed

    def _watch_loop(self) -> None:
        """Internal loop: optimized polling with metadata-first detection.
        Uses mtime/size for fast checks, only hashes when necessary.
        Daemon, runs until stop().
        """
        if self.save_path is None:
            return
        
        # Lower priority to reduce game impact
        self._lower_thread_priority()
        
        save_path = Path(self.save_path)
        if not save_path.exists():
            print("Save path does not exist")
            return
        
        # Initial metadata and hash capture
        if save_path.is_file():
            self._last_file_meta = _get_file_metadata(save_path)
        else:
            self._last_dir_meta = _get_dir_metadata(save_path)
        self.last_hash = get_save_hash(save_path)
        
        while self.running:
            time.sleep(self._current_interval)
            
            if not save_path.exists():
                continue
            
            # PHASE 1: Fast metadata check (no disk reads)
            metadata_changed = self._check_change_fast(save_path)
            
            if not metadata_changed:
                self._consecutive_no_change += 1
                self._current_interval = self._adaptive_interval()
                continue
            
            # PHASE 2: Metadata changed - need full hash to confirm
            self._consecutive_no_change = 0
            self._current_interval = float(self.interval)
            
            current_hash = get_save_hash(save_path)
            if current_hash != self.last_hash:
                print(f"Change detected in {self.game_name} save")
                backup_save(self.game_name)
                self.last_hash = current_hash
