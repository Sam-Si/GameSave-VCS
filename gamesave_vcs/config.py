import json
from pathlib import Path
from typing import Any, Dict, List, Optional

SUPPORTED_GAMES: Dict[str, str] = {
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


def get_base_dir() -> Path:
    """Return the base directory for GameSave-VCS data (~/.gamesave-vcs)."""
    return Path.home() / ".gamesave-vcs"


def get_config_file() -> Path:
    """Return path to the config.json file."""
    return get_base_dir() / "config.json"


def get_backups_dir() -> Path:
    """Return path to the backups directory."""
    return get_base_dir() / "backups"


def ensure_dirs() -> None:
    """Ensure base and backups directories exist."""
    base = get_base_dir()
    base.mkdir(parents=True, exist_ok=True)
    get_backups_dir().mkdir(parents=True, exist_ok=True)


def load_config() -> Dict[str, Any]:
    """Load game config from JSON file. Returns empty dict if no config."""
    ensure_dirs()
    config_file = get_config_file()
    if config_file.exists():
        with open(config_file, "r") as f:
            return json.load(f)
    return {}


def save_config(config: Dict[str, Any]) -> None:
    """Save config dict to JSON file."""
    ensure_dirs()
    with open(get_config_file(), "w") as f:
        json.dump(config, f, indent=2)


def add_game(
    name: str, save_path: str | Path, force: bool = False, backend: str = "git"
) -> None:
    """
    Add or update a game config.
    backend: 'git' (default, efficient delta-based) or 'full-copy' (original full folder copy).
    """
    config = load_config()
    if name in config:
        if not force:
            raise ValueError(f"Game {name} already exists")
        print(f"Game {name} already exists - updating path (force mode)")
    # Store as dict for extensibility, path + backend
    config[name] = {
        "path": str(save_path),
        "backend": backend,
    }
    save_config(config)
    (get_backups_dir() / name).mkdir(exist_ok=True)
    print(
        f"Added/updated game {name} with save path {save_path} using {backend} backend"
    )


def get_game_config(name: str) -> Dict[str, Any]:
    """
    Get full game config dict with 'path' and 'backend'.
    Backward compat: if old str config, treat as {'path': entry, 'backend': 'full-copy'}
    """
    config = load_config()
    entry = config.get(name)
    if isinstance(entry, str):
        # legacy full-copy
        return {"path": entry, "backend": "full-copy"}
    elif isinstance(entry, dict):
        return entry
    return {}


def get_game_path(name: str) -> Optional[str]:
    """Backward compat wrapper to get just the save path."""
    return get_game_config(name).get("path")


def get_game_backend(name: str) -> Optional[str]:
    """Get the backup backend/strategy for the game. Defaults to 'git' for new."""
    gc = get_game_config(name)
    return gc.get("backend", "git") if gc else None


def list_supported_games() -> List[str]:
    """Return list of supported game names."""
    return list(SUPPORTED_GAMES.keys())


def search_games(query: str) -> List[str]:
    """Search supported games by substring (case-insensitive)."""
    query = query.lower()
    return [game for game in SUPPORTED_GAMES if query in game.lower()]


def get_supported_game_path(game_name: str) -> Optional[str]:
    """Get predefined save path for a supported game, or None if unknown."""
    return SUPPORTED_GAMES.get(game_name)
