"""TUI Screens for GameSave-VCS.

Each screen represents a different view in the retro RPG-style interface.
"""

from gamesave_vcs.tui.screens.main_menu import MainMenuScreen
from gamesave_vcs.tui.screens.game_browser import GameBrowserScreen
from gamesave_vcs.tui.screens.timeline import TimelineScreen
from gamesave_vcs.tui.screens.save_details import SaveDetailsScreen

__all__ = [
    'MainMenuScreen',
    'GameBrowserScreen', 
    'TimelineScreen',
    'SaveDetailsScreen'
]
