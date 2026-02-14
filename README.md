# GameSave-VCS
GameSave-VCS is a Python-based tool that brings the power of Git version control to your PC game saves. It acts as an automated "Time Machine" for your games, allowing you to instantly restore your progress to a previous point in time, even if the game doesn't support manual saves.

**Key Features**:
- **Git Strategy (Default)**: Efficient delta-based backups using git commits (only stores changes between saves for space efficiency and full history).
- **Extensible Backends**: Choose `git` (default) or `full-copy` (original full folder copy-paste) via `--backend` for flexibility.
- **Full Folder + Recursive Subdirectory Support**: Handles entire save dirs (e.g., Minecraft worlds) in both strategies.
See Architectural Choices for tradeoffs/details.

## Installation
```bash
pip install -e .                  # CLI-only (pure Python backend)
pip install -e .[test]            # + pytest/coverage
```

## Running in Headless/Docker
Add `xvfb` to apt installs (for tests). Prefix: `xvfb-run pytest ...`

## Usage and Demos
GameSave-VCS supports 10 popular games out-of-the-box with predefined save paths (mostly directories for complex saves like Minecraft worlds; Linux-focused examples; adjust for your setup/OS/Steam/Proton installs as needed). Use `gamesave games --list` or `gamesave games --search <query>` (e.g. "elden") to browse/search them. The `add` command accepts an optional save path (supporting files **or full directories recursively**) for supported games (auto-fills predefined path; no existence check on add - taken as user-provided). If path missing on backup/watch, soft warning ("Backup skipped... nothing to backup yet") - non-blocking.

**Note on Backends**: Default is `git` for efficient deltas (git stores only changes); use `--backend full-copy` for original full copy-paste. Config stored per-game in `config.json`.

**Architectural Note**: Predefined paths are directories, aligning with recursive support. Change detection uses recursive SHA256 (contents + relpaths) to detect any mod in save structure. For git backend, backups are commits in per-game repo at `~/.gamesave-vcs/backups/<game>/.git`; full-copy uses timestamped copies.

Backups/repos in `~/.gamesave-vcs/backups/` , config in `~/.gamesave-vcs/config.json`.

### Quick CLI Summary
```bash
gamesave add <game> [save_path] [--force] [--backend git|full-copy]  # e.g. gamesave add Minecraft --backend git (default for deltas)
gamesave games --list             # List all 10 supported games + paths
gamesave games --search <query>   # Search (e.g. gamesave games --search witch)
gamesave watch <game>             # Auto-backup on change (SHA256 detect; backend from config)
gamesave list [--game <name>]     # Backups (reverse chrono; git shows repo@commit specs, full-copy timestamped)
gamesave restore [backup_spec]    # Restore; spec= path (full-copy) or repo@commit (git); omitted=latest overall
gamesave backup <game>            # Manual (uses game's backend)
```

Run `gamesave <cmd> --help` for details (or see full options below).

### Examples
Each example starts from scratch (fresh install assumed; run `pip install -e .` if needed). Cleanups included. Problems solved and differences noted.

#### Example 1: Manual Backup/Restore for Custom Game (Full-Copy Backend)
**Problem solved**: You made bad progress in a non-supported game (e.g., modded save) and want quick one-off backup/restore without ongoing monitoring.  
**Differs from others**: Explicit/manual control; demo's full-copy (old style). Use `--backend git` (default) for delta-efficient VCS.

**Architectural choice**: full-copy uses `shutil.copytree`/`rmtree` for recursive dirs/files; simple, no deps.

Full journey (recursive folder + full-copy):
1. Install + create initial save folder (with substructure):
```bash
pip install -e .
mkdir -p ~/customgame/saves/subdir
echo "level 5 progress" > ~/customgame/saves/subdir/data.txt
echo "config" > ~/customgame/saves/config.ini
```

2. Add game + manual backup (explicit full-copy), simulate bad change:
```bash
gamesave add mygame ~/customgame/saves --backend full-copy
gamesave backup mygame
echo "level 10 (bad) progress" > ~/customgame/saves/subdir/data.txt
```

3. List backups + restore previous:
```bash
gamesave list --game mygame  # timestamped dir e.g. <timestamp>_saves
gamesave restore ~/.gamesave-vcs/backups/mygame/<timestamp>_saves
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
- `add <name> [path] [--force] [--backend git|full-copy]`: Add game (supports file/dir save paths recursively; --backend git (default, deltas) or full-copy; --force updates). 
- `games [--list | --search <query>]`: List/search supported games.
- `watch <name> [--interval <secs>]`: Start watcher (SHA256 detect; backend from config).
- `list [--game <name>]`: List saves (reverse chrono; git: repo@commit specs; full-copy: timestamped).
- `restore [backup_spec]`: Restore (path for full-copy, repo@commit for git; omitted=latest overall).
- `backup <name>`: Manual backup using game's backend.

### Architectural Choices
Documented inline; summary:
- **Extensible Strategies**: Strategy pattern in backup.py with GitStrategy (default: deltas via commits for efficiency/space) and FullCopyStrategy (legacy full copy-paste). Dispatch via config/backend; detect for legacy. Enables future backends.
- **Git Default for Delta Efficiency**: Git per-game repo stores changes only (commits handle diffs); sync via copy to working tree + git add/commit/reset. Tradeoff: requires git, but far better than full copies for repeated saves.
- **Recursive Support + Hashing**: `shutil.copytree`/`os.walk` (sorted) for dirs/files in both; SHA256 for change detect in watcher.
- **Backward/ Legacy Compat**: Old full-copy backups listable; old config str auto full-copy; CLI/API unchanged.
- **Restore UX**: Optional spec , auto latest across backends , global for UX.
- **Error/Headless**: Git uses dummy config ; soft skips ; pure Python + subprocess git.
These prioritize usability , efficiency (git deltas) , extensibility , maintainability.

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

