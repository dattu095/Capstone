# Capstop IOT part
This repo is for Capstop IOT project.

## Mosquitto Installation
install [mosquitto](https://mosquitto.org/download/) broker. 

## BMP280 sensor
clone this repo [BMP280](https://github.com/flrrth/pico-bmp280.git) and upload bmp280 to pico w /lib

## micropython packages
* umqtt.simple
* umqtt.robust
* dht

## make config.py in pico directory
```bash
MQTT_SERVER =
MQTT_PORT =

WIFI_SSID =
WIFI_PASSWORD =
```

## To generate packet losses and latency use clumsy
[clumsy](https://github.com/jagt/clumsy/releases/download/0.3/clumsy-0.3-win64-a.zip)
