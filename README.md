# GameSave-VCS

GameSave-VCS provides automated version control for PC game saves, supporting both delta-based Git backups (via Dulwich), simple full-copy strategies, and an optimized chunked storage backend for massive save files.

## Prerequisites
- **Python** 3.13+
- **Bazel** (7.4.1 recommended) - for hermetic builds
- **pip-tools** (optional, for regenerating dependency locks)

## Installation

### Via pip (standard)
```bash
pip install -e .
```

### Via Bazel (hermetic)
Bazel ensures all dependencies (including Python 3.13 itself) are managed hermetically.
```bash
# Build the project
bazel build //...

# Run CLI
bazel run //:gamesave -- <command>
```

---

## Features

### 1. Retro TUI (Terminal User Interface)
A visually rich, 8-bit inspired interface for managing your saves.
```bash
bazel run //:gamesave -- tui
```
*Requires `textual` and `rich` (included in Bazel build).*

### 2. Multi-Strategy Backends
- **Git (Default):** Efficient delta-based backups using `dulwich`.
- **Full-Copy:** Simple timestamped directory mirrors with hard-link deduplication.
- **Chunked:** optimized for files >100MB; splits files into chunks to deduplicate internal changes.

### 3. Smart Monitoring
- **Inotify (Linux):** Zero-polling, kernel-level event monitoring.
- **Polling (Cross-platform):** High-frequency hashing fallback for Windows/macOS.

---

## Developer Guide

### Automated Testing
We use `pytest` integrated with Bazel.

#### Run all tests
```bash
bazel run //:pytest -- tests/
```

#### Run tests with Coverage
Because Bazel runs tests in a sandbox, `pytest-cov` requires the absolute path to the source tree to map coverage data correctly.
```bash
bazel run //:pytest -- tests/ --cov=$(pwd)/gamesave_vcs --cov-report=term-missing
```

### Dependency Management
Dependencies are locked in `requirements_lock.txt`. If you modify `pyproject.toml`, you must regenerate the lockfile.

#### Regenerating the Lockfile
We use `pip-compile` with specific flags to avoid circular dependencies in the Bazel graph (specifically stripping extras from transitive dependencies like `markdown-it-py`).
```bash
pip install pip-tools
pip-compile --extra test --strip-extras --generate-hashes --output-file=requirements_lock.txt pyproject.toml
```

### Troubleshooting Bazel
- **Read-only Filesystem Errors:** Tests must use the `tmp_path` fixture. Writing to absolute paths like `/dst` will fail in the Bazel sandbox.
- **ModuleNotFoundError:** Ensure the dependency is added to the `deps` attribute in `BUILD.bazel` AND included in `requirements_lock.txt`.
- **Async Test Failures:** Ensure `pytest-asyncio` is installed and the `asyncio_default_fixture_loop_scope` is considered if using older pytest versions.

---

## CLI Reference

| Command | Description | Example |
|---------|-------------|---------|
| `add <name> [path]` | Register a game | `gamesave add EldenRing ~/saves/er` |
| `backup <name>` | Manual backup | `gamesave backup EldenRing` |
| `watch <name>` | Start background monitor | `gamesave watch EldenRing --interval 5` |
| `list` | Show backup history | `gamesave list --game EldenRing` |
| `restore [spec]` | Restore to state | `gamesave restore repo@commit_hash` |
| `tui` | Launch Retro Manager | `gamesave tui` |

## File Locations
- **Config**: `~/.gamesave-vcs/config.json`
- **Backups**: `~/.gamesave-vcs/backups/`
