import json
import multiprocessing
from pathlib import Path
import pickle
import queue
import random
import sys
import shutil
import threading
import time
from tkinter import ttk
import tkinter.font as tkFont
import tkinter.messagebox as tkMBox
import tkinter as tk
from topics import tset
import zmq

from server_encode_faces import encode_and_write_to_file
from server_gui import EditUserWindow
from server_gui import ServerOptionsFrame

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

        encodings_path = Path("./encodings.pickle")
        if encodings_path.exists():
            self.encodings_mtime = encodings_path.stat().st_mtime
        else:
            self.encodings_mtime = -1

        self.updater()

        self.detected_profile = None

    def create_top_frame(self):
        self.topFrame = tk.Frame(master=self.master)
        self.topFrame.grid(row=0, sticky="nsew", padx=5, pady=5)
        self.profileLabel = tk.Label(master=self.topFrame, text="Profiles")
        self.profileLabel.grid(row=0, column=0, sticky="nsew")
        self.create_options_frame()
        self.configure_top_frame()

    def create_options_frame(self):
        add_user_command = lambda new_name, new_temp : self.addUserOnClick(new_name, new_temp)
        send_encodings_command = lambda : self.send_recognition_message()
        commands = {
            "add_user": add_user_command,
            "send_encodings": send_encodings_command
        }
        self.options_frame = ServerOptionsFrame(self.topFrame, commands)

    def configure_top_frame(self):
        self.topFrame.grid_rowconfigure(0,weight=1)
        self.topFrame.grid_columnconfigure(0,weight=1)
        self.topFrame.grid_columnconfigure(1,weight=1)
        self.topFrame.grid_columnconfigure(2,weight=1)


    def create_tree_view(self):
        self.treev = ttk.Treeview(self.master, columns = ("Name", "Preference"), show="headings", selectmode="browse")
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

    def addUserOnClick(self, profile_name, profile_temp):
        new_profile = dict()
        new_profile['name'] = profile_name
        new_profile['temperature_preference'] = profile_temp
        self.profiles[profile_name.lower()] = new_profile
        self.treev.insert('', 'end', text=profile_name, values=(profile_name,profile_temp))
        self.dump_to_config_file()


    def on_tree_view_double_click(self, event):
        item = self.treev.selection()[0]
        clicked_name, _ = self.treev.item(item, "values")
        commands = {
            "confirm_edit": lambda name, new_pref, window: self.update_user(name, new_pref, window),
            "delete_user": lambda name, window: self.delete_user(name, window),
            "cancel": lambda window: self.close_edit_window(window)
        }
        edit_window = EditUserWindow(clicked_name, commands)

    def update_tree_on_load(self):
        for profile in self.profiles.values():
            self.treev.insert('','end', text=profile['name'], values=(profile['name'], profile['temperature_preference']))
        self.update_temperature_tree()

    def update_temperature_tree(self):
        for room_id in self.rooms:
            room = self.rooms[room_id]
            self.room_treev.insert('','end', values=(room['id'], room['name'], room['temperature'], room['fan_status'], room['detected_name']))

    def update_user(self, name, new_preference, toplevel):
        self.profiles[name.lower()]["temperature_preference"] = new_preference
        self.reset_tree_and_close_window(toplevel)

    def delete_user(self, name, toplevel):
        try:
            self.profiles.pop(name.lower())
            shutil.rmtree("./dataset/" + name)
            encodings_process = multiprocessing.Process(target=do_encodings)
            encodings_process.start()
            print("Deleted users files!!")
        except FileNotFoundError:
            pass
        
        self.reset_tree_and_close_window(toplevel)

    def close_edit_window(self, toplevel):
        toplevel.destroy()
        toplevel.update()

    def reset_tree_and_close_window(self, toplevel):
        self.dump_to_config_file()

        # send message to all temperature pi's with new profiles
        self.send_temperature_client_message([])
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
            self.profiles = data["profiles"]
            self.rooms = data["rooms"]
            self.room_id = data["room_id"]
        self.update_tree_on_load()

    def dump_to_config_file(self):
        data_to_dump = {
            "subscriber_port": self.receiver_port,
            "publisher_port": self.publish_port,
            "forwarder_ip": self.ip[6:-1],
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
                data = self.receiver_socket.recv()
                self.queue.put(data.decode("utf-8"))
            except zmq.Again:
                continue

    def check_queue(self):
        """
            Check if there is any data received by the devices waiting to be processed.
        """
        if self.queue.qsize() > 0:
            raw_data = self.queue.get()[7:]
            data = json.loads(raw_data)
            if "names" in data:
                print("Received data from recognition client: " + raw_data)
                detected_names = [name.lower() for name in data["names"]]
                # if "Unknown" in detected_names:
                #     detected_names.remove("Unknown")
                if len(detected_names) > 0:
                    self.send_temperature_client_message(detected_names)
            else:
                print("Received data from temperature client: " + raw_data)
                room_id = data["room_id"]
                detected_profile = data["detected_profile"]
                self.rooms[room_id]["fan_status"] = data["fan_status"]
                self.rooms[room_id]["temperature"] = data["temperature"]
                if detected_profile != None and detected_profile != "Unknown":
                    self.rooms[room_id]["detected_name"] = detected_profile["name"]
                else:
                    self.rooms[room_id]["detected_name"] = "Unknown"
                self.room_treev.delete(*self.room_treev.get_children())
                self.update_temperature_tree()
                self.dump_to_config_file()

    def send_temperature_client_message(self, detected):
        temperature_message = {
            'names': detected,
            'profiles': self.profiles
        }
        serialized_message = self.publish_temp_pi_topic_id + " " + json.dumps(temperature_message)
        self.publish_socket.send_string(serialized_message)

    def send_recognition_message(self):
        print("Sending encodings!")
        encodings = pickle.load(open("encodings.pickle","rb"))
        encodings["profiles"] = self.profiles
        multipart_message = [str.encode(self.publish_recognition_pi_topic_id), pickle.dumps(encodings)]
        self.publish_socket.send_multipart(multipart_message)

    def check_encodings_file(self):
        encodings_path = Path("./encodings.pickle")

        if encodings_path.exists():
            current_mtime = encodings_path.stat().st_mtime
            if self.encodings_mtime == -1 or (self.encodings_mtime != current_mtime):
                self.encodings_mtime = current_mtime
                self.send_recognition_message()
                print("Updating encodings file!!")

    def updater(self):
        try:
            self.check_encodings_file()
        except FileNotFoundError:
            pass
        self.check_queue()
        self.after(250, self.updater)

    def debug_updater(self):
        self.check_for_received()
        random_id = random.randint(5,9)
        self.send_temperature_client_message(str(random_id))
        self.after(250, self.debug_updater)

    def start(self):
        self.receive_thread.start()
        try:
            self.send_recognition_message()
        except FileNotFoundError:
            pass
        

def do_encodings():
    encode_and_write_to_file("./dataset")

if __name__ == '__main__':
    root = tk.Tk()
    server = FogServer(master=root)
    server.start()
    server.mainloop()