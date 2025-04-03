import time

import ubinascii


def get_payload(sensor_id, value, wlan):
    timestamp = time.time()
    message_id = ubinascii.hexlify(str(timestamp).encode()).decode()
    wifi_rssi = wlan.status("rssi")
    return f"{timestamp},{sensor_id},{message_id},{value},{wifi_rssi}"


def publish_sensor_data(client, topic, sensor_id, value, wlan):
    payload = get_payload(sensor_id, value, wlan)
    print(payload)
    client.publish(topic, payload)