import json
from pathlib import Path

SUPPORTED_GAMES = {
    "Minecraft": "~/.minecraft/saves/",
    "Terraria": "~/.local/share/Terraria/",
    "Stardew Valley": "~/.config/StardewValley/Saves/",
    "The Witcher 3": "~/.local/share/CD Projekt Red/The Witcher 3/",
    "Elden Ring": "~/.local/share/EldenRing/",
    "Cyberpunk 2077": "~/.local/share/CD Projekt Red/Cyberpunk 2077/",
    "Hades": "~/.local/share/Supergiant Games/Hades/",
    "Celeste": "~/.local/share/Celeste/",
    "Hollow Knight": "~/.local/share/Hollow Knight/",
    "Doom Eternal": "~/.local/share/id Software/DOOM Eternal/",
}

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

def add_game(name, save_path, force=False):
    config = load_config()
    if name in config:
        if not force:
            raise ValueError(f"Game {name} already exists")
        print(f"Game {name} already exists - updating path (force mode)")
    config[name] = str(save_path)
    save_config(config)
    (get_backups_dir() / name).mkdir(exist_ok=True)
    print(f"Added/updated game {name} with save path {save_path}")

def get_game_path(name):
    config = load_config()
    return config.get(name)

def list_supported_games():
    return list(SUPPORTED_GAMES.keys())

def search_games(query):
    query = query.lower()
    return [game for game in SUPPORTED_GAMES if query in game.lower()]

def get_supported_game_path(game_name):
    return SUPPORTED_GAMES.get(game_name)
