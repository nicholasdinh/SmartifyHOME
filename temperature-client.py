import sys
import time
import zmq
import random
import threading
import queue
import json
import os
from gpiozero import OutputDevice


import signal

signal.signal(signal.SIGINT, signal.SIG_DFL);

class TemperatureDevice:
    
    def __init__(self):
        # Temperature stuff
        self.profiles = dict()
        self.detected_id = None

        # For future use
        self.room_id = None
        self.primary_profile = None

        self.temp_threshold = None
        self.fan_gpio_pin = 4
        self.fan_light_gpio_pin = 18
        self.fan = OutputDevice(self.fan_gpio_pin)
        self.fan_light = OutputDevice(self.fan_light_gpio_pin)

        # Base device stuff
        self.read_config_file()
        self.data_queue = queue.Queue()
        self.rec_topic_id = "1"
        self.fan_status = False

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
        while True:
            try:
                work = self.receiver.recv()
                self.data_queue.put(work)
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
            self.profiles = data["profiles"]
            self.room_id = data["room_id"]


    def check_queue(self):
        """
            Check if there is any data received by the fog server waiting to be processed.
        """

        #print(f"There are {self.data_queue.qsize()} items in the queue.")
        recorded_temp = self.measure_temp()
        self.print_temp(recorded_temp)
        if self.data_queue.qsize() > 0:
            raw_data = self.data_queue.get().decode("utf-8")[2:]
            data = json.loads(raw_data)

            self.profiles = data["profiles"]
            detected = data["detected"]
            self.detected_id = detected

            for profile in self.profiles:
                if profile['id'] == detected:
                    print(f"{profile['name']} was detected!")
                    self.temp_threshold = float(profile["temperature_preference"])

            print(f"Message on top of queue was {str(data)}")


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

            # This only happens before someone is detected in the room.
            if self.temp_threshold != None:
                recorded_temp = self.measure_temp()
                self.print_temp(recorded_temp)
                if recorded_temp > self.temp_threshold:
                    if self.fan_status == False:
                        print("TURNING ON FAN...")
                    print("FAN ON")
                    self.fan_status = True
                    self.fan.on()
                    self.fan_light.on()
                else:
                    if self.fan_status == True:
                        print("STOPPING FAN...")
                    print("FAN OFF")
                    self.fan_status = False
                    self.fan.off()
                    self.fan_light.off()
                
                temp_message = {
                    "fan_status": self.fan_status,
                    "temperature": recorded_temp,
                    "room_id": self.room_id,
                    "detected_id": self.detected_id
                }
                self.send_message_to_fog(self.producer_topic, json.dumps(temp_message))
            time.sleep(0.5)


    def measure_temp(self):
        temp_str = os.popen("vcgencmd measure_temp").readline()
        temp_str = temp_str.replace("temp=","")
        temp_C = float(temp_str.replace("'C", ""))
        temp_F = (temp_C*(9/5))
        return temp_F

    def print_temp(self, x):
        print("Temperature: " + str(x) + "'F")

    # def receive_updates(self):
    #     # receive data from facerec pi
    #     # data: updated_profiles(dict) , updated_primary(str), updated_detected(set)

    #     profiles = updated_profiles
    #     primary_profile = updated_primary

    #     if detected_people != updated_detected:
    #         detected_people = updated_detected
    #         if !detected_people:
    #             temp_threshold = 100
    #         else:
    #             if len(detected_people) > 1:
    #                 if primary_profile in detected_people:
    #                     temp_threshold = float(profiles[primary_profile])
    #                 else:
    #                     temp_threshold = float(profiles[updated_detected.pop()])
    #             else:
    #                 temp_threshold = float(profiles[updated_detected.pop()])
    
    def send_updates(self):
        # send updated data to fog
        # data: detected_people
        pass

if __name__ == '__main__':
    worker = TemperatureDevice()
    worker.run()
