from machine import Pin, I2C
from bmp280 import BMP280I2C


class BMP280(BMP280I2C):
    def __init__(self, sda_pin, scl_pin):
        super().__init__(0x76, I2C(0, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=400000))
    
    def get_value(self):
        readout = self.measurements
        return readout["t"], readout["p"]


i2c0_sda = Pin(0)
i2c0_scl = Pin(1)
i2c0 = I2C(0, sda=i2c0_sda, scl=i2c0_scl, freq=400000)