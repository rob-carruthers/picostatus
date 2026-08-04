import json
import time

import busio
import displayio
import fourwire
import usb_cdc
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import bitmap_label
from adafruit_displayio_ssd1305 import SSD1305

try:
    from typing import TYPE_CHECKING, Literal
except ImportError:
    TYPE_CHECKING = False  # ty: ignore[invalid-assignment]

if TYPE_CHECKING:
    from board_definitions import raspberry_pi_pico2 as board

    InputDataType = Literal["time"]
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

    @property
    def line_pos_y(self) -> dict[int, int]:
        output: dict[int, int] = {}

        for i in range(self.max_chars_y):
            output[i] = i * self.font.char_height + 4

        return output


class Module:
    def __init__(
        self,
        config: Config,
        font,
        input_key: InputDataType,
        x_char: int,
        y_char: int,
        scroll: tuple[int, float] | None = None,
    ) -> None:
        self.input_key = input_key
        self.line = y_char
        x = (((config.max_chars_x + x_char) * config.font.char_width) % config.display.width) - 1
        max_chars = scroll[0] if scroll is not None else None
        animate_time = scroll[1] if scroll is not None else 1.0
        self.label = bitmap_label.Label(
            font,
            text="",
            x=x,
            y=config.line_pos_y[y_char],
            max_characters=max_chars,
            animate_time=animate_time,
        )

    def update(self, input_data: dict[InputDataType, str]) -> None:
        text = input_data[self.input_key]
        if self.label.text != text:
            self.label.text = text


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

        display = SSD1305(
            display_bus,
            width=self.config.display.width,
            height=self.config.display.height,
        )

        display.auto_refresh = False

        return display

    def get_cdc_input_with_buffer(self, max_buffer: int = 4096) -> str | None:
        """Read serial input and return str data, if valid.

        This keeps a buffer but will only return the latest received input.
        """
        if self.serial is None:
            msg = "USB CDC not enabled."
            raise TypeError(msg)

        waiting = self.serial.in_waiting
        if not waiting:
            return None

        self.buffer += self.serial.read(waiting)
        if len(self.buffer) > max_buffer:
            self.buffer = self.buffer[-max_buffer:]

        if b"\n" not in self.buffer:
            return None

        lines = self.buffer.split(b"\n")
        self.buffer = lines[-1]
        complete_lines = lines[:-1]

        if not complete_lines:
            return None

        latest = complete_lines[-1]
        return latest.decode("utf-8", "replace").strip()

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

        modules = [Module(self.config, self.font, "time", x_char=-7, y_char=0)]
        for module in modules:
            self.display_group.append(module.label)
            self.dynamic_labels.append(module.label)

        while True:
            input_data_str = self.get_cdc_input_with_buffer()
            if input_data_str is not None:
                input_data: dict[InputDataType, str] = json.loads(input_data_str)
                for module in modules:
                    module.update(input_data)

            for e in self.dynamic_labels:
                e.update()

            self.display.refresh()
            time.sleep(self.config.update_interval_s)


def main() -> None:  # noqa: D103
    status = StatusDisplay()
    status.main_loop()


if __name__ == "__main__":
    main()
