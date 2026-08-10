import json  # noqa: A005, D100
import time

import busio
import displayio
import fourwire
import usb_cdc
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import bitmap_label
from adafruit_displayio_ssd1305 import SSD1305

from config import Config
from module import Module, MPDModule, PulseModule

try:
    from typing import TYPE_CHECKING, Any
except ImportError:
    TYPE_CHECKING = False  # ty: ignore[invalid-assignment]

if TYPE_CHECKING:
    from adafruit_bitmap_font.bdf import BDF
    from board_definitions import raspberry_pi_pico2 as board

    from module import InputDataType

else:
    import board


class StatusDisplay:
    """Main display."""

    def __init__(self) -> None:
        """Instantiate config, set up display and updaters."""
        self.config = Config()
        self.display = self.get_display()
        self.font: BDF = bitmap_font.load_font(self.config.font.file)  # ty: ignore[invalid-assignment]
        self.display_group = displayio.Group()
        self.display.root_group = self.display_group
        self.dynamic_labels: list[bitmap_label.Label] = []
        self.serial = usb_cdc.data
        self.buffer = b""
        self.modules = self.setup_modules()

        if self.serial is None:
            msg = "USB CDC not enabled."
            raise TypeError(msg)

    def setup_modules(self) -> list[Module]:
        """Set up modules for instance."""
        modules = [
            Module(
                self.config,
                self.font,
                "time",
                align="right",
                max_chars=8,
                y=4,
            ),
            PulseModule(
                self.config,
                self.font,
                "pulse",
                align="right",
                y=14,
            ),
            Module(
                self.config,
                self.font,
                "pacman",
                align="left",
                max_chars=12,
                y=4,
            ),
            MPDModule(
                self.config,
                self.font,
                "mpd",
                align="left",
                y=24,
                max_chars=self.config.max_chars_x - 2,
                animate_time=0.5,
            ),
        ]

        for module in modules:
            for element in module.display_elements:
                self.display_group.append(element)
                if isinstance(element, bitmap_label.Label):
                    self.dynamic_labels.append(element)

        return modules

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
        while True:
            input_data_str = self.get_cdc_input_with_buffer()
            if input_data_str is not None:
                input_data: dict[InputDataType, dict[str, Any]] = json.loads(input_data_str)
                for module in self.modules:
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
