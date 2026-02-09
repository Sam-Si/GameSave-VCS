import argparse
import time
from .config import add_game, get_game_path
from .backup import backup_save, list_saves, restore_save
from .watcher import GameWatcher

def main():
    parser = argparse.ArgumentParser(description='GameSave-VCS: Version control for game saves')
    subparsers = parser.add_subparsers(dest='command', required=True)

    add_parser = subparsers.add_parser('add', help='Add a game to watch')
    add_parser.add_argument('name', help='Game name')
    add_parser.add_argument('path', help='Path to save file')

    watch_parser = subparsers.add_parser('watch', help='Start watcher for a game')
    watch_parser.add_argument('name', help='Game name')
    watch_parser.add_argument('--interval', type=int, default=5, help='Polling interval in seconds (default: 5)')

    list_parser = subparsers.add_parser('list', help='List all saves')
    list_parser.add_argument('--game', help='Filter by game name')

    restore_parser = subparsers.add_parser('restore', help='Restore a save')
    restore_parser.add_argument('backup_path', help='Path to backup file to restore')

    # backup manual (re-added for integration)
    backup_parser = subparsers.add_parser('backup', help='Manually backup a game')
    backup_parser.add_argument('name', help='Game name')

    args = parser.parse_args()

    if args.command == 'add':
        add_game(args.name, args.path)
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
    elif args.command == 'restore':
        restore_save(args.backup_path)
    elif args.command == 'backup':
        backup_save(args.name)

if __name__ == "__main__":
    main()
