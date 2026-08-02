import datetime
import time

import serial

PORT = "/dev/ttyACM1"
BAUD = 115200

with serial.Serial(PORT, BAUD, timeout=1) as ser:
    while True:
        now = datetime.datetime.now(tz=datetime.UTC).astimezone()
        nowstr = now.strftime("%H:%M:%S")
        ser.write(f"{nowstr}\n".encode())
        time.sleep(0.5)
