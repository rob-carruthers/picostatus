"""Configuration for picostatus."""

import displayio


class DisplayConfig:
    """Configuration for the SSD1305 display."""

    width = 128
    height = 32


class FontConfig:
    """Configuration for display font."""

    file: str = "/fonts/5x8.bdf"
    char_width: int = 5
    char_height: int = 8


class Config:
    """Static configuration variables."""

    display: DisplayConfig = DisplayConfig()
    font: FontConfig = FontConfig()
    scroll_interval_s: float = 0.6
    update_interval_s: float = 0.05

    @property
    def max_chars_x(self) -> int:
        """Maximum displayable characters along width."""
        return self.display.width // self.font.char_width

    @property
    def max_chars_y(self) -> int:
        """Maximum displayable characters along height."""
        return self.display.height // self.font.char_height


PALETTE = displayio.Palette(2)
PALETTE[0] = 0x000000
PALETTE[1] = 0xFFFFFF
