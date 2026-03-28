import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch
from gamesave_vcs.backup import list_saves, restore_save, backup_save
from gamesave_vcs.strategies.full_copy import FullCopyStrategy
from gamesave_vcs.strategies.git import GitStrategy
import shutil
import os

def test_list_saves_aggregate_with_legacy_dirs(tmp_path):
    """Cover backup.py:88-89 (legacy full-copy dirs without config entry) and 95-97 (except block)."""
    backups_dir = tmp_path / "backups"
    backups_dir.mkdir()
    
    # Legacy game dir (no config)
    legacy_game = backups_dir / "LegacyGame"
    legacy_game.mkdir()
    # Create a valid full-copy style backup item
    (legacy_game / "20260301_120000_save").mkdir()
    
    # Broken game dir
    broken_game = backups_dir / "BrokenGame"
    broken_game.mkdir()

    # Patch get_backups_dir in all relevant places
    with patch("gamesave_vcs.backup.get_backups_dir", return_value=backups_dir):
        with patch("gamesave_vcs.strategies.base.get_backups_dir", return_value=backups_dir):
            with patch("gamesave_vcs.strategies.full_copy.get_backups_dir", return_value=backups_dir):
                with patch("gamesave_vcs.backup.load_config", return_value={}):
                    def side_effect(name):
                        if name == "BrokenGame":
                            raise Exception("Strategy failure")
                        from gamesave_vcs.strategies.base import detect_strategy
                        return detect_strategy(name)
                    
                    with patch("gamesave_vcs.strategies.get_strategy", side_effect=side_effect):
                        saves = list_saves()
                        # Verify we found the legacy game
                        assert any(s[2] == "LegacyGame" for s in saves)
                        # Verify we skipped the broken one
                        assert not any(s[2] == "BrokenGame" for s in saves)

def test_backup_save_missing_path_coverage(tmp_path):
    """Cover FullCopyStrategy:52 and GitStrategy:67 (missing save path)."""
    # FullCopyStrategy:52
    with patch("gamesave_vcs.strategies.full_copy.get_game_path", return_value=str(tmp_path / "nonexistent")):
        strategy = FullCopyStrategy()
        with patch('builtins.print') as mock_print:
            assert strategy.backup_save("test") is None
            mock_print.assert_any_call("Backup skipped for test: save path not found (nothing to backup yet)")

    # GitStrategy:67
    with patch("gamesave_vcs.strategies.git.get_game_path", return_value=str(tmp_path / "nonexistent")):
        strategy = GitStrategy()
        with patch('builtins.print') as mock_print:
            assert strategy.backup_save("test") is None
            mock_print.assert_any_call("Backup skipped for test: save path not found (nothing to backup yet)")

def test_git_restore_invalid_spec_branch():
    """Cover GitStrategy:128-130 (invalid spec)."""
    strategy = GitStrategy()
    # Explicitly test the branch where '@' is missing
    with patch('builtins.print') as mock_print:
        assert strategy.restore_save("no_at_symbol") is False
        mock_print.assert_any_call("Invalid git backup spec (expected repo@commit)")

def test_git_restore_repo_not_found_branch(tmp_path):
    """Cover GitStrategy:140-141 (repo not found)."""
    strategy = GitStrategy()
    # spec with @ but repo path doesn't exist
    spec = str(tmp_path / "nonexistent_repo") + "@hash"
    with patch('builtins.print') as mock_print:
        assert strategy.restore_save(spec) is False
        mock_print.assert_any_call("Git repo not found")

def test_full_copy_backup_missing_path_branch(tmp_path):
    """Cover FullCopyStrategy:52 (missing save path)."""
    strategy = FullCopyStrategy()
    # Mock get_game_path to return something that doesn't exist on FS
    with patch("gamesave_vcs.strategies.full_copy.get_game_path", return_value=str(tmp_path / "void")):
        with patch('builtins.print') as mock_print:
            assert strategy.backup_save("voidgame") is None
            mock_print.assert_any_call("Backup skipped for voidgame: save path not found (nothing to backup yet)")

def test_git_backup_missing_path_branch(tmp_path):
    """Cover GitStrategy:67-70 (missing save path)."""
    strategy = GitStrategy()
    with patch("gamesave_vcs.strategies.git.get_game_path", return_value=str(tmp_path / "void")):
        with patch('builtins.print') as mock_print:
            assert strategy.backup_save("voidgame") is None
            mock_print.assert_any_call("Backup skipped for voidgame: save path not found (nothing to backup yet)")

def test_full_copy_restore_missing_backup_branch(tmp_path):
    """Cover FullCopyStrategy:133-135 (backup not found)."""
    strategy = FullCopyStrategy()
    with patch('builtins.print') as mock_print:
        assert strategy.restore_save(tmp_path / "nonexistent") is False
        mock_print.assert_any_call("Backup not found")

def test_git_restore_game_not_found(tmp_path):
    """Cover GitStrategy:150-151 (game path not found)."""
    repo_dir = tmp_path / "TestGame"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()
    strategy = GitStrategy()
    spec = f"{repo_dir}@hash"
    with patch("gamesave_vcs.strategies.git.get_game_path", return_value=None):
        with patch('builtins.print') as mock_print:
            assert strategy.restore_save(spec) is False
            mock_print.assert_any_call("Game not found")

def test_git_restore_content_not_found(tmp_path):
    """Cover GitStrategy:161-162 (content path not found in repo)."""
    repo_dir = tmp_path / "TestGame"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()
    save_path = tmp_path / "live_save"
    
    strategy = GitStrategy()
    spec = f"{repo_dir}@hash"
    
    with patch("gamesave_vcs.strategies.git.get_game_path", return_value=str(save_path)):
        with patch("gamesave_vcs.strategies.git.porcelain.reset"):
            # Mock content path to something that doesn't exist
            with patch.object(GitStrategy, "_get_content_path", return_value=tmp_path / "nonexistent"):
                with patch('builtins.print') as mock_print:
                    assert strategy.restore_save(spec) is False
                    mock_print.assert_any_call(f"No content at {tmp_path / 'nonexistent'} for restore")

def test_git_restore_exception(tmp_path):
    """Cover GitStrategy:178-181 (restore exception)."""
    repo_dir = tmp_path / "TestGame"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()
    
    strategy = GitStrategy()
    spec = f"{repo_dir}@hash"
    
    with patch("gamesave_vcs.strategies.git.get_game_path", return_value=str(tmp_path / "save")):
        with patch("gamesave_vcs.strategies.git.porcelain.reset", side_effect=Exception("Git Error")):
            with patch('builtins.print') as mock_print:
                assert strategy.restore_save(spec) is False
                # The exception is printed at the end of the except block
                # Git restore failed: Git Error
                args, _ = mock_print.call_args
                assert "Git restore failed: Git Error" in args[0]

def test_full_copy_restore_game_not_found(tmp_path):
    """Cover FullCopyStrategy:137 (game not found in config during restore)."""
    backup_path = tmp_path / "SomeGame" / "20260101_120000_save"
    backup_path.mkdir(parents=True)
    
    with patch("gamesave_vcs.strategies.full_copy.get_game_path", return_value=None):
        strategy = FullCopyStrategy()
        with patch('builtins.print') as mock_print:
            assert strategy.restore_save(backup_path) is False
            mock_print.assert_any_call("Game not found")

def test_full_copy_restore_atomic_dir_exists(tmp_path):
    """Cover FullCopyStrategy:119-120, 124-125 (restore over existing file/dir)."""
    save_path = tmp_path / "live_save"
    save_path.write_text("old data") # It's a file initially
    
    backup_path = tmp_path / "backup"
    backup_path.mkdir()
    (backup_path / "data.txt").write_text("new data")
    
    strategy = FullCopyStrategy()
    with patch("gamesave_vcs.strategies.full_copy.get_game_path", return_value=str(save_path)):
        # Restore dir over file
        assert strategy.restore_save(backup_path) is True
        assert save_path.is_dir()
        assert (save_path / "data.txt").read_text() == "new data"

def test_git_backup_no_changes_exception(tmp_path):
    """Cover GitStrategy:111 (exception handling for commit)."""
    repo_dir = tmp_path / "TestGame"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()
    save_path = tmp_path / "save.dat"
    save_path.write_text("content")
    
    strategy = GitStrategy()
    with patch("gamesave_vcs.strategies.git.get_backups_dir", return_value=tmp_path):
        with patch("gamesave_vcs.strategies.git.get_game_path", return_value=str(save_path)):
            with patch("gamesave_vcs.strategies.git.porcelain.commit", side_effect=Exception("some other error")):
                with pytest.raises(Exception, match="some other error"):
                    strategy.backup_save("TestGame")

def test_full_copy_list_saves_aggregate_branch(tmp_path):
    """Cover FullCopyStrategy:103-107 (aggregate list for full-copy)."""
    backups_dir = tmp_path / "backups"
    backups_dir.mkdir()
    
    game1 = backups_dir / "Game1"
    game1.mkdir()
    (game1 / "20260101_120000_save").mkdir()
    
    # This one has .git, should be skipped by FullCopyStrategy.list_saves aggregate - Line 106
    game2 = backups_dir / "Game2"
    game2.mkdir()
    (game2 / ".git").mkdir()
    (game2 / "20260101_120000_save").mkdir()
    
    strategy = FullCopyStrategy()
    with patch("gamesave_vcs.strategies.full_copy.get_backups_dir", return_value=backups_dir):
        saves = strategy.list_saves() # aggregate
        game_names = [s[2] for s in saves]
        assert "Game1" in game_names
        assert "Game2" not in game_names

def test_git_strategy_list_saves_none_branch():
    """Cover GitStrategy:102 (list_saves with game_name=None)."""
    strategy = GitStrategy()
    assert strategy.list_saves(None) == []

def test_cli_main_coverage():
    """Cover cli.py:147-149, 153 (missing CLI branches)."""
    from gamesave_vcs.cli import main
    import sys
    
    # Mocking sys.argv for 'games' without flags
    with patch.object(sys, 'argv', ['gamesave', 'games']):
        with patch('builtins.print') as mock_print:
            main()
            mock_print.assert_any_call("Use --list or --search <query>")
    
    # The 'if __name__ == "__main__":' line (153) is hard to cover via standard import/call, 
    # but we've covered the main() function itself.
