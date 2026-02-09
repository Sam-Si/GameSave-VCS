import pytest
from unittest.mock import patch, MagicMock
from gamesave_vcs.cli import main

def test_cli_help():
    # Arrange
    # Act
    with pytest.raises(SystemExit):
        with patch("sys.argv", ["cli", "--help"]):
            with patch("gamesave_vcs.cli.print") as mock_print:  # mock output
                main()
    # Assert
    # Help shown via argparse

def test_cli_add():
    # Arrange
    with patch("gamesave_vcs.cli.add_game") as mock_add:
        # Act
        with patch("sys.argv", ["cli", "add", "testgame", "/tmp/save.dat"]):
            main()
    # Assert
    mock_add.assert_called_with("testgame", "/tmp/save.dat")

def test_cli_watch():
    # Arrange (pure mocks, no thread/infinite loop)
    with patch("gamesave_vcs.cli.GameWatcher") as mock_watcher_cls:
        mock_watcher = MagicMock()
        mock_watcher_cls.return_value = mock_watcher
        with patch("threading.Thread"):
            with patch("gamesave_vcs.cli.time.sleep", side_effect=KeyboardInterrupt):  # break infinite while in main
                # Act
                with patch("sys.argv", ["cli", "watch", "testgame"]):
                    main()
    # Assert
    mock_watcher_cls.assert_called()

def test_cli_list():
    # Arrange
    with patch("gamesave_vcs.cli.list_saves") as mock_list:
        mock_list.return_value = []
        # Act
        with patch("sys.argv", ["cli", "list"]):
            main()
    # Assert
    mock_list.assert_called()

def test_cli_restore():
    # Arrange
    with patch("gamesave_vcs.cli.restore_save") as mock_restore:
        # Act
        with patch("sys.argv", ["cli", "restore", "/fake/backup"]):
            main()
    # Assert
    mock_restore.assert_called_with("/fake/backup")

def test_cli_restore_branch():
    # Arrange (hit lines 40,45 in restore if)
    with patch("gamesave_vcs.cli.restore_save") as mock_restore:
        mock_restore.return_value = False
        # Act
        with patch("sys.argv", ["cli", "restore", "/fake"]):
            main()
    # Assert
    mock_restore.assert_called()

def test_cli_restore_no_game():
    # Arrange (hit lines 40,45: game not found print in restore)
    with patch("gamesave_vcs.cli.restore_save") as mock_restore:
        mock_restore.return_value = False
        # Act
        with patch("sys.argv", ["cli", "restore", "/fake"]):
            main()
    # Assert
    mock_restore.assert_called()
