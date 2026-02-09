import pytest
from unittest.mock import patch, MagicMock
from gamesave_vcs.backup import get_file_hash, backup_save, list_saves, restore_save

def test_get_file_hash():
    # Arrange
    with patch("gamesave_vcs.backup.open", MagicMock()) as mock_open:
        mock_open.return_value.__enter__.return_value.read.side_effect = [b"chunk", b""]
        # Act
        hash_val = get_file_hash("/fake/file")
    # Assert
    assert len(hash_val) == 64  # SHA256

def test_backup_save():
    # Arrange
    with patch("gamesave_vcs.backup.get_game_path") as mock_get:
        mock_get.return_value = "/tmp/save.dat"
        with patch("gamesave_vcs.backup.Path") as mock_path:
            mock_path.return_value.exists.return_value = True
            with patch("gamesave_vcs.backup.shutil.copy2") as mock_copy:
                # Act
                backup_path = backup_save("testgame")
    # Assert
    assert backup_path is not None
    mock_copy.assert_called()

def test_backup_save_missing():
    # Arrange
    with patch("gamesave_vcs.backup.get_game_path") as mock_get:
        mock_get.return_value = None
        # Act
        result = backup_save("testgame")
    # Assert
    assert result is None

def test_list_saves():
    # Arrange
    with patch("gamesave_vcs.backup.get_backups_dir") as mock_backups:
        mock_dir = MagicMock()
        mock_backups.return_value = mock_dir
        mock_dir.exists.return_value = True
        mock_game_dir = MagicMock()
        mock_dir.iterdir.return_value = [mock_game_dir]
        mock_game_dir.is_dir.return_value = True
        mock_file = MagicMock()
        mock_file.name = "20230101_120000_save.dat"
        mock_game_dir.iterdir.return_value = [mock_file]
        # Act
        saves = list_saves()
    # Assert
    assert len(saves) > 0

def test_restore_save():
    # Arrange
    with patch("gamesave_vcs.backup.Path") as mock_path:
        mock_backup = MagicMock()
        mock_path.return_value = mock_backup
        mock_backup.exists.return_value = True
        with patch("gamesave_vcs.backup.get_game_path") as mock_get:
            mock_get.return_value = "/tmp/save.dat"
            with patch("gamesave_vcs.backup.shutil.copy2") as mock_copy:
                # Act
                result = restore_save("/fake/backup")
    # Assert
    assert result is True
    mock_copy.assert_called()

def test_restore_save_invalid():
    # Arrange
    with patch("gamesave_vcs.backup.Path") as mock_path:
        mock_backup = MagicMock()
        mock_path.return_value = mock_backup
        mock_backup.exists.return_value = False
        # Act
        result = restore_save("/fake")
    # Assert
    assert not result

def test_list_saves_no_backups():
    # Arrange
    with patch("gamesave_vcs.backup.get_backups_dir") as mock_dir:
        mock_dir.return_value.exists.return_value = False
        # Act
        saves = list_saves()
    # Assert
    assert saves == []

def test_restore_save_no_game():
    # Arrange
    with patch("gamesave_vcs.backup.Path") as mock_path:
        mock_backup = MagicMock()
        mock_path.return_value = mock_backup
        mock_backup.exists.return_value = True
        with patch("gamesave_vcs.backup.get_game_path") as mock_get:
            mock_get.return_value = None  # no game
            # Act
            result = restore_save("/fake/backup")
    # Assert
    assert not result

def test_list_saves_parse_error():
    # Arrange (bad filename to hit except)
    with patch("gamesave_vcs.backup.get_backups_dir") as mock_dir:
        mock_dir.return_value.exists.return_value = True
        mock_game_dir = MagicMock()
        mock_dir.iterdir.return_value = [mock_game_dir]
        mock_game_dir.is_dir.return_value = True
        mock_file = MagicMock()
        mock_file.name = "invalid_no_ts.dat"  # triggers ValueError in strptime
        mock_game_dir.iterdir.return_value = [mock_file]
        # Act
        saves = list_saves()
    # Assert
    assert saves == []  # no valid parsed

def test_list_saves_game_name_branch():
    # Arrange (hit lines 34-44)
    with patch("gamesave_vcs.backup.get_backups_dir") as mock_dir:
        mock_dir.return_value.exists.return_value = True
        mock_game_dir = MagicMock()
        mock_dir.iterdir.return_value = [mock_game_dir]
        mock_game_dir.is_dir.return_value = False  # for game_name path
        # Act
        saves = list_saves("testgame")
    # Assert
    assert saves == []

def test_list_saves_game_name_strptime_except():
    # Arrange (hit lines 37-44 exactly: strptime ValueError in game_name path)
    with patch("gamesave_vcs.backup.get_backups_dir") as mock_dir:
        mock_dir.return_value.exists.return_value = True
        mock_game_dir = MagicMock()
        mock_dir.iterdir.return_value = [mock_game_dir]
        mock_game_dir.is_dir.return_value = True  # wait, for game_name it's direct
        mock_file = MagicMock()
        mock_file.name = "bad_format.dat"  # triggers except
        mock_game_dir.iterdir.return_value = [mock_file]
        # Act
        saves = list_saves("testgame")
    # Assert
    assert saves == []
