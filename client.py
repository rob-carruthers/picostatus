import datetime
import json
import time

import serial
from mpd import MPDClient

PORT = "/dev/ttyACM1"
BAUD = 115200

client = MPDClient()
client.connect(host="localhost", port=6600)


def get_mpd_data() -> tuple[str, int, int]:
    status = client.status()  # ty: ignore[unresolved-attribute]
    song = status.get("song")
    now_playing = "Stopped"
    pos = 0
    dur = 100
    if song is not None:
        now_playing = client.playlistinfo(song)  # ty:ignore[unresolved-attribute]
        if len(now_playing) == 0:
            return "Stopped", pos, dur

        now_playing = now_playing[0]["artist"] + " - " + now_playing[0]["title"]
        try:
            pos, dur = status["time"].split(":")
        except KeyError:
            return "Stopped", pos, dur

    return now_playing, pos, dur


with serial.Serial(PORT, BAUD, timeout=1) as ser:
    while True:
        now = datetime.datetime.now(tz=datetime.UTC).astimezone()
        nowstr = now.strftime("%H:%M:%S")
        now_playing, pos, dur = get_mpd_data()
        out_data = {
            "time": {"text": nowstr},
            "mpd": {"text": now_playing, "dur": dur, "pos": pos},
        }
        out_json = json.dumps(out_data)

        ser.write(f"{out_json}\n".encode())
        time.sleep(0.5)
