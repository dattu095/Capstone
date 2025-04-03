import time

import network


def connect_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)

    timeout = 10  # Timeout for connection
    while not wlan.isconnected() and timeout > 0:
        print("Waiting for connection...")
        time.sleep(1)
        timeout -= 1

    if wlan.isconnected():
        print("Connected:", wlan.ifconfig())
        return wlan
    else:
        print("Failed to connect to Wi-Fi")
        return None
