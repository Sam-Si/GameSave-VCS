# GameSave-VCS
GameSave-VCS is a Python-based tool that brings the power of Git version control to your PC game saves. It acts as an automated "Time Machine" for your games, allowing you to instantly restore your progress to a previous point in time, even if the game doesn't support manual saves.

## Installation
```bash
pip install -e .                  # CLI-only (pure Python backend)
pip install -e .[test]            # + pytest/coverage
```

## Running in Headless/Docker
Add `xvfb` to apt installs (for tests). Prefix: `xvfb-run pytest ...`

## Usage and Demos
GameSave-VCS supports 10 popular games out-of-the-box with predefined save paths (Linux-focused examples; adjust for your setup/OS/Steam/Proton installs as needed). Use `gamesave games --list` or `gamesave games --search <query>` (e.g. "elden") to browse/search them. The `add` command accepts an optional save path for supported games (auto-fills predefined path; no existence check on add - taken as user-provided). If path missing on backup/watch, soft warning ("Backup skipped... nothing to backup yet") - non-blocking.

Backups are stored in `~/.gamesave-vcs/backups/` and configs in `~/.gamesave-vcs/config.json`.

### Quick CLI Summary
```bash
gamesave add <game> [save_path] [--force]  # e.g. ... or gamesave add Minecraft; --force to update existing
gamesave games --list             # List all 10 supported games + paths
gamesave games --search <query>   # Search (e.g. gamesave games --search witch)
gamesave watch <game>             # Auto-backup on change (SHA256 polling)
gamesave list [--game <name>]     # Backups (reverse chrono)
gamesave restore <backup_path>    # Restore from list
gamesave backup <game>            # Manual backup
```

Run `gamesave <cmd> --help` for details (or see full options below).

### Examples
Each example starts from scratch (fresh install assumed; run `pip install -e .` if needed). Cleanups included. Problems solved and differences noted.

#### Example 1: Manual Backup/Restore for Custom Game
**Problem solved**: You made bad progress in a non-supported game (e.g., modded save) and want quick one-off backup/restore without ongoing monitoring.  
**Differs from others**: Explicit/manual control (no watcher/auto); simplest for occasional use vs. hands-free or supported-auto.

Full journey:
1. Install + create initial save:
```bash
pip install -e .
mkdir -p ~/customgame
echo "level 5 progress" > ~/customgame/save.dat
```

2. Add game + manual backup, simulate bad change:
```bash
gamesave add mygame ~/customgame/save.dat
gamesave backup mygame
echo "level 10 (bad) progress" > ~/customgame/save.dat
```

3. List backups + restore previous:
```bash
gamesave list --game mygame  # Note timestamped path
gamesave restore ~/.gamesave-vcs/backups/mygame/<timestamp>_save.dat  # Copy exact path from list
cat ~/customgame/save.dat  # Restored to "level 5 progress"
```

4. Cleanup:
```bash
rm -rf ~/.gamesave-vcs ~/customgame
```

#### Example 2: Auto-Watcher for Custom Game
**Problem solved**: Forgets manual backups during long play sessions; auto-detects save changes (e.g., autosave in RPG) for time-machine restore.  
**Differs from others**: Hands-free monitoring (vs. manual); custom game (no predefined path) vs. supported.

Full journey:
1. Install + create initial save:
```bash
pip install -e .
mkdir -p ~/customgame
echo "level 5 progress" > ~/customgame/save.dat
```

2. Add + start watcher, simulate change:
```bash
gamesave add mygame ~/customgame/save.dat
gamesave watch mygame --interval 2 &  # Bg auto-poll
sleep 3
echo "level 15 progress" > ~/customgame/save.dat  # Triggers detect/backup
sleep 5
pkill -f "gamesave watch"  # Stop
```

3. List + restore:
```bash
gamesave list --game mygame
gamesave restore ~/.gamesave-vcs/backups/mygame/<timestamp>_save.dat
cat ~/customgame/save.dat  # Restored
```

4. Cleanup:
```bash
rm -rf ~/.gamesave-vcs ~/customgame
```

#### Example 3: Supported Game with Auto-Path + Search
**Problem solved**: Don't remember exact save location for popular game (e.g., Minecraft worlds); quick search/add without manual path lookup.  
**Differs from others**: Leverages predefined list/search/auto-path (vs. custom manual input); combines with watcher for full journey.

Full journey:
1. Install + create initial save:
```bash
pip install -e .
mkdir -p ~/mc_test
echo "world data" > ~/mc_test/level.dat
```

2. Search supported + add (override path for demo), start watcher, change:
```bash
gamesave games --search mine  # Finds Minecraft + path hint
gamesave add Minecraft ~/mc_test/level.dat  # Override predefined with our test file
gamesave watch Minecraft --interval 2 &
sleep 3
echo "updated world" > ~/mc_test/level.dat  # Triggers auto-backup
sleep 5
pkill -f "gamesave watch"
```

3. List + restore:
```bash
gamesave list --game Minecraft
gamesave restore ~/.gamesave-vcs/backups/Minecraft/<timestamp>_level.dat  # Use exact from list
cat ~/mc_test/level.dat  # Restored
```

4. Cleanup:
```bash
rm -rf ~/.gamesave-vcs ~/mc_test
```

#### Example 4: Handling Missing Save Path (Edge Case)
**Problem solved**: Game not installed yet or save file missing (e.g., fresh setup); still add/config without failure, soft-skip backups.  
**Differs from others**: Graceful non-blocking for absent paths (vs. strict; all prior assume existing save).

Full journey:
1. Install + add with missing path (no verify):
```bash
pip install -e .
gamesave add missinggame /nonexistent/save.dat  # Succeeds (user-provided)
```

2. Attempt backup (soft skip), simulate create + retry:
```bash
gamesave backup missinggame  # Warns: "Backup skipped... nothing to backup yet"
mkdir -p /tmp/missing
echo "initial" > /tmp/missing/save.dat
gamesave add missinggame /tmp/missing/save.dat  # Re-add if needed
gamesave backup missinggame  # Now succeeds
```

3. List + restore:
```bash
gamesave list --game missinggame
gamesave restore ~/.gamesave-vcs/backups/missinggame/<timestamp>_save.dat
cat /tmp/missing/save.dat  # Restored
```

4. Cleanup:
```bash
rm -rf ~/.gamesave-vcs /tmp/missing
```

### Full CLI Options
- `add <name> [path] [--force]`: Add game (name, optional save file path; uses predefined for supported games). --force updates existing game's path.
- `games [--list | --search <query>]`: List 10 supported games or search them.
- `watch <name> [--interval <secs>]`: Start watcher (default 5s polling).
- `list [--game <name>]`: List saves (reverse chrono; optional filter).
- `restore <backup_path>`: Restore backup.
- `backup <name>`: Manual backup.

### Testing (from project root)
```bash
# Setup
pip install -e .[test]

# Run tests
pytest                                  # Basic
./run_tests.sh                          # Full coverage + HTML (recommended; AAA pattern)
pytest tests/test_backup.py             # Specific
pytest --cov=gamesave_vcs --cov-report=html  # Coverage only
pytest -q --tb=no                       # Quiet
pytest tests/integration -q --tb=no      # Integration (real, no mocks)
```

- Coverage HTML: `htmlcov/index.html` (100% on logic/branches).
- See `tests/` + `run_tests.sh`.
- Backups/configs in `~/.gamesave-vcs/`.

