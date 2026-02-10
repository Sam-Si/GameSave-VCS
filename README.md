# GameSave-VCS
GameSave-VCS is a Python-based tool that brings the power of Git version control to your PC game saves. It acts as an automated "Time Machine" for your games, allowing you to instantly restore your progress to a previous point in time, even if the game doesn't support manual saves.

**Key Feature: Full Folder + Recursive Subdirectory Support**  
Instead of limiting to single files, GameSave-VCS now fully supports entire save folders (including subdirectories) recursively. This was an architectural decision to better handle real-world game saves (e.g., Minecraft worlds with multiple files/folders, modded saves). See Architectural Choices section for details on implementation tradeoffs.

## Installation
```bash
pip install -e .                  # CLI-only (pure Python backend)
pip install -e .[test]            # + pytest/coverage
```

## Running in Headless/Docker
Add `xvfb` to apt installs (for tests). Prefix: `xvfb-run pytest ...`

## Usage and Demos
GameSave-VCS supports 10 popular games out-of-the-box with predefined save paths (mostly directories for complex saves like Minecraft worlds; Linux-focused examples; adjust for your setup/OS/Steam/Proton installs as needed). Use `gamesave games --list` or `gamesave games --search <query>` (e.g. "elden") to browse/search them. The `add` command accepts an optional save path (now supporting files **or full directories recursively**) for supported games (auto-fills predefined path; no existence check on add - taken as user-provided). If path missing on backup/watch, soft warning ("Backup skipped... nothing to backup yet") - non-blocking.

**Architectural Note**: Predefined paths for supported games are directories, aligning with recursive folder support. Change detection uses recursive SHA256 (file contents + relative paths in dirs) to reliably detect modifications anywhere in the save structure. Backups for folders create timestamped subdirectories in `~/.gamesave-vcs/backups/<game>/` mirroring the original tree.

Backups are stored in `~/.gamesave-vcs/backups/` and configs in `~/.gamesave-vcs/config.json`.

### Quick CLI Summary
```bash
gamesave add <game> [save_path] [--force]  # save_path now file or dir (recursive); e.g. ... or gamesave add Minecraft; --force to update existing
gamesave games --list             # List all 10 supported games + paths (many are dirs)
gamesave games --search <query>   # Search (e.g. gamesave games --search witch)
gamesave watch <game>             # Auto-backup on change (recursive SHA256 for dirs/files)
gamesave list [--game <name>]     # Backups (reverse chrono; supports file/dir paths)
gamesave restore <backup_path>    # Restore from list (file or dir backup)
gamesave backup <game>            # Manual backup
```

Run `gamesave <cmd> --help` for details (or see full options below).

### Examples
Each example starts from scratch (fresh install assumed; run `pip install -e .` if needed). Cleanups included. Problems solved and differences noted.

#### Example 1: Manual Backup/Restore for Custom Game (with Folder Support)
**Problem solved**: You made bad progress in a non-supported game (e.g., modded save) and want quick one-off backup/restore without ongoing monitoring.  
**Differs from others**: Explicit/manual control (no watcher/auto); simplest for occasional use vs. hands-free or supported-auto.

**Architectural choice documented here**: For folder support, we use `shutil.copytree` (recursive) for directories vs. `copy2` for files; this choice keeps code simple, avoids external deps like rsync, and ensures subdir structure is preserved exactly in backups. Restore mirrors this with rmtree/copytree for safety.

Full journey (now using recursive folder to demo new capability):
1. Install + create initial save folder (with substructure):
```bash
pip install -e .
mkdir -p ~/customgame/saves/subdir
echo "level 5 progress" > ~/customgame/saves/subdir/data.txt
echo "config" > ~/customgame/saves/config.ini
```

2. Add game + manual backup, simulate bad change:
```bash
gamesave add mygame ~/customgame/saves
gamesave backup mygame
echo "level 10 (bad) progress" > ~/customgame/saves/subdir/data.txt
```

3. List backups + restore previous:
```bash
gamesave list --game mygame  # Note timestamped dir path (e.g. <timestamp>_saves)
gamesave restore ~/.gamesave-vcs/backups/mygame/<timestamp>_saves  # Use exact from list (dir)
cat ~/customgame/saves/subdir/data.txt  # Restored to "level 5 progress" (recursive)
```

4. Cleanup:
```bash
rm -rf ~/.gamesave-vcs ~/customgame
```

#### Example 2: Auto-Watcher for Custom Game (Folder Support)
**Problem solved**: Forgets manual backups during long play sessions; auto-detects save changes (e.g., autosave in RPG) for time-machine restore.  
**Differs from others**: Hands-free monitoring (vs. manual); custom game (no predefined path) vs. supported.

**Architectural choice documented here**: Watcher now uses recursive `get_save_hash` (os.walk + sorted files + content hash) instead of single-file hash. This choice ensures any subdir change triggers backup without polling every file separately (efficient, deterministic via sorting). Polling interval kept for simplicity vs. inotify (platform-specific).

Full journey (demo recursive folder):
1. Install + create initial save folder:
```bash
pip install -e .
mkdir -p ~/customgame/saves
echo "level 5 progress" > ~/customgame/saves/data.txt
```

2. Add + initial backup + start watcher, simulate change:
```bash
gamesave add mygame ~/customgame/saves
gamesave backup mygame  # Initial backup (for demo restore to old state)
gamesave watch mygame --interval 2 &  # Bg auto-poll
sleep 3
echo "level 15 progress" > ~/customgame/saves/data.txt  # Triggers detect/backup (recursive hash)
sleep 5
pkill -f "gamesave watch"  # Stop
```

3. List + restore (pick older <timestamp> from list output to restore initial state):
```bash
gamesave list --game mygame
gamesave restore ~/.gamesave-vcs/backups/mygame/<older_timestamp>_saves  # Dir backup path
cat ~/customgame/saves/data.txt  # Restored to level 5
```

4. Cleanup:
```bash
rm -rf ~/.gamesave-vcs ~/customgame
```

#### Example 3: Supported Game with Auto-Path + Search (Folder Demo)
**Problem solved**: Don't remember exact save location for popular game (e.g., Minecraft worlds); quick search/add without manual path lookup.  
**Differs from others**: Leverages predefined list/search/auto-path (vs. custom manual input); combines with watcher for full journey.

**Architectural choice documented here**: Supported games use dir paths (e.g. Minecraft saves/); recursive support chosen over file-only to handle this natively. Backup dirs in per-game subfolders preserve structure without flattening (tradeoff: uses more space than deltas but simpler, no Git dep).

Full journey (using folder for Minecraft-style save):
1. Install + create initial save folder:
```bash
pip install -e .
mkdir -p ~/mc_test/worlds
echo "world data" > ~/mc_test/worlds/level.dat
echo "config" > ~/mc_test/config.ini
```

2. Search supported + add (override path for demo), start watcher, change:
```bash
gamesave games --search mine  # Finds Minecraft + path hint
gamesave add Minecraft ~/mc_test/worlds  # Override predefined with our test dir
gamesave watch Minecraft --interval 2 &
sleep 3
echo "updated world" > ~/mc_test/worlds/level.dat  # Triggers auto-backup (recursive)
sleep 5
pkill -f "gamesave watch"
```

3. List + restore:
```bash
gamesave list --game Minecraft
gamesave restore ~/.gamesave-vcs/backups/Minecraft/<timestamp>_worlds  # Dir from list
cat ~/mc_test/worlds/level.dat  # Restored
```

4. Cleanup:
```bash
rm -rf ~/.gamesave-vcs ~/mc_test
```

#### Example 4: Handling Missing Save Path (Edge Case)
**Problem solved**: Game not installed yet or save path (file/dir) missing (e.g., fresh setup); still add/config without failure, soft-skip backups.  
**Differs from others**: Graceful non-blocking for absent paths (vs. strict; all prior assume existing save).

**Architectural choice documented here**: Existence checks are soft (only on backup/watch, not add) to support games not yet installed; for dirs/files unified via Path.exists() + is_file/is_dir in backup/restore. This choice prioritizes user-friendliness over strict validation.

Full journey (using dir in valid step):
1. Install + add with missing path (no verify):
```bash
pip install -e .
gamesave add missinggame /nonexistent/save.dat  # Succeeds (user-provided)
```

2. Attempt backup (soft skip), simulate create + retry:
```bash
gamesave backup missinggame  # Warns: "Backup skipped... nothing to backup yet"
mkdir -p /tmp/missing/saves
echo "initial" > /tmp/missing/saves/data.txt
gamesave add missinggame /tmp/missing/saves --force  # Re-add (dir; --force to update path)
gamesave backup missinggame  # Now succeeds (recursive; now 2 backups total)
```

3. List + restore (demo non-latest + optional latest; `gamesave restore` with no args/flags auto-restores the last/overall latest save):
```bash
gamesave list --game missinggame  # Shows multiple; pick older for non-latest
gamesave restore ~/.gamesave-vcs/backups/missinggame/<older_timestamp>_saves  # Explicit non-latest
gamesave restore  # No args = auto latest save (demo'd here)
cat /tmp/missing/saves/data.txt  # Restored
```

4. Cleanup:
```bash
rm -rf ~/.gamesave-vcs /tmp/missing
```

### Full CLI Options
- `add <name> [path] [--force]`: Add game (name, optional save path - now supports files **or entire directories recursively**; uses predefined for supported games). --force updates existing game's path. (Architectural choice: no type enforcement on add for flexibility.)
- `games [--list | --search <query>]`: List 10 supported games or search them.
- `watch <name> [--interval <secs>]`: Start watcher (default 5s polling; recursive change detection).
- `list [--game <name>]`: List saves (reverse chrono; optional filter; now lists dir backups too).
- `restore [backup_path]`: Restore backup (handles file or full dir recursively; omitted = latest overall backup for quick undo).
- `backup <name>`: Manual backup.

### Architectural Choices
Documented inline in examples above; summary:
- **Recursive Support**: Chose `shutil.copytree`/`rmtree` + `os.walk` (sorted) for dirs vs single-file ops. Tradeoff: full copies (space-heavy but reliable, no diff needed) over complex Git integration (keeps deps minimal, pure Python).
- **Hashing**: Recursive SHA256 includes relpaths + content for complete change detection in subdirs; deterministic sort avoids false negatives. Chose over file mtime/size for robustness (games may touch files without content change).
- **Backward Compat**: Single files still work unchanged (copy2, simple hash); dirs become subdirs in backups. List/restore unified via is_file/is_dir checks.
- **Error Handling**: Soft skips, parent mkdirs in restore for UX; no symlinks in hash (followlinks=False) to prevent loops.
- **Restore UX**: Made `backup_path` optional (defaults to latest via `list_saves()[0]`). Thought: greatly improves common "undo last mistake" flows for gamers (no need to copy long path); chose global latest (vs per-game --game) for simplicity/minimal args. Non-latest still supported explicitly for precise history restore.
- **Why not Git?**: Avoided to keep lightweight/CLI-only; backups are timestamped copies for instant restore. Future: could add Git backend as option.
These choices prioritize gamer usability (simple, works for folders) and code maintainability.

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

