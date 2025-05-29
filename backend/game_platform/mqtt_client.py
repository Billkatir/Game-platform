import paho.mqtt.client as mqtt

class MQTTClient:
    def __init__(self, greenhouse, broker_address, topics):
        self.greenhouse = greenhouse
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.broker_address = broker_address
        self.topics = topics if isinstance(topics, list) else [topics]

    def on_connect(self, client, userdata, flags, reason_code, properties=None):
        for topic in self.topics:
            client.subscribe(topic)
    
    
    def on_message(self, client, userdata, message):
        try:
            payload = message.payload.decode()
            self.greenhouse.process_message(message.topic, payload)
        except Exception as e:
            print(f"Error handling message: {e}")

    def connect(self):
        self.client.connect(self.broker_address)

    def loop_forever(self):
        self.client.loop_forever()

    # New function to publish the number 3 to "control_topic"
    def publish_control(self, topic, payload):
        print(f"Publishing to topic '{topic}' with payload: {payload}")  # Print payload
        result = self.client.publish(topic, str(payload), qos=0)  # Set QoS to 0 (not 2 as per comment)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"Published successfully")
        else:
            print(f"Failed to publish message to topic '{topic}'")


