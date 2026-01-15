import os
import sys
import tkinter as tk
from tkinter import messagebox
import subprocess
import minecraft_launcher_lib


# -------------------------
# Cross-platform .minecraft path
# -------------------------
def get_minecraft_dir():
    if sys.platform.startswith("win"):
        return os.path.join(os.environ["APPDATA"], ".minecraft")
    else:
        return os.path.expanduser("~/.minecraft")


MINECRAFT_DIR = get_minecraft_dir()


# -------------------------
# Launcher UI
# -------------------------
class MercuryLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Mercury Launcher")
        self.root.geometry("420x300")
        self.root.resizable(False, False)

        tk.Label(root, text="Mercury Launcher", font=("Arial", 16, "bold")).pack(pady=10)

        tk.Label(root, text="Username").pack()
        self.username_entry = tk.Entry(root)
        self.username_entry.pack()

        tk.Label(root, text="Minecraft Version").pack(pady=(10, 0))
        self.version_var = tk.StringVar()
        self.version_menu = tk.OptionMenu(
            root, self.version_var, *self.get_versions()
        )
        self.version_menu.pack()

        tk.Button(
            root, text="Download & Launch", height=2, command=self.launch
        ).pack(pady=25)

    # -------------------------
    # Get available versions
    # -------------------------
    def get_versions(self):
        versions = minecraft_launcher_lib.utils.get_version_list()
        release_versions = [
            v["id"] for v in versions if v["type"] == "release"
        ]

        if release_versions:
            self.version_var.set(release_versions[0])

        return release_versions[:30]  # keep UI simple

    # -------------------------
    # Download + launch
    # -------------------------
    def launch(self):
        username = self.username_entry.get().strip()
        version = self.version_var.get()

        if not username:
            messagebox.showerror("Error", "Please enter a username")
            return

        try:
            messagebox.showinfo(
                "Downloading",
                "Minecraft will download if needed.\nThis may take a few minutes."
            )

            minecraft_launcher_lib.install.install_minecraft_version(
                version, MINECRAFT_DIR
            )

            options = {
                "username": username,
                "uuid": "0",
                "token": "0",
                "launcherName": "MercuryLauncher",
                "launcherVersion": "1.0",
            }

            command = minecraft_launcher_lib.command.get_minecraft_command(
                version, MINECRAFT_DIR, options
            )

            subprocess.Popen(command)
            self.root.destroy()

        except Exception as e:
            messagebox.showerror("Launch Error", str(e))


# -------------------------
# Run app
# -------------------------
root = tk.Tk()
app = MercuryLauncher(root)
root.mainloop()
