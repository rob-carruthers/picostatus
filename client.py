import datetime
import json
import time

import serial

PORT = "/dev/ttyACM1"
BAUD = 115200

with serial.Serial(PORT, BAUD, timeout=1) as ser:
    while True:
        now = datetime.datetime.now(tz=datetime.UTC).astimezone()
        nowstr = now.strftime("%H:%M:%S")
        out_data = {"time": nowstr, "mpd": "Radiohead - Everything In Its Right Place"}
        out_json = json.dumps(out_data)
        ser.write(f"{out_json}\n".encode())
        time.sleep(0.5)
