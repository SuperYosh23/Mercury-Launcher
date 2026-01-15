import os
import sys
import subprocess
import threading # Added for background tasks
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import minecraft_launcher_lib
import shutil

# -------------------------
# Paths
# -------------------------
def get_minecraft_dir():
    if sys.platform.startswith("win"):
        return os.path.join(os.environ["APPDATA"], ".minecraft")
    else:
        return os.path.expanduser("~/.minecraft")

MINECRAFT_DIR = get_minecraft_dir()

# -------------------------
# Mercury Launcher UI
# -------------------------
class MercuryLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Mercury Launcher")
        self.root.geometry("520x600") # Increased height for progress bar
        self.root.configure(bg="#1e1e1e")
        self.root.resizable(False, False)

        # Modern ttk style
        self.style = ttk.Style(root)
        self.style.theme_use("clam")

        # Dark theme configuration
        self.style.configure("TLabel", background="#1e1e1e", foreground="#ffffff", font=("Segoe UI", 10))
        self.style.configure("TButton", font=("Segoe UI", 10, "bold"), foreground="#ffffff", background="#3a3a3a", borderwidth=0)
        self.style.map("TButton", background=[("active", "#505050")])
        self.style.configure("TEntry", fieldbackground="#3a3a3a", foreground="#ffffff", insertcolor="white")
        self.style.configure("TCombobox", fieldbackground="#3a3a3a", background="#1e1e1e", foreground="#ffffff", arrowcolor="white")

        # Title
        title = tk.Label(root, text="Mercury Launcher", font=("Segoe UI", 24, "bold"), bg="#1e1e1e", fg="#00d1ff")
        title.pack(pady=20)

        # Container Frame
        self.frame = tk.Frame(root, bg="#1e1e1e")
        self.frame.pack(padx=30, fill="x")

        # Username
        ttk.Label(self.frame, text="Username").pack(anchor="w", pady=(0,2))
        self.username_entry = ttk.Entry(self.frame)
        self.username_entry.pack(fill="x", pady=(0,15))

        # Instance Name
        ttk.Label(self.frame, text="Instance Name (Subfolder)").pack(anchor="w", pady=(0,2))
        self.instance_entry = ttk.Entry(self.frame)
        self.instance_entry.insert(0, "default")
        self.instance_entry.pack(fill="x", pady=(0,15))

        # Version Selector (Changed to Combobox)
        ttk.Label(self.frame, text="Minecraft Version").pack(anchor="w", pady=(0,2))
        self.version_combo = ttk.Combobox(self.frame, state="readonly")
        self.version_combo.pack(fill="x", pady=(0,15))

        # Load versions in background to not freeze startup
        threading.Thread(target=self.load_versions, daemon=True).start()

        # Skin Section
        ttk.Label(self.frame, text="Skin (Visual only - requires mod for in-game)").pack(anchor="w", pady=(0,2))
        self.skin_frame = tk.Frame(self.frame, bg="#1e1e1e")
        self.skin_frame.pack(fill="x", pady=(0,10))
        self.skin_path_var = tk.StringVar()
        ttk.Entry(self.skin_frame, textvariable=self.skin_path_var).pack(side="left", fill="x", expand=True)
        ttk.Button(self.skin_frame, text="Browse", command=self.browse_skin).pack(side="left", padx=5)

        # Skin Preview Card
        self.skin_preview_card = tk.Frame(root, bg="#2d2d2d", width=80, height=80)
        self.skin_preview_card.pack(pady=5)
        self.skin_preview_card.pack_propagate(False)
        self.skin_preview_label = tk.Label(self.skin_preview_card, bg="#2d2d2d")
        self.skin_preview_label.pack(expand=True)

        # Progress Info
        self.status_label = tk.Label(root, text="Ready", bg="#1e1e1e", fg="#aaaaaa", font=("Segoe UI", 9))
        self.status_label.pack(pady=(10, 0))

        # Launch Button
        self.launch_btn = ttk.Button(root, text="Download & Launch", command=self.start_launch_thread)
        self.launch_btn.pack(pady=15, ipadx=20, ipady=8)

    # -------------------------
    # Logic
    # -------------------------
    def load_versions(self):
        try:
            versions = minecraft_launcher_lib.utils.get_version_list()
            release_versions = [v["id"] for v in versions if v["type"] == "release"]
            # Schedule UI update on main thread
            self.root.after(0, lambda: self.version_combo.configure(values=release_versions[:30]))
            if release_versions:
                self.root.after(0, lambda: self.version_combo.set(release_versions[0]))
        except Exception:
            self.root.after(0, lambda: messagebox.showerror("Error", "Could not fetch versions"))

    def browse_skin(self):
        path = filedialog.askopenfilename(title="Select Skin PNG", filetypes=[("PNG Images", "*.png")])
        if path:
            self.skin_path_var.set(path)
            self.update_skin_preview(path)

    def update_skin_preview(self, path):
        try:
            img = Image.open(path)
            # Resize keeping aspect ratio
            img.thumbnail((64, 64))
            self.skin_image = ImageTk.PhotoImage(img)
            self.skin_preview_label.config(image=self.skin_image)
        except Exception:
            pass

    def start_launch_thread(self):
        # Disable button to prevent double clicks
        self.launch_btn.config(state="disabled")
        self.status_label.config(text="Initializing...")

        # Start the heavy lifting in a new thread
        threading.Thread(target=self.launch, daemon=True).start()

    def launch(self):
        username = self.username_entry.get().strip()
        version = self.version_combo.get()
        instance_name = self.instance_entry.get().strip() or "default"
        instance_dir = os.path.join(MINECRAFT_DIR, "instances", instance_name)
        os.makedirs(instance_dir, exist_ok=True)

        if not username or not version:
            self.root.after(0, lambda: messagebox.showerror("Error", "Username and Version required"))
            self.root.after(0, lambda: self.launch_btn.config(state="normal"))
            return

        # Callback to update UI from the background thread
        def update_status(text):
            self.status_label.config(text=text)

        # Callback for download progress
        def progress_callback(current, max_val, text):
            self.root.after(0, lambda: update_status(f"{text}: {current}/{max_val}"))

        try:
            self.root.after(0, lambda: update_status("Checking/Downloading Game Files..."))

            # Install with callbacks
            minecraft_launcher_lib.install.install_minecraft_version(
                version=version,
                minecraft_directory=MINECRAFT_DIR,
                callback={'setStatus': lambda text: self.root.after(0, lambda: update_status(text))}
            )

            options = {
                "username": username,
                "uuid": "0", # Offline mode UUID
                "token": "0",
                "launcherName": "MercuryLauncher",
                "gameDir": instance_dir,
            }

            self.root.after(0, lambda: update_status("Launching..."))

            command = minecraft_launcher_lib.command.get_minecraft_command(version, MINECRAFT_DIR, options)

            # Launch the game
            subprocess.Popen(command)

            # Close launcher
            self.root.after(0, self.root.destroy)

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Launch Error", str(e)))
            self.root.after(0, lambda: self.launch_btn.config(state="normal"))
            self.root.after(0, lambda: update_status("Error occurred"))

# -------------------------
# Run Launcher
# -------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = MercuryLauncher(root)
    root.mainloop()
