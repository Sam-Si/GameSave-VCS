"""Main TUI Application for GameSave-VCS.

A retro game-inspired terminal interface using Textual.
"""

from textual.app import App, ComposeResult
from textual.widgets import Static

from gamesave_vcs.tui.screens.main_menu import MainMenuScreen
from gamesave_vcs.tui.screens.game_browser import GameBrowserScreen
from gamesave_vcs.tui.screens.timeline import TimelineScreen
from gamesave_vcs.tui.screens.save_details import SaveDetailsScreen
from gamesave_vcs.tui.pixel_art import RetroColors


class RetroSaveManagerApp(App):
    """Retro-styled save manager TUI application."""
    
    TITLE = "GameSave-VCS"
    SUB_TITLE = "Version Control for Game Saves"
    
    CSS = """
    Screen {
        background: #1a1a2e;
    }
    
    Static {
        color: #F5F5F5;
    }
    
    Button {
        background: #1a1a2e;
        color: #FFD700;
        border: solid #B8860B;
        text-style: bold;
    }
    
    Button:hover {
        background: #16213e;
        border: solid #FFD700;
    }
    
    Button:focus {
        border: double #FFD700;
    }
    
    ListView {
        background: #16213e;
        border: solid #B8860B;
    }
    
    ListItem {
        background: #1a1a2e;
        color: #F5F5F5;
    }
    
    ListItem:hover {
        background: #16213e;
    }
    
    ListItem:focus {
        background: #1a3a5e;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("m", "main_menu", "Main Menu"),
        ("g", "show_games", "Games"),
        ("t", "timeline", "Timeline"),
        ("r", "restore", "Restore"),
        ("h", "help", "Help"),
    ]
    
    SCREENS = {
        "main_menu": MainMenuScreen,
        "game_browser": GameBrowserScreen,
    }
    
    def __init__(self):
        super().__init__()
        self._retro_colors = RetroColors()
    
    def on_mount(self) -> None:
        """Called when app is mounted."""
        self.push_screen("main_menu")
    
    def action_main_menu(self):
        """Return to main menu."""
        self.pop_screen()
        self.push_screen("main_menu")
    
    def action_show_games(self):
        """Show game browser."""
        self.push_screen("game_browser")
    
    def action_timeline(self):
        """Show timeline for current game."""
        # Would need to track current game
        self.notify("Select a game first", title="Info")
    
    def action_restore(self):
        """Restore save."""
        self.notify("Select a save to restore", title="Info")
    
    def action_help(self):
        """Show help."""
        help_text = """
        [bold]GameSave-VCS Help[/]
        
        [bold]Navigation:[/]
        • ↑/↓ or Tab: Navigate menus
        • Enter: Select item
        • Q: Quit application
        
        [bold]Screens:[/]
        • M: Main Menu
        • G: Game Browser
        
        [bold]Actions:[/]
        • B: Backup
        • R: Restore
        • D: Delete
        """
        self.notify(help_text, title="Help", timeout=10)
    
    def action_quit(self):
        """Quit the application."""
        self.exit()


def run_tui():
    """Run the TUI application."""
    app = RetroSaveManagerApp()
    app.run()


if __name__ == "__main__":
    run_tui()
