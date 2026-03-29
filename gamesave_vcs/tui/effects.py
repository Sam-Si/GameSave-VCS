"""Retro-style effects and animations for the TUI.

Typewriter text, blinking cursors, and other nostalgic effects.
"""

import time
from typing import Optional


class Typewriter:
    """Typewriter text effect - reveals text gradually."""
    
    def __init__(self, text: str, speed: float = 0.05):
        """Initialize typewriter effect.
        
        Args:
            text: Full text to reveal
            speed: Seconds per character
        """
        self.full_text = text
        self.speed = speed
        self.current_text = ""
        self._elapsed = 0.0
        self._char_index = 0
        self._complete = False
    
    def update(self, delta_time: float) -> None:
        """Update the typewriter effect.
        
        Args:
            delta_time: Time elapsed since last update
        """
        if self._complete:
            return
        
        self._elapsed += delta_time
        chars_to_add = int(self._elapsed / self.speed)
        
        if chars_to_add > 0:
            self._char_index = min(self._char_index + chars_to_add, len(self.full_text))
            self.current_text = self.full_text[:self._char_index]
            self._elapsed = 0.0
            
            if self._char_index >= len(self.full_text):
                self._complete = True
    
    @property
    def is_complete(self) -> bool:
        """Check if typewriter effect is complete."""
        return self._complete
    
    def skip(self) -> None:
        """Skip to end of text."""
        self.current_text = self.full_text
        self._complete = True


class BlinkingCursor:
    """Blinking cursor effect for input fields."""
    
    def __init__(self, blink_interval: float = 0.5, cursor_char: str = "▌"):
        """Initialize blinking cursor.
        
        Args:
            blink_interval: Seconds between blinks
            cursor_char: Character to use for cursor
        """
        self.blink_interval = blink_interval
        self.cursor_char = cursor_char
        self.visible = True
        self._elapsed = 0.0
    
    def update(self, delta_time: float) -> None:
        """Update cursor blink state.
        
        Args:
            delta_time: Time elapsed since last update
        """
        self._elapsed += delta_time
        if self._elapsed >= self.blink_interval:
            self.visible = not self.visible
            self._elapsed = 0.0
    
    def get_display(self) -> str:
        """Get current cursor display."""
        return self.cursor_char if self.visible else " "


class ScrollingText:
    """Horizontally scrolling text for long messages."""
    
    def __init__(self, text: str, width: int = 20, scroll_speed: float = 0.3):
        """Initialize scrolling text.
        
        Args:
            text: Full text to scroll
            width: Visible width of the scroll area
            scroll_speed: Seconds between scroll steps
        """
        self.text = text
        self.width = width
        self.scroll_speed = scroll_speed
        self._elapsed = 0.0
        self._offset = 0
        self._direction = 1  # 1 = right, -1 = left
        self.visible_text = text[:width]
    
    def update(self, delta_time: float) -> None:
        """Update scroll position.
        
        Args:
            delta_time: Time elapsed since last update
        """
        self._elapsed += delta_time
        if self._elapsed >= self.scroll_speed:
            self._elapsed = 0.0
            
            # Bounce back and forth
            max_offset = max(0, len(self.text) - self.width)
            
            if max_offset == 0:
                self.visible_text = self.text
                return
            
            self._offset += self._direction
            
            if self._offset >= max_offset:
                self._offset = max_offset
                self._direction = -1
            elif self._offset <= 0:
                self._offset = 0
                self._direction = 1
            
            self.visible_text = self.text[self._offset:self._offset + self.width]


class PulsingEffect:
    """Pulsing brightness effect for important elements."""
    
    def __init__(self, min_alpha: float = 0.5, max_alpha: float = 1.0, 
                 pulse_speed: float = 1.0):
        """Initialize pulsing effect.
        
        Args:
            min_alpha: Minimum brightness (0.0-1.0)
            max_alpha: Maximum brightness (0.0-1.0)
            pulse_speed: Pulses per second
        """
        self.min_alpha = min_alpha
        self.max_alpha = max_alpha
        self.pulse_speed = pulse_speed
        self._elapsed = 0.0
        self.current_alpha = max_alpha
    
    def update(self, delta_time: float) -> None:
        """Update pulse state.
        
        Args:
            delta_time: Time elapsed since last update
        """
        self._elapsed += delta_time
        # Sine wave for smooth pulsing
        import math
        phase = (self._elapsed * self.pulse_speed * 2 * math.pi) % (2 * math.pi)
        normalized = (math.sin(phase) + 1) / 2  # 0 to 1
        self.current_alpha = self.min_alpha + (normalized * (self.max_alpha - self.min_alpha))


class SparkleEffect:
    """Sparkle/star twinkle effect for treasure/magic items."""
    
    def __init__(self, chars: list = None, interval: float = 0.1):
        """Initialize sparkle effect.
        
        Args:
            chars: List of characters to cycle through
            interval: Seconds between character changes
        """
        self.chars = chars or ['✦', '✧', '★', '☆', '✦']
        self.interval = interval
        self._elapsed = 0.0
        self._index = 0
        self.current_char = self.chars[0]
    
    def update(self, delta_time: float) -> None:
        """Update sparkle animation.
        
        Args:
            delta_time: Time elapsed since last update
        """
        self._elapsed += delta_time
        if self._elapsed >= self.interval:
            self._elapsed = 0.0
            self._index = (self._index + 1) % len(self.chars)
            self.current_char = self.chars[self._index]
    
    def get_char(self) -> str:
        """Get current sparkle character."""
        return self.current_char


class LoadingSpinner:
    """Retro-style loading spinner."""
    
    def __init__(self, style: str = 'dots'):
        """Initialize loading spinner.
        
        Args:
            style: 'dots', 'arrows', or 'blocks'
        """
        if style == 'dots':
            self.frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        elif style == 'arrows':
            self.frames = ['←', '↖', '↑', '↗', '→', '↘', '↓', '↙']
        elif style == 'blocks':
            self.frames = ['▖', '▘', '▝', '▗']
        else:
            self.frames = ['◐', '◓', '◑', '◒']
        
        self._frame_index = 0
        self._elapsed = 0.0
        self.frame_time = 0.1
        self.current_frame = self.frames[0]
    
    def update(self, delta_time: float) -> None:
        """Update spinner animation.
        
        Args:
            delta_time: Time elapsed since last update
        """
        self._elapsed += delta_time
        if self._elapsed >= self.frame_time:
            self._elapsed = 0.0
            self._frame_index = (self._frame_index + 1) % len(self.frames)
            self.current_frame = self.frames[self._frame_index]
    
    def get_frame(self) -> str:
        """Get current spinner frame."""
        return self.current_frame
