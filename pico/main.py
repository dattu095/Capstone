import time

from config import MQTT_PORT, MQTT_SERVER, WIFI_PASSWORD, WIFI_SSID
from sensor_controller import publish_sensor_data
from sensors.bmp280 import BMP280
from sensors.dht22 import DHT22
from sensors.mq135 import MQ135
from topic import (TOPIC_BMP280_PRESSURE, TOPIC_BMP280_TEMP,
                   TOPIC_DHT22_HUMIDITY, TOPIC_DHT22_TEMP,
                   TOPIC_MQ135_AIR_QUALITY)
from utils.mqtt import connect_mqtt
from utils.wifi import connect_wifi

temp_sensor = DHT22(9)
smoke_sensor = MQ135(26)
pressure_sensor = BMP280(0, 1)


def main():
    wlan = connect_wifi(WIFI_SSID, WIFI_PASSWORD)
    client = connect_mqtt(MQTT_SERVER, MQTT_PORT)

    while True:
        publish_sensor_data(
            client,
            TOPIC_DHT22_TEMP,
            "DHT22_TEMP",
            temp_sensor.get_value()[0],
            wlan
        )
        publish_sensor_data(
            client,
            TOPIC_DHT22_HUMIDITY,
            "DHT22_HUMIDITY",
            temp_sensor.get_value()[1],
            wlan,
        )
        publish_sensor_data(
            client,
            TOPIC_BMP280_TEMP,
            "BMP280_TEMP",
            pressure_sensor.get_value()[0],
            wlan,
        )
        publish_sensor_data(
            client,
            TOPIC_BMP280_PRESSURE,
            "BMP280_PRESSURE",
            pressure_sensor.get_value()[1],
            wlan,
        )
        publish_sensor_data(
            client,
            TOPIC_MQ135_AIR_QUALITY,
            "MQ135_AIR_QUALITY",
            smoke_sensor.get_value(),
            wlan,
        )
        time.sleep(2)


if __name__ == "__main__":
    main()
