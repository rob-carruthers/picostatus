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
    from typing import TYPE_CHECKING, Any, Literal
except ImportError:
    TYPE_CHECKING = False  # ty: ignore[invalid-assignment]

if TYPE_CHECKING:
    from board_definitions import raspberry_pi_pico2 as board

    InputDataType = Literal["time", "mpd", "pacman"]
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
        y: int,
        align: Literal["left", "right"],
        max_chars: int,
        animate_time: float = 1.0,
    ) -> None:
        self.input_key = input_key

        self.label = bitmap_label.Label(
            font,
            text=" " * (max_chars or 1),
            max_characters=max_chars,
            animate_time=animate_time,
        )

        if align == "right":
            self.label.x = config.display.width - (max_chars or 1) * config.font.char_width
        else:
            self.label.x = 0
        self.label.y = y

        self.display_elements = [self.label]

    def update(self, input_data: dict[InputDataType, dict[str, Any]]) -> None:
        text = input_data[self.input_key]["text"]
        if self.label.text.strip() != text:
            self.label.text = text


class MPDModule(Module):
    def __init__(
        self,
        config: Config,
        font,
        input_key: InputDataType,
        y: int,
        align: Literal["left", "right"],
        max_chars: int,
        animate_time: float = 1.0,
    ) -> None:
        super().__init__(
            config=config,
            font=font,
            input_key=input_key,
            y=y,
            align=align,
            max_chars=max_chars - 1,
            animate_time=animate_time,
        )
        self.label.x = 9
        self.bar_width = config.display.width
        self.bar = displayio.Bitmap(self.bar_width, 1, 2)
        self.palette = displayio.Palette(2)
        self.palette[0] = 0x000000
        self.palette[1] = 0xFFFFFF
        self.bar_grid = displayio.TileGrid(
            self.bar,
            pixel_shader=self.palette,
            x=0,
            y=config.display.height - 1,
        )

        self.icon_width = 6
        self.icon_height = 6
        self.icon = displayio.Bitmap(self.icon_width, self.icon_height, 2)
        self.icon_grid = displayio.TileGrid(self.icon, pixel_shader=self.palette, x=0, y=y - 3)

        for j in range(self.icon_height):
            for i in range(self.icon_width):
                self.icon[i, j] = 1

        self.display_elements = [self.label, self.bar_grid, self.icon_grid]

        self.icon_dispatcher = {
            "stop": self.icon_fill_all,
            "play": self.icon_play,
            "pause": self.icon_pause,
        }

    def icon_blank(self) -> None:
        for i in range(self.icon_width):
            for j in range(self.icon_height):
                self.icon[i, j] = 0

    def icon_fill_all(self) -> None:
        for i in range(self.icon_width):
            for j in range(self.icon_height):
                self.icon[i, j] = 1

    def icon_play(self) -> None:
        self.icon_blank()

        for i in range(self.icon_width):
            for j in range(self.icon_height):
                if j < i or (j >= (self.icon_height - i)):
                    continue
                self.icon[i, j] = 1

    def icon_pause(self) -> None:
        self.icon_fill_all()

        r = list(range(self.icon_width))
        low = self.icon_width // 3
        high = self.icon_width * 2 // 3
        for i in r[low:high]:
            for j in range(self.icon_height):
                self.icon[i, j] = 0

    def update(self, input_data: dict[InputDataType, dict[str, str | int]]) -> None:
        mpd_data = input_data[self.input_key]
        text = mpd_data["text"]
        state = str(mpd_data["state"])

        if not isinstance(text, str):
            return
        text = text + (" | " if text != "Stopped" else "")
        if self.label.text.strip() != text:
            self.label.text = text

        dur = int(mpd_data["dur"])
        pos = int(mpd_data["pos"])
        self.icon_dispatcher[state]()

        bar_fill = int((pos / dur) * self.bar_width)

        for x in range(self.bar_width):
            self.bar[x, 0] = 1 if x < bar_fill else 0


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
        self.modules = self.setup_modules()

        if self.serial is None:
            msg = "USB CDC not enabled."
            raise TypeError(msg)

    def setup_modules(self) -> list[Module]:
        modules = [
            Module(
                self.config,
                self.font,
                "time",
                align="right",
                max_chars=8,
                y=4,
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
                max_chars=self.config.max_chars_x,
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
