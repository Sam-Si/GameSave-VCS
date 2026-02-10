import hashlib
import shutil
import os
from pathlib import Path
from datetime import datetime
from .config import get_backups_dir, get_game_path

def get_save_hash(save_path):
    save_path = Path(save_path)
    hasher = hashlib.sha256()
    if save_path.is_file():
        with open(save_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hasher.update(chunk)
    elif save_path.is_dir():
        for root, dirs, files in os.walk(save_path, followlinks=False):
            for name in sorted(files):
                fpath = Path(root) / name
                rel = fpath.relative_to(save_path)
                hasher.update(str(rel).encode())
                with open(fpath, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b''):
                        hasher.update(chunk)
    return hasher.hexdigest()

def backup_save(game_name):
    save_path = get_game_path(game_name)
    if not save_path or not Path(save_path).exists():
        print(f"Backup skipped for {game_name}: save path not found (nothing to backup yet)")
        return None
    save_path = Path(save_path)
    backup_dir = get_backups_dir() / game_name
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"{timestamp}_{save_path.name}"
    backup_path = backup_dir / backup_name
    if save_path.is_file():
        shutil.copy2(save_path, backup_path)
    elif save_path.is_dir():
        if backup_path.exists():
            shutil.rmtree(backup_path)
        shutil.copytree(save_path, backup_path)
    print(f"Backed up {game_name} save to {backup_path}")
    return backup_path

def list_saves(game_name=None):
    saves = []
    backups_dir = get_backups_dir()
    if not backups_dir.exists():
        return saves
    if game_name:
        game_dir = backups_dir / game_name
        if game_dir.exists():
            for f in game_dir.iterdir():
                if f.is_file() or f.is_dir():
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
                    if f.is_file() or f.is_dir():
                        try:
                            parts = f.name.split('_')
                            ts_str = '_'.join(parts[:2])
                            ts = datetime.strptime(ts_str, '%Y%m%d_%H%M%S')
                            saves.append((ts, f, game_dir.name))
                        except ValueError:
                            pass
    saves.sort(key=lambda x: x[0], reverse=True)
    return saves

def restore_save(backup_path=None):
    if not backup_path:
        saves = list_saves()
        if not saves:
            print("No backups found")
            return False
        backup_path = saves[0][1]  # latest (reverse chrono)
        print(f"Auto-restoring latest: {backup_path}")
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
    if backup_path.is_dir():
        if save_path.exists():
            if save_path.is_dir():
                shutil.rmtree(save_path)
            else:
                save_path.unlink()
        save_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(backup_path, save_path)
    else:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup_path, save_path)
    print(f"Restored {backup_path} to {save_path}")
    return True
