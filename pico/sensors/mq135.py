from machine import ADC


class MQ135:
    def __init__(self, out_pin):
        self.sensor = ADC(out_pin)
    
    def get_value(self):
        return self.sensor.read_u16()