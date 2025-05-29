from mqtt_client import MQTTClient
from node import Node
import json

class Greenhouse:
    def __init__(self, broker_address, topics):
        self.nodes = []
        self.mqtt_client = MQTTClient(self, broker_address, topics)
        print("started greenhouse")

    def process_message(self, topic, payload):

        parts = topic.split('/')
        if len(parts) < 6:  # Ensure the topic has sufficient parts
            return  # Malformed topic, do nothing

        data = json.loads(payload)
        topic_type = parts[-1]  # 'environment', 'light', or 'weather'
        device_id = int(parts[4])  # Extract device_id, assuming it's the 5th element
        # Check if the topic is for environment and manage node existence
        if topic_type == 'environment':
            node = next((n for n in self.nodes if n.id == device_id), None)
            if not node:

                node_name = parts[2]  # Assuming node names are stored in the 3rd segment of the topic
                node = Node(device_id, node_name, self.mqtt_client)
                self.nodes.append(node)
                print(f"Created and added new node: {node}")

            # Update the node with environment data

            temperature = data.get('temperature')
            humidity = data.get('humidity')
            print(f"Device ID: {device_id}, Temperature: {temperature}, Humidity: {humidity}")
            node.update_environment(float(temperature), float(humidity))

        elif topic_type == 'light':
            light =int(data.get('light_intensity'))
            for node in self.nodes:
                node.update_light(light)

        elif topic_type == 'weather':
            is_raining = data.get('is_raining', False)
            is_windy = data.get('is_windy', False)
            for node in self.nodes:
                node.update_weather(is_windy, is_raining)

    def start(self):
        self.mqtt_client.connect()
        self.mqtt_client.loop_forever()
