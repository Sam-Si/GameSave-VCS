"""Retro-styled widgets for the TUI.

Custom Textual widgets that look like classic RPG UI elements.
"""

from textual.widgets import Static, Label, Button, ListItem
from textual.reactive import reactive
from rich.text import Text
from rich.panel import Panel
from rich.align import Align
from rich.columns import Columns

from gamesave_vcs.tui.pixel_art import PixelArtAssets, RetroColors, ASSETS


class RetroHeader(Static):
    """Retro-styled header with pixel art decoration."""
    
    def __init__(self, title: str = "GameSave-VCS", show_triforce: bool = True):
        self.title = title
        self.show_triforce = show_triforce
        super().__init__()
    
    def render(self):
        """Render the header with retro styling."""
        colors = RetroColors()
        
        # Build header content
        lines = []
        
        if self.show_triforce:
            # Add triforce above title
            triforce = ASSETS.get_triforce()
            for line in triforce:
                lines.append(Text(line, style=f"bold {colors.TRI_YELLOW}"))
        
        # Title with border
        title_text = Text(f"◆ {self.title} ◆", style=f"bold {colors.GOLD}")
        title_text.stylize(f"on {colors.BG_PANEL}")
        
        border = Text("═" * (len(self.title) + 6), style=colors.DARK_GOLD)
        
        lines.extend([
            Text(""),
            border,
            title_text,
            border,
        ])
        
        return "\n".join(str(line) for line in lines)


class GameListItem(Static):
    """A game entry in the list, styled like an RPG menu item."""
    
    def __init__(self, game_name: str, last_backup: str = "Never",
                 total_backups: int = 0, health_status: str = "good"):
        self.game_name = game_name
        self.last_backup = last_backup
        self.total_backups = total_backups
        self.health_status = health_status
        super().__init__()
    
    def render(self):
        """Render the game list item."""
        colors = RetroColors()
        from rich.text import Text as RichText
        
        # Get game icon
        icon_lines = ASSETS.get_icon(self.game_name)
        icon_str = "\n".join(icon_lines)
        
        # Build info text using Rich Text
        content = RichText()
        content.append(icon_str + "\n\n", style=colors.MAGIC_BLUE)
        content.append(self.game_name + "\n", style=f"bold {colors.GOLD}")
        content.append(f"Last: {self.last_backup}\n", style="dim")
        content.append(f"Saves: {self.total_backups}\n\n", style="dim")
        
        # Health indicator
        if self.health_status == "good":
            content.append("♥", style="green")
        elif self.health_status == "warning":
            content.append("♥", style="yellow")
        else:
            content.append("♥", style="red")
        
        return Panel(
            content,
            border_style=colors.DARK_GOLD,
            box="ROUNDED",
            padding=(1, 2)
        )


class SaveSlot(Static):
    """A save slot widget styled like in-game save slots."""
    
    def __init__(self, slot_number: int, timestamp: str, playtime: str = "",
                 location: str = "", thumbnail_char: str = "▼"):
        self.slot_number = slot_number
        self.timestamp = timestamp
        self.playtime = playtime
        self.location = location
        self.thumbnail_char = thumbnail_char
        super().__init__()
    
    def render(self):
        """Render save slot like a game save menu."""
        colors = RetroColors()
        from rich.text import Text as RichText
        
        # Header with slot number
        header = f" SLOT {self.slot_number} "
        
        # Build content using Rich Text
        content = RichText()
        content.append(f"\n  {self.thumbnail_char}\n \n", style=f"bold {colors.MAGIC_BLUE}")
        content.append("Time: ", style="dim")
        content.append(self.timestamp + "\n")
        
        if self.playtime:
            content.append("Playtime: ", style="dim")
            content.append(self.playtime + "\n")
        
        if self.location:
            content.append("Location: ", style="dim")
            content.append(self.location)
        
        return Panel(
            content,
            title=header,
            title_align="left",
            border_style=colors.DARK_GOLD,
            box="DOUBLE"
        )


class HealthBar(Static):
    """Health bar using heart containers."""
    
    def __init__(self, current: int = 10, max: int = 10):
        self.current = current
        self.max = max
        super().__init__()
    
    def render(self):
        """Render health bar with hearts."""
        colors = RetroColors()
        
        full_hearts = ASSETS.get_heart(full=True)
        empty_hearts = ASSETS.get_heart(full=False)
        
        # Build heart row
        heart_line = ""
        for i in range(self.max):
            if i < self.current:
                heart_line += full_hearts[0] + " "
            else:
                heart_line += empty_hearts[0] + " "
        
        return Text(heart_line, style=f"bold {colors.HEART_RED}")


class ScrollIndicator(Static):
    """Scroll indicator arrows."""
    
    def __init__(self, direction: str = "down"):
        self.direction = direction
        super().__init__()
    
    def render(self):
        """Render scroll arrow."""
        colors = RetroColors()
        
        if self.direction == "down":
            arrow = "▼ MORE BELOW ▼"
        elif self.direction == "up":
            arrow = "▲ MORE ABOVE ▲"
        elif self.direction == "both":
            arrow = "▲ SCROLL ▼"
        else:
            arrow = "◆"
        
        return Text(arrow, style=f"dim {colors.TEXT_GRAY}", justify="center")


class RetroButton(Button):
    """Retro-styled button."""
    
    DEFAULT_CSS = """
    RetroButton {
        background: #1a1a2e;
        color: #FFD700;
        border: solid #B8860B;
        text-style: bold;
    }
    RetroButton:hover {
        background: #16213e;
        border: solid #FFD700;
    }
    RetroButton:focus {
        border: double #FFD700;
    }
    """


class TreasureNotification(Static):
    """Notification styled like finding treasure in a game."""
    
    def __init__(self, message: str, item_type: str = "chest"):
        self.message = message
        self.item_type = item_type
        super().__init__()
    
    def render(self):
        """Render treasure notification."""
        colors = RetroColors()
        from rich.text import Text as RichText
        
        if self.item_type == "chest":
            art = ASSETS.get_chest(opened=True)
        elif self.item_type == "potion":
            art = ASSETS.get_potion("red")
        else:
            art = ASSETS.get_key()
        
        # Build content as RichText
        content = RichText("\n".join(art), style=colors.MAGIC_BLUE)
        content.append("\n\n")
        content.append(self.message, style=f"bold {colors.GOLD}")
        
        title = RichText("ITEM GET!", style="bold")
        
        return Panel(
            content,
            border_style=colors.GOLD,
            box="DOUBLE",
            title=title,
            title_align="center"
        )


class RetroFooter(Static):
    """Retro-styled footer with key hints."""
    
    def __init__(self, hints: dict = None):
        self.hints = hints or {
            "↑↓": "Navigate",
            "Enter": "Select",
            "Q": "Quit",
            "H": "Help"
        }
        super().__init__()
    
    def render(self):
        """Render footer with key hints."""
        colors = RetroColors()
        
        # Build hint text using Rich Text
        from rich.text import Text as RichText
        
        hint_text = RichText()
        first = True
        for key, action in self.hints.items():
            if not first:
                hint_text.append("  ")
            first = False
            hint_text.append(key, style=f"bold {colors.DARK_GOLD}")
            hint_text.append(": ")
            hint_text.append(action, style="dim")
        
        return Panel(
            hint_text,
            border_style=colors.DARK_BROWN,
            box="SINGLE",
            padding=(0, 1)
        )


class ProgressBar(Static):
    """Retro progress bar for operations."""
    
    def __init__(self, current: int = 0, total: int = 100, width: int = 30):
        self.current = current
        self.total = total
        self.width = width
        super().__init__()
    
    def render(self):
        """Render progress bar."""
        colors = RetroColors()
        
        if self.total == 0:
            percent = 0
        else:
            percent = min(100, int((self.current / self.total) * 100))
        
        filled = int((percent / 100) * self.width)
        empty = self.width - filled
        
        bar = "█" * filled + "░" * empty
        
        return Text(f"[{bar}] {percent}%", style=colors.FOREST_GREEN)
