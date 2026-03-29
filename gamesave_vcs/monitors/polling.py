"""Polling-based file monitor fallback.

Layer 1 fallback: Uses metadata polling when native events unavailable.
Implements Layer 2 (metadata-first) and Layer 3 (I/O scheduling).
"""

import os
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from gamesave_vcs.monitors.base import FileMonitor


def _lower_thread_priority() -> None:
    """Lower thread priority to reduce impact on game performance.
    
    Layer 3: I/O scheduling optimization.
    """
    try:
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.kernel32.SetThreadPriority(
                ctypes.windll.kernel32.GetCurrentThread(), 1
            )  # THREAD_PRIORITY_LOWEST
        else:
            os.nice(10)  # Lower priority (higher nice value)
    except Exception:
        pass  # Best effort


def _get_file_metadata(path: Path) -> tuple[int, int]:
    """Get file metadata (mtime, size) for fast change detection.
    
    Layer 2: Metadata-first change detection.
    Returns (0, 0) if path doesn't exist.
    """
    try:
        st = path.stat()
        return (int(st.st_mtime), st.st_size)
    except (OSError, IOError):
        return (0, 0)


def _get_dir_metadata(path: Path) -> dict[str, tuple[int, int]]:
    """Get metadata for all files in directory recursively.
    
    Layer 2: Metadata-first change detection.
    Returns dict of relative_path -> (mtime, size).
    """
    metadata = {}
    try:
        for root, dirs, files in os.walk(path):
            for name in files:
                try:
                    fpath = Path(root) / name
                    rel = str(fpath.relative_to(path))
                    st = fpath.stat()
                    metadata[rel] = (int(st.st_mtime), st.st_size)
                except (OSError, IOError):
                    continue
    except (OSError, IOError):
        pass
    return metadata


class PollingMonitor(FileMonitor):
    """Polling-based file monitor using metadata-first detection.
    
    Fallback implementation when native event monitoring is unavailable.
    Uses mtime/size metadata to detect changes without reading file contents.
    """

    def __init__(self, poll_interval: float = 1.0) -> None:
        """Initialize polling monitor.
        
        Args:
            poll_interval: Seconds between polls (default: 1.0)
        """
        self.poll_interval = poll_interval
        self._path: Optional[Path] = None
        self._callback: Optional[Callable[[Path], None]] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._last_file_meta: tuple[int, int] = (0, 0)
        self._last_dir_meta: Optional[dict[str, tuple[int, int]]] = None

    def start(self, path: Path, callback: Callable[[Path], None]) -> None:
        """Start polling the path for changes."""
        self._path = path
        self._callback = callback
        self._running = True

        # Capture initial metadata
        if path.is_file():
            self._last_file_meta = _get_file_metadata(path)
        elif path.is_dir():
            self._last_dir_meta = _get_dir_metadata(path)

        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop polling."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _poll_loop(self) -> None:
        """Main polling loop with metadata-first detection."""
        _lower_thread_priority()

        while self._running:
            time.sleep(self.poll_interval)

            if not self._path or not self._path.exists():
                continue

            # Check for changes using metadata (fast, no disk reads)
            changed = self._check_metadata_changed()

            if changed and self._callback:
                self._callback(self._path)

    def _check_metadata_changed(self) -> bool:
        """Check if metadata changed - fast, no file content reads."""
        if not self._path:
            return False

        if self._path.is_file():
            current_meta = _get_file_metadata(self._path)
            if current_meta != self._last_file_meta:
                self._last_file_meta = current_meta
                return True
            return False

        elif self._path.is_dir():
            current_meta = _get_dir_metadata(self._path)
            if self._last_dir_meta is None:
                self._last_dir_meta = current_meta
                return True
            if set(current_meta.keys()) != set(self._last_dir_meta.keys()):
                self._last_dir_meta = current_meta
                return True
            if current_meta != self._last_dir_meta:
                self._last_dir_meta = current_meta
                return True
            return False

        return False
