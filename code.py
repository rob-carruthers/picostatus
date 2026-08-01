import time

import busio
import displayio
import fourwire
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import bitmap_label
from adafruit_displayio_ssd1305 import SSD1305

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False  # ty: ignore[invalid-assignment]

if TYPE_CHECKING:
    from board_definitions import raspberry_pi_pico2 as board
else:
    import board


class DisplayConfig:
    width = 128
    height = 32


class FontConfig:
    file: str = "/fonts/5x8.bdf"
    char_width: int = 5
    char_height: int = 8


class Config:
    display: DisplayConfig = DisplayConfig()
    font: FontConfig = FontConfig()

    @property
    def max_chars_x(self) -> int:
        return self.display.width // self.font.char_width

    @property
    def max_chars_y(self) -> int:
        return self.display.height // self.font.char_height


class StatusDisplay:
    def __init__(self):
        self.config = Config()
        self.display = self.get_display()
        self.font = bitmap_font.load_font(self.config.font.file)

    def get_display(self) -> SSD1305:
        displayio.release_displays()

        spi = busio.SPI(clock=board.GP10, MOSI=board.GP11)
        display_bus = fourwire.FourWire(
            spi,
            command=board.GP8,
            chip_select=board.GP9,
            reset=board.GP12,
            baudrate=1000000,
        )

        display = SSD1305(
            display_bus, width=self.config.display.width, height=self.config.display.height
        )

        return display

    def run(self) -> None:
        group = displayio.Group()
        text = bitmap_label.Label(self.font, text="test static text", x=0, y=4)  # ty: ignore[invalid-argument-type]
        scroll = bitmap_label.Label(
            self.font,  # ty: ignore[invalid-argument-type]
            text="test scrolling text",
            max_characters=8,
            x=0,
            y=20,
            animate_time=0.5,
        )
        group.append(text)
        group.append(scroll)
        self.display.root_group = group

        while True:
            scroll.update()
            time.sleep(0.05)


def main() -> None:
    status = StatusDisplay()
    status.run()


if __name__ == "__main__":
    main()
