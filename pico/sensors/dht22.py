import dht
from machine import Pin


class DHT22(dht.DHT22):
    def __init__(self, out_pin):
        super().__init__(Pin(out_pin))
        
    def get_value(self):
        self.measure()
        return self.temperature(), self.humidity()