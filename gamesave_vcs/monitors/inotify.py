"""Linux inotify-based file monitor.

Layer 1: Native Linux file system event monitoring using inotify.
Zero polling, kernel-level change detection for minimal overhead.
"""

import ctypes
import ctypes.util
import os
import select
import struct
import sys
import threading
from pathlib import Path
from typing import Callable, Dict, Optional

if sys.platform != "linux":
    raise ImportError("InotifyMonitor is only available on Linux.")

from gamesave_vcs.monitors.base import FileMonitor

# inotify constants
IN_MODIFY = 0x00000002
IN_ATTRIB = 0x00000004
IN_CLOSE_WRITE = 0x00000008
IN_MOVED_FROM = 0x00000040
IN_MOVED_TO = 0x00000080
IN_CREATE = 0x00000100
IN_DELETE = 0x00000200
IN_DELETE_SELF = 0x00000400
IN_MOVE_SELF = 0x00000800

IN_WATCH_MASK = (
    IN_MODIFY
    | IN_ATTRIB
    | IN_CLOSE_WRITE
    | IN_MOVED_FROM
    | IN_MOVED_TO
    | IN_CREATE
    | IN_DELETE
    | IN_DELETE_SELF
    | IN_MOVE_SELF
)

# struct inotify_event header size
EVENT_HEADER_SIZE = struct.calcsize("iIII")

# Load libc for inotify functions
_libc = None
if sys.platform == "linux":
    try:
        libc_path = ctypes.util.find_library("c")
        if libc_path:
            _libc = ctypes.CDLL(libc_path, use_errno=True)
    except Exception:
        pass


def _inotify_init() -> int:
    """Initialize inotify instance."""
    if _libc is None:
        raise OSError("libc not available")
    fd = _libc.inotify_init()
    if fd < 0:
        errno = ctypes.get_errno()
        raise OSError(errno, os.strerror(errno))
    return fd


def _inotify_add_watch(fd: int, path: str, mask: int) -> int:
    """Add watch to inotify instance."""
    if _libc is None:
        raise OSError("libc not available")
    wd = _libc.inotify_add_watch(fd, path.encode("utf-8"), mask)
    if wd < 0:
        errno = ctypes.get_errno()
        raise OSError(errno, os.strerror(errno))
    return wd


def _inotify_rm_watch(fd: int, wd: int) -> None:
    """Remove watch from inotify instance."""
    if _libc is None:
        return
    _libc.inotify_rm_watch(fd, wd)


def _lower_thread_priority() -> None:
    """Lower thread priority to reduce impact on game performance."""
    try:
        os.nice(10)
    except Exception:
        pass


class InotifyMonitor(FileMonitor):
    """Linux inotify-based file monitor.
    
    Uses kernel-level file system events for zero-polling change detection.
    Automatically watches directories recursively.
    """

    def __init__(self) -> None:
        """Initialize inotify monitor."""
        self._path: Optional[Path] = None
        self._callback: Optional[Callable[[Path], None]] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._inotify_fd: int = -1
        self._watch_descriptors: Dict[int, Path] = {}

    def start(self, path: Path, callback: Callable[[Path], None]) -> None:
        """Start monitoring using inotify.
        
        Args:
            path: File or directory to monitor
            callback: Function to call when changes are detected
        """
        self._path = path
        self._callback = callback
        self._running = True

        # Create inotify instance
        try:
            self._inotify_fd = _inotify_init()
        except (AttributeError, OSError) as e:
            raise OSError(f"inotify not available: {e}")

        # Add watch
        self._add_watch(path)

        # If directory, add watches for existing subdirectories
        if path.is_dir():
            for subdir in path.rglob("*"):
                if subdir.is_dir():
                    self._add_watch(subdir)

        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop monitoring and clean up inotify resources."""
        self._running = False

        # Close inotify file descriptor
        if self._inotify_fd >= 0:
            try:
                os.close(self._inotify_fd)
            except OSError:
                pass
            self._inotify_fd = -1

        if self._thread:
            self._thread.join(timeout=2.0)

    def _add_watch(self, path: Path) -> None:
        """Add an inotify watch for the given path."""
        if self._inotify_fd < 0:
            return

        try:
            wd = _inotify_add_watch(
                self._inotify_fd, str(path), IN_WATCH_MASK
            )
            if wd >= 0:
                self._watch_descriptors[wd] = path
        except (OSError, AttributeError):
            pass

    def _remove_watch(self, wd: int) -> None:
        """Remove an inotify watch."""
        if wd in self._watch_descriptors:
            try:
                _inotify_rm_watch(self._inotify_fd, wd)
            except (OSError, AttributeError):
                pass
            del self._watch_descriptors[wd]

    def _watch_loop(self) -> None:
        """Main inotify event loop."""
        _lower_thread_priority()

        while self._running and self._inotify_fd >= 0:
            try:
                # Wait for events with timeout
                readable, _, _ = select.select(
                    [self._inotify_fd], [], [], 0.5
                )

                if not readable:
                    continue

                # Read events
                data = os.read(self._inotify_fd, 4096)
                if not data:
                    continue

                # Process events
                self._process_events(data)

            except (select.error, OSError):
                if self._running:
                    continue
                break
            except Exception:
                if self._running:
                    continue
                break

    def _process_events(self, data: bytes) -> None:
        """Process inotify event data."""
        offset = 0

        while offset < len(data):
            # Parse event header
            if offset + EVENT_HEADER_SIZE > len(data):
                break

            wd, mask, cookie, name_len = struct.unpack(
                "iIII", data[offset : offset + EVENT_HEADER_SIZE]
            )

            # Extract name
            name_start = offset + EVENT_HEADER_SIZE
            name_end = name_start + name_len

            if name_end > len(data):
                break

            name = data[name_start:name_end].rstrip(b"\x00").decode("utf-8")

            # Handle event
            self._handle_event(wd, mask, name)

            # Move to next event (aligned to 16 bytes)
            offset = name_end
            if offset % 16 != 0:
                offset += 16 - (offset % 16)

    def _handle_event(self, wd: int, mask: int, name: str) -> None:
        """Handle a single inotify event."""
        # Get the watched path
        watch_path = self._watch_descriptors.get(wd, self._path)

        # Build full path
        if name:
            event_path = watch_path / name
        else:
            event_path = watch_path

        # Check if this is a deletion of the watched path itself
        if mask & IN_DELETE_SELF or mask & IN_MOVE_SELF:
            self._remove_watch(wd)

        # New directory created - add watch
        if mask & IN_CREATE and event_path.is_dir():
            self._add_watch(event_path)

        # Trigger callback for relevant events
        if mask & (
            IN_MODIFY
            | IN_CLOSE_WRITE
            | IN_MOVED_TO
            | IN_CREATE
            | IN_DELETE
            | IN_ATTRIB
        ):
            if self._callback and self._path:
                self._callback(self._path)
