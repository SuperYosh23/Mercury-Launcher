import os
import sys
import subprocess
import threading
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import minecraft_launcher_lib
import shutil

# -------------------------
# Global Paths
# -------------------------
def get_minecraft_dir():
    if sys.platform.startswith("win"):
        return os.path.join(os.environ["APPDATA"], ".minecraft")
    else:
        return os.path.expanduser("~/.minecraft")

MINECRAFT_DIR = get_minecraft_dir()
INSTANCES_DIR = os.path.join(MINECRAFT_DIR, "mercury_instances")
CONFIG_FILE = os.path.join(MINECRAFT_DIR, "mercury_config.json")

# Ensure base folders exist
os.makedirs(INSTANCES_DIR, exist_ok=True)

# -------------------------
# Mercury Launcher Class
# -------------------------
class MercuryLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Mercury Launcher - Multi-Instance")
        self.root.geometry("800x550") # Wider for the dashboard look
        self.root.configure(bg="#1e1e1e")

        # Data
        self.instances = self.load_config()
        self.current_instance_name = None
        self.available_versions = []

        # Styles
        self.setup_styles()

        # --- UI Layout (Paned Window) ---
        # Split into Left (List) and Right (Details)
        self.main_pane = tk.PanedWindow(root, orient="horizontal", bg="#1e1e1e", sashwidth=4)
        self.main_pane.pack(fill="both", expand=True, padx=10, pady=10)

        # === LEFT PANEL: Instance List ===
        self.left_frame = tk.Frame(self.main_pane, bg="#252526")
        self.main_pane.add(self.left_frame, minsize=200, width=250)

        # Title
        tk.Label(self.left_frame, text="My Instances", bg="#252526", fg="#00d1ff", font=("Segoe UI", 14, "bold")).pack(pady=10)

        # Listbox with Scrollbar
        list_frame = tk.Frame(self.left_frame, bg="#252526")
        list_frame.pack(fill="both", expand=True, padx=10)

        self.instance_listbox = tk.Listbox(list_frame, bg="#303031", fg="white", borderwidth=0, highlightthickness=0, selectbackground="#007acc", font=("Segoe UI", 11))
        self.instance_listbox.pack(side="left", fill="both", expand=True)
        self.instance_listbox.bind("<<ListboxSelect>>", self.on_instance_select)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.instance_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.instance_listbox.config(yscrollcommand=scrollbar.set)

        # Bottom Buttons (Add/Remove)
        btn_frame = tk.Frame(self.left_frame, bg="#252526")
        btn_frame.pack(fill="x", pady=10, padx=10)

        ttk.Button(btn_frame, text="+ New Instance", command=self.add_instance).pack(side="left", fill="x", expand=True, padx=(0,5))
        ttk.Button(btn_frame, text="- Delete", command=self.delete_instance).pack(side="right", fill="x", expand=True, padx=(5,0))


        # === RIGHT PANEL: Details & Settings ===
        self.right_frame = tk.Frame(self.main_pane, bg="#1e1e1e")
        self.main_pane.add(self.right_frame, minsize=400)

        # Header
        self.header_label = tk.Label(self.right_frame, text="Select an Instance", bg="#1e1e1e", fg="white", font=("Segoe UI", 20, "bold"))
        self.header_label.pack(pady=(20, 20))

        # Settings Container
        self.settings_frame = tk.Frame(self.right_frame, bg="#1e1e1e")
        self.settings_frame.pack(fill="x", padx=40)

        # Username
        ttk.Label(self.settings_frame, text="Username").pack(anchor="w", pady=(0,2))
        self.username_entry = ttk.Entry(self.settings_frame)
        self.username_entry.pack(fill="x", pady=(0, 15))

        # Version
        ttk.Label(self.settings_frame, text="Minecraft Version").pack(anchor="w", pady=(0,2))
        self.version_combo = ttk.Combobox(self.settings_frame, state="readonly")
        self.version_combo.pack(fill="x", pady=(0, 15))

        # Mod Loader
        ttk.Label(self.settings_frame, text="Mod Loader").pack(anchor="w", pady=(0,2))
        self.loader_combo = ttk.Combobox(self.settings_frame, state="readonly", values=["Vanilla", "Fabric", "Forge"])
        self.loader_combo.pack(fill="x", pady=(0, 15))

        # Management Buttons
        self.mods_btn = ttk.Button(self.settings_frame, text="📂 Open Mods Folder", command=self.open_mods_folder)
        self.mods_btn.pack(fill="x", pady=(0, 20))

        # Status & Launch
        self.status_label = tk.Label(self.right_frame, text="", bg="#1e1e1e", fg="#aaaaaa", font=("Segoe UI", 9))
        self.status_label.pack(side="bottom", pady=(0, 10))

        self.launch_btn = ttk.Button(self.right_frame, text="Launch Instance", command=self.start_launch_thread)
        self.launch_btn.pack(side="bottom", pady=(0, 10), ipadx=30, ipady=10)

        # Initial Load
        self.refresh_instance_list()

        # Start background version fetch
        threading.Thread(target=self.load_versions_bg, daemon=True).start()

    # -------------------------
    # Styling
    # -------------------------
    def setup_styles(self):
        self.style = ttk.Style(self.root)
        self.style.theme_use("clam")
        self.style.configure("TLabel", background="#1e1e1e", foreground="#ffffff", font=("Segoe UI", 10))
        self.style.configure("TButton", font=("Segoe UI", 10, "bold"), foreground="#ffffff", background="#3a3a3a", borderwidth=0)
        self.style.map("TButton", background=[("active", "#505050")])
        self.style.configure("TEntry", fieldbackground="#3a3a3a", foreground="#ffffff", insertcolor="white")
        self.style.configure("TCombobox", fieldbackground="#3a3a3a", background="#1e1e1e", foreground="#ffffff", arrowcolor="white")

    # -------------------------
    # Data Management
    # -------------------------
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_config(self):
        # Save current inputs to the current instance in memory before writing to file
        if self.current_instance_name:
            self.instances[self.current_instance_name] = {
                "username": self.username_entry.get(),
                "version": self.version_combo.get(),
                "loader": self.loader_combo.get()
            }

        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.instances, f, indent=4)

    def load_versions_bg(self):
        try:
            versions = minecraft_launcher_lib.utils.get_version_list()
            self.available_versions = [v["id"] for v in versions if v["type"] == "release"]
            self.root.after(0, lambda: self.version_combo.configure(values=self.available_versions[:50]))
        except:
            pass

    # -------------------------
    # GUI Logic
    # -------------------------
    def refresh_instance_list(self):
        self.instance_listbox.delete(0, tk.END)
        for name in self.instances:
            self.instance_listbox.insert(tk.END, name)

    def add_instance(self):
        name = simpledialog.askstring("New Instance", "Enter name for new instance:")
        if name:
            if name in self.instances:
                messagebox.showerror("Error", "Instance already exists!")
                return

            # Create default data
            self.instances[name] = {
                "username": "",
                "version": self.available_versions[0] if self.available_versions else "1.20.4",
                "loader": "Vanilla"
            }
            self.save_config()
            self.refresh_instance_list()

            # Select the new one
            idx = self.instance_listbox.get(0, tk.END).index(name)
            self.instance_listbox.selection_clear(0, tk.END)
            self.instance_listbox.selection_set(idx)
            self.on_instance_select(None)

    def delete_instance(self):
        sel = self.instance_listbox.curselection()
        if not sel: return
        name = self.instance_listbox.get(sel[0])

        if messagebox.askyesno("Delete", f"Are you sure you want to delete '{name}'?\nThis will remove its configs but keep the folder files."):
            del self.instances[name]
            self.save_config()
            self.refresh_instance_list()

            # Clear right panel
            self.current_instance_name = None
            self.header_label.config(text="Select an Instance")
            self.username_entry.delete(0, tk.END)
            self.version_combo.set('')
            self.loader_combo.set('')

    def on_instance_select(self, event):
        # 1. Save previous if exists
        self.save_config()

        # 2. Load new
        sel = self.instance_listbox.curselection()
        if not sel: return

        name = self.instance_listbox.get(sel[0])
        self.current_instance_name = name
        data = self.instances[name]

        self.header_label.config(text=name)

        self.username_entry.delete(0, tk.END)
        self.username_entry.insert(0, data.get("username", ""))

        self.version_combo.set(data.get("version", ""))
        self.loader_combo.set(data.get("loader", "Vanilla"))

    def open_mods_folder(self):
        if not self.current_instance_name: return

        instance_path = os.path.join(INSTANCES_DIR, self.current_instance_name)
        mods_path = os.path.join(instance_path, "mods")
        os.makedirs(mods_path, exist_ok=True)

        # Open folder based on OS
        if sys.platform == "win32":
            os.startfile(mods_path)
        else:
            subprocess.Popen(["xdg-open", mods_path])

    # -------------------------
    # Launch Logic
    # -------------------------
    def start_launch_thread(self):
        if not self.current_instance_name:
            messagebox.showwarning("Warning", "Please select an instance first.")
            return

        self.save_config() # Save changes before launch
        self.launch_btn.config(state="disabled")
        threading.Thread(target=self.launch, daemon=True).start()

    def find_internal_java(self):
        runtime_dir = os.path.join(MINECRAFT_DIR, "runtime")
        found_java = None
        if os.path.exists(runtime_dir):
            for root, dirs, files in os.walk(runtime_dir):
                if "java" in files:
                    full_path = os.path.join(root, "java")
                    if sys.platform != "win32":
                        try: os.chmod(full_path, 0o755)
                        except: pass
                    if "bin" in root:
                        found_java = full_path
                        break
        return found_java if found_java else "java"

    def update_status(self, text, error=False):
        self.root.after(0, lambda: self.status_label.config(text=text, fg="#ff5555" if error else "#aaaaaa"))
        if error:
            self.root.after(0, lambda: messagebox.showerror("Launch Error", text))

        if error or "Launching" in text:
             self.root.after(0, lambda: self.launch_btn.config(state="normal"))

    def launch(self):
        try:
            # Get Data
            data = self.instances[self.current_instance_name]
            username = data["username"]
            version = data["version"]
            loader = data["loader"]

            # Setup Paths
            instance_dir = os.path.join(INSTANCES_DIR, self.current_instance_name)
            os.makedirs(instance_dir, exist_ok=True)

            if not username or not version:
                self.update_status("Error: Username and Version required", error=True)
                return

            def set_status(text):
                self.root.after(0, lambda: self.status_label.config(text=text))

            # 1. Install Vanilla
            set_status(f"Verifying Vanilla {version}...")
            minecraft_launcher_lib.install.install_minecraft_version(
                version=version,
                minecraft_directory=MINECRAFT_DIR,
                callback={'setStatus': set_status}
            )

            # 2. Java Setup
            java_path = self.find_internal_java()
            if java_path != "java":
                os.environ["PATH"] = os.path.dirname(java_path) + os.pathsep + os.environ["PATH"]

            # 3. Mod Loader
            launch_id = version

            if loader == "Fabric":
                set_status("Installing Fabric...")
                launch_id = minecraft_launcher_lib.fabric.install_fabric(version, MINECRAFT_DIR)
                if not launch_id:
                     # Fallback search
                     for v in minecraft_launcher_lib.utils.get_installed_versions(MINECRAFT_DIR):
                        if "fabric" in v["id"] and version in v["id"]:
                            launch_id = v["id"]
                            break

            elif loader == "Forge":
                set_status("Finding Forge...")
                forge_ver = minecraft_launcher_lib.forge.find_forge_version(version)
                if not forge_ver: raise Exception("Forge not found")

                set_status(f"Installing Forge {forge_ver}...")
                minecraft_launcher_lib.forge.install_forge_version(forge_ver, MINECRAFT_DIR, java=java_path)
                launch_id = forge_ver

            # 4. Launch
            set_status(f"Launching {launch_id}...")

            options = {
                "username": username,
                "uuid": "0",
                "token": "0",
                "launcherName": "Mercury",
                "gameDir": instance_dir, # This creates the isolation!
                "executablePath": java_path,
            }

            cmd = minecraft_launcher_lib.command.get_minecraft_command(launch_id, MINECRAFT_DIR, options)
            subprocess.Popen(cmd)

            # Close launcher on success
            self.root.after(0, self.root.destroy)

        except Exception as e:
            print(e)
            self.update_status(str(e), error=True)

if __name__ == "__main__":
    root = tk.Tk()
    app = MercuryLauncher(root)
    root.mainloop()
