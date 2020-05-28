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
    * What is the best method to subscribe to multiple topics?
        Should we create multiple class instances?
        Or should one instance establish multiple connections?
"""


class Subscriber:
    def __init__(self, *args):
        print("Initialized!")
        self.read_config_file()
        self.data_queue = queue.Queue()
        self.zContext = zmq.Context()
        self.receiver = self.context.socket(zmq.SUB)
        self.receiver.connect(self.ip + self.receiver_port)
        self.receiver.setsockopt_string(zmq.SUBSCRIBE, self.receive_topic_id)

    def read_config_file(self):
        """
            Load in values from config file for the ip address of the forwarder and the port numbers.
        """
        with open("./config.json") as config_file:
            data = json.load(config_file)
            self.receiver_port = data["subscriber_port"]
            self.producer_port = data["publisher_port"]
            self.ip = "tcp://" + data["forwarder_ip"] + ":"

    def receive(self, handle):
        print("")
        try:
            [topic, msg] = self.receiver.recv_multipart()
            work = handle(msg)
            self.data_queue.put(work)
        except zmq.Again:
            pass
