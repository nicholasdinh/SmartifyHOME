import sys
import time
import zmq
import random
import threading
import pickle
import queue
import json
import os
from topics import topics

import signal

signal.signal(signal.SIGINT, signal.SIG_DFL)

"""
Questions
    * What happens to zmq if the connection gets interrupted or lost?
    * What is the best method to subscribe to multiple topics?
        Should we create multiple class instances?
        Or should one instance establish multiple connections?
"""


class Subscriber:
    def __init__(self, topic):
        print("Initialized!")
        self.read_config_file()
        self.data_queue = queue.Queue()
        self.zContext = zmq.Context()
        self.receiver = self.zContext.socket(zmq.SUB)
        self.receiver.connect(self.ip + self.receiver_port)
        self.receiver.setsockopt_string(zmq.SUBSCRIBE, topic)

    def read_config_file(self):
        """
            Load in values from config file for the ip address of the forwarder and the port numbers.
        """
        with open("./config.json") as config_file:
            data = json.load(config_file)
            self.receiver_port = data["subscriber_port"]
            self.producer_port = data["publisher_port"]
            self.ip = "tcp://" + data["forwarder_ip"] + ":"

    def recv_multipart(self, handle):
        try:
            [topic, msg] = self.receiver.recv_multipart()
            work = handle(msg)
            self.data_queue.put(work)
            print("Message received")
        except zmq.Again:
            pass

    def recv(self):
        try:
            work = self.receiver.recv()
            self.data_queue.put(work)
        except zmq.Again:
            pass
