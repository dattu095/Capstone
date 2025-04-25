import time
import gc
import machine
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

# Initialize sensors
temp_sensor = DHT22(9)
smoke_sensor = MQ135(26)
pressure_sensor = BMP280(0, 1)

# Track connection state
connection_stats = {
    "reconnects": 0,
    "message_failures": 0,
    "last_connection_time": 0
}

def main():
    # Connect to WiFi
    wlan = connect_wifi(WIFI_SSID, WIFI_PASSWORD)
    connection_stats["last_connection_time"] = time.time()
    
    # Connect to MQTT broker
    client = connect_mqtt(MQTT_SERVER, MQTT_PORT)
    
    # Setup MQTT callbacks if available
    if hasattr(client, 'on_disconnect'):
        def on_disconnect(client, userdata, rc):
            print(f"Disconnected with code {rc}")
            connection_stats["reconnects"] += 1
        client.on_disconnect = on_disconnect
    QOS = 1
    try:
        while True:
            try:
                # DHT22 Temperature
                publish_sensor_data(
                    client,
                    TOPIC_DHT22_TEMP,
                    "DHT22_TEMP",
                    temp_sensor.get_value()[0],
                    wlan,
                    qos=QOS,
                )
                
                # DHT22 Humidity
                publish_sensor_data(
                    client,
                    TOPIC_DHT22_HUMIDITY,
                    "DHT22_HUMIDITY",
                    temp_sensor.get_value()[1],
                    wlan,
                    qos=QOS,
                )
                
                # BMP280 Temperature
                publish_sensor_data(
                    client,
                    TOPIC_BMP280_TEMP,
                    "BMP280_TEMP",
                    pressure_sensor.get_value()[0],
                    wlan,
                    qos=QOS,
                )
                
                # BMP280 Pressure
                publish_sensor_data(
                    client,
                    TOPIC_BMP280_PRESSURE,
                    "BMP280_PRESSURE",
                    pressure_sensor.get_value()[1],
                    wlan,
                    qos=QOS,
                )
                
                # MQ135 Air Quality
                publish_sensor_data(
                    client,
                    TOPIC_MQ135_AIR_QUALITY,
                    "MQ135_AIR_QUALITY",
                    smoke_sensor.get_value(),
                    wlan,
                    qos=QOS,
                )
                    
            except Exception as e:
                print(f"Error publishing data: {e}")
                connection_stats["message_failures"] += 1
                
                # Try to reconnect if needed
                if hasattr(client, 'is_connected') and not client.is_connected():
                    print("MQTT disconnected, attempting to reconnect...")
                    try:
                        client = connect_mqtt(MQTT_SERVER, MQTT_PORT)
                        connection_stats["last_connection_time"] = time.time()
                    except:
                        print("Reconnection failed")
            
            
    except KeyboardInterrupt:
        print("Program stopped by user")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        # Perform clean disconnect
        if hasattr(client, 'disconnect'):
            client.disconnect()
        print("Program terminated")

if __name__ == "__main__":
    main()