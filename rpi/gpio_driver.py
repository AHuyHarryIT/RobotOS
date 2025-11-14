# import RPi.GPIO as GPIO
from typing import Tuple, Sequence

class GPIODriver:
    def __init__(self, pins: Sequence[int]):
        self.pins = tuple(pins)
        self._configured = False

    def setup(self):
        if self._configured:
            return
        # GPIO.setmode(GPIO.BCM)
        # for p in self.pins:
        #     GPIO.setup(p, GPIO.OUT)
        #     GPIO.output(p, GPIO.LOW)
        self._configured = True

    def apply_bits(self, bits: Tuple[int, int, int]):
        """bits = (b1, b2, b3), each 0/1"""
        if not self._configured:
            self.setup()
        # for pin, bit in zip(self.pins, bits):
        #     GPIO.output(pin, GPIO.HIGH if bit else GPIO.LOW)

    def stop(self):
        """All LOW."""
        self.apply_bits((0, 0, 0))

    def cleanup(self):
        try:
            self.stop()
        finally:
            print("GPIO cleanup called.")
            # GPIO.cleanup()

