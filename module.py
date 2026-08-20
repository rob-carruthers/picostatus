"""Modules for picostatus."""

import displayio
from adafruit_display_text import bitmap_label

from config import PALETTE

try:
    from typing import TYPE_CHECKING, Any, Literal
except ImportError:
    TYPE_CHECKING = False  # ty: ignore[invalid-assignment]

if TYPE_CHECKING:
    from adafruit_bitmap_font.bdf import BDF

    from config import Config

    InputDataType = Literal["time", "mpd", "pacman", "pulse"]


class Module:
    """A module taking data for display."""

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        config: Config,
        font: BDF,
        input_key: InputDataType,
        y: int,
        align: Literal["left", "right"],
        max_chars: int | None,
        animate_time: float = 1.0,
    ) -> None:
        """Initialise input key and label."""
        self.input_key = input_key

        self.label = bitmap_label.Label(
            font,  # ty: ignore[invalid-argument-type]
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
        """Update the output for this Module."""
        text = input_data[self.input_key]["text"]
        if self.label.text.strip() != text:
            self.label.text = text


class MPDModule(Module):
    """Module for displaying MPD status."""

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        config: Config,
        font: BDF,
        input_key: InputDataType,
        y: int,
        align: Literal["left", "right"],
        max_chars: int,
        animate_time: float = 1.0,
    ) -> None:
        """Initialise input key, label, progress bar, and icon."""
        super().__init__(
            config=config,
            font=font,
            input_key=input_key,
            y=y,
            align=align,
            max_chars=max_chars,
            animate_time=animate_time,
        )
        self.label.x = 10
        self.bar_width = config.display.width
        self.bar = displayio.Bitmap(self.bar_width, 1, 2)
        self.bar_grid = displayio.TileGrid(
            self.bar,
            pixel_shader=PALETTE,
            x=0,
            y=config.display.height - 1,
        )

        self.icon_width = 6
        self.icon_height = 7
        icon_x = 0
        self.icon = displayio.Bitmap(self.icon_width, self.icon_height, 2)
        self.icon_grid = displayio.TileGrid(self.icon, pixel_shader=PALETTE, x=icon_x, y=y - 3)

        for j in range(self.icon_height):
            for i in range(self.icon_width):
                self.icon[i, j] = 1

        self.display_elements = [self.label, self.bar_grid, self.icon_grid]

        self.icon_dispatcher = {
            "stop": self.icon_fill_all,
            "play": self.icon_play,
            "pause": self.icon_pause,
        }

    def icon_set_all(self, val: Literal[0, 1]) -> None:
        """Set all pixels in icon to same value."""
        for i in range(self.icon_width):
            for j in range(self.icon_height):
                self.icon[i, j] = val

    def icon_blank(self) -> None:  # noqa: D102
        self.icon_set_all(0)

    def icon_fill_all(self) -> None:  # noqa: D102
        self.icon_set_all(1)

    def icon_play(self) -> None:
        """Create a 'play' icon."""
        self.icon_blank()

        for i in range(self.icon_width):
            for j in range(self.icon_height):
                if j < i or (j >= (self.icon_height - i)):
                    continue
                self.icon[i, j] = 1

    def icon_pause(self) -> None:
        """Create a 'pause' icon."""
        self.icon_fill_all()

        r = list(range(self.icon_width))
        low = self.icon_width // 3
        high = self.icon_width * 2 // 3
        for i in r[low:high]:
            for j in range(self.icon_height):
                self.icon[i, j] = 0

    def update(self, input_data: dict[InputDataType, dict[str, str | int]]) -> None:
        """Update output from MPD data input."""
        mpd_data = input_data[self.input_key]
        text = mpd_data["text"]
        state = str(mpd_data["state"])

        if not isinstance(text, str):
            return

        if self.label.text.strip() != text:
            text = text + ("    " if text != "Stopped" else "")
            self.label.text = text

        dur = int(mpd_data["dur"])
        pos = int(mpd_data["pos"])
        self.icon_dispatcher[state]()

        bar_fill = int((pos / dur) * self.bar_width)

        for x in range(self.bar_width):
            self.bar[x, 0] = 1 if x < bar_fill else 0


class PulseModule(Module):
    """Module for displaying PulseAudio / pipewire-pulse status."""

    def __init__(
        self,
        config: Config,
        font: BDF,
        input_key: InputDataType,
        y: int,
        align: Literal["left", "right"],
    ) -> None:
        """Initialise input key, label, and icon."""
        super().__init__(
            config=config,
            font=font,
            input_key=input_key,
            y=y,
            align=align,
            max_chars=None,
        )
        self.label.x = 99

        self.icon_width = 6
        self.icon_height = 6
        self.icon = displayio.Bitmap(self.icon_width, self.icon_height, 2)
        icon_x = 89
        self.icon_grid = displayio.TileGrid(self.icon, pixel_shader=PALETTE, x=icon_x, y=y - 3)

        for j in range(self.icon_height):
            for i in range(self.icon_width):
                self.icon[i, j] = 1

        self.display_elements = [self.label, self.icon_grid]
        self.icons: dict[Literal["headset", "speaker"], list[list[int]]] = {
            "headset": [
                [0, 1, 1, 1, 1, 0],
                [1, 0, 0, 0, 0, 1],
                [1, 0, 0, 0, 0, 1],
                [1, 0, 0, 0, 0, 1],
                [1, 1, 0, 0, 1, 1],
                [1, 1, 0, 0, 1, 1],
            ],
            "speaker": [
                [0, 0, 1, 0, 0, 0],
                [0, 1, 1, 0, 1, 0],
                [1, 1, 1, 0, 0, 1],
                [1, 1, 1, 0, 0, 1],
                [0, 1, 1, 0, 1, 0],
                [0, 0, 1, 0, 0, 0],
            ],
        }
        self.current_icon: Literal["headset", "speaker"] | None = None

    def icon_blank(self) -> None:
        """Set all icon px values to 0."""
        for i in range(self.icon_width):
            for j in range(self.icon_height):
                self.icon[i, j] = 0

    def set_icon(self, icon_type: Literal["headset", "speaker"]) -> None:
        """Create a headset icon."""
        icon = self.icons[icon_type]
        for j, line in enumerate(icon):
            for i, px in enumerate(line):
                self.icon[i, j] = px

    def update(self, input_data: dict[InputDataType, dict[str, str | bool]]) -> None:
        """Update output from PulseAudio data input."""
        pulse_data = input_data[self.input_key]
        text = pulse_data["text"]
        is_headset = pulse_data["is_headset"]

        if not isinstance(text, str):
            return

        if self.label.text.strip() != text:
            text = text + ("    " if text != "Stopped" else "")
            self.label.text = text

        icon = "headset" if is_headset else "speaker"
        if icon != self.current_icon:
            self.set_icon(icon)
            self.current_icon = icon
