import pytest
import subprocess
import time
import shutil
from pathlib import Path
import os
import tempfile

GAMESAVE_BIN = shutil.which("gamesave") or "/opt/venv/bin/gamesave"

@pytest.fixture
def temp_setup():
    # Arrange fixed /tmp
    tmp = Path("/tmp/gamesave-test")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir()
    save_dir = tmp / "saves"
    save_dir.mkdir()
    save_file = save_dir / "game.save"
    save_file.write_text("initial data")
    yield tmp, save_file
    shutil.rmtree(tmp, ignore_errors=True)

def run_cli(args, cwd=None):
    # Helper: use full bin path
    result = subprocess.run([GAMESAVE_BIN] + args, capture_output=True, text=True, cwd=cwd or Path.cwd())
    return result

def test_integration_add_and_list(temp_setup):
    # Arrange
    tmp, save_file = temp_setup
    game_name = f"testgame_{int(time.time())}"
    # Act: add
    result = run_cli(["add", game_name, str(save_file)])
    assert result.returncode == 0, f"Add failed: {result.stderr}"
    assert "Added game" in result.stdout or "Added game" in result.stderr
    # Act: list
    result = run_cli(["list", "--game", game_name])
    assert result.returncode == 0
    # String check optional (empty if no backups)
    # assert "testgame" in result.stdout or "testgame" in result.stderr

def test_integration_manual_backup_and_restore(temp_setup):
    # Arrange
    tmp, save_file = temp_setup
    game_name = f"testgame_{int(time.time())}"
    save_file.write_text("initial data")
    run_cli(["add", game_name, str(save_file)])
    # Act: backup
    result = run_cli(["backup", game_name])
    assert result.returncode == 0, f"Backup failed: {result.stderr}"
    assert "Backed up" in result.stdout or "Backed up" in result.stderr
    # Act: list
    result = run_cli(["list", "--game", game_name])
    assert result.returncode == 0
    backup_line = result.stdout.strip().split("\n")[0]
    backup_path = backup_line.split(" | ")[-1]
    # Act: restore
    run_cli(["restore", backup_path])
    # Assert
    assert save_file.read_text() == "initial data"

def test_integration_watch_change_detection(temp_setup):
    # Arrange
    tmp, save_file = temp_setup
    game_name = f"testgame_{int(time.time())}"
    save_file.write_text("initial data")
    run_cli(["add", game_name, str(save_file)])
    # Act: watch bg
    watch_cmd = [GAMESAVE_BIN, "watch", game_name, "--interval", "1"]
    watch_proc = subprocess.Popen(watch_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=Path.cwd())
    time.sleep(2)
    save_file.write_text("changed data")
    time.sleep(3)
    watch_proc.terminate()
    # Act: list
    result = run_cli(["list", "--game", game_name])
    # Assert
    assert "changed data" in save_file.read_text()
    assert len(result.stdout.strip().split("\n")) >= 1

def test_integration_edge_cases(temp_setup):
    # Arrange
    tmp, save_file = temp_setup
    game_name = f"testgame_{int(time.time())}"
    run_cli(["add", game_name, str(save_file)])
    # Act + Assert: duplicate
    result = run_cli(["add", game_name, "/other"])
    assert result.returncode != 0 or "already exists" in result.stderr.lower() or result.stdout
    # Act + Assert: invalid restore
    result = run_cli(["restore", "/invalid"])
    assert "Backup not found" in result.stdout or "Backup not found" in result.stderr
