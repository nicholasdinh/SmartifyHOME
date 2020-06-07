import tkinter as tk

class EditUserWindow(tk.Toplevel): 
    def __init__(self, name, commands):
        tk.Toplevel.__init__(self)

        confirm_edit_command = commands["confirm_edit"]
        delete_user_command = commands["delete_user"]
        cancel_button_command = commands["cancel"]

       # Frame of entire window
        self.edit_user_frame = tk.Frame(master=self)
        self.configure_edit_user_frame()

        # First row, label in window
        tk.Label(self.edit_user_frame, text="Editing " + name).grid(row=0, padx=5, pady=5, sticky="nsew")

        # Second row, labelframe of edit options
        self.edit_label_frame = tk.LabelFrame(master=self.edit_user_frame, text="Edit Options")
        self.configure_edit_label_frame()
        
        tk.Label(self.edit_label_frame, text="New temperature preference").grid(row=1, column=0, padx=5, sticky="nsew")
        new_preference_entry = tk.Entry(master=self.edit_label_frame)
        new_preference_entry.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")

        self.confirm_edit_button = tk.Button(self.edit_label_frame, text="Enter", command=lambda: confirm_edit_command(name, new_preference_entry.get(), self))
        self.configure_edit_button()

        self.delete_user_button = tk.Button(self.edit_label_frame, text="Delete User", command=lambda: delete_user_command(name, self) )
        self.configure_delete_user_button()

        # Third row, cancel button
        self.cancel_button = tk.Button(self.edit_user_frame, text="Cancel", command=lambda: cancel_button_command(self) )
        self.configure_cancel_button()

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

    
    def configure_edit_user_frame(self):
        self.edit_user_frame.grid(row=0, sticky="nsew")
        self.edit_user_frame.grid_rowconfigure(0, weight=1)
        self.edit_user_frame.grid_rowconfigure(1, weight=1)
        self.edit_user_frame.grid_rowconfigure(2, weight=1)
        self.edit_user_frame.grid_columnconfigure(0, weight=1)

    def configure_edit_label_frame(self):
        self.edit_label_frame.grid(row=1, padx=5, pady=5, sticky="nsew")
        self.edit_label_frame.grid_rowconfigure(0,weight=1)
        self.edit_label_frame.grid_rowconfigure(1,weight=1)
        self.edit_label_frame.grid_rowconfigure(2,weight=1)
        self.edit_label_frame.grid_columnconfigure(0, weight=1)
        self.edit_label_frame.grid_columnconfigure(1, weight=1)
        self.edit_label_frame.grid_columnconfigure(2, weight=1)

    def configure_edit_button(self):
        self.confirm_edit_button.grid(row=1, column=2, padx=5, pady=5, sticky="nsew")

    def configure_delete_user_button(self):
        self.delete_user_button.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")

    def configure_cancel_button(self):
        self.cancel_button.grid(row=2, padx=5, pady=5, sticky="nsew")