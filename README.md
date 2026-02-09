# GameSave-VCS
GameSave-VCS is a Python-based tool that brings the power of Git version control to your PC game saves. It acts as an automated "Time Machine" for your games, allowing you to instantly restore your progress to a previous point in time, even if the game doesn't support manual saves.

## Installation
```bash
pip install -e .                  # CLI-only (pure Python backend)
pip install -e .[test]            # + pytest/coverage
```

## Usage (CLI-only)
```bash
gamesave add <game> <save_path>    # e.g. gamesave add tekken ~/saves/tekken.dat
gamesave watch <game>              # SHA256 every 30s + auto-backup on change
gamesave list [--game <name>]      # All saves (reverse chrono)
gamesave restore <backup_path>     # From list output
```

The tool stores backups in `~/.gamesave-vcs/backups/` and configs in `~/.gamesave-vcs/config.json`.

## Running in Headless/Docker
Add `xvfb` to apt installs (for tests). Prefix: `xvfb-run pytest ...`

## Useful Commands (from project root)
```bash
# Setup
pip install -e .[test]

# CLI examples
gamesave add tekken ~/game.sav
gamesave watch tekken
gamesave list
gamesave list --game tekken
gamesave restore ~/.gamesave-vcs/backups/tekken/2024...sav

# Tests (AAA pattern everywhere, full coverage)
pytest                                  # Basic
./run_tests.sh                          # Full coverage + HTML (recommended)
pytest tests/test_backup.py             # Specific
pytest --cov=gamesave_vcs --cov-report=html  # Coverage report only
pytest -q --tb=no                       # Quiet
```

- Coverage HTML: `htmlcov/index.html` (100% on logic/branches).
- See `tests/` (refactored to Arrange-Act-Assert) + `run_tests.sh`.
- Backups/configs in `~/.gamesave-vcs/`.

# Integration tests (real, no mocks)
pytest tests/integration -q --tb=no

## Demo Example
1. Create a test save:
```bash
mkdir -p ~/testgame
echo "level 5 progress" > ~/testgame/save.dat
```

2. Add and backup:
```bash
gamesave add tekken ~/testgame/save.dat
gamesave backup tekken
```

3. Simulate change:
```bash
echo "level 10 progress" > ~/testgame/save.dat
```

4. List and restore:
```bash
gamesave list
gamesave restore ~/.gamesave-vcs/backups/tekken/<timestamp>_save.dat
cat ~/testgame/save.dat  # Restored!
```


## CLI Options (from `gamesave --help`)
- `add <name> <path>`: Add game (name, save file path).
- `watch <name> [--interval <secs>]`: Start watcher (default 5s polling).
- `list [--game <name>]`: List saves (reverse chrono; optional filter).
- `restore <backup_path>`: Restore backup.
- `backup <name>`: Manual backup.

Run `gamesave <cmd> --help` for details.


5. Watch demo (start watcher, simulate change):
```bash
gamesave watch tekken --interval 2 &  # Bg watch
sleep 3
echo "level 15 progress" > ~/testgame/save.dat
sleep 5  # Allow detect/backup
pkill -f "gamesave watch"  # Stop
gamesave list  # See auto-backup
```

