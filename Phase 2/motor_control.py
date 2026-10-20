from gpiozero import OutputDevice

# Raspberry Pi GPIO pins (BCM numbering)
EN1 = 22
IN1 = 27
IN2 = 17

# Create the GPIO devices
enable = OutputDevice(EN1, initial_value=False)
input1 = OutputDevice(IN1, initial_value=True)
input2 = OutputDevice(IN2, initial_value=False)


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
