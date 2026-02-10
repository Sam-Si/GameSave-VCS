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
    mock_add.assert_called_with("testgame", "/tmp/save.dat", force=False)

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

def test_cli_games_list():
    with patch("gamesave_vcs.cli.list_supported_games") as mock_list:
        mock_list.return_value = ["Minecraft"]
        with patch("gamesave_vcs.cli.get_supported_game_path") as mock_path:
            mock_path.return_value = "~/.minecraft"
            with patch("sys.argv", ["cli", "games", "--list"]):
                main()

def test_cli_games_search():
    with patch("gamesave_vcs.cli.search_games") as mock_search:
        mock_search.return_value = ["Minecraft"]
        with patch("gamesave_vcs.cli.get_supported_game_path") as mock_path:
            mock_path.return_value = "~/.minecraft"
            with patch("sys.argv", ["cli", "games", "--search", "mine"]):
                main()

def test_cli_games_no_args():
    with patch("sys.argv", ["cli", "games"]):
        main()

def test_cli_add_supported(capsys):
    with patch("gamesave_vcs.cli.get_supported_game_path") as mock_get:
        mock_get.return_value = "~/.minecraft/saves/"
        with patch("gamesave_vcs.config.Path") as mock_path:
            mock_path.return_value.exists.return_value = True
            with patch("gamesave_vcs.cli.add_game") as mock_add:  # still mock to avoid real FS/config
                with patch("sys.argv", ["cli", "add", "Minecraft"]):
                    main()
    mock_add.assert_called_with("Minecraft", "~/.minecraft/saves/", force=False)
    captured = capsys.readouterr()
    assert "Using suggested path for Minecraft" in captured.out

def test_cli_add_force(capsys):
    with patch("gamesave_vcs.cli.add_game") as mock_add:
        with patch("sys.argv", ["cli", "add", "mygame", "/new/path", "--force"]):
            main()
    mock_add.assert_called_with("mygame", "/new/path", force=True)
    captured = capsys.readouterr()
    # Force handled in add_game

def test_cli_add_unsupported_no_path(capsys):
    with patch("gamesave_vcs.cli.get_supported_game_path") as mock_get:
        mock_get.return_value = None
        with patch("sys.argv", ["cli", "add", "unknowngame"]):
            main()
    captured = capsys.readouterr()
    assert "Path required for unsupported games" in captured.out

def test_cli_games_no_match(capsys):
    with patch("gamesave_vcs.cli.search_games") as mock_search:
        mock_search.return_value = []
        with patch("sys.argv", ["cli", "games", "--search", "foo"]):
            main()
    captured = capsys.readouterr()
    assert "No matching games found" in captured.out

def test_cli_games_list_full(capsys):
    with patch("gamesave_vcs.cli.list_supported_games") as mock_list:
        mock_list.return_value = ["Game1", "Game2"]
        with patch("gamesave_vcs.cli.get_supported_game_path") as mock_path:
            mock_path.return_value = "/fake/path"
            with patch("sys.argv", ["cli", "games", "--list"]):
                main()
    captured = capsys.readouterr()
    assert "1. Game1 - Suggested save path: /fake/path" in captured.out
