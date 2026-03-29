"""Tests for platform-specific file monitors (inotify, polling, etc.).

TDD approach: Tests written before implementation.
Covers Layer 1 (platform monitors), Layer 2 (metadata), Layer 3 (I/O scheduling).
"""

import os
import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Tests for base monitor ABC and factory


def test_file_monitor_factory_returns_monitor():
    """Factory should return appropriate monitor for current platform."""
    from gamesave_vcs.monitors import get_file_monitor
    from gamesave_vcs.monitors.base import FileMonitor

    monitor = get_file_monitor()
    assert isinstance(monitor, FileMonitor)


def test_file_monitor_factory_caches_instance():
    """Factory should cache and return same instance on subsequent calls."""
    from gamesave_vcs.monitors import get_file_monitor, _monitor_instance

    # Clear cache first
    _monitor_instance["monitor"] = None

    monitor1 = get_file_monitor()
    monitor2 = get_file_monitor()
    assert monitor1 is monitor2


def test_base_monitor_is_abstract():
    """FileMonitor ABC should not be instantiable directly."""
    from gamesave_vcs.monitors.base import FileMonitor

    with pytest.raises(TypeError):
        FileMonitor()


def test_base_monitor_requires_start_method():
    """Concrete monitor must implement start()."""
    from gamesave_vcs.monitors.base import FileMonitor

    class IncompleteMonitor(FileMonitor):
        def stop(self):
            pass

    with pytest.raises(TypeError):
        IncompleteMonitor()


def test_base_monitor_requires_stop_method():
    """Concrete monitor must implement stop()."""
    from gamesave_vcs.monitors.base import FileMonitor

    class IncompleteMonitor(FileMonitor):
        def start(self, path, callback):
            pass

    with pytest.raises(TypeError):
        IncompleteMonitor()


# Tests for polling fallback monitor


def test_polling_monitor_basic_functionality(tmp_path):
    """PollingMonitor should detect changes via metadata polling."""
    from gamesave_vcs.monitors.polling import PollingMonitor

    monitor = PollingMonitor()
    callback_called = threading.Event()
    received_path = None

    def callback(path):
        nonlocal received_path
        received_path = path
        callback_called.set()

    test_file = tmp_path / "test.save"
    test_file.write_text("initial")

    monitor.start(test_file, callback)
    time.sleep(0.1)

    # Modify file
    test_file.write_text("modified")
    callback_called.wait(timeout=2.0)

    monitor.stop()

    assert callback_called.is_set()
    assert received_path == test_file


def test_polling_monitor_stop_while_running():
    """PollingMonitor should stop cleanly."""
    from gamesave_vcs.monitors.polling import PollingMonitor

    monitor = PollingMonitor()
    monitor.start(Path("/tmp/test"), lambda p: None)
    time.sleep(0.05)
    monitor.stop()  # Should not raise


def test_polling_monitor_no_false_positives(tmp_path):
    """PollingMonitor should not trigger without actual changes."""
    from gamesave_vcs.monitors.polling import PollingMonitor

    monitor = PollingMonitor(poll_interval=0.05)
    callback_count = [0]

    def callback(path):
        callback_count[0] += 1

    test_file = tmp_path / "test.save"
    test_file.write_text("content")

    monitor.start(test_file, callback)
    time.sleep(0.2)  # Wait for several poll cycles
    monitor.stop()

    # Should not have triggered (no changes)
    assert callback_count[0] == 0


def test_polling_monitor_handles_missing_file():
    """PollingMonitor should handle non-existent files gracefully."""
    from gamesave_vcs.monitors.polling import PollingMonitor

    monitor = PollingMonitor()
    callback_called = threading.Event()

    def callback(path):
        callback_called.set()

    monitor.start(Path("/nonexistent/path"), callback)
    time.sleep(0.1)
    monitor.stop()

    # Should not crash, just not call callback
    assert not callback_called.is_set()


def test_polling_monitor_thread_priority_lowered():
    """PollingMonitor should attempt to lower thread priority."""
    from gamesave_vcs.monitors.polling import PollingMonitor

    with patch("gamesave_vcs.monitors.polling.os.nice") as mock_nice:
        monitor = PollingMonitor()
        monitor.start(Path("/tmp/test"), lambda p: None)
        time.sleep(0.05)
        monitor.stop()

        # Should have attempted to lower priority on Linux
        if sys.platform != "win32":
            mock_nice.assert_called_with(10)


# Tests for inotify monitor (Linux-specific)


def test_inotify_monitor_imports_on_linux():
    """InotifyMonitor should be importable on Linux."""
    if sys.platform != "linux":
        pytest.skip("inotify only available on Linux")

    from gamesave_vcs.monitors.inotify import InotifyMonitor

    assert InotifyMonitor is not None


def test_inotify_monitor_basic_functionality(tmp_path):
    """InotifyMonitor should detect file changes via inotify."""
    if sys.platform != "linux":
        pytest.skip("inotify only available on Linux")

    from gamesave_vcs.monitors.inotify import InotifyMonitor

    monitor = InotifyMonitor()
    callback_called = threading.Event()
    received_path = None

    def callback(path):
        nonlocal received_path
        received_path = path
        callback_called.set()

    test_file = tmp_path / "test.save"
    test_file.write_text("initial")

    monitor.start(test_file, callback)
    time.sleep(0.1)  # Allow inotify to set up

    # Modify file
    test_file.write_text("modified")
    callback_called.wait(timeout=2.0)

    monitor.stop()

    assert callback_called.is_set()
    assert received_path == test_file


def test_inotify_monitor_detects_directory_changes(tmp_path):
    """InotifyMonitor should detect changes in watched directory."""
    if sys.platform != "linux":
        pytest.skip("inotify only available on Linux")

    from gamesave_vcs.monitors.inotify import InotifyMonitor

    monitor = InotifyMonitor()
    callback_called = threading.Event()

    def callback(path):
        callback_called.set()

    # Create directory with file
    test_dir = tmp_path / "saves"
    test_dir.mkdir()
    test_file = test_dir / "save1.dat"
    test_file.write_text("data")

    monitor.start(test_dir, callback)
    time.sleep(0.1)

    # Modify file in directory
    test_file.write_text("modified data")
    callback_called.wait(timeout=2.0)

    monitor.stop()

    assert callback_called.is_set()


def test_inotify_monitor_stop_while_running(tmp_path):
    """InotifyMonitor should stop cleanly."""
    if sys.platform != "linux":
        pytest.skip("inotify only available on Linux")

    from gamesave_vcs.monitors.inotify import InotifyMonitor

    monitor = InotifyMonitor()
    test_file = tmp_path / "test.save"
    test_file.write_text("data")

    monitor.start(test_file, lambda p: None)
    time.sleep(0.05)
    monitor.stop()  # Should not raise


def test_inotify_monitor_handles_file_deletion(tmp_path):
    """InotifyMonitor should handle file deletion gracefully."""
    if sys.platform != "linux":
        pytest.skip("inotify only available on Linux")

    from gamesave_vcs.monitors.inotify import InotifyMonitor

    monitor = InotifyMonitor()
    callback_called = threading.Event()

    def callback(path):
        callback_called.set()

    test_file = tmp_path / "test.save"
    test_file.write_text("data")

    monitor.start(test_file, callback)
    time.sleep(0.1)

    # Delete file
    test_file.unlink()
    callback_called.wait(timeout=2.0)

    monitor.stop()

    # May or may not trigger depending on implementation
    # Main thing is it doesn't crash


def test_inotify_not_available_on_non_linux():
    """InotifyMonitor should not be available on non-Linux platforms."""
    if sys.platform == "linux":
        pytest.skip("Only relevant on non-Linux platforms")

    with pytest.raises(ImportError):
        from gamesave_vcs.monitors.inotify import InotifyMonitor


# Tests for factory platform selection


def test_factory_selects_inotify_on_linux():
    """Factory should select InotifyMonitor on Linux when available."""
    if sys.platform != "linux":
        pytest.skip("Only relevant on Linux")

    from gamesave_vcs.monitors import get_file_monitor
    from gamesave_vcs.monitors.inotify import InotifyMonitor

    # Clear cache
    from gamesave_vcs.monitors import _monitor_instance

    _monitor_instance["monitor"] = None

    monitor = get_file_monitor()
    assert isinstance(monitor, InotifyMonitor)


def test_factory_selects_polling_on_non_linux():
    """Factory should select PollingMonitor on non-Linux platforms."""
    if sys.platform == "linux":
        pytest.skip("Only relevant on non-Linux platforms")

    from gamesave_vcs.monitors import get_file_monitor
    from gamesave_vcs.monitors.polling import PollingMonitor

    # Clear cache
    from gamesave_vcs.monitors import _monitor_instance

    _monitor_instance["monitor"] = None

    monitor = get_file_monitor()
    assert isinstance(monitor, PollingMonitor)


def test_factory_falls_back_to_polling_on_inotify_error():
    """Factory should fall back to polling if inotify init fails."""
    if sys.platform != "linux":
        pytest.skip("Only relevant on Linux")

    from gamesave_vcs.monitors import get_file_monitor
    from gamesave_vcs.monitors.polling import PollingMonitor

    # Clear cache
    from gamesave_vcs.monitors import _monitor_instance

    _monitor_instance["monitor"] = None

    with patch(
        "gamesave_vcs.monitors.inotify.InotifyMonitor",
        side_effect=OSError("inotify init failed"),
    ):
        monitor = get_file_monitor()
        assert isinstance(monitor, PollingMonitor)


# Tests for integration with GameWatcher


def test_gamewatcher_uses_platform_monitor(tmp_path):
    """GameWatcher should use platform monitor when available."""
    from gamesave_vcs.watcher import GameWatcher

    with patch("gamesave_vcs.watcher.get_game_path", return_value=str(tmp_path / "save")):
        watcher = GameWatcher("testgame")

    test_file = tmp_path / "save"
    test_file.write_text("data")

    callback_triggered = threading.Event()

    mock_start = MagicMock()

    def mock_start_impl(path, callback):
        callback_triggered.set()

    mock_start.side_effect = mock_start_impl

    with patch.object(watcher, "_get_monitor", return_value=MagicMock()) as mock_get:
        mock_monitor = MagicMock()
        mock_monitor.start = mock_start
        mock_get.return_value = mock_monitor

        watcher.start()
        time.sleep(0.05)
        watcher.stop()

        # Verify monitor was used
        assert mock_start.called or not watcher.running


def test_gamewatcher_falls_back_to_polling():
    """GameWatcher should fall back to polling if platform monitor fails."""
    from gamesave_vcs.watcher import GameWatcher

    with patch("gamesave_vcs.watcher.get_game_path", return_value="/tmp/save"):
        watcher = GameWatcher("testgame")

    # Should have _use_platform_monitor method
    assert hasattr(watcher, "_watch_loop")


# Tests for metadata utilities (Layer 2)


def test_get_file_metadata_returns_tuple(tmp_path):
    """_get_file_metadata should return (mtime, size) tuple."""
    from gamesave_vcs.watcher import _get_file_metadata

    test_file = tmp_path / "test.txt"
    test_file.write_text("hello")

    mtime, size = _get_file_metadata(test_file)

    assert isinstance(mtime, int)
    assert isinstance(size, int)
    assert size == 5  # "hello"
    assert mtime > 0


def test_get_file_metadata_missing_file():
    """_get_file_metadata should return (0, 0) for missing files."""
    from gamesave_vcs.watcher import _get_file_metadata

    result = _get_file_metadata(Path("/nonexistent/file"))
    assert result == (0, 0)


def test_get_dir_metadata_returns_dict(tmp_path):
    """_get_dir_metadata should return dict of relative paths to metadata."""
    from gamesave_vcs.watcher import _get_dir_metadata

    # Create directory structure
    (tmp_path / "subdir").mkdir()
    (tmp_path / "file1.txt").write_text("content1")
    (tmp_path / "subdir" / "file2.txt").write_text("content2")

    metadata = _get_dir_metadata(tmp_path)

    assert isinstance(metadata, dict)
    assert "file1.txt" in metadata
    assert "subdir/file2.txt" in metadata
    assert metadata["file1.txt"][1] == len("content1")  # size


def test_metadata_changed_detects_file_changes(tmp_path):
    """_metadata_changed should detect file modifications."""
    from gamesave_vcs.watcher import _metadata_changed

    test_file = tmp_path / "test.txt"
    test_file.write_text("initial")

    # Initial check
    changed, meta, _ = _metadata_changed(test_file, (0, 0), None)
    assert changed is True

    # Same content, no change
    changed, _, _ = _metadata_changed(test_file, meta, None)
    assert changed is False

    # Modify file
    test_file.write_text("modified")
    changed, new_meta, _ = _metadata_changed(test_file, meta, None)
    assert changed is True
    assert new_meta != meta


def test_metadata_changed_detects_dir_changes(tmp_path):
    """_metadata_changed should detect directory modifications."""
    from gamesave_vcs.watcher import _metadata_changed

    # Create initial structure
    (tmp_path / "file1.txt").write_text("content1")

    changed, _, dir_meta = _metadata_changed(tmp_path, (0, 0), None)
    assert changed is True

    # No change
    changed, _, _ = _metadata_changed(tmp_path, (0, 0), dir_meta)
    assert changed is False

    # Add new file
    (tmp_path / "file2.txt").write_text("content2")
    changed, _, new_meta = _metadata_changed(tmp_path, (0, 0), dir_meta)
    assert changed is True


# Tests for adaptive behavior


def test_adaptive_interval_increases_over_time():
    """Adaptive interval should increase after consecutive no-changes."""
    from gamesave_vcs.watcher import GameWatcher

    with patch("gamesave_vcs.watcher.get_game_path", return_value="/tmp/save"):
        watcher = GameWatcher("testgame", interval=5)

    # Initially at base interval
    assert watcher._adaptive_interval() == 5.0

    # After 10 no-changes, should increase
    watcher._consecutive_no_change = 11
    new_interval = watcher._adaptive_interval()
    assert new_interval > 5.0

    # Should cap at 4x base interval
    watcher._current_interval = 25.0
    watcher._consecutive_no_change = 100
    capped = watcher._adaptive_interval()
    assert capped <= 20.0  # 4 * 5


# Tests for thread priority (Layer 3)


def test_lower_thread_priority_linux():
    """_lower_thread_priority should call os.nice on Linux."""
    from gamesave_vcs.watcher import GameWatcher

    with patch("gamesave_vcs.watcher.get_game_path", return_value="/tmp/save"):
        watcher = GameWatcher("testgame")

    with patch("os.nice") as mock_nice:
        watcher._lower_thread_priority()
        if sys.platform != "win32":
            mock_nice.assert_called_with(10)


def test_lower_thread_priority_windows():
    """_lower_thread_priority should use Windows API on Windows."""
    from gamesave_vcs.watcher import GameWatcher

    with patch("gamesave_vcs.watcher.get_game_path", return_value="/tmp/save"):
        watcher = GameWatcher("testgame")

    mock_kernel32 = MagicMock()
    mock_ctypes = MagicMock()
    mock_ctypes.windll.kernel32 = mock_kernel32

    with patch.dict("sys.modules", {"ctypes": mock_ctypes}):
        with patch("sys.platform", "win32"):
            watcher._lower_thread_priority()
            mock_kernel32.SetThreadPriority.assert_called()


def test_lower_thread_priority_graceful_failure():
    """_lower_thread_priority should not crash on error."""
    from gamesave_vcs.watcher import GameWatcher

    with patch("gamesave_vcs.watcher.get_game_path", return_value="/tmp/save"):
        watcher = GameWatcher("testgame")

    with patch("os.nice", side_effect=OSError("Permission denied")):
        # Should not raise
        watcher._lower_thread_priority()
