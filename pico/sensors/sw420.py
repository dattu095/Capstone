from machine import Pin


class SW420:
    def __init__(self, out_pin):
        self.sensor = Pin(out_pin, Pin.IN)
    
    def get_value(self):
        return self.sensor.value()