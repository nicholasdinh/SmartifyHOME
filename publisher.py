import sys
import time
import zmq
import random
import threading
import pickle
import queue
import json
import os

import signal

signal.signal(signal.SIGINT, signal.SIG_DFL)

"""
Questions
    * What happens to zmq if the connection gets interrupted or lost?
"""


class Publisher:
    def __init__(self, *args):
        self.read_config_file()
        self.zContext = zmq.Context()
        self.producer = self.zContext.socket(zmq.PUB)
        self.producer.connect(self.ip + self.producer_port)

    def read_config_file(self):
        """
            Load in values from config file for the ip address of the forwarder and the port numbers.
        """
        with open("./config.json") as config_file:
            data = json.load(config_file)
            self.topics = data["topics"]
            self.producer_port = data["publisher_port"]
            self.ip = "tcp://" + data["forwarder_ip"] + ":"
            self.publish_to_server_topic_id = data["server_receive_topic"]

    def publish(self, topic: str, message: str):
        """
            API to publish message to subscribers.
        """
        self.producer.send_string(topic + " " + message)
