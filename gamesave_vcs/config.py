import json
from pathlib import Path

def get_base_dir():
    return Path.home() / '.gamesave-vcs'

def get_config_file():
    return get_base_dir() / 'config.json'

def get_backups_dir():
    return get_base_dir() / 'backups'

def ensure_dirs():
    base = get_base_dir()
    base.mkdir(parents=True, exist_ok=True)
    get_backups_dir().mkdir(parents=True, exist_ok=True)

def load_config():
    ensure_dirs()
    config_file = get_config_file()
    if config_file.exists():
        with open(config_file, 'r') as f:
            return json.load(f)
    return {}

def save_config(config):
    ensure_dirs()
    with open(get_config_file(), 'w') as f:
        json.dump(config, f, indent=2)

def add_game(name, save_path):
    config = load_config()
    if name in config:
        raise ValueError(f"Game {name} already exists")
    config[name] = str(save_path)
    save_config(config)
    (get_backups_dir() / name).mkdir(exist_ok=True)
    print(f"Added game {name} with save path {save_path}")

def get_game_path(name):
    config = load_config()
    return config.get(name)
