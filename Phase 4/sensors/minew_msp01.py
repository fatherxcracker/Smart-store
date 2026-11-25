"""Minew MSP01 (temperature / humidity / light / motion) - BLE receiver and decoder.

Three ways a reading reaches the store, all ending in sensors.record_reading():

1. BLE scan on the Raspberry Pi (this file, needs `pip install bleak`, MSP01_BLE=1).
   decode_service_data() reads Minew's service data (UUID 0xFFE1). Only the
   frame layout described below is decoded; verify it against your own sensor
   after configuring it with BeaconSET+ (see README).
2. MQTT: publish {"temperature":..,"humidity":..,"light":..,"motion":..} to topic MSP01.
3. HTTP: POST the same JSON to /sensors/api/ingest with the X-Sensor-Token header
   (for a gateway or a reelyActive pipeline).

A built-in simulator (MSP01_SIMULATE=1) fills the widgets for demos with no sensor.
"""

import asyncio
import math
import os
import random
import threading

MINEW_SERVICE_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"
FRAME_TYPE = 0xA1  # every Minew sensor frame starts with 0xA1

# Byte 1 says which slot/frame this is. The MSP01 rotates through them, so one
# advertisement carries only some of the values (the dashboard keeps the newest
# value of each field). Layouts follow reelyActive's advlib-ble-services (minew.js)
# and were checked against our sensor (C3:00:00:45:5D:A6).
FRAME_TEMP_HUMIDITY = 0x01  # bytes 3-4 temperature, 5-6 humidity (signed 8.8)
FRAME_ACCELERATION = 0x03   # x/y/z acceleration (not stored)
FRAME_INFO = 0x08           # device name "MSP01" (only battery is used)
FRAME_PIR = 0x11            # bit 0 of byte 4 = motion detected
FRAME_LIGHT = 0x19          # bytes 3-4 photoresistor reading, unsigned 16-bit big-endian (raw, not calibrated lux)


def _fixed_8_8(high, low):
    """Minew writes temperature/humidity as signed int8 + unsigned 1/256 fraction."""
    return round(int.from_bytes([high], "big", signed=True) + low / 256.0, 2)


def decode_service_data(data: bytes):
    """Decode one Minew service-data frame. Returns a dict (maybe empty) with the
    fields this frame carries: battery plus temperature/humidity, motion or light.

    Common layout: byte 0 = 0xA1 | byte 1 = frame type | byte 2 = battery %
    followed by the frame's values and the sensor's MAC address (6 bytes, reversed).
    """
    if not data or len(data) < 3 or data[0] != FRAME_TYPE:
        return {}
    frame = data[1]
    result = {"battery": int(data[2])}
    if frame == FRAME_TEMP_HUMIDITY and len(data) >= 7:
        temperature, humidity = _fixed_8_8(data[3], data[4]), _fixed_8_8(data[5], data[6])
        if -40 <= temperature <= 100:
            result["temperature"] = temperature
        if 0 <= humidity <= 100:
            result["humidity"] = humidity
    elif frame == FRAME_PIR and len(data) >= 5:
        result["motion"] = data[4] & 0x01
    elif frame == FRAME_LIGHT and len(data) >= 5:
        result["light"] = int.from_bytes(data[3:5], "big")
    return result


def start_ble_scanner(app, record, address=""):
    """Background thread: listen for MSP01 advertisements with bleak."""
    try:
        from bleak import BleakScanner
    except ImportError:
        print("[ble] 'bleak' is not installed - run: pip install bleak  (BLE scanning is off)")
        return None
    wanted = address.strip().lower()

    def on_advert(device, advert):
        if wanted and device.address.lower() != wanted:
            return
        data = (advert.service_data or {}).get(MINEW_SERVICE_UUID)
        if not data:
            return
        fields = decode_service_data(bytes(data))
        if len(fields) > 1:
            with app.app_context():
                try:
                    record(fields, source="ble")
                except ValueError as error:
                    print(f"[ble] Ignored reading: {error}")

    async def scan_forever():
        while True:
            try:
                async with BleakScanner(on_advert):
                    while True:
                        await asyncio.sleep(3600)
            except Exception as error:
                print(f"[ble] Scanner stopped ({error}); retrying in 15 s")
                await asyncio.sleep(15)

    thread = threading.Thread(target=lambda: asyncio.run(scan_forever()), daemon=True, name="msp01-ble")
    thread.start()
    print("[ble] Listening for Minew MSP01 advertisements")
    return thread


def start_simulator(app, record, every=5, stop_event=None):
    """Simulate MSP01 readings until the optional stop event is set."""
    stop_event = stop_event if stop_event is not None else threading.Event()

    def run():
        t = 0
        while not stop_event.is_set():
            t += 1
            reading = {
                "temperature": round(21 + 2 * math.sin(t / 30) + random.uniform(-.2, .2), 1),
                "humidity": round(45 + 6 * math.sin(t / 40) + random.uniform(-.5, .5), 1),
                "light": round(max(0, 320 + 200 * math.sin(t / 25) + random.uniform(-15, 15))),
                "motion": 1 if random.random() < 0.25 else 0,
                "battery": 87,
            }
            with app.app_context():
                try:
                    record(reading, source="simulator")
                except Exception as error:
                    print(f"[sim] {error}")
            stop_event.wait(every)

    thread = threading.Thread(target=run, daemon=True, name="msp01-sim")
    thread.start()
    print("[sim] MSP01 simulator running (MSP01_SIMULATE=1)")
    return thread
