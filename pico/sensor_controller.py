import time
import ubinascii
import machine
import gc
import network

def get_payload(sensor_id, value, wlan):
    timestamp = time.time()
    message_id = ubinascii.hexlify(str(timestamp).encode()).decode()
    
    # Network information
    if wlan and wlan.isconnected():
        wifi_rssi = wlan.status("rssi")
        link_quality = max(0, min(100, (wifi_rssi + 100) * 2))  # Convert RSSI to approximate quality
    else:
        wifi_rssi = 0
        link_quality = 0
    
    # System information
    try:
        free_mem = gc.mem_free()
        total_mem = gc.mem_alloc() + free_mem
        mem_percent = 100 - (free_mem * 100 // total_mem) if total_mem > 0 else 0
        
        # Get CPU frequency as a proxy for CPU load
        cpu_freq = machine.freq() // 1000000  # MHz
    except:
        mem_percent = 0
        cpu_freq = 0
    
    # Create a more comprehensive payload
    payload = (
        f"{timestamp},"          # Timestamp
        f"{sensor_id},"          # Sensor ID
        f"{message_id},"         # Message ID
        f"{value},"              # Sensor value
        f"{wifi_rssi},"          # WiFi RSSI
        f"{link_quality},"       # Link quality estimate
        f"{mem_percent},"        # Memory usage percent
        f"{cpu_freq},"           # CPU frequency (MHz)
        f"{machine.reset_cause()}"  # Last reset cause
    )
    
    return payload

def publish_sensor_data(client, topic, sensor_id, value, wlan, qos=0, retain=False):
    try:
        payload = get_payload(sensor_id, value, wlan)
        print(f"Publishing to {topic}: {payload}")
        
        # Record attempt time for tracking delivery success
        start_time = time.time()
        
        # Publish with QoS level
        result = client.publish(topic, payload, qos=qos, retain=retain)
        
        # Calculate publishing time (local processing only)
        pub_time = time.time() - start_time
        print(f"Local processing time: {pub_time*1000:.2f}ms")
        
        return True
    except Exception as e:
        print(f"Publish error: {e}")
        return False