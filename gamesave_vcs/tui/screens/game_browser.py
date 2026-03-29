"""Game browser screen - list and manage games."""

from textual.screen import Screen
from textual.widgets import Static, Button, ListView, ListItem, Label
from textual.containers import Vertical, Horizontal

from gamesave_vcs.tui.widgets import RetroHeader, RetroFooter, GameListItem
from gamesave_vcs.tui.pixel_art import RetroColors


def list_registered_games():
    """Get list of registered games."""
    # This would integrate with actual config
    return [
        {'name': 'Skyrim', 'backups': 5, 'last_backup': '2h ago'},
        {'name': 'Minecraft', 'backups': 12, 'last_backup': '1d ago'},
    ]


class GameBrowserScreen(Screen):
    """Screen for browsing and selecting games."""
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("m", "main_menu", "Main Menu"),
        ("r", "refresh", "Refresh"),
    ]
    
    CSS = """
    GameBrowserScreen {
        background: #1a1a2e;
    }
    
    #browser-container {
        width: 100%;
        height: 100%;
        padding: 1 2;
    }
    
    #game-list {
        width: 100%;
        height: 1fr;
        border: solid #B8860B;
        background: #16213e;
    }
    
    .game-item {
        padding: 1;
        border-bottom: solid #333;
    }
    
    .game-item:hover {
        background: #1a1a2e;
    }
    """
    
    def compose(self):
        """Compose the game browser."""
        with Vertical(id="browser-container"):
            yield RetroHeader(title="◆ Select Game ◆", show_triforce=False)
            
            # Game list
            games = list_registered_games()
            list_items = []
            for game in games:
                item = GameListItem(
                    game_name=game['name'],
                    last_backup=game['last_backup'],
                    total_backups=game['backups']
                )
                list_items.append(ListItem(item, classes="game-item"))
            
            yield ListView(*list_items, id="game-list")
            
            yield RetroFooter({
                "↑↓": "Navigate",
                "Enter": "Select",
                "M": "Menu",
                "R": "Refresh",
                "Q": "Quit"
            })
    
    def action_main_menu(self):
        """Return to main menu."""
        self.app.pop_screen()
    
    def action_refresh(self):
        """Refresh game list."""
        self.refresh()
    
    def action_quit(self):
        """Quit application."""
        self.app.exit()
