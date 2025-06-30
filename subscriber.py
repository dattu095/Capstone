import csv
import datetime
import json
import os
import platform
import socket
import statistics
import subprocess
import threading
import time

import paho.mqtt.client as mqtt
import psutil

# MQTT Configuration
MQTT_BROKER = "172.31.240.1"
MQTT_PORT = 1883
TOPICS = [
    "sensor/dht22/temp",
    "sensor/dht22/humidity",
    "sensor/bmp280/temp",
    "sensor/bmp280/pressure",
    "sensor/mq135/air_quality",
]

# Global variables
message_history = {topic: [] for topic in TOPICS}
latency_history = {topic: [] for topic in TOPICS}
message_counters = {topic: 0 for topic in TOPICS}
message_per_minute = {topic: 0 for topic in TOPICS}
failed_deliveries = {topic: 0 for topic in TOPICS}
network_stats = {
    "rtt_history": [],
    "packet_loss": 0,
    "interface_errors": 0,
    "retransmissions": 0,
    "throughput": 0,
    "link_speed": 1000,
    "buffer_status": 50,
}

# CSV File Setup
csv_filename = "dataset/new_dataset_2.csv"
csv_headers = [
    "Timestamp",
    "Time_of_Day",
    "Sensor_ID",
    "Message_ID",
    "Published_Payload",
    "Received_Payload",
    "Message_Size_Bytes",
    "Latency_ms",
    "Jitter_ms",
    "Packet_Loss_Percent",
    "RTT_ms",
    "Throughput_BytesPerSec",
    "TCP_Retransmissions",
    "Interface_Errors",
    "Link_Speed_Mbps",
    "MQTT_Connection_State",
    "MQTT_Message_Queue_Size",
    "QoS_Level",
    "QoS_Success_Rate",
    "Messages_Per_Minute",
    "Failed_Delivery_Count",
    "CPU_Utilization_Percent",
    "Memory_Usage_Percent",
    "System_Load",
    "Network_Buffer_Status",
    "Network_Condition",
    "Moving_Avg_Latency_ms",
    "Rate_of_Change_Latency",
    "Sender_CPU_Freq",
    "Sender_Memory_Percent",
    "Sender_Reset_Cause",
    "Communication_Issue_Type",
    "Topic",
]


# Create CSV file with headers
def initialize_csv():
    with open(csv_filename, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(csv_headers)
    print(f"Created dataset file: {csv_filename}")


# Functions to collect system metrics
def get_network_interface():
    """Determine the main network interface"""
    if platform.system() == "Windows":
        return "Ethernet"  # Default for Windows

    try:
        # Try to get the interface used to reach the MQTT broker
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((MQTT_BROKER, MQTT_PORT))
        ip = s.getsockname()[0]
        s.close()

        # On Linux, check /proc/net/route for default interface
        if os.path.exists("/proc/net/route"):
            with open("/proc/net/route", "r") as f:
                for line in f.readlines()[1:]:  # Skip header
                    fields = line.strip().split()
                    if fields[1] == "00000000":  # Default route
                        return fields[0]

        return "eth0"  # Default fallback
    except:
        return "eth0"  # Default fallback


NETWORK_INTERFACE = get_network_interface()
print(f"Using network interface: {NETWORK_INTERFACE}")


def get_cpu_usage():
    return psutil.cpu_percent(interval=0.1)


def get_memory_usage():
    return psutil.virtual_memory().percent


def get_system_load():
    try:
        if platform.system() == "Windows":
            return psutil.cpu_percent()
        else:
            return os.getloadavg()[0]  # 1-minute load average
    except:
        return psutil.cpu_percent()


def get_interface_stats():
    """Get network interface statistics"""
    try:
        if platform.system() == "Windows":
            # On Windows, gather what we can from psutil
            net_io = psutil.net_io_counters(pernic=True).get(NETWORK_INTERFACE)
            if net_io:
                errors = net_io.errin + net_io.errout
                return errors, 1000  # Assume 1Gbps as default
        else:
            # For Linux, try ethtool and netstat
            try:
                # Get link speed with ethtool
                cmd = subprocess.run(
                    ["ethtool", NETWORK_INTERFACE], capture_output=True, text=True
                )
                output = cmd.stdout
                speed = 1000  # Default 1Gbps

                for line in output.split("\n"):
                    if "Speed" in line:
                        speed_str = line.split(":")[1].strip()
                        if "Mb/s" in speed_str:
                            try:
                                speed = int(speed_str.replace("Mb/s", ""))
                            except:
                                pass

                # Get errors with ifconfig/ip
                if os.path.exists("/sbin/ifconfig"):
                    cmd = subprocess.run(
                        ["ifconfig", NETWORK_INTERFACE], capture_output=True, text=True
                    )
                    output = cmd.stdout
                    errors = 0

                    for line in output.split("\n"):
                        if "errors" in line.lower():
                            parts = line.split()
                            for i, part in enumerate(parts):
                                if part.lower() == "errors:" and i + 1 < len(parts):
                                    try:
                                        errors = int(parts[i + 1])
                                    except:
                                        pass

                    return errors, speed
            except:
                # Fall back to psutil
                net_io = psutil.net_io_counters(
                    pernic=True).get(NETWORK_INTERFACE)
                if net_io:
                    errors = net_io.errin + net_io.errout
                    return errors, 1000

        return 0, 1000  # Default values
    except Exception as e:
        print(f"Error getting interface stats: {e}")
        return 0, 1000


def get_tcp_retransmissions():
    """Get TCP retransmission count"""
    try:
        if platform.system() == "Linux":
            cmd = subprocess.run(
                ["netstat", "-s"], capture_output=True, text=True)
            output = cmd.stdout

            for line in output.split("\n"):
                if "retransmitted" in line.lower() and "segments" in line.lower():
                    parts = line.strip().split()
                    try:
                        return int(parts[0])
                    except:
                        pass

        # Default or fallback value
        return 0
    except:
        return 0


def measure_rtt():
    """Measure round trip time to the MQTT broker"""
    try:
        ping_count = "1"
        ping_cmd = []

        if platform.system() == "Windows":
            ping_cmd = ["ping", "-n", ping_count, MQTT_BROKER]
        else:
            ping_cmd = ["ping", "-c", ping_count, MQTT_BROKER]

        start_time = time.time()
        result = subprocess.run(ping_cmd, capture_output=True, text=True)
        end_time = time.time()

        # Calculate RTT from ping output
        output = result.stdout
        rtt = 0

        if "time=" in output:
            for line in output.split("\n"):
                if "time=" in line:
                    try:
                        time_part = line.split("time=")[1].split()[0]
                        rtt = float(time_part.replace("ms", ""))
                        break
                    except:
                        pass

        # If we couldn't parse the output, use our own timing as fallback
        if rtt == 0:
            rtt = (end_time - start_time) * 1000

        return rtt
    except Exception as e:
        print(f"Error measuring RTT: {e}")
        return 0


def calculate_throughput(prev_bytes, curr_bytes, time_diff):
    """Calculate network throughput"""
    if time_diff <= 0:
        return 0
    bytes_diff = curr_bytes - prev_bytes
    return bytes_diff / time_diff


def calculate_jitter(latencies):
    """Calculate jitter from latency measurements"""
    if len(latencies) < 2:
        return 0

    differences = [
        abs(latencies[i] - latencies[i - 1]) for i in range(1, len(latencies))
    ]
    if not differences:
        return 0

    return statistics.mean(differences)


def calculate_moving_average(values, window=5):
    """Calculate moving average of the last N values"""
    if not values:
        return 0
    recent = values[-window:] if len(values) >= window else values
    return sum(recent) / len(recent)


def calculate_rate_of_change(values, window=5):
    """Calculate rate of change over the last N values"""
    if len(values) < 2:
        return 0

    recent = values[-window:] if len(values) >= window else values
    if len(recent) < 2:
        return 0

    return (recent[-1] - recent[0]) / len(recent)


def get_network_buffer_status():
    """Estimate network buffer status"""
    try:
        # This is an approximation based on system metrics
        cpu_usage = get_cpu_usage()
        mem_usage = get_memory_usage()

        # Weighted combination of CPU and memory as proxy for buffer stress
        buffer_status = (cpu_usage * 0.7) + (mem_usage * 0.3)
        return min(100, buffer_status)
    except:
        return 50  # Default middle value


def determine_issue_type(metrics):
    """Determine communication issue type from metrics"""
    # 0: Normal, 1: Latency, 2: Packet Loss, 3: Throughput, 4: Connection, 5: Resource

    # Default is normal
    issue_type = 0

    # Check for issues in priority order
    if metrics["mqtt_connection_state"] != "Connected":
        issue_type = 4  # Connection issue
    elif metrics["packet_loss"] > 5:
        issue_type = 2  # Packet loss issue
    elif metrics["latency"] > 500:
        issue_type = 1  # Latency issue
    elif metrics["throughput"] < 1000:
        issue_type = 3  # Throughput issue
    elif metrics["cpu_usage"] > 90 or metrics["memory_usage"] > 90:
        issue_type = 5  # Resource constraint

    return issue_type


def parse_enhanced_payload(payload):
    """Parse the enhanced payload from the publisher"""
    try:
        # Expected format based on your updated publish_sensor_data function
        parts = payload.split(",")

        if len(parts) >= 10:  # Basic check for minimum expected fields
            return {
                "timestamp": float(parts[0]),
                "sensor_id": parts[1],
                "message_id": parts[2],
                "value": float(parts[3]),
                "wifi_rssi": int(parts[4]),
                "link_quality": int(parts[5]),
                "memory_percent": int(parts[6]),
                "cpu_freq": int(parts[7]),
                "reset_cause": int(parts[8]),
                "qos": int(parts[9]),
                "network_condition": parts[10] if len(parts) > 10 else "unknown",
            }
        else:
            # Fallback for old format
            return {
                "timestamp": float(parts[0]),
                "sensor_id": parts[1],
                "message_id": parts[2],
                "value": float(parts[3]),
                "wifi_rssi": int(parts[4]) if len(parts) > 4 else 0,
                "link_quality": 0,
                "memory_percent": 0,
                "cpu_freq": 0,
                "reset_cause": 0,
                "network_condition": "unknown",
            }
    except Exception as e:
        print(f"Error parsing payload: {e}")
        # Return default values if parsing fails
        return {
            "timestamp": time.time(),
            "sensor_id": "unknown",
            "message_id": "unknown",
            "value": 0,
            "wifi_rssi": 0,
            "link_quality": 0,
            "memory_percent": 0,
            "cpu_freq": 0,
            "reset_cause": 0,
            "network_condition": "unknown",
        }


# Background monitoring thread
def network_monitoring_thread():
    """Background thread for continuous network monitoring"""
    global network_stats

    last_bytes_total = 0
    last_check_time = time.time()

    while True:
        try:
            # Measure RTT
            rtt = measure_rtt()
            network_stats["rtt_history"].append(rtt)
            if len(network_stats["rtt_history"]) > 10:
                network_stats["rtt_history"].pop(0)

            # Get interface statistics
            errors, link_speed = get_interface_stats()
            network_stats["interface_errors"] = errors
            network_stats["link_speed"] = link_speed

            # Get TCP retransmissions
            retrans = get_tcp_retransmissions()
            network_stats["retransmissions"] = retrans

            # Calculate throughput
            current_time = time.time()
            time_diff = current_time - last_check_time

            if time_diff >= 1.0:  # At least 1 second between measurements
                net_io = psutil.net_io_counters()
                current_bytes = net_io.bytes_sent + net_io.bytes_recv

                if last_bytes_total > 0:
                    throughput = calculate_throughput(
                        last_bytes_total, current_bytes, time_diff
                    )
                    network_stats["throughput"] = throughput

                last_bytes_total = current_bytes
                last_check_time = current_time

            # Get buffer status
            network_stats["buffer_status"] = get_network_buffer_status()

            # Sleep before next check
            time.sleep(5)

        except Exception as e:
            print(f"Error in monitoring thread: {e}")
            time.sleep(5)


# MQTT callbacks
def on_connect(client, userdata, flags, rc):
    """Called when connected to MQTT broker"""
    connection_state = "Connected" if rc == 0 else f"Failed (code: {rc})"
    print(f"MQTT connection: {connection_state}")

    # Subscribe to all topics
    for topic in TOPICS:
        client.subscribe(topic)
        print(f"Subscribed to {topic}")


def on_disconnect(client, userdata, rc):
    """Called when disconnected from MQTT broker"""
    print(f"MQTT disconnected with code: {rc}")


def on_message(client, userdata, msg):
    """Called when a message is received"""
    try:
        # Record reception time
        receive_time = time.time()

        # Decode and parse payload
        payload = msg.payload.decode()
        message_data = parse_enhanced_payload(payload)

        # Update message counter for this topic
        message_counters[msg.topic] = message_counters.get(msg.topic, 0) + 1

        # Calculate latency
        latency = (receive_time - message_data["timestamp"]) * 1000  # ms

        # Add to latency history for this topic
        if msg.topic in latency_history:
            latency_history[msg.topic].append(latency)
            if len(latency_history[msg.topic]) > 20:
                latency_history[msg.topic].pop(0)

        # Calculate jitter
        jitter = calculate_jitter(latency_history[msg.topic])

        # Get system metrics
        cpu_usage = get_cpu_usage()
        memory_usage = get_memory_usage()
        system_load = get_system_load()

        # Get network metrics
        rtt = calculate_moving_average(network_stats["rtt_history"])

        # Gather derived metrics
        moving_avg_latency = calculate_moving_average(
            latency_history[msg.topic])
        rate_of_change = calculate_rate_of_change(latency_history[msg.topic])

        # Messages per minute
        current_minute = int(time.time() / 60)
        message_per_minute[msg.topic] = message_counters[msg.topic]

        # Process QoS information
        qos_level = msg.qos

        # Calculate packet loss (placeholder - would need sequence numbers to be accurate)
        packet_loss = 0  # Placeholder

        # Calculate QoS success rate (placeholder)
        qos_success_rate = 100 - packet_loss

        # Metrics for issue determination
        metrics = {
            "latency": latency,
            "packet_loss": packet_loss,
            "throughput": network_stats["throughput"],
            "mqtt_connection_state": "Connected",
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
        }

        # Determine communication issue type
        issue_type = determine_issue_type(metrics)

        # Prepare log data
        log_data = [
            receive_time,
            datetime.datetime.fromtimestamp(receive_time).strftime("%H:%M:%S"),
            message_data["sensor_id"],
            message_data["message_id"],
            message_data["value"],
            payload,
            len(msg.payload),
            latency,
            jitter,
            packet_loss,
            rtt,
            network_stats["throughput"],
            network_stats["retransmissions"],
            network_stats["interface_errors"],
            network_stats["link_speed"],
            "Connected",  # MQTT connection state
            0,  # Message queue size (placeholder)
            qos_level,
            qos_success_rate,
            message_per_minute[msg.topic],
            failed_deliveries.get(msg.topic, 0),
            cpu_usage,
            memory_usage,
            system_load,
            network_stats["buffer_status"],
            message_data["network_condition"],
            moving_avg_latency,
            rate_of_change,
            message_data["cpu_freq"],
            message_data["memory_percent"],
            message_data["reset_cause"],
            issue_type,
            msg.topic,
        ]

        # Save to CSV
        with open(csv_filename, "a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(log_data)

        # Print short status
        print(
            f"[{datetime.datetime.now().strftime('%H:%M:%S')}] "
            f"Message from {message_data['sensor_id']}: "
            f"value={message_data['value']:.2f}, "
            f"latency={latency:.2f}ms, "
            f"condition={message_data['network_condition']}"
        )

    except Exception as e:
        print(f"Error processing message: {e}")


def simulate_network_conditions():
    """Simulate different network conditions for testing"""
    conditions = [
        {"name": "baseline", "cmd": "sudo tc qdisc del dev IFACE root"},
        {
            "name": "high_latency",
            "cmd": "sudo tc qdisc add dev IFACE root netem delay 100ms 20ms",
        },
        {
            "name": "packet_loss",
            "cmd": "sudo tc qdisc add dev IFACE root netem loss 5%",
        },
        {
            "name": "combined",
            "cmd": "sudo tc qdisc add dev IFACE root netem delay 50ms 10ms loss 2%",
        },
    ]

    current_condition = 0

    print("\nNetwork Condition Simulator")
    print("==========================")
    print("This will modify your network settings to simulate different conditions.")
    print("You need sudo privileges to run these commands.")
    print("Press Ctrl+C to exit the simulator at any time.")
    print()

    try:
        while True:
            condition = conditions[current_condition]
            print(f"\nApplying condition: {condition['name']}")

            # Replace IFACE with actual interface
            cmd = condition["cmd"].replace("IFACE", NETWORK_INTERFACE)

            # Ask for confirmation before applying
            response = input(f"Run command: '{cmd}'? (y/n): ")

            if response.lower() == "y":
                try:
                    result = os.system(cmd)
                    if result == 0:
                        print(f"Applied condition: {condition['name']}")
                    else:
                        print(
                            f"Failed to apply condition (exit code {result})")
                except Exception as e:
                    print(f"Error applying network condition: {e}")

            # Move to next condition
            current_condition = (current_condition + 1) % len(conditions)

            # Wait before next change
            user_wait = input(
                "Press Enter to continue to next condition, or Ctrl+C to exit"
            )

    except KeyboardInterrupt:
        print("\nExiting network condition simulator")
        # Try to restore normal conditions
        try:
            reset_cmd = f"sudo tc qdisc del dev {NETWORK_INTERFACE} root"
            os.system(reset_cmd)
            print("Network conditions reset to normal")
        except:
            pass


def main():
    # Initialize CSV file
    initialize_csv()

    # Create MQTT client
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    # Start network monitoring in background thread
    monitor_thread = threading.Thread(target=network_monitoring_thread)
    monitor_thread.daemon = True
    monitor_thread.start()

    # Create condition simulation menu thread
    sim_thread = threading.Thread(target=simulate_network_conditions)
    sim_thread.daemon = True

    try:
        # Connect to MQTT broker
        print(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}...")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)

        # Start MQTT loop in a background thread
        client.loop_start()

        print("MQTT Subscriber started. Press Ctrl+C to exit.")
        print("Recording data to:", csv_filename)

        # Menu for controlling the application
        while True:
            print("\nOptions:")
            print("1. Show current network statistics")
            print("2. Start network condition simulator")
            print("3. Reset network conditions")
            print("4. Exit")

            choice = input("Select an option: ")

            if choice == "1":
                # Show current network stats
                print("\nCurrent Network Statistics:")
                print(
                    f"RTT: {calculate_moving_average(
                        network_stats['rtt_history']):.2f} ms"
                )
                print(f"Throughput: {
                      network_stats['throughput']:.2f} bytes/sec")
                print(f"Retransmissions: {network_stats['retransmissions']}")
                print(f"Interface Errors: {network_stats['interface_errors']}")
                print(f"Link Speed: {network_stats['link_speed']} Mbps")
                print(f"CPU Usage: {get_cpu_usage():.1f}%")
                print(f"Memory Usage: {get_memory_usage():.1f}%")

            elif choice == "2":
                # Start network condition simulator
                if not sim_thread.is_alive():
                    sim_thread = threading.Thread(
                        target=simulate_network_conditions)
                    sim_thread.daemon = True
                    sim_thread.start()
                else:
                    print("Simulator is already running")

            elif choice == "3":
                # Reset network conditions
                try:
                    if platform.system() == "Linux":
                        reset_cmd = f"sudo tc qdisc del dev {
                            NETWORK_INTERFACE} root"
                        os.system(reset_cmd)
                        print("Network conditions reset to normal")
                    else:
                        print("This feature is only available on Linux")
                except Exception as e:
                    print(f"Error resetting network conditions: {e}")

            elif choice == "4":
                # Exit the program
                break

            else:
                print("Invalid choice. Please select a valid option.")

    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error in main loop: {e}")
    finally:
        # Clean up and exit
        try:
            client.loop_stop()
            client.disconnect()
        except:
            pass
        print("Subscriber stopped.")


if __name__ == "__main__":
    main()
