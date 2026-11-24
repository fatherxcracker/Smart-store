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
FRAME_INFO = 0xA1  # Minew "info" frame carrying battery + temperature/humidity


def _fixed_8_8(high, low):
    """Minew writes temperature/humidity as signed int8 + 1/256 fraction."""
    value = int.from_bytes([high], "big", signed=True)
    return round(value + low / 256.0 * (1 if value >= 0 else -1), 2)


def decode_service_data(data: bytes):
    """Decode Minew service data. Returns a dict (maybe empty) with the fields
    that could be read: battery, temperature, humidity.

    Layout used (Minew info frame for temperature/humidity sensors):
        byte 0 frame type 0xA1 | 1 product model | 2 battery % |
        bytes 3-4 temperature (int8 + 1/256) | bytes 5-6 humidity (int8 + 1/256)
    """
    if not data or data[0] != FRAME_INFO or len(data) < 3:
        return {}
    result = {"battery": int(data[2])}
    if len(data) >= 7:
        temperature, humidity = _fixed_8_8(data[3], data[4]), _fixed_8_8(data[5], data[6])
        if -40 <= temperature <= 100:
            result["temperature"] = temperature
        if 0 <= humidity <= 100:
            result["humidity"] = humidity
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
