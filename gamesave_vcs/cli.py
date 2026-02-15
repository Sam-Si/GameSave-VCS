import argparse
import time
from argparse import Namespace
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union

# Local imports (types inferred from typed modules where possible)
from .backup import backup_save, list_saves, restore_save
from .config import (
    add_game,
    get_supported_game_path,
    list_supported_games,
    search_games,
)
from .watcher import GameWatcher


def main() -> None:
    """CLI entrypoint: parse args and dispatch to commands (add/watch/list/etc).
    Uses subparsers for commands; types args for clarity.
    """
    parser = argparse.ArgumentParser(
        description="GameSave-VCS: Version control for game saves "
        "(git strategy default for efficient deltas; --backend=full-copy for original)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add a game to watch")
    add_parser.add_argument("name", help="Game name")
    add_parser.add_argument(
        "path",
        nargs="?",
        help="Path to save file or directory (optional for supported games)",
    )
    add_parser.add_argument(
        "--force",
        action="store_true",
        help="Update existing game path if already added",
    )
    add_parser.add_argument(
        "--backend",
        choices=["git", "full-copy"],
        default="git",
        help="Backup strategy: git (default, efficient delta-based VCS via pure-Python Dulwich) or full-copy (original full folder copy-paste)",
    )

    watch_parser = subparsers.add_parser(
        "watch", help="Start watcher for a game"
    )
    watch_parser.add_argument("name", help="Game name")
    watch_parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Polling interval in seconds (default: 5)",
    )

    list_parser = subparsers.add_parser("list", help="List all saves")
    list_parser.add_argument("--game", help="Filter by game name")

    games_parser = subparsers.add_parser(
        "games", help="List or search supported games"
    )
    games_parser.add_argument(
        "--list", action="store_true", help="List all supported games"
    )
    games_parser.add_argument("--search", help="Search for games by name")

    restore_parser = subparsers.add_parser("restore", help="Restore a save")
    restore_parser.add_argument(
        "backup_path",
        nargs="?",
        help="Backup spec to restore (path for full-copy or repo@commit for git); "
        "omitted = latest overall (across backends)",
    )

    backup_parser = subparsers.add_parser(
        "backup", help="Manually backup a game"
    )
    backup_parser.add_argument("name", help="Game name")

    args: Namespace = parser.parse_args()

    if args.command == "add":
        # path: Optional[str] (from CLI arg or supported; add_game accepts str|Path for flex)
        path: Optional[str] = args.path
        if path is None:
            supported_path: Optional[str] = get_supported_game_path(args.name)
            if supported_path:
                path = supported_path
                print(f"Using suggested path for {args.name}: {path}")
            else:
                print("Path required for unsupported games")
                return
        # Pass backend (default git for delta efficiency; full-copy for old style)
        add_game(
            args.name,
            path,
            force=getattr(args, "force", False),
            backend=getattr(args, "backend", "git"),
        )
    elif args.command == "watch":
        # watcher typed in GameWatcher class
        watcher = GameWatcher(args.name, args.interval)
        watcher.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            watcher.stop()
    elif args.command == "list":
        # list_saves returns typed list of tuples from backup; backup_spec can be Path|str
        saves: List[tuple[datetime, Union[Path, str], str]] = list_saves(
            args.game
        )
        for ts, backup_spec, game in saves:
            print(f"{ts} | {game} | {backup_spec}")
    elif args.command == "games":
        if getattr(args, "list", False):
            # games: List[str]
            games: List[str] = list_supported_games()
            for i, game in enumerate(games, 1):
                # avoid shadowing 'path' from list block (Union[Path,str] vs str)
                suggested_path: Optional[str] = get_supported_game_path(game)
                print(f"{i}. {game} - Suggested save path: {suggested_path}")
        elif args.search:
            results: List[str] = search_games(args.search)
            if results:
                for game in results:
                    # avoid shadowing
                    suggested_path: Optional[str] = get_supported_game_path(
                        game
                    )
                    print(f"{game} - Suggested save path: {suggested_path}")
            else:
                print("No matching games found")
        else:
            print("Use --list or --search <query>")
    elif args.command == "restore":
        # backup_path: Optional[str | Path] from arg, matches restore_save
        restore_save(args.backup_path)
    elif args.command == "backup":
        # name: str
        backup_save(args.name)


if __name__ == "__main__":
    main()
