import time  # noqa: A005, D100

import busio
import displayio
import fourwire
import usb_cdc
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


class StatusDisplay:
    """Main display."""

    def __init__(self) -> None:
        """Instantiate config, set up display and updaters."""
        self.config = Config()
        self.display = self.get_display()
        self.font = bitmap_font.load_font(self.config.font.file)
        self.display_group = displayio.Group()
        self.display.root_group = self.display_group
        self.dynamic_labels: list[bitmap_label.Label] = []
        self.serial = usb_cdc.data
        self.buffer = b""

        if self.serial is None:
            msg = "USB CDC not enabled."
            raise TypeError(msg)

    def get_display(self) -> SSD1305:
        """Initialize display."""
        displayio.release_displays()

        spi = busio.SPI(clock=board.GP10, MOSI=board.GP11)
        display_bus = fourwire.FourWire(
            spi,
            command=board.GP8,
            chip_select=board.GP9,
            reset=board.GP12,
            baudrate=1000000,
        )

        return SSD1305(
            display_bus,
            width=self.config.display.width,
            height=self.config.display.height,
        )

    def get_input(self) -> str | None:
        if self.serial is None:
            msg = "USB CDC not enabled."
            raise TypeError(msg)

        waiting = self.serial.in_waiting
        if not waiting:
            return None

        self.buffer += self.serial.read(waiting)

        if b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            return line.decode("utf-8", "replace").strip()

        return None

    def main_loop(self) -> None:
        """Run main synchronous loop."""
        text = bitmap_label.Label(self.font, text="test static text", x=0, y=4)  # ty: ignore[invalid-argument-type]
        scroll = bitmap_label.Label(
            self.font,  # ty: ignore[invalid-argument-type]
            text="test scrolling text",
            max_characters=8,
            x=0,
            y=20,
            animate_time=self.config.scroll_interval_s,
        )
        input_label = bitmap_label.Label(self.font, text="test static text", x=89, y=4)  # ty: ignore[invalid-argument-type]
        self.display_group.append(text)
        self.display_group.append(scroll)
        self.display_group.append(input_label)
        self.dynamic_labels.append(scroll)
        self.dynamic_labels.append(input_label)

        while True:
            for e in self.dynamic_labels:
                e.update()

            input_text = self.get_input()
            if input_text is not None:
                input_label.text = input_text

            time.sleep(self.config.update_interval_s)


def main() -> None:  # noqa: D103
    status = StatusDisplay()
    status.main_loop()


if __name__ == "__main__":
    main()
