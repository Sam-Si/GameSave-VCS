import argparse
import time
from .config import add_game, get_game_path, list_supported_games, search_games, get_supported_game_path
from .backup import backup_save, list_saves, restore_save
from .watcher import GameWatcher

def main():
    parser = argparse.ArgumentParser(description='GameSave-VCS: Version control for game saves')
    subparsers = parser.add_subparsers(dest='command', required=True)

    add_parser = subparsers.add_parser('add', help='Add a game to watch')
    add_parser.add_argument('name', help='Game name')
    add_parser.add_argument('path', nargs='?', help='Path to save file (optional for supported games)')
    add_parser.add_argument('--force', action='store_true', help='Update existing game path if already added')

    watch_parser = subparsers.add_parser('watch', help='Start watcher for a game')
    watch_parser.add_argument('name', help='Game name')
    watch_parser.add_argument('--interval', type=int, default=5, help='Polling interval in seconds (default: 5)')

    list_parser = subparsers.add_parser('list', help='List all saves')
    list_parser.add_argument('--game', help='Filter by game name')

    games_parser = subparsers.add_parser('games', help='List or search supported games')
    games_parser.add_argument('--list', action='store_true', help='List all supported games')
    games_parser.add_argument('--search', help='Search for games by name')

    restore_parser = subparsers.add_parser('restore', help='Restore a save')
    restore_parser.add_argument('backup_path', help='Path to backup file to restore')

    # backup manual (re-added for integration)
    backup_parser = subparsers.add_parser('backup', help='Manually backup a game')
    backup_parser.add_argument('name', help='Game name')

    args = parser.parse_args()

    if args.command == 'add':
        path = args.path
        if path is None:
            supported_path = get_supported_game_path(args.name)
            if supported_path:
                path = supported_path
                print(f"Using suggested path for {args.name}: {path}")
            else:
                print("Path required for unsupported games")
                return
        add_game(args.name, path, force=getattr(args, 'force', False))
    elif args.command == 'watch':
        watcher = GameWatcher(args.name, args.interval)
        watcher.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            watcher.stop()
    elif args.command == 'list':
        saves = list_saves(args.game)
        for ts, path, game in saves:
            print(f"{ts} | {game} | {path}")
    elif args.command == 'games':
        if getattr(args, 'list', False):
            games = list_supported_games()
            for i, game in enumerate(games, 1):
                path = get_supported_game_path(game)
                print(f"{i}. {game} - Suggested save path: {path}")
        elif args.search:
            results = search_games(args.search)
            if results:
                for game in results:
                    path = get_supported_game_path(game)
                    print(f"{game} - Suggested save path: {path}")
            else:
                print("No matching games found")
        else:
            print("Use --list or --search <query>")
    elif args.command == 'restore':
        restore_save(args.backup_path)
    elif args.command == 'backup':
        backup_save(args.name)

if __name__ == "__main__":
    main()
