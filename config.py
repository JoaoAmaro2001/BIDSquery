import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox

CONFIG_FILE = os.path.join(os.path.expanduser('~'), '.bidsquery_config.json')

# --- add near the top, next to CONFIG_FILE ---
CACHE_FILE = os.path.join(os.path.expanduser('~'), '.bidsquery_cache.json')

def load_cache():
    """Load BIDS discovery cache."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_cache(cache_data):
    """Persist BIDS discovery cache."""
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache_data, f, indent=2)

def clear_cache_file():
    """Delete persisted BIDS discovery cache."""
    try:
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
    except OSError:
        pass


def load_config():
    """Load the entire configuration from config file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_config(config_data):
    """Save the entire configuration to config file."""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_data, f, indent=2)

def load_base_dir():
    """Load the saved base directory from config file."""
    config = load_config()
    return config.get('base_dir')

def save_base_dir(path):
    """Save the chosen base directory to config file."""
    config = load_config()
    config['base_dir'] = path
    save_config(config)

def load_participant_file_path():
    """Load the saved participant file path from config file."""
    config = load_config()
    return config.get('participant_file')

def save_participant_file_path(path):
    """Save the chosen participant file path to config file."""
    config = load_config()
    config['participant_file'] = path
    save_config(config)

def choose_folder():
    """Open a GUI dialog to choose a directory."""
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    
    folder = filedialog.askdirectory(
        title="Select the main directory containing your studies/projects"
    )
    
    root.destroy()
    return folder

def choose_participant_file():
    """Open a GUI dialog to choose a participant data file."""
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    
    file_path = filedialog.askopenfilename(
        title="Select participant data file",
        filetypes=[
            ("CSV files", "*.csv"),
            ("Excel files", "*.xlsx *.xls"),
            ("All files", "*.*")
        ]
    )
    
    root.destroy()
    return file_path

def show_setup_dialog():
    """Show a setup dialog to configure both directories and participant file."""
    root = tk.Tk()
    root.title("BIDSQuery Setup")
    root.geometry("500x300")
    
    current_config = load_config()
    
    # Variables to store paths
    base_dir_var = tk.StringVar(value=current_config.get('base_dir', ''))
    participant_file_var = tk.StringVar(value=current_config.get('participant_file', ''))
    
    def choose_base_dir():
        folder = filedialog.askdirectory(title="Select main directory")
        if folder:
            base_dir_var.set(folder)
    
    def choose_participant_data():
        file_path = filedialog.askopenfilename(
            title="Select participant data file",
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx *.xls")]
        )
        if file_path:
            participant_file_var.set(file_path)
    
    def save_and_close():
        config = {
            'base_dir': base_dir_var.get(),
            'participant_file': participant_file_var.get()
        }
        save_config(config)
        messagebox.showinfo("Success", "Configuration saved successfully!")
        root.destroy()
    
    # GUI Layout
    tk.Label(root, text="BIDSQuery Configuration", font=('Arial', 14, 'bold')).pack(pady=10)
    
    # Base directory section
    tk.Label(root, text="Main Directory (containing studies/projects):").pack(anchor='w', padx=20)
    frame1 = tk.Frame(root)
    frame1.pack(fill='x', padx=20, pady=5)
    tk.Entry(frame1, textvariable=base_dir_var, width=50).pack(side='left', fill='x', expand=True)
    tk.Button(frame1, text="Browse", command=choose_base_dir).pack(side='right', padx=(5,0))
    
    # Participant file section
    tk.Label(root, text="Participant Data File (CSV/Excel):").pack(anchor='w', padx=20, pady=(20,0))
    frame2 = tk.Frame(root)
    frame2.pack(fill='x', padx=20, pady=5)
    tk.Entry(frame2, textvariable=participant_file_var, width=50).pack(side='left', fill='x', expand=True)
    tk.Button(frame2, text="Browse", command=choose_participant_data).pack(side='right', padx=(5,0))
    
    # Info text
    info_text = """
    Instructions:
    1. Select the main directory containing your study folders
    2. Select the CSV/Excel file with participant information
    3. The app will search for 'bids' folders in subdirectories
    4. Participant file should have columns linking names to subject IDs
    """
    tk.Label(root, text=info_text, justify='left', fg='gray').pack(padx=20, pady=20)
    
    # Buttons
    button_frame = tk.Frame(root)
    button_frame.pack(pady=20)
    tk.Button(button_frame, text="Save Configuration", command=save_and_close, bg='green', fg='white').pack(side='left', padx=5)
    tk.Button(button_frame, text="Cancel", command=root.destroy).pack(side='left', padx=5)
    
    root.mainloop()

if __name__ == '__main__':
    # Test the setup dialog
    show_setup_dialog()