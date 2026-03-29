"""Timeline screen - show backup history for a game."""

from textual.screen import Screen
from textual.widgets import Static, Button, ListView, ListItem
from textual.containers import Vertical

from gamesave_vcs.tui.widgets import RetroHeader, RetroFooter, SaveSlot
from gamesave_vcs.tui.pixel_art import RetroColors


def get_save_history(game_name: str):
    """Get save history for a game."""
    return [
        {'timestamp': '2024-01-15 14:00', 'size': '5MB', 'message': 'Before boss'},
        {'timestamp': '2024-01-15 16:30', 'size': '5.1MB', 'message': 'After boss'},
    ]


class TimelineScreen(Screen):
    """Screen showing backup timeline for a game."""
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("b", "back", "Back"),
        ("r", "restore", "Restore"),
    ]
    
    CSS = """
    TimelineScreen {
        background: #1a1a2e;
    }
    
    #timeline-container {
        width: 100%;
        height: 100%;
        padding: 1 2;
    }
    
    #save-list {
        width: 100%;
        height: 1fr;
        border: solid #B8860B;
    }
    """
    
    def __init__(self, game_name: str):
        self.game_name = game_name
        super().__init__()
    
    def compose(self):
        """Compose the timeline screen."""
        with Vertical(id="timeline-container"):
            yield RetroHeader(title=f"◆ {self.game_name} Saves ◆", show_triforce=False)
            
            # Save slots
            saves = get_save_history(self.game_name)
            list_items = []
            for i, save in enumerate(saves, 1):
                slot = SaveSlot(
                    slot_number=i,
                    timestamp=save['timestamp'],
                    location=save['message']
                )
                list_items.append(ListItem(slot))
            
            yield ListView(*list_items, id="save-list")
            
            yield RetroFooter({
                "↑↓": "Navigate",
                "R": "Restore",
                "B": "Back",
                "Q": "Quit"
            })
    
    def action_back(self):
        """Go back to game browser."""
        self.app.pop_screen()
    
    def action_restore(self):
        """Restore selected save."""
        self.notify(f"Restoring {self.game_name}...", title="Restore")
    
    def action_quit(self):
        """Quit application."""
        self.app.exit()
