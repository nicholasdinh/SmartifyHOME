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
from topics import tset
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
        self.updater()

        self.detected_profile = None

    def create_top_frame(self):
        self.topFrame = tk.Frame(master=self.master)
        self.topFrame.grid(row=0, sticky="nsew", padx=5, pady=5)

        self.profileLabel = tk.Label(master=self.topFrame, text="Profiles")
        self.profileLabel.grid(row=0, column=0, sticky="nsew")


        self.entryFrame = tk.LabelFrame(master=self.topFrame, text="Server Options")
        self.entryFrame.grid(row=0, column=2, sticky="nsew")

        self.nameEntry = tk.Entry(self.entryFrame)
        self.tempEntry = tk.Entry(self.entryFrame)
        tk.Label(self.entryFrame, text="Profile Name").grid(row=0, padx=5, pady=5)
        tk.Label(self.entryFrame, text="Temp Preference").grid(row=1, padx=5, pady=5)
        self.nameEntry.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.tempEntry.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)


        self.addUserButton = tk.Button(master=self.entryFrame, text="Add User", command=self.addUserOnClick)
        self.addUserButton.grid(row=2, column=0, sticky="nsew", columnspan=2, padx=5, pady=5)

        self.sendEncodingsButton = tk.Button(master=self.entryFrame, text="Send Encodings", command=self.send_recognition_message)
        self.sendEncodingsButton.grid(row=3, column=0,sticky="nsew", columnspan=2, padx=5, pady=5)

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
        self.treev = ttk.Treeview(self.master, columns = ("id", "Name", "Preference"), show="headings", selectmode="browse")
        self.treev.heading("id", text="User ID")
        self.treev.heading("Name", text="Name")
        self.treev.heading("Preference", text="Preference")
        self.treev.bind("<Double-1>", self.on_tree_view_double_click)
        self.treev.grid(row=1, column=0, sticky="nsew")

        self.room_treev = ttk.Treeview(self.master, columns= ("id", "Name", "Temperature", "Fan", "Detected"), show="headings", selectmode="browse")
        self.room_treev.heading("id", text="Room ID")
        self.room_treev.heading("Name", text="Room Name")
        self.room_treev.heading("Detected", text="Detected User")
        self.room_treev.heading("Temperature", text="Temperature")
        self.room_treev.heading("Fan", text="Fan Status")
        self.room_treev.grid(row=2, column=0, sticky="nsew")

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
        self.profiles[str(self.available_id)] = new_profile
        self.treev.insert('', 'end', text=username, values=(new_profile['id'],username,temp))
        self.dump_to_config_file()


    def on_tree_view_double_click(self, event):
        item = self.treev.selection()[0]
        clicked_id, clicked_name, clicked_preference = self.treev.item(item, "values")
        self.edit_user_window(clicked_id, clicked_name, clicked_preference)

    def update_tree_on_load(self):
        for profile_id in self.profiles:
            profile = self.profiles[profile_id]
            self.treev.insert('','end', text=profile['name'], values=(profile['id'], profile['name'], profile['temperature_preference']))
        self.update_temperature_tree()

    def update_temperature_tree(self):
        for room_id in self.rooms:
            room = self.rooms[room_id]
            self.room_treev.insert('','end', values=(room['id'], room['name'], room['temperature'], room['fan_status'], room['detected_name']))

    def edit_user_window(self, id, name, preference):
        window = tk.Toplevel(self.master)

        # Frame of entire window
        edit_user_frame = tk.Frame(master = window)
        edit_user_frame.grid(row=0, sticky="nsew")
        edit_user_frame.grid_rowconfigure(0, weight=1)
        edit_user_frame.grid_rowconfigure(1, weight=1)
        edit_user_frame.grid_rowconfigure(2, weight=1)
        edit_user_frame.grid_columnconfigure(0, weight=1)

        # First row, label in window
        tk.Label(edit_user_frame, text="Editing " + name).grid(row=0, padx=5, pady=5, sticky="nsew")
        
        
        # Second row, labelframe of edit options
        edit_label_frame = tk.LabelFrame(master=edit_user_frame, text="Edit Options")
        edit_label_frame.grid(row=1, padx=5, pady=5, sticky="nsew")
        edit_label_frame.grid_rowconfigure(0,weight=1)
        edit_label_frame.grid_rowconfigure(1,weight=1)
        edit_label_frame.grid_rowconfigure(2,weight=1)
        edit_label_frame.grid_columnconfigure(0, weight=1)
        edit_label_frame.grid_columnconfigure(1, weight=1)
        edit_label_frame.grid_columnconfigure(2, weight=1)

        tk.Label(edit_label_frame, text="New temperature preference").grid(row=1, column=0, padx=5, sticky="nsew")
        new_preference_entry = tk.Entry(master=edit_label_frame)
        new_preference_entry.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")

        confirm_edit_button = tk.Button(edit_label_frame, text="Enter", command=lambda: self.update_user(id, new_preference_entry.get(), window))
        confirm_edit_button.grid(row=1, column=2, padx=5, pady=5, sticky="nsew")

        delete_user_button = tk.Button(edit_label_frame, text="Delete User", command=lambda: self.delete_user(id, window))
        delete_user_button.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")

        # Third row, cancel button
        cancel_button = tk.Button(edit_user_frame, text="Cancel", command=lambda: self.close_edit_window(window))
        cancel_button.grid(row=2, padx=5, pady=5, sticky="nsew")

        window.grid_rowconfigure(0, weight=1)
        window.grid_columnconfigure(0, weight=1)

    def update_user(self, user_id, new_preference, toplevel):
        for profile in self.profiles:
            if profile["id"] == user_id:
                profile["temperature_preference"] = new_preference
    
        self.reset_tree_and_close_window(toplevel)

    def delete_user(self, user_id, toplevel):
        for profile_id in self.profiles:
            if profile_id == user_id:
                self.profiles.pop(profile_id)
        self.reset_tree_and_close_window(toplevel)

    def close_edit_window(self, toplevel):
        toplevel.destroy()
        toplevel.update()

    def reset_tree_and_close_window(self, toplevel):
        self.dump_to_config_file()

        # send message to all temperature pi's with new profiles
        self.send_temperature_client_message(-1)
        self.treev.delete(*self.treev.get_children())
        self.room_treev.delete(*self.room_treev.get_children())
        self.update_tree_on_load()
        self.close_edit_window(toplevel)

    def read_config_file(self):
        """
            Load in values from config file for the ip address of the forwarder and the port numbers.
        """

        self.rec_topic_id = tset["SERVER"]
        self.publish_temp_pi_topic_id = tset["TEMP"]
        self.publish_recognition_pi_topic_id = tset["IDENTITY"]

        with open("./config.json") as config_file:
            data = json.load(config_file)
            self.receiver_port = data["subscriber_port"]
            self.publish_port = data["publisher_port"]
            self.ip = "tcp://" + data["forwarder_ip"] + ":"
            self.available_id = data["available_id"]
            self.profiles = data["profiles"]
            self.rooms = data["rooms"]
            self.room_id = data["room_id"]
        self.update_tree_on_load()

    def dump_to_config_file(self):
        data_to_dump = {
            "subscriber_port": self.receiver_port,
            "publisher_port": self.publish_port,
            "forwarder_ip": self.ip[6:-1],
            "available_id": self.available_id,
            "profiles": self.profiles,
            "rooms": self.rooms,
            "room_id": self.room_id
        }
        with open("./config.json", "w") as config_file:
            json.dump(data_to_dump, config_file, indent=4, sort_keys=True)

    def receiver(self):
        """
            Thread were data is received from the devices.
        """
        while True:
            try:
                # print("Trying to receive!")
                data = self.receiver_socket.recv()
                # print(data.decode("utf-8"))
                self.queue.put(data.decode("utf-8"))
            except zmq.Again:
                continue

    def check_queue(self):
        """
            Check if there is any data received by the devices waiting to be processed.
        """
        if self.queue.qsize() > 0:
            data = json.loads(self.queue.get()[2:])
            if "names" in data:
                detected_names = data["names"]
                self.send_temperature_client_message(detected_names)
            else:
                print(data)
                room_id = data["room_id"]
                detected_profile = data["detected_profile"]
                self.rooms[room_id]["temperature"] = data["temperature"]
                self.rooms[room_id]["fan_status"] = data["fan_status"]
                self.rooms[room_id]["detected_id"] = detected_profile["id"]
                self.rooms[room_id]["detected_name"] = detected_profile["name"]
                self.room_treev.delete(*self.room_treev.get_children())
                self.update_temperature_tree()
                self.dump_to_config_file()
            # print("New room " + self.rooms[room_id])
        else:
            print("Server's receive queue was empty.")

    def send_temperature_client_message(self, detected):
        temperature_message = {
            'names': detected,
            'profiles': self.profiles
        }
        serialized_message = self.publish_temp_pi_topic_id + " " + json.dumps(temperature_message)
        self.publish_socket.send_string(serialized_message)

    def send_recognition_message(self):
        encodings = pickle.load(open("encodings.pickle","rb"))
        encodings["profiles"] = self.profiles
        multipart_message = [str.encode(self.publish_recognition_pi_topic_id), pickle.dumps(encodings)]
        self.publish_socket.send_multipart(multipart_message)

    def check_for_received(self):
            print("Checking for any received messages...")
            self.check_queue()

    def updater(self):
        self.check_for_received()
        self.after(500, self.updater)

    def debug_updater(self):
        self.check_for_received()
        random_id = random.randint(5,9)
        self.send_temperature_client_message(str(random_id))
        self.after(500, self.debug_updater)

    def start(self):
        self.receive_thread.start()
        self.send_recognition_message()
        

if __name__ == '__main__':
    root = tk.Tk()
    server = FogServer(master=root)
    server.start()
    server.mainloop()