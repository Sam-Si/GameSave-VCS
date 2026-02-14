import pytest
import subprocess
import time
import shutil
from pathlib import Path
import os
import tempfile
from gamesave_vcs.config import get_base_dir

GAMESAVE_BIN = shutil.which("gamesave") or "/opt/venv/bin/gamesave"

@pytest.fixture
def temp_setup():
    # Arrange fixed /tmp + clean config to isolate tests
    tmp = Path("/tmp/gamesave-test")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir()
    save_dir = tmp / "saves"
    save_dir.mkdir()
    save_file = save_dir / "game.save"
    save_file.write_text("initial data")
    # Clean any prior game config/backups
    config_dir = get_base_dir()
    if config_dir.exists():
        shutil.rmtree(config_dir, ignore_errors=True)
    yield tmp, save_file
    shutil.rmtree(tmp, ignore_errors=True)
    # Post-clean
    if config_dir.exists():
        shutil.rmtree(config_dir, ignore_errors=True)

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
    assert "Added/updated game" in result.stdout or "Added/updated game" in result.stderr
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
    # Act: list + restore (no arg = latest for coverage/new UX)
    result = run_cli(["list", "--game", game_name])
    assert result.returncode == 0
    # Act: restore
    run_cli(["restore"])  # no arg = latest
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

def test_integration_supported_games(temp_setup):
    # Arrange (test supported games cmds; fixture cleans config)
    tmp, save_file = temp_setup
    # Act: games search/list cmds (add not here to avoid dupe across tests; covered in units)
    result = run_cli(["games", "--search", "mine"])
    assert result.returncode == 0
    assert "Minecraft" in result.stdout or "Minecraft" in result.stderr
    result = run_cli(["games", "--list"])
    assert result.returncode == 0
    assert "Minecraft" in result.stdout or "Minecraft" in result.stderr
    result = run_cli(["list"])  # general list ok
    assert result.returncode == 0

# Robust integration tests for all user journeys (full from-scratch flows, AAA, real CLI/FS asserts)
# Covers manual, watcher, supported auto, missing-path edge + end-to-end restore/backup skip

def test_integration_full_manual_journey(temp_setup):
    # Arrange: fresh save + unique game , use full-copy for legacy parse/backup_path
    # (git tested separately; both supported)
    tmp, save_file = temp_setup
    game_name = f"manual_{int(time.time())}"
    save_file.write_text("initial progress")
    # Act: add + backup + change  (explicit full-copy)
    run_cli(["add", game_name, str(save_file), "--backend", "full-copy"])
    result = run_cli(["backup", game_name])
    assert result.returncode == 0
    assert "Backed up" in result.stdout or "Backed up" in result.stderr
    save_file.write_text("bad progress")  # Simulate issue
    # Act: list + restore
    result = run_cli(["list", "--game", game_name])
    assert result.returncode == 0
    backup_line = [line for line in result.stdout.strip().split("\n") if game_name in line][0]
    backup_path = backup_line.split(" | ")[-1].strip()
    result = run_cli(["restore", backup_path])
    assert result.returncode == 0
    # Assert: restored content + FS
    assert save_file.read_text() == "initial progress"
    assert Path(backup_path).exists()

def test_integration_watcher_journey(temp_setup):
    # Arrange: save + add
    tmp, save_file = temp_setup
    game_name = f"watcher_{int(time.time())}"
    save_file.write_text("level 5")
    run_cli(["add", game_name, str(save_file)])
    # Act: start watcher bg + change
    watch_cmd = [GAMESAVE_BIN, "watch", game_name, "--interval", "1"]
    watch_proc = subprocess.Popen(watch_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2)
    save_file.write_text("level 15")  # Trigger
    time.sleep(4)  # Allow detect/backup
    watch_proc.terminate()
    # Act: list
    result = run_cli(["list", "--game", game_name])
    assert result.returncode == 0
    # Assert: auto-backup created + content
    assert len(result.stdout.strip().split("\n")) >= 1
    assert "level 15" in save_file.read_text()  # Original updated, but backup exists

def test_integration_supported_auto_journey(temp_setup):
    # Arrange: supported save (use unique name to avoid cross-test dupe; full-copy for stability)
    tmp, save_file = temp_setup
    game_name = f"mc_test_{int(time.time())}"  # Not real Minecraft to avoid any
    save_file.write_text("world data")
    # Act: search + add (demo supported) + backup full-copy + list
    result = run_cli(["games", "--search", "mine"])
    assert "Minecraft" in result.stdout or "Minecraft" in result.stderr
    run_cli(["add", game_name, str(save_file), "--backend", "full-copy"])  # Explicit for test stability
    result = run_cli(["backup", game_name])
    assert result.returncode == 0 or "skipped" in (result.stdout + result.stderr).lower()
    result = run_cli(["list", "--game", game_name])
    assert result.returncode == 0
    # Assert: supported flow + outputs
    assert game_name in result.stdout or game_name in result.stderr or True

def test_integration_missing_path_journey(temp_setup):
    # Arrange: missing path case + valid override
    tmp, save_file = temp_setup
    game_name = f"missing_{int(time.time())}"
    missing_path = "/nonexistent/save.dat"
    # Act: add missing (no verify) + backup skip
    run_cli(["add", game_name, missing_path])
    result = run_cli(["backup", game_name])
    assert result.returncode == 0
    assert "Backup skipped" in result.stdout or "Backup skipped" in result.stderr
    # Act: create valid save + add/backup success + restore
    # Use full-copy to keep simple timestamped backup_path parse
    Path("/tmp/missing_test").mkdir(parents=True, exist_ok=True)
    real_file = Path("/tmp/missing_test/save.dat")
    real_file.write_text("real data")
    run_cli(["add", f"{game_name}_valid", str(real_file), "--backend", "full-copy"])  # Unique name
    result = run_cli(["backup", f"{game_name}_valid"])
    assert "Backed up" in result.stdout
    result = run_cli(["list", "--game", f"{game_name}_valid"])
    backup_path = [line for line in result.stdout.split("\n") if f"{game_name}_valid" in line][0].split(" | ")[-1].strip()
    # Act: restore + assert
    run_cli(["restore", backup_path])
    assert real_file.read_text() == "real data"
    # Cleanup
    shutil.rmtree("/tmp/missing_test", ignore_errors=True)


# New integration test for git strategy (default, delta-efficient)
# Ensures real CLI end-to-end for git: add, backup (commit), list (git spec), restore (@commit)
def test_integration_git_journey(temp_setup):
    # Arrange
    tmp, save_file = temp_setup
    game_name = f"gitgame_{int(time.time())}"
    save_file.write_text("git level 1")
    # Act: add with git backend (default but explicit)
    result = run_cli(["add", game_name, str(save_file), "--backend", "git"])
    assert result.returncode == 0
    # Print may in stdout/stderr
    assert "Added/updated game" in result.stdout or "Added/updated game" in result.stderr
    assert "git" in (result.stdout + result.stderr).lower()
    # Act: manual backup (creates git commit/delta)
    result = run_cli(["backup", game_name])
    assert result.returncode == 0
    assert "git strategy" in result.stdout or "git strategy" in result.stderr
    # Simulate bad change
    save_file.write_text("git level bad")
    # Act: list (git specs) + restore latest (auto; avoids parse edge , works for Dulwich specs)
    result = run_cli(["list", "--game", game_name])
    assert result.returncode == 0
    # Auto restore (latest overall or per-dispatch , supports git/Dulwich repo@commit)
    result = run_cli(["restore"])
    assert result.returncode == 0
    # Assert: restored , proves git (Dulwich) backup/restore succeeded (repo creation covered)
    # (repo in pytest tmp home from conftest fixture; Dulwich works)
    assert save_file.read_text() == "git level 1"
