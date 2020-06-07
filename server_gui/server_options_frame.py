import tkinter as tk

class ServerOptionsFrame(tk.LabelFrame):
    def __init__(self, master, commands):
        super().__init__(master, text="Server Options")

        self.add_user_command = commands["add_user"]
        self.send_encodings_command = commands["send_encodings"]

        self.grid(row=0, column=2, sticky="nsew")

        self.add_text_entry()
        self.add_buttons()
        self.configure_buttons()
        self.configure_frame()


    def add_text_entry(self):
        self.nameEntry = tk.Entry(self)
        self.tempEntry = tk.Entry(self)
        tk.Label(self, text="Profile Name").grid(row=0, padx=5, pady=5)
        tk.Label(self, text="Temp Preference").grid(row=1, padx=5, pady=5)
        self.nameEntry.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.tempEntry.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)

    def add_buttons(self):
        self.addUserButton = tk.Button(master=self, text="Add User", command=self.addUserOnClick)
        self.sendEncodingsButton = tk.Button(master=self, text="Send Encodings", command=self.send_encodings_command)

    def configure_buttons(self):
        self.addUserButton.grid(row=2, column=0, sticky="nsew", columnspan=2, padx=5, pady=5)
        self.sendEncodingsButton.grid(row=3, column=0,sticky="nsew", columnspan=2, padx=5, pady=5)

    def configure_frame(self):
        self.grid_rowconfigure(0,weight=1)
        self.grid_rowconfigure(1,weight=1)
        self.grid_rowconfigure(2,weight=1)
        self.grid_columnconfigure(0,weight=1)
        self.grid_columnconfigure(1,weight=1)

    def addUserOnClick(self):
        # Clear entries first
        temp = self.tempEntry.get()
        name = self.nameEntry.get()
        self.add_user_command(name, temp)
        self.tempEntry.delete(0,'end')
        self.nameEntry.delete(0,'end')
