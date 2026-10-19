from gpiozero import Buzzer
from time import sleep
led = Buzzer(22)
led.on()
sleep(3)
led.off()
