"""Platform-specific file monitors for GameSave-VCS.

This package provides efficient, native file system change detection:
- Linux: inotify (kernel-level events)
- macOS: FSEvents (via polling fallback for now)
- Windows: ReadDirectoryChangesW (via polling fallback for now)
- Fallback: PollingMonitor (metadata-based, low overhead)

Usage:
    from gamesave_vcs.monitors import get_file_monitor
    
    monitor = get_file_monitor()
    monitor.start(Path("/path/to/save"), on_change_callback)
    # ... later ...
    monitor.stop()
"""

import sys
from typing import Optional

from gamesave_vcs.monitors.base import FileMonitor
from gamesave_vcs.monitors.polling import PollingMonitor

# Singleton instance cache
_monitor_instance: dict[str, Optional[FileMonitor]] = {"monitor": None}


def get_file_monitor() -> FileMonitor:
    """Get the best available file monitor for the current platform.
    
    Returns a cached singleton instance. Prefers native event-based
    monitors over polling when available.
    
    Returns:
        FileMonitor: Platform-appropriate monitor instance
        
    Platform Support:
        - Linux: inotify (kernel events, zero polling)
        - macOS: PollingMonitor (FSEvents TODO)
        - Windows: PollingMonitor (ReadDirectoryChangesW TODO)
    """
    # Return cached instance if available
    if _monitor_instance["monitor"] is not None:
        return _monitor_instance["monitor"]

    monitor: FileMonitor

    # Try platform-specific monitors first
    if sys.platform == "linux":
        try:
            from gamesave_vcs.monitors.inotify import InotifyMonitor

            monitor = InotifyMonitor()
        except (ImportError, OSError):
            # Fall back to polling if inotify unavailable
            monitor = PollingMonitor(poll_interval=1.0)
    else:
        # Non-Linux platforms use polling for now
        # TODO: Implement FSEvents for macOS
        # TODO: Implement ReadDirectoryChangesW for Windows
        monitor = PollingMonitor(poll_interval=1.0)

    # Cache and return
    _monitor_instance["monitor"] = monitor
    return monitor


# Re-exports
__all__ = [
    "FileMonitor",
    "PollingMonitor",
    "get_file_monitor",
]

# Conditional re-export for Linux
if sys.platform == "linux":
    try:
        from gamesave_vcs.monitors.inotify import InotifyMonitor

        __all__.append("InotifyMonitor")
    except ImportError:
        pass
