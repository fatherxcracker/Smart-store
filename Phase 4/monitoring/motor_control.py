"""
Smart Store - Phase 2
DC fan/motor control using PWM duty cycle on the L293D enable pin.
GPIO numbers use BCM numbering.
"""

EN1 = 22   # L293D EN1: PWM speed control
IN1 = 27   # L293D IN1: direction
IN2 = 17   # L293D IN2: direction

DEFAULT_DUTY_CYCLE = 40  # percent; adjust as needed (0-100)
PWM_FREQUENCY = 1000     # Hz

def _use_header_gpio_chip():
    """Point gpiozero at the gpiochip that drives the 40-pin header.

    gpiozero 2.0.1 only tries gpiochip4 (Pi 5) or gpiochip0. On newer Pi 5
    kernels the header chip ("pinctrl-rp1") can have another number
    (gpiochip15 on our Pi), so gpiozero finds no pins and the fan silently
    falls back to the mock driver. Needs the lgpio package in the venv.
    """
    import glob
    import lgpio
    from gpiozero import Device
    from gpiozero.pins.lgpio import LGPIOFactory, LGPIOPin
    from gpiozero.pins.local import LocalPiFactory

    for path in sorted(glob.glob("/dev/gpiochip*")):
        number = int(path.removeprefix("/dev/gpiochip"))
        try:
            handle = lgpio.gpiochip_open(number)
        except lgpio.error:
            continue
        label = lgpio.gpio_get_chip_info(handle)[3]
        if label == "pinctrl-rp1" or label.startswith("pinctrl-bcm"):
            class HeaderFactory(LGPIOFactory):
                def __init__(self):
                    LocalPiFactory.__init__(self)
                    self._handle = handle
                    self._chip = number
                    self.pin_class = LGPIOPin

            Device.pin_factory = HeaderFactory()
            print(f"[hardware] Using {path} ({label}) for the GPIO header.")
            return
        lgpio.gpiochip_close(handle)


try:
    from gpiozero import OutputDevice, PWMOutputDevice

    try:
        _use_header_gpio_chip()
    except ImportError:
        pass  # no lgpio: let gpiozero pick its default pin factory

    enable = PWMOutputDevice(
        EN1,
        frequency=PWM_FREQUENCY,
        initial_value=0
    )
    input1 = OutputDevice(IN1, initial_value=True)
    input2 = OutputDevice(IN2, initial_value=False)

    HARDWARE_MODE = "real"
    print("[hardware] PWM motor control initialized.")

except Exception as gpio_error:
    print(f"[hardware] GPIO not available ({gpio_error}). Using mock motor driver.")

    class MockOutputDevice:
        def __init__(self, pin, initial_value=False, **kwargs):
            self.pin = pin
            self.value = initial_value

        def on(self):
            self.value = 1

        def off(self):
            self.value = 0

        def close(self):
            pass

    enable = MockOutputDevice(EN1, initial_value=0)
    input1 = MockOutputDevice(IN1, initial_value=1)
    input2 = MockOutputDevice(IN2, initial_value=0)

    HARDWARE_MODE = "mock"


def set_fan_speed(duty_cycle):
    """Set motor PWM duty cycle as an integer percentage from 0 to 100."""
    duty_cycle = int(duty_cycle)

    if not 0 <= duty_cycle <= 100:
        raise ValueError("Duty cycle must be between 0 and 100.")

    # Duty cycle 0 means no power; 100 means continuously enabled.
    enable.value = duty_cycle / 100.0

    print(f"Fan duty cycle: {duty_cycle}%")


def fan_on(duty_cycle=DEFAULT_DUTY_CYCLE):
    """Run the fan at the requested duty cycle."""
    duty_cycle = int(duty_cycle)

    if not 0 <= duty_cycle <= 100:
        raise ValueError("Duty cycle must be between 0 and 100.")

    input1.on()
    input2.off()

    set_fan_speed(duty_cycle)

    print("Fan ON")


def fan_off():
    """Stop the motor by setting PWM duty cycle to zero."""
    set_fan_speed(0)

    print("Fan OFF")


def cleanup():
    """Safely stop PWM and release GPIO resources."""
    enable.value = 0

    input1.off()
    input2.off()

    input1.close()
    input2.close()
    enable.close()

    print("GPIO cleaned up")