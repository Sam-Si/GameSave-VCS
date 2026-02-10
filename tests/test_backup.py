import pytest
import shutil
from unittest.mock import patch, MagicMock
from datetime import datetime
from gamesave_vcs.backup import get_save_hash, backup_save, list_saves, restore_save
from gamesave_vcs.config import get_backups_dir

def test_get_save_hash(tmp_path):
    # Arrange: real file to hit file hash branch
    save_file = tmp_path / "test.dat"
    save_file.write_text("test content")
    # Act
    hash_val = get_save_hash(save_file)
    # Assert
    assert len(hash_val) == 64

def test_get_save_hash_dir(tmp_path):
    # Arrange: real dir for recursive hash coverage
    save_dir = tmp_path / "testsave"
    save_dir.mkdir()
    (save_dir / "data.txt").write_text("test")
    (save_dir / "subdir").mkdir()
    ((save_dir / "subdir") / "sub.txt").write_text("sub")
    # Act
    hash_val = get_save_hash(save_dir)
    # Assert
    assert len(hash_val) == 64

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

def test_backup_save_dir(tmp_path):
    # Arrange: test dir branch for copytree coverage (force exists True for inner if)
    with patch("gamesave_vcs.backup.get_game_path") as mock_get:
        mock_get.return_value = str(tmp_path / "testsave")
        test_dir = tmp_path / "testsave"
        test_dir.mkdir()
        (test_dir / "data.txt").write_text("test")
        # no Path patch; use real Paths
        with patch("gamesave_vcs.backup.shutil.copytree") as mock_copytree:
            with patch("gamesave_vcs.backup.shutil.rmtree") as mock_rmtree:
                # pre-create backup_path to hit exists if
                backup_dir = get_backups_dir() / "testgame"  # from config
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                pre_backup = backup_dir / f"{timestamp}_testsave"
                pre_backup.mkdir(parents=True, exist_ok=True)
                # Act
                backup_path = backup_save("testgame")
    # Assert
    assert backup_path is not None
    mock_copytree.assert_called()
    mock_rmtree.assert_called()  # hit the exists=True branch

def test_backup_save_missing(capsys):
    # Arrange
    with patch("gamesave_vcs.backup.get_game_path") as mock_get:
        mock_get.return_value = None
        # Act
        result = backup_save("testgame")
    # Assert
    assert result is None
    captured = capsys.readouterr()
    assert "Backup skipped for testgame: save path not found" in captured.out

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
        mock_backup.is_dir.return_value = False  # file branch for copy2
        with patch("gamesave_vcs.backup.get_game_path") as mock_get:
            mock_get.return_value = "/tmp/save.dat"
            with patch("gamesave_vcs.backup.shutil.copy2") as mock_copy:
                # Act
                result = restore_save("/fake/backup")
    # Assert
    assert result is True
    mock_copy.assert_called()

def test_restore_save_dir(tmp_path):
    # Arrange + Act: test dir restore for BOTH save-is-dir (rmtree) and save-is-file (unlink) branches
    backup_dir = tmp_path / "backupdir"
    backup_dir.mkdir()
    (backup_dir / "data.txt").write_text("backup")
    save_target = tmp_path / "save_target"
    # Case 1: save as dir -> hit rmtree
    if save_target.exists():
        shutil.rmtree(save_target)
    save_target.mkdir()
    with patch("gamesave_vcs.backup.Path") as mock_path:
        mock_backup = MagicMock()
        mock_save = MagicMock()
        mock_path.side_effect = [mock_backup, mock_save]
        mock_backup.exists.return_value = True
        mock_backup.is_dir.return_value = True
        mock_save.exists.return_value = True
        mock_save.is_dir.return_value = True  # rmtree
        with patch("gamesave_vcs.backup.get_game_path") as mock_get:
            mock_get.return_value = str(save_target)
            with patch("gamesave_vcs.backup.shutil.copytree") as mock_copytree:
                with patch("gamesave_vcs.backup.shutil.rmtree") as mock_rmtree:
                    result = restore_save(str(backup_dir))
    assert result is True
    mock_copytree.assert_called()
    mock_rmtree.assert_called()
    # Case 2: save as file -> hit unlink (covers remaining restore lines)
    shutil.rmtree(save_target)  # was dir
    save_target.write_text("old")
    with patch("gamesave_vcs.backup.Path") as mock_path:
        mock_backup = MagicMock()
        mock_save = MagicMock()
        mock_path.side_effect = [mock_backup, mock_save]
        mock_backup.exists.return_value = True
        mock_backup.is_dir.return_value = True
        mock_save.exists.return_value = True
        mock_save.is_dir.return_value = False  # unlink
        with patch("gamesave_vcs.backup.get_game_path") as mock_get:
            mock_get.return_value = str(save_target)
            with patch("gamesave_vcs.backup.shutil.copytree") as mock_copytree:
                with patch("gamesave_vcs.backup.shutil.rmtree") as mock_rmtree:
                    result = restore_save(str(backup_dir))
    assert result is True
    # both if/else covered

def test_restore_save_latest_and_no_backups(capsys):
    # Arrange + Act: cover new None=latest path (incl no-backups)
    with patch("gamesave_vcs.backup.list_saves") as mock_list:
        mock_list.return_value = []  # no backups case
        result = restore_save(None)
    assert not result
    captured = capsys.readouterr()
    assert "No backups found" in captured.out
    # Now with backup
    with patch("gamesave_vcs.backup.list_saves") as mock_list:
        mock_latest = MagicMock()
        mock_list.return_value = [(datetime.now(), mock_latest, "game")]
        with patch("gamesave_vcs.backup.Path") as mock_path:
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.is_dir.return_value = False
            with patch("gamesave_vcs.backup.get_game_path") as mock_get:
                mock_get.return_value = "/tmp/save.dat"
                with patch("gamesave_vcs.backup.shutil.copy2") as mock_copy:
                    result = restore_save(None)  # auto latest
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
        mock_file.is_file.return_value = True  # ensure if branch + except
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
    # Arrange: hit game_name success parse + except; use __truediv__ for / game_name
    with patch("gamesave_vcs.backup.get_backups_dir") as mock_get_backups:
        mock_backups = MagicMock()
        mock_get_backups.return_value = mock_backups
        mock_game_dir = MagicMock()
        mock_backups.__truediv__.return_value = mock_game_dir  # for game_dir = backups / name
        mock_game_dir.exists.return_value = True
        # valid + bad names
        mock_file_good = MagicMock()
        mock_file_good.name = "20230101_120000_good.dat"
        mock_file_bad = MagicMock()
        mock_file_bad.name = "bad_format.dat"
        mock_game_dir.iterdir.return_value = [mock_file_good, mock_file_bad]
        # Act
        saves = list_saves("testgame")
    # Assert: hits try success (one) + except
    assert len(saves) == 1
