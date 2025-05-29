from greenhouse import Greenhouse

def main():
    broker_address = "192.168.1.7"  # Replace with your MQTT broker's address
    topics = ["/greenhouse/#"]  # MQTT topics to subscribe to

    # Create an instance of the Greenhouse
    greenhouse = Greenhouse(broker_address, topics)
    
    # Start the MQTT client and begin processing messages
    greenhouse.start()

if __name__ == "__main__":
    main()
