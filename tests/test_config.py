import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from gamesave_vcs.config import add_game, get_game_path, load_config, save_config, ensure_dirs, list_supported_games, search_games, get_supported_game_path

def test_dirs_created():
    # Arrange
    with patch("gamesave_vcs.config.get_base_dir") as mock_get_base:
        mock_base = MagicMock()
        mock_backups = MagicMock()
        mock_get_base.return_value = mock_base
        mock_base.__truediv__.return_value = mock_backups
        # Act
        ensure_dirs()
    # Assert
    mock_base.mkdir.assert_called()
    mock_backups.mkdir.assert_called()

def test_load_save_config():
    # Arrange
    with patch("gamesave_vcs.config.ensure_dirs"):
        with patch("gamesave_vcs.config.get_config_file") as mock_config:
            mock_config.return_value = Path("/fake/config.json")
            with patch("pathlib.Path.exists", return_value=True):
                with patch("builtins.open", MagicMock()) as mock_open:
                    with patch("json.load") as mock_json:
                        mock_json.return_value = {"test": "/path"}
                        mock_file = MagicMock()
                        mock_file.read.return_value = "dummy"
                        mock_open.return_value.__enter__.return_value = mock_file
                        # Act
                        loaded = load_config()
    # Assert
    assert loaded == {"test": "/path"}

def test_add_game(capsys):
    # Arrange
    with patch("gamesave_vcs.config.load_config") as mock_load:
        mock_load.return_value = {}
        with patch("gamesave_vcs.config.save_config") as mock_save:
            with patch("gamesave_vcs.config.get_backups_dir") as mock_backups:
                # Act
                add_game("testgame", "/tmp/save.dat")
    # Assert
    mock_save.assert_called()
    captured = capsys.readouterr()
    assert "Added/updated game testgame" in captured.out

def test_add_game_duplicate():
    # Arrange
    with patch("gamesave_vcs.config.load_config") as mock_load:
        mock_load.return_value = {"testgame": "/path"}
        # Act + Assert (no force raises)
        with pytest.raises(ValueError):
            add_game("testgame", "/tmp/other.dat")

def test_add_game_force_update(capsys):
    # Arrange
    with patch("gamesave_vcs.config.load_config") as mock_load:
        mock_load.return_value = {"testgame": "/old/path"}
        with patch("gamesave_vcs.config.save_config") as mock_save:
            with patch("gamesave_vcs.config.get_backups_dir") as mock_backups:
                # Act
                add_game("testgame", "/new/path", force=True)
    # Assert
    mock_save.assert_called()
    captured = capsys.readouterr()
    assert "updating path (force mode)" in captured.out
    assert "Added/updated game testgame" in captured.out

def test_get_game_path():
    # Arrange
    with patch("gamesave_vcs.config.load_config") as mock_load:
        mock_load.return_value = {"testgame": "/tmp/save.dat"}
        # Act + Assert
        assert get_game_path("testgame") == "/tmp/save.dat"
        assert get_game_path("missing") is None

def test_list_supported_games():
    games = list_supported_games()
    assert len(games) == 10
    assert "Minecraft" in games

def test_search_games():
    results = search_games("witch")
    assert "The Witcher 3" in results
    results = search_games("xyz")
    assert results == []
    results = search_games("")
    assert len(results) == 10
    results = search_games("ELDEN")
    assert "Elden Ring" in results

def test_get_supported_game_path():
    path = get_supported_game_path("Elden Ring")
    assert path == "~/.local/share/EldenRing/"
    assert get_supported_game_path("unknown") is None
