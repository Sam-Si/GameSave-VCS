import hashlib
import shutil
from pathlib import Path
from datetime import datetime
from .config import get_backups_dir, get_game_path

def get_file_hash(file_path):
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hasher.update(chunk)
    return hasher.hexdigest()

def backup_save(game_name):
    save_path = get_game_path(game_name)
    if not save_path or not Path(save_path).exists():
        print(f"Save file for {game_name} not found")
        return None
    save_path = Path(save_path)
    backup_dir = get_backups_dir() / game_name
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"{timestamp}_{save_path.name}"
    backup_path = backup_dir / backup_name
    shutil.copy2(save_path, backup_path)
    print(f"Backed up {game_name} save to {backup_path}")
    return backup_path

def list_saves(game_name=None):
    saves = []
    backups_dir = get_backups_dir()
    if not backups_dir.exists():
        return saves  # no backups dir yet
    if game_name:
        game_dir = backups_dir / game_name
        if game_dir.exists():
            for f in game_dir.iterdir():
                if f.is_file():
                    try:
                        parts = f.name.split('_')
                        ts_str = '_'.join(parts[:2])
                        ts = datetime.strptime(ts_str, '%Y%m%d_%H%M%S')
                        saves.append((ts, f, game_name))
                    except ValueError:
                        pass
    else:
        for game_dir in backups_dir.iterdir():
            if game_dir.is_dir():
                for f in game_dir.iterdir():
                    if f.is_file():
                        try:
                            parts = f.name.split('_')
                            ts_str = '_'.join(parts[:2])
                            ts = datetime.strptime(ts_str, '%Y%m%d_%H%M%S')
                            saves.append((ts, f, game_dir.name))
                        except ValueError:
                            pass
    saves.sort(key=lambda x: x[0], reverse=True)
    return saves

def restore_save(backup_path):
    backup_path = Path(backup_path)
    if not backup_path.exists():
        print("Backup not found")
        return False
    game_name = backup_path.parent.name
    save_path = get_game_path(game_name)
    if not save_path:
        print("Game not found")
        return False
    save_path = Path(save_path)
    shutil.copy2(backup_path, save_path)
    print(f"Restored {backup_path} to {save_path}")
    return True
