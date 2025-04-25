from umqtt.simple import MQTTClient

def connect_mqtt(server, port):
    client = MQTTClient(client_id="pico_client", server=server, port=port)
    client.connect()
    return client