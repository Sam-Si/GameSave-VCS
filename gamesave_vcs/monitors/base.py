"""Abstract base class for platform-specific file monitors.

Layer 1: Platform-specific file system event monitoring.
Extensible architecture supporting inotify (Linux), FSEvents (macOS),
ReadDirectoryChangesW (Windows), and fallback polling.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable


class FileMonitor(ABC):
    """Abstract base class for file system change monitors.
    
    Implementations should provide efficient, platform-native file
    change detection without polling when possible.
    """

    @abstractmethod
    def start(self, path: Path, callback: Callable[[Path], None]) -> None:
        """Start monitoring the given path for changes.
        
        Args:
            path: File or directory to monitor
            callback: Function to call when changes are detected
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop monitoring and clean up resources."""
        pass
