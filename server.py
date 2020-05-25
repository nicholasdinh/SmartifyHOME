import time
import zmq
import sys
import random
import queue
import threading
import json

import signal

signal.signal(signal.SIGINT, signal.SIG_DFL);

class FogServer:
    def __init__(self):
        self.read_config_file()
        self.context = zmq.Context()

        # The socket that data is published to the forwarder through.
        self.publish_socket = self.context.socket(zmq.PUB)
        self.publish_socket.connect(self.ip + self.publish_port)


        self.rec_topic_id = "2"

        # The socket that receives data from the forwarder.
        self.receiver_socket = self.context.socket(zmq.SUB)
        self.receiver_socket.connect(self.ip + self.receiver_port)
        self.receiver_socket.setsockopt_string(zmq.SUBSCRIBE, self.rec_topic_id)

        # The queue where all messages from devices waiting to be processed wait.
        self.queue = queue.Queue()

        # The thread that checks receiver_socket for any new messages
        self.receive_thread = threading.Thread(target=self.receiver)


    def read_config_file(self):
        """
            Load in values from config file for the ip address of the forwarder and the port numbers.
        """

        with open("./config.json") as config_file:
            data = json.load(config_file)
            self.receiver_port = data["subscriber_port"]
            self.publish_port = data["publisher_port"]
            self.ip = "tcp://" + data["forwarder_ip"] + ":"

    def producer(self):
        """
            Main function of this class, this is where data is published to the devices.
            For example:
                User preferences are sent to the device maintaining temperature.
        """
        self.receive_thread.start()
        publisher_id = random.randrange(0,9999)
        time.sleep(1)
        device_id = "1"

        """
            This is where we will need to send device specific data.
        """

        for num in range(20):
            self.publish_socket.send_string(device_id + " has a message of " + str(num))
            self.check_for_received()

    def receiver(self):
        """
            Thread were data is received from the devices.
        """
        while True:
            try:
                data = self.receiver_socket.recv()
                self.queue.put(data)
            except zmq.Again:
                continue

    def check_queue(self):
        """
            Check if there is any data received by the devices waiting to be processed.
        """
        if self.queue.qsize() > 0:
            data = self.queue.get()
            print(f"Message on top of queue was {data}")
        else:
            print("Server's receive queue was empty.")

    def debug_producer(self):
        """
            Debug producer, allows us to send debug messages to a device.
            Invoked by adding the '-d' flag when executing this script.
        """
        self.receive_thread.start()
        while True:
            self.check_for_received()
            device_id = input("Enter device id\n")
            command = input("Enter debug message \n")
            if command.lower() == 'q':
                break
            message_dict = {'message': command}
            serialized_message = device_id + " " + json.dumps(message_dict)
            self.publish_socket.send_string(serialized_message)


            print("published " + serialized_message)

            
    def check_for_received(self):
            print("Checking for any received messages...")
            self.check_queue()



if __name__ == '__main__':
    server = FogServer()
    if len(sys.argv) > 1 and sys.argv[1].lower() == '-d':
        server.debug_producer()
    else:
        server.producer()
