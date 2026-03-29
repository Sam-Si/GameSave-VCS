"""Pixel art assets for retro game-inspired TUI.

Inspired by classic games like Zelda, featuring chests, hearts, swords,
and other RPG-style UI elements rendered in ASCII/Unicode box drawing.
"""

from typing import List


class RetroColors:
    """Classic NES/Retro game color palette."""
    
    # Gold/Yellow (treasure, highlights)
    GOLD = '#FFD700'
    DARK_GOLD = '#B8860B'
    
    # Greens (forest, life)
    DARK_GREEN = '#006400'
    FOREST_GREEN = '#228B22'
    
    # Reds (hearts, danger)
    HEART_RED = '#DC143C'
    DARK_RED = '#8B0000'
    
    # Blues (magic, water)
    MAGIC_BLUE = '#4169E1'
    DARK_BLUE = '#00008B'
    
    # Browns (wood, earth)
    DARK_BROWN = '#8B4513'
    WOOD_BROWN = '#A0522D'
    
    # UI Colors
    TEXT_WHITE = '#F5F5F5'
    TEXT_GRAY = '#A9A9A9'
    BG_DARK = '#1a1a2e'
    BG_PANEL = '#16213e'
    
    # Triforce colors
    TRI_ORANGE = '#FF8C00'
    TRI_YELLOW = '#FFD700'


class PixelArtAssets:
    """Collection of pixel art assets for the TUI."""
    
    def get_chest(self, opened: bool = False) -> List[str]:
        """Get treasure chest pixel art.
        
        Args:
            opened: If True, returns opened chest showing contents.
            
        Returns:
            List of strings representing the chest art.
        """
        if opened:
            return [
                "     ▓▓▓▓▓     ",
                "    ▓     ▓    ",
                "   ▓  ◆◆◆  ▓   ",
                "╔═══════════════╗",
                "║▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓║",
                "║▓  TREASURE  ▓║",
                "║▓    ◆◆◆     ▓║",
                "║▓   $$$$     ▓║",
                "╚═══════════════╝",
            ]
        else:
            return [
                "╔═══════════════╗",
                "║▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓║",
                "║▓  ░░░░░░░░  ▓║",
                "║▓  ░ LOCK ░  ▓║",
                "║▓  ░░░░░░░░  ▓║",
                "║▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓║",
                "╚══════╦══╦═════╝",
                "       ║  ║      ",
            ]
    
    def get_heart(self, full: bool = True) -> List[str]:
        """Get heart container pixel art.
        
        Args:
            full: If True, returns full heart, else empty.
            
        Returns:
            List of strings representing the heart.
        """
        if full:
            return [
                " ██  ██ ",
                "████████",
                "████████",
                " ██████ ",
                "  ████  ",
                "   ██   ",
            ]
        else:
            return [
                " ██  ██ ",
                "█  ██  █",
                "█      █",
                " █    █ ",
                "  █  █  ",
                "   ██   ",
            ]
    
    def get_sword(self) -> List[str]:
        """Get sword pixel art for toolbar.
        
        Returns:
            List of strings representing the sword.
        """
        return [
            "    /▲    ",
            "   /███   ",
            "  /█████  ",
            " /███████ ",
            "    ███   ",
            "    ███   ",
            "   ═╦═    ",
            "    ║     ",
            "    ║     ",
        ]
    
    def get_triforce(self) -> List[str]:
        """Get Triforce symbol.
        
        Returns:
            List of strings representing the Triforce.
        """
        return [
            "    ▲    ",
            "   ███   ",
            "  ▲███▲  ",
            " ███████ ",
            "█████████",
        ]
    
    def get_potion(self, color: str = 'red') -> List[str]:
        """Get potion bottle pixel art.
        
        Args:
            color: 'red', 'blue', 'green', or 'gold'
            
        Returns:
            List of strings representing the potion.
        """
        fill_char = '█'
        if color == 'red':
            fill_char = '▓'
        elif color == 'blue':
            fill_char = '▒'
        elif color == 'green':
            fill_char = '░'
        elif color == 'gold':
            fill_char = '▞'
            
        return [
            "    ▓▓    ",
            "   ▓  ▓   ",
            "  ╔════╗  ",
            "  ║" + fill_char * 4 + "║  ",
            "  ║" + fill_char * 4 + "║  ",
            "  ║" + fill_char * 4 + "║  ",
            "  ╚════╝  ",
        ]
    
    def get_shield(self) -> List[str]:
        """Get shield pixel art.
        
        Returns:
            List of strings representing the shield.
        """
        return [
            "  ╭────╮  ",
            " ╱▓▓▓▓▓▓╲ ",
            "│▓▓▓◆▓◆▓▓▓│",
            "│▓▓▓▓▓▓▓▓▓│",
            "│▓▓▓▓▓▓▓▓▓│",
            " ╲▓▓▓▓▓▓▓╱ ",
            "  ╰────╯  ",
        ]
    
    def get_key(self) -> List[str]:
        """Get key pixel art.
        
        Returns:
            List of strings representing the key.
        """
        return [
            "  ╔═══╗  ",
            "  ║▓▓▓║  ",
            "  ╚═╦═╝  ",
            "    ║    ",
            "   ╔╧╗   ",
            "   ║ ║   ",
            "   ╚═╝   ",
        ]
    
    def get_scroll(self) -> List[str]:
        """Get scroll pixel art.
        
        Returns:
            List of strings representing the scroll.
        """
        return [
            "╔═══════════════╗",
            "║▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓║",
            "║ ~~~~~~~~~~~~~ ║",
            "║ ~~~~~~~~~~~~~ ║",
            "║ ~~~~~~~~~~~~~ ║",
            "║▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓║",
            "╚═══════════════╝",
        ]
    
    def get_icon(self, game_name: str) -> List[str]:
        """Get game-specific icon.
        
        Args:
            game_name: Name of the game (e.g., 'skyrim', 'minecraft', 'zelda')
            
        Returns:
            List of strings representing the icon.
        """
        game_lower = game_name.lower()
        
        if 'skyrim' in game_lower or 'elder' in game_lower:
            # Dragon symbol
            return [
                "  ╱▲╲  ",
                " ╱◆◆◆╲ ",
                "╱▓▓▓▓▓╲",
                "  ███  ",
                "  ███  ",
            ]
        elif 'minecraft' in game_lower or 'mine' in game_lower:
            # Block/cube
            return [
                "  ╱▓▓╲  ",
                " ╱▓▓▓▓╲ ",
                "╱▓▓▓▓▓▓╲",
                "▓▓▓▓▓▓▓▓",
                "╲▓▓▓▓▓▓╱",
            ]
        elif 'zelda' in game_lower or 'link' in game_lower:
            # Triforce
            return self.get_triforce()
        elif 'witcher' in game_lower:
            # Wolf medallion
            return [
                "  ╱▲╲  ",
                " ╱◆◆◆╲ ",
                "│▓▓▓▓▓│",
                " ╲███╱ ",
                "  ╲█╱  ",
            ]
        else:
            # Generic save disk
            return [
                "  ╭────╮  ",
                " ╱  ▓▓  ╲ ",
                "│  ▓▓▓▓  │",
                "│ ▓▓▓▓▓▓ │",
                " ╲______╱ ",
            ]
    
    def get_border_horizontal(self, width: int = 40) -> str:
        """Get horizontal border line.
        
        Args:
            width: Width of the border in characters.
            
        Returns:
            String representing the horizontal border.
        """
        return '╔' + '═' * (width - 2) + '╗'
    
    def get_border_bottom(self, width: int = 40) -> str:
        """Get bottom border line.
        
        Args:
            width: Width of the border in characters.
            
        Returns:
            String representing the bottom border.
        """
        return '╚' + '═' * (width - 2) + '╝'


# Singleton instance for easy access
ASSETS = PixelArtAssets()
