import sys
import time
import zmq
import random
import threading
import queue
import json
import os
import RPi.GPIO as GPIO
from gpiozero import OutputDevice
from colors import bcolors

from topics import tset

import signal

signal.signal(signal.SIGINT, signal.SIG_DFL)

class TemperatureDevice:
    
    def __init__(self):
        # Temperature stuff
        self.profiles = dict()
        self.detected_profile = None

        # For future use
        self.room_id = None
        self.primary_profile = None

        self.temp_threshold = None
        self.fan_gpio_pin = 4
        self.fan_light_gpio_pin = 18
        
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(25, GPIO.IN)
        
        self.fan = OutputDevice(self.fan_gpio_pin)
        self.fan_light = OutputDevice(self.fan_light_gpio_pin)

        # Base device stuff
        self.read_config_file()
        self.data_queue = queue.Queue()
        self.rec_topic_id = tset["TEMP"]

        self.context = zmq.Context()
        self.receiver = self.context.socket(zmq.SUB)
        self.receiver.connect(self.ip + self.receiver_port)
        self.receiver.setsockopt_string(zmq.SUBSCRIBE, self.rec_topic_id)

        self.producer_topic = tset["SERVER"]
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
            self.rooms = data["rooms"]

    def check_queue(self):
        """
            Check if there is any data received by the fog server waiting to be processed.
        """

        #print(f"There are {self.data_queue.qsize()} items in the queue.")
        recorded_temp = self.measure_temp()
        self.print_temp(recorded_temp)
        if self.data_queue.qsize() > 0:
            raw_data = self.data_queue.get().decode("utf-8")[5:]
            data = json.loads(raw_data)
            # print(data)

            self.profiles = data["profiles"]
            names = data["names"]
            # If no names detected, this frame was used only to update the profiles. Need to update detected_profile
            if names == []:
                if self.detected_profile != None:
                    detected_name = self.detected_profile["name"]
                    self.detected_profile = self.profiles[detected_name]
                    self.temp_threshold = float(self.detected_profile["temperature_preference"])
                return
            primary_name = self.rooms[self.room_id]["primary_user"]
            if primary_name in names:
                primary_profile = self.profiles[primary_name]
                if self.detected_profile["name"] != primary_name:
                    self.detected_profile = self.profiles[primary_name]
                    self.temp_threshold = float(self.detected_profile["temperature_preference"])
                    print(f"\nPrimary user {self.detected_profile['name']} was detected!")
                    print(f"Setting temperature to {self.detected_profile['name']}'s preferred setting: " + str(self.temp_threshold) + "'F")
            else:
                # If detected name is not unknown
                if names[0] in [key.lower() for key in self.profiles]:
                    first_profile_detected = self.profiles[names[0]]
                    if self.detected_profile == None:
                        self.detected_profile = first_profile_detected
                    elif self.detected_profile["name"] != first_profile_detected["name"]:
                        self.detected_profile = first_profile_detected
                    self.temp_threshold = float(self.detected_profile["temperature_preference"])
                    print(f"\n{self.detected_profile['name']} was detected!")
                    print(f"Setting temperature to {self.detected_profile['name']}'s preferred setting: " + str(self.temp_threshold) + "'F")

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
            recorded_temp = self.measure_temp()
            # This only happens before someone is detected in the room.
            if self.temp_threshold != None:
                
                if recorded_temp > self.temp_threshold:
                    #if self.fan_status == False:
                        #print("TURNING ON FAN...")
                    self.fan.on()
                    self.fan_light.on()
                else:
                    #if self.fan_status == True:
                        #print("STOPPING FAN...")
                    self.fan.off()
                    self.fan_light.off()
            
            fan_status = "ON" if not GPIO.input(25) else "OFF"

            temp_message = {
                "fan_status": fan_status,
                "temperature": recorded_temp,
                "room_id": self.room_id,
                "detected_profile": self.detected_profile
            }
            self.send_message_to_fog(self.producer_topic, json.dumps(temp_message))
            time.sleep(1)


    def measure_temp(self):
        temp_str = os.popen("vcgencmd measure_temp").readline()
        temp_str = temp_str.replace("temp=","")
        temp_C = float(temp_str.replace("'C", ""))
        temp_F = (temp_C*(9/5))
        return temp_F

    def print_temp(self, x):
        fan_str = 'Fan: ON' if not GPIO.input(25) else 'Fan: OFF'
        sys.stdout.write(
            '\r >> ' + bcolors.CGREEN + bcolors.BOLD +
            'Temp: {:.3f}'.format(x) + "'F, " + fan_str + bcolors.ENDC + ' <<')
        sys.stdout.flush()

if __name__ == '__main__':
    worker = TemperatureDevice()
    worker.run()
