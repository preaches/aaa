import tkinter as tk
import ctypes
import json
import time
import threading
import socket
import pickle
from pynput import mouse, keyboard  # Cross-platform mouse and keyboard library

with open(r"config.json") as json_file:
    data = json.load(json_file)
ip = data["misc_settings"]["ip"]
port = data["misc_settings"]["port"]
tcp_sleep = data["misc_settings"]["tcp_sleep"]

class FullScreenApp:
    def __init__(self, host, port):
        self.root = tk.Tk()
        self.root.attributes("-fullscreen", True)
        self.root.configure(background='white')
        self.root.bind('<Motion>', self.on_mouse_motion)
        
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        self.center_x = self.screen_width // 2
        self.center_y = self.screen_height // 2
        self.prev_x = self.center_x
        self.prev_y = self.center_y
        
        self.mouse_movement = {"x": 0, "y": 0}
        self.mouse_button = None
        self.mouse5_state = False
        self.mouse6_state = False
        self.running = True
        
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        
        # Setup mouse and keyboard listeners
        self.mouse_listener = mouse.Listener(on_move=self.on_mouse_move)
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_press, 
            on_release=self.on_release
        )

    def on_mouse_motion(self, event):
        rel_x = event.x - self.prev_x
        rel_y = event.y - self.prev_y

        max_movement = 256 #limits the value
        rel_x = max(min(rel_x, max_movement), -max_movement)
        rel_y = max(min(rel_y, max_movement), -max_movement)

        if event.x == self.center_x and event.y == self.center_y:
            rel_x = rel_y = 0  # resets mouse_movement (just in case)
        self.mouse_movement = {"x": rel_x, "y": rel_y}

    def on_mouse_move(self, x, y):
        # This method is called by pynput mouse listener
        rel_x = x - self.prev_x
        rel_y = y - self.prev_y

        max_movement = 256
        rel_x = max(min(rel_x, max_movement), -max_movement)
        rel_y = max(min(rel_y, max_movement), -max_movement)

        self.mouse_movement = {"x": rel_x, "y": rel_y}
        self.prev_x, self.prev_y = x, y

    def on_press(self, key):
        try:
            # Check mouse buttons
            if key == mouse.Button.left:
                self.mouse_button = "Left"
            elif key == mouse.Button.right:
                self.mouse_button = "Right"
            elif key == mouse.Button.middle:
                self.mouse_button = "Middle"
            
            # Check additional mouse buttons
            if key == mouse.Button.x1:
                self.mouse5_state = True
            elif key == mouse.Button.x2:
                self.mouse6_state = True
        except AttributeError:
            pass

    def on_release(self, key):
        # Reset button states on release
        if key in [mouse.Button.left, mouse.Button.right, mouse.Button.middle]:
            self.mouse_button = None
        
        if key == mouse.Button.x1:
            self.mouse5_state = False
        elif key == mouse.Button.x2:
            self.mouse6_state = False

    def print_state(self): 
        last_state = None
        while self.running:
            state = {
                "mouse_movement": self.mouse_movement,
                "mouse_button": self.mouse_button,
                "mouse5": self.mouse5_state,
                "mouse6": self.mouse6_state
            }

            # this basically checks for any active movements (holding is considered active)
            if (state != last_state) or (self.mouse_movement["x"] != 0) or (self.mouse_movement["y"] != 0) or \
            (self.mouse_button is not None) or self.mouse5_state or self.mouse6_state:
                print(state)
                # send it to the server.py (main pc)
                self.socket.send(pickle.dumps(state))
                last_state = state

            self.mouse_movement = {"x": 0, "y": 0}
            time.sleep(tcp_sleep) #a sleep to stabilize

    def reset_mouse_position(self):
        # Cross-platform mouse reset
        mouse_controller = mouse.Controller()
        mouse_controller.position = (self.center_x, self.center_y)

    def data_received_handler(self):
        while self.running:
            data = self.socket.recv(1024)
            if data:
                received_data = pickle.loads(data)  # Deserialize data and reset the position
                print("Received data:", received_data)
                self.reset_mouse_position()

    def run(self):
        # Start listeners
        self.mouse_listener.start()
        self.keyboard_listener.start()

        # Start threads
        data_received_thread = threading.Thread(target=self.data_received_handler)
        print_thread = threading.Thread(target=self.print_state)
        
        print_thread.start()
        data_received_thread.start()

        self.root.mainloop()
        
        # Stop listeners when done
        self.running = False
        self.mouse_listener.stop()
        self.keyboard_listener.stop()

if __name__ == "__main__":
    remote_host = ip  
    remote_port = port  

    app = FullScreenApp(remote_host, remote_port)
    app.run()
