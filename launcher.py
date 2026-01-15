import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
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
        self.root.geometry("480x450")
        self.root.resizable(False, False)

        tk.Label(root, text="Mercury Launcher", font=("Arial", 16, "bold")).pack(pady=10)

        # Username
        tk.Label(root, text="Username").pack()
        self.username_entry = tk.Entry(root)
        self.username_entry.pack()

        # Instance Name
        tk.Label(root, text="Instance Name").pack(pady=(10, 0))
        self.instance_entry = tk.Entry(root)
        self.instance_entry.insert(0, "default")
        self.instance_entry.pack()

        # Version Selector
        tk.Label(root, text="Minecraft Version").pack(pady=(10, 0))
        self.version_var = tk.StringVar()
        self.version_menu = tk.OptionMenu(
            root, self.version_var, *self.get_versions()
        )
        self.version_menu.pack()

        # Skin Settings
        tk.Label(root, text="Skin (optional)").pack(pady=(10, 0))
        self.skin_frame = tk.Frame(root)
        self.skin_frame.pack()
        self.skin_path_var = tk.StringVar()
        tk.Entry(self.skin_frame, textvariable=self.skin_path_var, width=35).pack(side=tk.LEFT)
        tk.Button(self.skin_frame, text="Browse", command=self.browse_skin).pack(side=tk.LEFT, padx=5)
        self.skin_preview_label = tk.Label(root)
        self.skin_preview_label.pack(pady=5)

        # Progress Bar
        tk.Label(root, text="Download Progress").pack(pady=(10, 0))
        self.progress_var = tk.IntVar()
        self.progress_bar = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate", variable=self.progress_var)
        self.progress_bar.pack(pady=5)

        # Launch Button
        tk.Button(root, text="Download & Launch", height=2, command=self.launch).pack(pady=15)

    # -------------------------
    # Version list
    # -------------------------
    def get_versions(self):
        try:
            versions = minecraft_launcher_lib.utils.get_version_list()
            release_versions = [v["id"] for v in versions if v["type"] == "release"]
            if release_versions:
                self.version_var.set(release_versions[0])
            return release_versions[:30]  # limit UI clutter
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch versions:\n{e}")
            return []

    # -------------------------
    # Skin browser
    # -------------------------
    def browse_skin(self):
        path = filedialog.askopenfilename(
            title="Select Skin PNG",
            filetypes=[("PNG Images", "*.png")]
        )
        if path:
            self.skin_path_var.set(path)
            self.update_skin_preview(path)

    def update_skin_preview(self, path):
        try:
            img = Image.open(path).resize((64, 64))
            self.skin_image = ImageTk.PhotoImage(img)
            self.skin_preview_label.config(image=self.skin_image)
        except Exception as e:
            messagebox.showerror("Skin Error", f"Cannot load skin:\n{e}")

    # -------------------------
    # Launch Minecraft
    # -------------------------
    def launch(self):
        username = self.username_entry.get().strip()
        version = self.version_var.get()
        instance_name = self.instance_entry.get().strip() or "default"
        instance_dir = os.path.join(MINECRAFT_DIR, "instances", instance_name)
        os.makedirs(instance_dir, exist_ok=True)

        if not username:
            messagebox.showerror("Error", "Please enter a username")
            return

        if not version:
            messagebox.showerror("Error", "Please select a version")
            return

        skin_path = self.skin_path_var.get()
        if skin_path and not os.path.isfile(skin_path):
            messagebox.showerror("Error", "Skin file not found")
            return

        try:
            messagebox.showinfo(
                "Downloading",
                "Minecraft will download if needed.\nThis may take a few minutes."
            )

            # Download with progress callback
            def progress_callback(current, total):
                self.progress_var.set(int(current / total * 100))
                self.root.update_idletasks()

            minecraft_launcher_lib.install.install_minecraft_version(version, MINECRAFT_DIR)


            options = {
                "username": username,
                "uuid": "0",
                "token": "0",
                "launcherName": "MercuryLauncher",
                "launcherVersion": "1.0",
                "gameDir": instance_dir,
            }

            command = minecraft_launcher_lib.command.get_minecraft_command(
                version, MINECRAFT_DIR, options
            )

            # Optional: copy skin file into temporary location if provided
            if skin_path:
                assets_skin_dir = os.path.join(instance_dir, "skins")
                os.makedirs(assets_skin_dir, exist_ok=True)
                import shutil
                shutil.copy(skin_path, os.path.join(assets_skin_dir, "player.png"))

            subprocess.Popen(command)
            self.root.destroy()

        except Exception as e:
            messagebox.showerror("Launch Error", str(e))


# -------------------------
# Run launcher
# -------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = MercuryLauncher(root)
    root.mainloop()
