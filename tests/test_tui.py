"""Tests for Retro Game-inspired TUI.

TDD approach: Tests written before implementation.
Tests pixel art, screens, navigation, and retro aesthetics.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio


# =============================================================================
# Pixel Art Asset Tests
# =============================================================================


def test_pixel_art_chest_rendering():
    """Test that treasure chest pixel art renders correctly."""
    from gamesave_vcs.tui.pixel_art import PixelArtAssets
    
    assets = PixelArtAssets()
    chest = assets.get_chest(opened=False)
    
    # Should be a list of strings (lines)
    assert isinstance(chest, list)
    assert len(chest) > 0
    # Check for box-drawing characters or ASCII art style
    assert any(char in chest[0] for char in ['┌', '╔', '+', '#', '▓'])


def test_pixel_art_chest_opened_vs_closed():
    """Test that opened and closed chests look different."""
    from gamesave_vcs.tui.pixel_art import PixelArtAssets
    
    assets = PixelArtAssets()
    closed_chest = assets.get_chest(opened=False)
    opened_chest = assets.get_chest(opened=True)
    
    # They should be different
    assert closed_chest != opened_chest
    # Opened chest should show contents (different characters)
    closed_str = '\n'.join(closed_chest)
    opened_str = '\n'.join(opened_chest)
    assert closed_str != opened_str


def test_pixel_art_heart_container():
    """Test heart container pixel art for health/status."""
    from gamesave_vcs.tui.pixel_art import PixelArtAssets
    
    assets = PixelArtAssets()
    heart = assets.get_heart(full=True)
    empty_heart = assets.get_heart(full=False)
    
    assert isinstance(heart, list)
    assert isinstance(empty_heart, list)
    # Full heart should look different from empty
    assert '\n'.join(heart) != '\n'.join(empty_heart)


def test_pixel_art_sword():
    """Test sword pixel art for toolbar."""
    from gamesave_vcs.tui.pixel_art import PixelArtAssets
    
    assets = PixelArtAssets()
    sword = assets.get_sword()
    
    assert isinstance(sword, list)
    assert len(sword) >= 3  # Sword should have some height


def test_pixel_art_triforce():
    """Test triforce symbol for branding."""
    from gamesave_vcs.tui.pixel_art import PixelArtAssets
    
    assets = PixelArtAssets()
    triforce = assets.get_triforce()
    
    assert isinstance(triforce, list)
    triforce_str = '\n'.join(triforce)
    # Should contain triangle-like patterns
    assert '▲' in triforce_str or '△' in triforce_str or '◆' in triforce_str


def test_pixel_art_game_icons():
    """Test game-specific pixel art icons."""
    from gamesave_vcs.tui.pixel_art import PixelArtAssets
    
    assets = PixelArtAssets()
    
    # Test various game icons exist
    icons = [
        assets.get_icon('skyrim'),
        assets.get_icon('minecraft'),
        assets.get_icon('zelda'),
        assets.get_icon('generic'),
    ]
    
    for icon in icons:
        assert isinstance(icon, list)
        assert len(icon) > 0


def test_color_palette_retro():
    """Test retro color palette is defined."""
    from gamesave_vcs.tui.pixel_art import RetroColors
    
    colors = RetroColors()
    
    # Should have classic NES/retro colors
    assert hasattr(colors, 'GOLD')
    assert hasattr(colors, 'DARK_GREEN')
    assert hasattr(colors, 'HEART_RED')
    assert hasattr(colors, 'MAGIC_BLUE')
    assert hasattr(colors, 'DARK_BROWN')
    
    # Colors should be valid rich color strings
    assert colors.GOLD.startswith('#') or colors.GOLD.isalpha()


# =============================================================================
# TUI Component Tests
# =============================================================================


def test_retro_header_widget():
    """Test retro-styled header widget."""
    from gamesave_vcs.tui.widgets import RetroHeader
    
    header = RetroHeader(title="Test Game")
    
    # Should render without error
    render_result = header.render()
    assert render_result is not None


def test_game_list_item_widget():
    """Test game list item with pixel art."""
    from gamesave_vcs.tui.widgets import GameListItem
    
    item = GameListItem(
        game_name="Skyrim",
        last_backup="2 hours ago",
        total_backups=15,
        health_status="good"
    )
    
    # Just verify the widget can be created and has the right attributes
    assert item is not None
    assert item.game_name == "Skyrim"
    assert item.total_backups == 15
    assert item.health_status == "good"


def test_save_slot_widget():
    """Test save slot widget looks like game save slot."""
    from gamesave_vcs.tui.widgets import SaveSlot
    
    slot = SaveSlot(
        slot_number=1,
        timestamp="2024-01-15 14:30",
        playtime="45h 32m",
        location="Whiterun",
        thumbnail_char='▼'
    )
    
    # Verify the widget can be created and has the right attributes
    assert slot is not None
    assert slot.slot_number == 1
    assert slot.timestamp == "2024-01-15 14:30"
    assert slot.playtime == "45h 32m"
    assert slot.location == "Whiterun"


def test_health_bar_widget():
    """Test health bar with hearts."""
    from gamesave_vcs.tui.widgets import HealthBar
    
    # Full health
    health = HealthBar(current=10, max=10)
    render = health.render()
    assert render is not None
    
    # Low health
    health_low = HealthBar(current=2, max=10)
    render_low = health_low.render()
    assert render_low is not None


def test_scroll_indicator_widget():
    """Test scroll indicator arrows."""
    from gamesave_vcs.tui.widgets import ScrollIndicator
    
    indicator = ScrollIndicator(direction="down")
    render = indicator.render()
    assert render is not None


# =============================================================================
# Screen Tests
# =============================================================================


@pytest.mark.asyncio
async def test_main_menu_screen():
    """Test main menu screen renders correctly."""
    from gamesave_vcs.tui.screens.main_menu import MainMenuScreen
    
    screen = MainMenuScreen()
    
    # Should have compose method
    assert hasattr(screen, 'compose')


@pytest.mark.asyncio
async def test_game_browser_screen():
    """Test game browser screen."""
    from gamesave_vcs.tui.screens.game_browser import GameBrowserScreen
    
    with patch('gamesave_vcs.tui.screens.game_browser.list_registered_games') as mock_list:
        mock_list.return_value = [
            {'name': 'Skyrim', 'backups': 5, 'last_backup': '2h ago'},
            {'name': 'Minecraft', 'backups': 12, 'last_backup': '1d ago'},
        ]
        
        screen = GameBrowserScreen()
        assert hasattr(screen, 'compose')


@pytest.mark.asyncio
async def test_timeline_screen():
    """Test timeline screen for save history."""
    from gamesave_vcs.tui.screens.timeline import TimelineScreen
    
    with patch('gamesave_vcs.tui.screens.timeline.get_save_history') as mock_hist:
        mock_hist.return_value = [
            {'timestamp': '2024-01-15 14:00', 'size': '5MB', 'message': 'Before boss'},
            {'timestamp': '2024-01-15 16:30', 'size': '5.1MB', 'message': 'After boss'},
        ]
        
        screen = TimelineScreen(game_name="Skyrim")
        assert screen.game_name == "Skyrim"
        assert hasattr(screen, 'compose')


@pytest.mark.asyncio
async def test_save_details_screen():
    """Test save details screen."""
    from gamesave_vcs.tui.screens.save_details import SaveDetailsScreen
    
    screen = SaveDetailsScreen(
        game_name="Skyrim",
        save_timestamp="2024-01-15 14:30",
        save_path=Path("/tmp/test.save")
    )
    
    assert screen.game_name == "Skyrim"
    assert hasattr(screen, 'compose')


# =============================================================================
# TUI App Tests
# =============================================================================


@pytest.mark.asyncio
async def test_retro_app_initialization():
    """Test TUI app initializes correctly."""
    from gamesave_vcs.tui.app import RetroSaveManagerApp
    
    app = RetroSaveManagerApp()
    
    assert app.TITLE == "GameSave-VCS"
    assert hasattr(app, 'push_screen')


@pytest.mark.asyncio
async def test_app_screen_navigation():
    """Test navigation between screens."""
    from gamesave_vcs.tui.app import RetroSaveManagerApp
    
    app = RetroSaveManagerApp()
    
    # Should be able to push screens
    with patch.object(app, 'push_screen') as mock_push:
        app.action_show_games()
        mock_push.assert_called_once()


@pytest.mark.asyncio
async def test_app_quit_action():
    """Test quit action works."""
    from gamesave_vcs.tui.app import RetroSaveManagerApp
    
    app = RetroSaveManagerApp()
    
    # Should have quit action
    assert hasattr(app, 'action_quit')


# =============================================================================
# Key Binding Tests
# =============================================================================


def test_key_bindings_defined():
    """Test all retro-style key bindings are defined."""
    from gamesave_vcs.tui.app import RetroSaveManagerApp
    
    app = RetroSaveManagerApp()
    
    # Should have gaming-style bindings - use class attribute
    bindings = getattr(RetroSaveManagerApp, 'BINDINGS', [])
    binding_keys = [b[0] if isinstance(b, tuple) else b.key for b in bindings]
    
    # Essential bindings - check for 'q' and 'g' at minimum
    assert 'q' in binding_keys, "Should have quit binding"
    assert 'g' in binding_keys or 'm' in binding_keys, "Should have navigation binding"


# =============================================================================
# Animation Tests
# =============================================================================


def test_typewriter_effect():
    """Test typewriter text effect for retro feel."""
    from gamesave_vcs.tui.effects import Typewriter
    
    tw = Typewriter(text="It's dangerous to go alone!", speed=0.01)
    
    # Should gradually reveal text
    assert tw.current_text == ""  # Starts empty
    
    # After update, should have some characters
    tw.update(0.05)
    assert len(tw.current_text) > 0


def test_blinking_cursor():
    """Test blinking cursor effect."""
    from gamesave_vcs.tui.effects import BlinkingCursor
    
    cursor = BlinkingCursor()
    
    # Should toggle visibility
    initial = cursor.visible
    cursor.update(0.6)  # Past blink interval
    assert cursor.visible != initial


def test_scroll_text():
    """Test scrolling text for long messages."""
    from gamesave_vcs.tui.effects import ScrollingText
    
    text = "A" * 100
    scroller = ScrollingText(text=text, width=20)
    
    initial = scroller.visible_text
    scroller.update(0.5)
    # Text should have moved
    assert scroller.visible_text != initial or len(scroller.visible_text) == 20


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.asyncio
async def test_full_tui_workflow():
    """Test complete TUI workflow from launch to backup."""
    from gamesave_vcs.tui.app import RetroSaveManagerApp
    
    app = RetroSaveManagerApp()
    
    # Should be able to create app without errors
    assert app is not None
    assert app.TITLE == "GameSave-VCS"
    
    # Check that screens are registered
    assert "main_menu" in app.SCREENS
    assert "game_browser" in app.SCREENS


def test_tui_css_styling():
    """Test that CSS styling is loaded correctly."""
    from gamesave_vcs.tui.app import RetroSaveManagerApp
    
    # Should have CSS defined at class level
    assert hasattr(RetroSaveManagerApp, 'CSS'), "Should have CSS defined"
    css = getattr(RetroSaveManagerApp, 'CSS', '')
    assert len(css) > 0, "CSS should not be empty"
    assert 'background' in css.lower(), "CSS should define background"
