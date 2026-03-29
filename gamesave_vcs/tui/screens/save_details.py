"""Save details screen - show information about a specific save."""

from pathlib import Path
from textual.screen import Screen
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal

from gamesave_vcs.tui.widgets import RetroHeader, RetroFooter, TreasureNotification
from gamesave_vcs.tui.pixel_art import RetroColors, ASSETS


class SaveDetailsScreen(Screen):
    """Screen showing details of a specific save."""
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("b", "back", "Back"),
        ("r", "restore", "Restore"),
        ("d", "delete", "Delete"),
    ]
    
    CSS = """
    SaveDetailsScreen {
        background: #1a1a2e;
    }
    
    #details-container {
        width: 100%;
        height: 100%;
        padding: 1 2;
    }
    
    #info-panel {
        width: 100%;
        height: auto;
        border: double #B8860B;
        background: #16213e;
        padding: 1 2;
        margin: 1 0;
    }
    """
    
    def __init__(self, game_name: str, save_timestamp: str, save_path: Path):
        self.game_name = game_name
        self.save_timestamp = save_timestamp
        self.save_path = save_path
        super().__init__()
    
    def compose(self):
        """Compose the save details screen."""
        from rich.text import Text as RichText
        
        with Vertical(id="details-container"):
            yield RetroHeader(title="Save Details", show_triforce=False)
            
            # Info panel - use RichText to avoid markup issues
            info_text = RichText()
            info_text.append("Game: ", style="bold")
            info_text.append(f"{self.game_name}\n")
            info_text.append("Date: ", style="bold")
            info_text.append(f"{self.save_timestamp}\n")
            info_text.append("Path: ", style="bold")
            info_text.append(f"{self.save_path}\n")
            
            yield Static(info_text, id="info-panel")
            
            # Chest art
            chest_lines = ASSETS.get_chest(opened=True)
            chest_text = RichText("\n".join(chest_lines), style="yellow")
            yield Static(chest_text)
            
            # Actions
            with Horizontal():
                yield Button("Restore", id="btn-restore", variant="primary")
                yield Button("Delete", id="btn-delete", variant="error")
                yield Button("Back", id="btn-back")
            
            yield RetroFooter({
                "R": "Restore",
                "D": "Delete",
                "B": "Back",
                "Q": "Quit"
            })
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id
        
        if button_id == "btn-restore":
            self.action_restore()
        elif button_id == "btn-delete":
            self.action_delete()
        elif button_id == "btn-back":
            self.action_back()
    
    def action_restore(self):
        """Restore this save."""
        self.notify(f"Restored {self.game_name}!")
    
    def action_delete(self):
        """Delete this save."""
        self.notify(f"Deleted save for {self.game_name}")
    
    def action_back(self):
        """Go back."""
        self.app.pop_screen()
    
    def action_quit(self):
        """Quit application."""
        self.app.exit()
