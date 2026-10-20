"""
Smart Store - Phase 2
DC motor control (simulates the fridge fan), driven by a motor driver board
(e.g. L298N) wired to the Raspberry Pi's GPIO pins.

Like Phase 1, this falls back to a "mock" mode when real GPIO hardware isn't
available (e.g. running on a laptop), so the rest of the dashboard can be
developed and tested without the Pi.
"""

# Raspberry Pi GPIO pins (BCM numbering) - match these to your wiring.
EN1 = 22   # motor driver enable (speed/on-off)
IN1 = 27   # motor driver direction pin 1
IN2 = 17   # motor driver direction pin 2

try:
    from gpiozero import OutputDevice

    enable = OutputDevice(EN1, initial_value=False)
    input1 = OutputDevice(IN1, initial_value=True)
    input2 = OutputDevice(IN2, initial_value=False)
    HARDWARE_MODE = "real"
    print("[hardware] gpiozero detected real Raspberry Pi GPIO pins (motor driver).")
except Exception as gpio_error:
    print(f"[hardware] GPIO not available ({gpio_error}). Using mock motor driver for local testing.")

    class MockOutputDevice:
        def __init__(self, pin, initial_value=False):
            self.pin = pin
            self.value = initial_value

        def on(self):
            self.value = True
            print(f"[mock-hardware] GPIO{self.pin} -> ON")

        def off(self):
            self.value = False
            print(f"[mock-hardware] GPIO{self.pin} -> OFF")

        def close(self):
            pass

    enable = MockOutputDevice(EN1, initial_value=False)
    input1 = MockOutputDevice(IN1, initial_value=True)
    input2 = MockOutputDevice(IN2, initial_value=False)
    HARDWARE_MODE = "mock"


def fan_on():
    input1.on()
    input2.off()
    enable.on()
    print("Fan ON")


def fan_off():
    enable.off()
    print("Fan OFF")


def cleanup():
    enable.off()
    input1.close()
    input2.close()
    enable.close()
    print("GPIO cleaned up")
