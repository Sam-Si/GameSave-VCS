# GameSave-VCS

GameSave-VCS provides automated version control for PC game saves, supporting both delta-based Git backups (via Dulwich) and simple full-copy strategies.

## Prerequisites
- **Bazel** (7.4.1 recommended)

## Quick Start: End-to-End Manual Test
This walkthrough verifies the core lifecycle: configuration, backup, change detection, and restoration.

```bash
# 1. Create a dummy save directory
mkdir -p ~/test-save
echo "Initial State" > ~/test-save/save.dat

# 2. Add the game to GameSave-VCS
bazel run //:gamesave -- add TestGame ~/test-save --backend git

# 3. Create initial backup
bazel run //:gamesave -- backup TestGame

# 4. Modify the save (simulate progress/corruption)
echo "Corrupted State" > ~/test-save/save.dat

# 5. List backups and restore the latest
bazel run //:gamesave -- list --game TestGame
bazel run //:gamesave -- restore  # Omitted spec restores latest overall

# 6. Verify restoration
cat ~/test-save/save.dat  # Should output "Initial State"

# 7. Test the Watcher (Auto-backup)
bazel run //:gamesave -- watch TestGame --interval 2 &
sleep 3
echo "New Progress" > ~/test-save/save.dat
sleep 5
pkill -f "gamesave watch"

# 8. Verify auto-backup exists
bazel run //:gamesave -- list --game TestGame
```

## Automated Testing
Run the full suite of unit and integration tests with coverage:

```bash
# Run all tests
bazel run //:pytest -- tests/

# Run specific test file
bazel run //:pytest -- tests/test_backup.py

# Run with coverage report
bazel run //:pytest -- tests/ --cov=gamesave_vcs --cov-report=term-missing
```

## CLI Reference
- `add <name> [path] [--backend git|full-copy]`: Register a game.
- `backup <name>`: Manual backup.
- `watch <name> [--interval <secs>]`: Monitor for changes.
- `list [--game <name>]`: Show backup history.
- `restore [spec]`: Restore to a specific or latest state.
- `games [--list | --search <query>]`: Browse supported games.

## Configuration & Storage
- **Config**: `~/.gamesave-vcs/config.json`
- **Backups**: `~/.gamesave-vcs/backups/`
