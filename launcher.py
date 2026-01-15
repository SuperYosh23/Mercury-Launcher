import os
import sys
import subprocess
import threading
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import minecraft_launcher_lib
import shutil
import zipfile
import requests

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
        self.root.title("Mercury Launcher - Force Path Fix")
        self.root.geometry("850x600")
        self.root.configure(bg="#1e1e1e")

        # Data
        self.instances = self.load_config()
        self.current_instance_name = None
        self.available_versions = []

        # Styles
        self.setup_styles()

        # --- UI Layout ---
        self.main_pane = tk.PanedWindow(root, orient="horizontal", bg="#1e1e1e", sashwidth=4)
        self.main_pane.pack(fill="both", expand=True, padx=10, pady=10)

        # === LEFT PANEL ===
        self.left_frame = tk.Frame(self.main_pane, bg="#252526")
        self.main_pane.add(self.left_frame, minsize=220, width=260)

        tk.Label(self.left_frame, text="My Instances", bg="#252526", fg="#00d1ff", font=("Segoe UI", 14, "bold")).pack(pady=10)

        list_frame = tk.Frame(self.left_frame, bg="#252526")
        list_frame.pack(fill="both", expand=True, padx=10)

        self.instance_listbox = tk.Listbox(list_frame, bg="#303031", fg="white", borderwidth=0, highlightthickness=0, selectbackground="#007acc", font=("Segoe UI", 11))
        self.instance_listbox.pack(side="left", fill="both", expand=True)
        self.instance_listbox.bind("<<ListboxSelect>>", self.on_instance_select)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.instance_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.instance_listbox.config(yscrollcommand=scrollbar.set)

        btn_frame = tk.Frame(self.left_frame, bg="#252526")
        btn_frame.pack(fill="x", pady=10, padx=10)

        ttk.Button(btn_frame, text="+ New", command=self.add_instance).pack(side="left", fill="x", expand=True, padx=(0,2))
        ttk.Button(btn_frame, text="📥 Import", command=self.import_modpack).pack(side="left", fill="x", expand=True, padx=2)
        ttk.Button(btn_frame, text="- Del", command=self.delete_instance).pack(side="left", fill="x", expand=True, padx=(2,0))

        # === RIGHT PANEL ===
        self.right_frame = tk.Frame(self.main_pane, bg="#1e1e1e")
        self.main_pane.add(self.right_frame, minsize=450)

        self.header_label = tk.Label(self.right_frame, text="Select an Instance", bg="#1e1e1e", fg="white", font=("Segoe UI", 20, "bold"))
        self.header_label.pack(pady=(20, 20))

        self.settings_frame = tk.Frame(self.right_frame, bg="#1e1e1e")
        self.settings_frame.pack(fill="x", padx=40)

        ttk.Label(self.settings_frame, text="Username").pack(anchor="w", pady=(0,2))
        self.username_entry = ttk.Entry(self.settings_frame)
        self.username_entry.pack(fill="x", pady=(0, 15))

        ttk.Label(self.settings_frame, text="Minecraft Version").pack(anchor="w", pady=(0,2))
        self.version_combo = ttk.Combobox(self.settings_frame, state="readonly")
        self.version_combo.pack(fill="x", pady=(0, 15))

        ttk.Label(self.settings_frame, text="Mod Loader").pack(anchor="w", pady=(0,2))
        self.loader_combo = ttk.Combobox(self.settings_frame, state="readonly", values=["Vanilla", "Fabric", "Forge", "Quilt"])
        self.loader_combo.pack(fill="x", pady=(0, 15))

        self.mods_btn = ttk.Button(self.settings_frame, text="📂 Open Mods Folder", command=self.open_mods_folder)
        self.mods_btn.pack(fill="x", pady=(0, 20))

        self.status_label = tk.Label(self.right_frame, text="", bg="#1e1e1e", fg="#aaaaaa", font=("Segoe UI", 9))
        self.status_label.pack(side="bottom", pady=(0, 10))

        self.launch_btn = ttk.Button(self.right_frame, text="Launch Instance", command=self.start_launch_thread)
        self.launch_btn.pack(side="bottom", pady=(0, 10), ipadx=30, ipady=10)

        self.refresh_instance_list()
        threading.Thread(target=self.load_versions_bg, daemon=True).start()

    # -------------------------
    # Utilities
    # -------------------------
    def setup_styles(self):
        self.style = ttk.Style(self.root)
        self.style.theme_use("clam")
        self.style.configure("TLabel", background="#1e1e1e", foreground="#ffffff", font=("Segoe UI", 10))
        self.style.configure("TButton", font=("Segoe UI", 10, "bold"), foreground="#ffffff", background="#3a3a3a", borderwidth=0)
        self.style.map("TButton", background=[("active", "#505050")])
        self.style.configure("TEntry", fieldbackground="#3a3a3a", foreground="#ffffff", insertcolor="white")
        self.style.configure("TCombobox", fieldbackground="#3a3a3a", background="#1e1e1e", foreground="#ffffff", arrowcolor="white")
        self.style.configure("Horizontal.TProgressbar", background="#00d1ff", troughcolor="#3a3a3a", borderwidth=0)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_config(self):
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
    # Modpack & Import
    # -------------------------
    def import_modpack(self):
        path = filedialog.askopenfilename(title="Select Modpack", filetypes=[("Modrinth Pack", "*.mrpack"), ("Zip File", "*.zip")])
        if not path: return

        self.progress_win = tk.Toplevel(self.root)
        self.progress_win.title("Installing Modpack")
        self.progress_win.geometry("400x150")
        self.progress_win.config(bg="#1e1e1e")

        self.prog_label = tk.Label(self.progress_win, text="Analyzing file...", bg="#1e1e1e", fg="white", wraplength=350)
        self.prog_label.pack(pady=20)

        self.progress_bar = ttk.Progressbar(self.progress_win, mode='indeterminate')
        self.progress_bar.pack(fill="x", padx=20, pady=10)
        self.progress_bar.start()

        threading.Thread(target=self.process_modpack, args=(path,), daemon=True).start()

    def process_modpack(self, path):
        try:
            with zipfile.ZipFile(path, 'r') as z:
                if "modrinth.index.json" in z.namelist():
                    self.install_mrpack(z)
                else:
                    self.install_basic_zip(z, path)

            self.root.after(0, self.progress_win.destroy)
            self.root.after(0, self.refresh_instance_list)
            self.root.after(0, lambda: messagebox.showinfo("Success", "Modpack installed!"))
        except Exception as e:
            self.root.after(0, self.progress_win.destroy)
            self.root.after(0, lambda: messagebox.showerror("Import Error", str(e)))

    def install_mrpack(self, zip_ref):
        index_data = json.loads(zip_ref.read("modrinth.index.json"))
        pack_name = index_data.get("name", "Imported Modpack")

        base_name = pack_name
        counter = 1
        while pack_name in self.instances:
            pack_name = f"{base_name} ({counter})"
            counter += 1

        self.root.after(0, lambda: self.prog_label.config(text=f"Creating instance: {pack_name}"))

        deps = index_data["dependencies"]
        loader_type = "Fabric" if "fabric-loader" in deps else "Forge" if "forge" in deps else "Quilt" if "quilt-loader" in deps else "Vanilla"

        self.instances[pack_name] = {
            "username": "",
            "version": deps["minecraft"],
            "loader": loader_type
        }
        self.save_config()

        instance_path = os.path.join(INSTANCES_DIR, pack_name)
        os.makedirs(instance_path, exist_ok=True)

        files = index_data.get("files", [])
        total = len(files)

        for i, file_obj in enumerate(files):
            env = file_obj.get("env", {})
            if env.get("client") == "unsupported": continue

            file_path = file_obj["path"]
            download_url = file_obj["downloads"][0]

            self.root.after(0, lambda t=f"Downloading mod {i+1}/{total}": self.prog_label.config(text=t))

            full_path = os.path.join(instance_path, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            resp = requests.get(download_url)
            if resp.status_code == 200:
                with open(full_path, "wb") as f:
                    f.write(resp.content)

        # Overrides
        for file in zip_ref.namelist():
            if file.startswith("overrides/"):
                target_path = os.path.join(instance_path, file.replace("overrides/", "", 1))
                if file.endswith("/"): os.makedirs(target_path, exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    with open(target_path, "wb") as f:
                        f.write(zip_ref.read(file))

    def install_basic_zip(self, zip_ref, original_path):
        pack_name = os.path.splitext(os.path.basename(original_path))[0]
        while pack_name in self.instances: pack_name += "_copy"

        self.root.after(0, lambda: self.prog_label.config(text="Extracting zip..."))

        self.instances[pack_name] = {"username": "", "version": "1.20.4", "loader": "Vanilla"}
        self.save_config()

        instance_path = os.path.join(INSTANCES_DIR, pack_name)
        os.makedirs(instance_path, exist_ok=True)
        zip_ref.extractall(instance_path)

        # Fix nested folders
        items = os.listdir(instance_path)
        if len(items) == 1 and os.path.isdir(os.path.join(instance_path, items[0])):
            nested_folder = os.path.join(instance_path, items[0])
            self.root.after(0, lambda: self.prog_label.config(text="Fixing folder structure..."))
            for item in os.listdir(nested_folder):
                shutil.move(os.path.join(nested_folder, item), instance_path)
            os.rmdir(nested_folder)

    # -------------------------
    # Interactions
    # -------------------------
    def refresh_instance_list(self):
        self.instance_listbox.delete(0, tk.END)
        for name in self.instances:
            self.instance_listbox.insert(tk.END, name)

    def add_instance(self):
        name = simpledialog.askstring("New Instance", "Enter name:")
        if name:
            if name in self.instances: return
            self.instances[name] = {"username": "", "version": "1.20.4", "loader": "Vanilla"}
            self.save_config()
            self.refresh_instance_list()

    def delete_instance(self):
        sel = self.instance_listbox.curselection()
        if not sel: return
        name = self.instance_listbox.get(sel[0])
        if messagebox.askyesno("Delete", f"Delete '{name}'?"):
            del self.instances[name]
            self.save_config()
            self.refresh_instance_list()
            self.current_instance_name = None
            self.header_label.config(text="Select an Instance")

    def on_instance_select(self, event):
        self.save_config()
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
        mods_path = os.path.join(INSTANCES_DIR, self.current_instance_name, "mods")
        os.makedirs(mods_path, exist_ok=True)
        if sys.platform == "win32": os.startfile(mods_path)
        else: subprocess.Popen(["xdg-open", mods_path])

    # -------------------------
    # Launch Logic
    # -------------------------
    def start_launch_thread(self):
        if not self.current_instance_name: return
        self.save_config()
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

    def launch(self):
        try:
            data = self.instances[self.current_instance_name]
            username = data["username"]
            version = data["version"]
            loader = data["loader"]
            instance_dir = os.path.abspath(os.path.join(INSTANCES_DIR, self.current_instance_name))
            os.makedirs(instance_dir, exist_ok=True)

            # --- DEBUG: CHECK MODS ---
            mods_dir = os.path.join(instance_dir, "mods")
            if os.path.exists(mods_dir):
                files = os.listdir(mods_dir)
                jar_files = [f for f in files if f.endswith(".jar")]
                print(f"DEBUG: Found {len(jar_files)} .jar files in {mods_dir}")
                print(f"DEBUG: First 3 files: {jar_files[:3]}")

                for f in files:
                    if f.endswith(".jar.disabled"):
                        os.rename(os.path.join(mods_dir, f), os.path.join(mods_dir, f.replace(".disabled", "")))

            if not username or not version: raise Exception("Username/Version missing")

            def set_status(text):
                self.root.after(0, lambda: self.status_label.config(text=text))

            # 1. Verify/Install Vanilla
            set_status(f"Verifying {version}...")
            minecraft_launcher_lib.install.install_minecraft_version(version, MINECRAFT_DIR, callback={'setStatus': set_status})

            # 2. Setup Java
            java_path = self.find_internal_java()
            if java_path != "java":
                os.environ["PATH"] = os.path.dirname(java_path) + os.pathsep + os.environ["PATH"]

            # 3. Setup Loader
            launch_id = version
            if loader == "Fabric":
                set_status("Installing Fabric...")
                launch_id = minecraft_launcher_lib.fabric.install_fabric(version, MINECRAFT_DIR)
                if not launch_id:
                     for v in minecraft_launcher_lib.utils.get_installed_versions(MINECRAFT_DIR):
                        if "fabric" in v["id"] and version in v["id"]:
                            launch_id = v["id"]
                            break
            elif loader == "Forge":
                set_status("Installing Forge...")
                forge_ver = minecraft_launcher_lib.forge.find_forge_version(version)
                if not forge_ver: raise Exception("Forge not found")
                minecraft_launcher_lib.forge.install_forge_version(forge_ver, MINECRAFT_DIR, java=java_path)
                launch_id = forge_ver
            elif loader == "Quilt":
                set_status("Installing Quilt...")
                launch_id = minecraft_launcher_lib.quilt.install_quilt(version, MINECRAFT_DIR)

            # 4. Launch with ARGUMENT FORCING
            set_status(f"Launching {launch_id}...")

            jvm_args = [
                f"-Duser.dir={instance_dir}",
                f"-Dfabric.gameDir={instance_dir}",
                f"-Dminecraft.launcher.brand=mercury-launcher"
            ]

            options = {
                "username": username,
                "uuid": "0",
                "token": "0",
                "launcherName": "Mercury",
                "gameDir": instance_dir,
                "executablePath": java_path,
                "jvmArguments": jvm_args
            }

            cmd = minecraft_launcher_lib.command.get_minecraft_command(launch_id, MINECRAFT_DIR, options)

            # --- FORCE ARGUMENTS PATCH ---
            # This ensures that even if the library messes up, we forcefully inject the gameDir
            # into the actual game arguments (after the main class)

            # Find where the main class is (it's usually the first arg that doesn't start with -)
            # But simpler approach: append --gameDir to the end. Minecraft uses the last one provided.

            cmd.append("--gameDir")
            cmd.append(instance_dir)

            cmd.append("--assetsDir")
            cmd.append(os.path.join(MINECRAFT_DIR, "assets"))

            print(f"DEBUG: Final Command: {' '.join(cmd)}")

            subprocess.Popen(cmd, cwd=instance_dir)

            self.root.after(0, self.root.destroy)

        except Exception as e:
            print(e)
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.root.after(0, lambda: self.launch_btn.config(state="normal"))

if __name__ == "__main__":
    root = tk.Tk()
    app = MercuryLauncher(root)
    root.mainloop()
