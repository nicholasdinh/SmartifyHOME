import sys
import time
import zmq
import random
import threading
import pickle
import queue
import json
import os

from server_encode_faces import encode_faces

import signal

signal.signal(signal.SIGINT, signal.SIG_DFL)

class RecognitionDevice:

    def __init__(self):
        # For future use
        self.room_id = None
        
        # Base device stuff
        self.read_config_file()
        self.data_queue = queue.Queue()
        self.context = zmq.Context()
        self.receiver = self.context.socket(zmq.SUB)
        self.receiver.connect(self.ip + self.receiver_port)
        self.receiver.setsockopt_string(zmq.SUBSCRIBE, self.receive_topic_id)

        self.producer = self.context.socket(zmq.PUB)
        self.producer.connect(self.ip + self.producer_port)
        self.receiver_thread = threading.Thread(target=self.consumer)

    def read_config_file(self):
        """
            Load in values from config file for the ip address of the forwarder and the port numbers.
        """

        with open("./config.json") as config_file:
            data = json.load(config_file)
            self.receiver_port = data["subscriber_port"]
            self.producer_port = data["publisher_port"]
            self.ip = "tcp://" + data["forwarder_ip"] + ":"
            self.receive_topic_id = data["face_recognition_pi_topic"]
            self.publish_to_server_topic_id = data["server_receive_topic"]


    def consumer(self):
        while True:
            try:
                [topic,msg] = self.receiver.recv_multipart()
                work = pickle.loads(msg)
                self.data_queue.put(work)
            except zmq.Again:
                continue


    def send_message_to_fog(self, topic: str, message: str):
        """
            API to send message from device to fog server.
        """
        self.producer.send_string(topic + " " + message)


    def check_queue(self):
        """
            Check if there is any data received by the fog server waiting to be processed.
        """

        print(f"There are {self.data_queue.qsize()} items in the queue.")
        if self.data_queue.qsize() > 0:
            # Do something with data we received
            encodings = self.data_queue.get()
            self.profiles = encodings["profiles"]
            print(f"Message on top of queue was {str(encodings)}")
    
    def run(self):
        self.receiver_thread.start()
        try:
            self.main_loop()
        except KeyboardInterrupt:
            pass

    def main_loop(self):
        """
            Device specific work will be performed in this loop.
            First checks the queue to see if any messages need to be processed.
        """
        while True:
            # check for updates from fog
            self.check_queue()
            # send updates to fog
            # random_id = str(random.randint(5,9))
            names = ["Damian", "Nick"]
            message = {
                "names": names
            }
            self.send_message_to_fog(self.publish_to_server_topic_id, json.dumps(message))
            time.sleep(0.5)
    
if __name__ == '__main__':
    worker = RecognitionDevice()
    worker.run()
