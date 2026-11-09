"""
Smart Store - Phase 3
Chafon CF600 UHF RFID reader (USB serial), based on the class SDK test script.

    import rfid_reader
    epcs = rfid_reader.read_tags()   # every tag on the reader right now, e.g. ["E280...01", "E280...02"]

Pi setup (once): see README "RFID reader setup" (usbserial driver + dialout group).

No reader plugged in (e.g. testing on a laptop)? Set RFID_SIMULATE=1 in .env:
read_tags() then returns the EPCs listed in RFID_SIMULATED_TAGS instead.
"""

import os
import threading
import time

from dotenv import load_dotenv

load_dotenv()

PORT = os.environ.get("RFID_PORT", "/dev/ttyUSB0")   # /dev/ttyACM0 on some Pis
BAUD = int(os.environ.get("RFID_BAUD", "115200"))
SCAN_SECONDS = float(os.environ.get("RFID_SCAN_SECONDS", "1.5"))
SIMULATE = os.environ.get("RFID_SIMULATE", "0").lower() in ("1", "true", "yes")
SIMULATED_TAGS = [
    tag.strip().upper()
    for tag in os.environ.get(
        "RFID_SIMULATED_TAGS",
        "E28011700000020A1B2C3D01,E28011700000020A1B2C3D02,E28011700000020A1B2C3D04",
    ).split(",")
    if tag.strip()
]

# Chafon "inventory" command: asks the reader for every tag in range.
READ_TAGS_COMMAND = bytes([0x04, 0xFF, 0x01, 0x1B, 0xB4])

# Only one request may use the serial port at a time.
_port_lock = threading.Lock()


class RFIDError(Exception):
    """Raised with a message that can be shown to the user."""


def parse_epcs(buf):
    """Pull EPCs out of CF600 tag frames.

    Frame: CF | addr | cmd(2) | len | status | rssi(2) | ant | ? | epc_len | epc | crc(2)
    Returns (list of EPC hex strings, leftover bytes of an incomplete frame).
    """
    epcs = []
    i = 0
    while True:
        i = buf.find(0xCF, i)
        if i < 0 or i + 5 > len(buf):
            return epcs, buf[i:] if i >= 0 else b""
        length = buf[i + 4]
        end = i + 5 + length + 2
        if end > len(buf):
            return epcs, buf[i:]
        data = buf[i + 5:i + 5 + length]
        if length >= 6 and data[0] == 0x00:
            epc_len = data[5]
            epc = data[6:6 + epc_len]
            if len(epc) == epc_len and epc_len > 0:
                epcs.append(epc.hex().upper())
        i = end


def read_tags(seconds=None):
    """Read for `seconds` and return every distinct EPC seen (all tags at once)."""
    seconds = SCAN_SECONDS if seconds is None else seconds

    if SIMULATE:
        time.sleep(min(seconds, 0.3))
        return list(SIMULATED_TAGS)

    try:
        import serial
    except ImportError:
        raise RFIDError("pyserial is not installed. Run: pip install -r requirements.txt")

    if not _port_lock.acquire(timeout=seconds + 3):
        raise RFIDError("The RFID reader is busy. Try again.")

    try:
        try:
            ser = serial.Serial(PORT, BAUD, timeout=0.2)
        except serial.SerialException as error:
            text = str(error)
            if "Permission denied" in text:
                raise RFIDError(
                    f"No permission to open {PORT}. Run: sudo usermod -aG dialout $USER, then log out and in."
                )
            raise RFIDError(
                f"RFID reader not found on {PORT}. Check the USB cable and run the usbserial "
                f"setup from the README (or set RFID_PORT in .env)."
            )

        found = {}
        buf = b""
        try:
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                ser.write(READ_TAGS_COMMAND)
                time.sleep(0.3)
                buf += ser.read(ser.in_waiting or 1)
                epcs, buf = parse_epcs(buf)
                for epc in epcs:
                    found[epc] = True  # keeps first-seen order, drops repeats
        finally:
            ser.close()
        return list(found)
    finally:
        _port_lock.release()


def status():
    """Small summary for the UI / README checks."""
    return {"simulate": SIMULATE, "port": PORT, "baud": BAUD, "scan_seconds": SCAN_SECONDS}


if __name__ == "__main__":
    # Quick test on the Pi:  python rfid_reader.py
    print(f"Reading from {'SIMULATED reader' if SIMULATE else PORT} ... hold tags near the reader (Ctrl+C to stop)")
    try:
        while True:
            tags = read_tags()
            print(tags if tags else "(no tags)")
    except RFIDError as error:
        print("Error:", error)
    except KeyboardInterrupt:
        pass
