import os
import json
import tkinter as tk
from tkinter import filedialog

CONFIG_FILE = os.path.join(os.path.expanduser('~'), '.bidsquery_config.json')

def load_base_dir():
    """Load the saved base directory from config file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            data = json.load(f)
            return data.get('base_dir')
    return None


def save_base_dir(path):
    """Save the chosen base directory to config file."""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump({'base_dir': path}, f)


def choose_folder():
    """Open a GUI dialog to choose a directory."""
    root = tk.Tk()
    root.withdraw()
    folder = filedialog.askdirectory(title="Select BIDS base folder")
    root.destroy()
    return folder