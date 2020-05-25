import sys
import time
import zmq
import random
import threading
import queue
import json

import signal

signal.signal(signal.SIGINT, signal.SIG_DFL);

class Worker:
    def __init__(self):
        self.read_config_file()
        self.consumer_id = random.randrange(1,10005)
        self.data_queue = queue.Queue()
        self.rec_topic_id = "1"

        self.context = zmq.Context()
        self.receiver = self.context.socket(zmq.SUB)
        self.receiver.connect(self.ip + self.receiver_port)
        self.receiver.setsockopt_string(zmq.SUBSCRIBE, self.rec_topic_id)

        self.producer_topic = "2"
        self.producer = self.context.socket(zmq.PUB)
        self.producer.connect(self.ip + self.producer_port)

        self.receiver_thread = threading.Thread(target=self.consumer)
        
        self.data_queue = queue.Queue()

    def consumer(self):
        """
            This is the thread that checks the receiver_socket if there are any new messages from the fog_server waiting to be processed.
        """

        data_count = 1
        while True:
            try:
                work = self.receiver.recv()
                
                # This snippet is only used for debug purposes when testing sending data back to server
                if data_count % 2 == 0:
                    message = "message to server from device " + str(data_count)
                    self.send_message_to_fog(self.producer_topic, message)

                self.data_queue.put(work)
                data_count += 1
            except zmq.Again:
                continue

    def send_message_to_fog(self, topic: str, message: str):
        """
            API to send message from device to fog server.
        """
        self.producer.send_string(topic + " " + message)

    def read_config_file(self):
        """
            Load in values from config file for the ip address of the forwarder and the port numbers.
        """

        with open("./config.json") as config_file:
            data = json.load(config_file)
            self.receiver_port = data["subscriber_port"]
            self.producer_port = data["publisher_port"]
            self.ip = "tcp://" + data["forwarder_ip"] + ":"

    def check_queue(self):
        """
            Check if there is any data received by the fog server waiting to be processed.
        """

        print(f"There are {self.data_queue.qsize()} items in the queue.")
        if self.data_queue.qsize() > 0:
            data = self.data_queue.get()
            print(f"Message on top of queue was {data}")
        

    def main_loop(self):
        """
            Device specific work will be performed in this loop.
            First checks the queue to see if any messages need to be processed.
        """
        while True:
            self.check_queue()
            time.sleep(3.0)




    def run(self):
        self.receiver_thread.start()
        try:
            self.main_loop()
        except KeyboardInterrupt:
            pass

if __name__ == '__main__':
    worker = Worker()
    worker.run()
