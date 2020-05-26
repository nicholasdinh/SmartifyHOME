import json
import pickle
import queue
import random
import sys
import threading
import time
from tkinter import ttk
import tkinter.font as tkFont
import tkinter.messagebox as tkMBox
import tkinter as tk
import zmq

import signal

signal.signal(signal.SIGINT, signal.SIG_DFL);

class FogServer(tk.Frame):
    def __init__(self, master=None):

        super().__init__(master)
        self.master = master
        self.grid(row=0, column=0, sticky="nsew")
        self.create_top_frame()
        self.create_tree_view()

        self.master.grid_rowconfigure(0, weight=1)
        self.master.grid_rowconfigure(1, weight=1)
        self.master.grid_columnconfigure(0,weight=1)

        self.read_config_file()
        self.context = zmq.Context()

        # The socket that data is published to the forwarder through.
        self.publish_socket = self.context.socket(zmq.PUB)
        self.publish_socket.connect(self.ip + self.publish_port)

        # The socket that receives data from the forwarder.
        self.receiver_socket = self.context.socket(zmq.SUB)
        self.receiver_socket.connect(self.ip + self.receiver_port)
        self.receiver_socket.setsockopt_string(zmq.SUBSCRIBE, self.rec_topic_id)

        # The queue where all messages from devices waiting to be processed wait.
        self.queue = queue.Queue()

        # The thread that checks receiver_socket for any new messages
        self.receive_thread = threading.Thread(target=self.receiver)


    def create_top_frame(self):
        self.topFrame = tk.Frame(master=self.master)
        self.topFrame.grid(row=0, sticky="nsew", padx=5, pady=5)

        self.profileLabel = tk.Label(master=self.topFrame, text="Profiles")
        self.profileLabel.grid(row=0, column=0, sticky="nsew")


        self.entryFrame = tk.LabelFrame(master=self.topFrame, text="Update User")
        self.entryFrame.grid(row=0, column=2, sticky="nsew")

        self.nameEntry = tk.Entry(self.entryFrame)
        self.tempEntry = tk.Entry(self.entryFrame)
        tk.Label(self.entryFrame, text="Profile Name").grid(row=0, padx=5, pady=5)
        tk.Label(self.entryFrame, text="Temp Preference").grid(row=1, padx=5, pady=5)
        self.nameEntry.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.tempEntry.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)


        self.addUserButton = tk.Button(master=self.entryFrame, text="Update User", command=self.addUserOnClick)
        self.addUserButton.grid(row=2, column=0, sticky="nsew", columnspan=2, padx=5, pady=5)

        self.entryFrame.grid_rowconfigure(0,weight=1)
        self.entryFrame.grid_rowconfigure(1,weight=1)
        self.entryFrame.grid_rowconfigure(2,weight=1)
        self.entryFrame.grid_columnconfigure(0,weight=1)
        self.entryFrame.grid_columnconfigure(1,weight=1)

        self.topFrame.grid_rowconfigure(0,weight=1)
        self.topFrame.grid_columnconfigure(0,weight=1)
        self.topFrame.grid_columnconfigure(1,weight=1)
        self.topFrame.grid_columnconfigure(2,weight=1)

    def create_tree_view(self):
        self.treev = ttk.Treeview(self.master, columns = ("id", "Name", "Preference"), show="headings")
        self.treev.heading("id", text="User ID")
        self.treev.heading("Name", text="Name")
        self.treev.heading("Preference", text="Preference")
        self.treev.grid(row=1, column=0, sticky="nsew")

    def addUserOnClick(self):
        username = self.nameEntry.get()
        temp = self.tempEntry.get()
        print(username + " " + temp)

        self.tempEntry.delete(0,'end')
        self.nameEntry.delete(0,'end')

        new_profile = dict()
        new_profile['name'] = username
        new_profile['temperature_preference'] = temp
        new_profile['id'] = str(self.available_id)
        self.available_id +=1
        self.profiles.append(new_profile)
        self.treev.insert('', 'end', text=username, values=(new_profile['id'],username,temp))
        self.dump_to_config_file()




    def update_tree_on_load(self):
        for profile in self.profiles:

            self.treev.insert('','end', text=profile['name'], values=(profile['id'], profile['name'], profile['temperature_preference']))

    def read_config_file(self):
        """
            Load in values from config file for the ip address of the forwarder and the port numbers.
        """

        with open("./config.json") as config_file:
            data = json.load(config_file)
            self.receiver_port = data["subscriber_port"]
            self.publish_port = data["publisher_port"]
            self.ip = "tcp://" + data["forwarder_ip"] + ":"
            self.available_id = data["available_id"]
            self.profiles = data["profiles"]
            self.rec_topic_id = data["server_receive_topic"]
            self.publish_temp_pi_topic_id = data["temperature_pi_topic"]
            self.publish_recognition_pi_topic_id = data["face_recognition_pi_topic"]
        self.update_tree_on_load()

    def dump_to_config_file(self):
        data_to_dump = {
            "subscriber_port": self.receiver_port,
            "publisher_port": self.publish_port,
            "forwarder_ip": self.ip[6:-1],
            "available_id": self.available_id,
            "profiles": self.profiles
        }
        with open("./config.json", "w") as config_file:
            json.dump(data_to_dump, config_file, indent=4, sort_keys=True)
            

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
                print(data.decode("utf-8"))
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

    def debug_temp(self):
        """
            Debug temperature sensing subscriber. We can send to the sensing pi
            which person has been detected.
        """
        self.receive_thread.start()
        while True:
            detected = input("Who was detected? ")
            if detected.lower() == 'q':
                break
            temperature_message = {
                'detected': detected,
                'profiles': self.profiles
            }
            serialized_message = self.publish_temp_pi_topic_id + " " + json.dumps(temperature_message)
            print(serialized_message)
            self.publish_socket.send_string(serialized_message)
            
    def debug_recognition(self):
        """
            Debug face recognition subscriber. We will be sending face encodings.
        """
        self.receive_thread.start()
        while True:
            pause = input("Press enter to send encodings ")
            if(pause.lower() == 'q'):
                break
            encodings = pickle.load(open("encodings.pickle","rb"))
            multipart_message = [str.encode(self.publish_recognition_pi_topic_id), pickle.dumps(encodings)]
            self.publish_socket.send_multipart(multipart_message)


    def check_for_received(self):
            print("Checking for any received messages...")
            self.check_queue()


if __name__ == '__main__':
    root = tk.Tk()
    server = FogServer(master=root)
    if len(sys.argv) > 1 and sys.argv[1].lower() == '-d':
        server.debug_producer()
    elif len(sys.argv) > 1 and sys.argv[1].lower() == '-t':
        server.debug_temp()
    elif len(sys.argv) > 1 and sys.argv[1].lower() == '-f':
        server.debug_recognition()
    else:
        server.producer()
    server.mainloop()
