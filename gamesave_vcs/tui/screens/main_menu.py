"""Main menu screen - the entry point to the TUI."""

from textual.screen import Screen
from textual.widgets import Static, Button
from textual.containers import Vertical, Center, Horizontal
from textual.reactive import reactive

from gamesave_vcs.tui.widgets import RetroHeader, RetroFooter
from gamesave_vcs.tui.pixel_art import RetroColors, ASSETS


class MainMenuScreen(Screen):
    """Main menu with retro RPG styling."""
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("g", "show_games", "Games"),
        ("b", "backup_all", "Backup All"),
        ("h", "show_help", "Help"),
    ]
    
    CSS = """
    MainMenuScreen {
        align: center middle;
        background: #1a1a2e;
    }
    
    #main-container {
        width: 80;
        height: auto;
        border: double #B8860B;
        background: #16213e;
        padding: 1 2;
    }
    
    #menu-title {
        text-align: center;
        text-style: bold;
        color: #FFD700;
        margin: 1 0;
    }
    
    #menu-items {
        width: 100%;
        height: auto;
        margin: 1 0;
    }
    
    .menu-button {
        width: 100%;
        margin: 1 0;
        background: #1a1a2e;
        color: #FFD700;
        border: solid #B8860B;
        text-style: bold;
    }
    
    .menu-button:hover {
        background: #16213e;
        border: solid #FFD700;
    }
    
    #triforce-art {
        text-align: center;
        color: #FFD700;
        margin: 1 0;
    }
    """
    
    def compose(self):
        """Compose the main menu."""
        from rich.text import Text as RichText
        
        with Vertical(id="main-container"):
            # Triforce art - use RichText to avoid markup issues
            triforce_lines = ASSETS.get_triforce()
            triforce_text = RichText("\n".join(triforce_lines), style="bold yellow")
            yield Static(triforce_text, id="triforce-art")
            
            # Title - use RichText
            title_text = RichText("◆ GameSave-VCS ◆", style="bold gold")
            yield Static(title_text, id="menu-title")
            
            # Menu buttons
            with Vertical(id="menu-items"):
                yield Button("Browse Games", id="btn-games", variant="primary", classes="menu-button")
                yield Button("Backup All", id="btn-backup", classes="menu-button")
                yield Button("Statistics", id="btn-stats", classes="menu-button")
                yield Button("Settings", id="btn-settings", classes="menu-button")
                yield Button("Help", id="btn-help", classes="menu-button")
                yield Button("Quit", id="btn-quit", classes="menu-button")
            
            # Footer
            yield RetroFooter({
                "up/down": "Navigate",
                "Enter": "Select",
                "G": "Games",
                "Q": "Quit"
            })
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id
        
        if button_id == "btn-games":
            self.action_show_games()
        elif button_id == "btn-backup":
            self.action_backup_all()
        elif button_id == "btn-stats":
            self.action_show_stats()
        elif button_id == "btn-settings":
            self.action_show_settings()
        elif button_id == "btn-help":
            self.action_show_help()
        elif button_id == "btn-quit":
            self.action_quit()
    
    def action_show_games(self):
        """Show game browser screen."""
        self.app.push_screen("game_browser")
    
    def action_backup_all(self):
        """Backup all games."""
        self.notify("Backing up all games...", title="Backup", severity="information")
    
    def action_show_stats(self):
        """Show statistics screen."""
        self.notify("Statistics coming soon!", title="Info")
    
    def action_show_settings(self):
        """Show settings screen."""
        self.notify("Settings coming soon!", title="Info")
    
    def action_show_help(self):
        """Show help screen."""
        self.notify("Help: Use arrow keys to navigate, Enter to select", title="Help")
    
    def action_quit(self):
        """Quit the application."""
        self.app.exit()
