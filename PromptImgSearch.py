# Auth: c-stev-en
import os
import sys
import time
import string
import threading
import subprocess
import warnings
import torch
import torch.nn.functional as F
import open_clip
from PIL import Image
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

warnings.filterwarnings("ignore", category=UserWarning)

IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.tiff'}

def get_drives():
    """Detect all available drives on Windows."""
    if os.name == 'nt':
        drives = sorted([f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")])
        # Ensure C: is checked first
        if "C:\\" in drives:
            drives.remove("C:\\")
            drives.insert(0, "C:\\")
        return drives
    else:
        # Fallback for non-Windows platforms
        return ["/"]


class PromptSearchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Prompt Image Search")
        self.root.geometry("600x600")
        self.root.resizable(False, False)

        self.drives = get_drives()
        self.model = None
        self.preprocess = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.setup_ui()

        # Load AI Model in background
        threading.Thread(target=self.load_model, daemon=True).start()

    def setup_ui(self):
        # Prompt Input
        tk.Label(self.root, text="Search Prompt:", font=("Arial", 12, "bold")).pack(pady=(10, 0))
        self.prompt_entry = tk.Entry(self.root, width=50, font=("Arial", 11))
        self.prompt_entry.pack(pady=5)

        # Location Selection
        tk.Label(self.root, text="Search Location:", font=("Arial", 10, "bold")).pack(pady=(10, 0))
        self.location_var = tk.StringVar(value="all_drives")
        self.location_var.trace("w", self.on_location_change)

        tk.Radiobutton(self.root, text="All drives", variable=self.location_var, value="all_drives").pack()

        # If user has multiple drives, offer Single Drive selection
        if len(self.drives) > 1:
            frame_single_drive = tk.Frame(self.root)
            frame_single_drive.pack()
            tk.Radiobutton(
                frame_single_drive,
                text="Single drive",
                variable=self.location_var,
                value="single_drive"
            ).pack(side="left")

            self.drive_combo = ttk.Combobox(
                frame_single_drive,
                values=self.drives,
                state="disabled",
                width=10
            )
            self.drive_combo.pack(side="left", padx=5)

            if self.drives:
                self.drive_combo.current(0)
        else:
            self.location_var.set("all_drives")

        tk.Radiobutton(
            self.root,
            text="Base folder",
            variable=self.location_var,
            value="base_folder"
        ).pack()

        # Search Button
        self.search_btn = tk.Button(
            self.root,
            text="Start Search",
            command=self.start_search,
            state="disabled",
            font=("Arial", 11, "bold"),
            bg="#4CAF50",
            fg="white"
        )
        self.search_btn.pack(pady=15)

        # Status Label
        self.status_var = tk.StringVar(value="Status: Initializing UI...")
        tk.Label(
            self.root,
            textvariable=self.status_var,
            font=("Arial", 9),
            fg="grey"
        ).pack()

        # Results Frame
        tk.Label(
            self.root,
            text="Top 10 Matches:",
            font=("Arial", 10, "bold")
        ).pack(pady=(10, 0))

        self.results_frame = tk.Frame(self.root)
        self.results_frame.pack(fill="both", expand=True, padx=20, pady=5)

    def on_location_change(self, *args):
        if hasattr(self, 'drive_combo'):
            if self.location_var.get() == "single_drive":
                self.drive_combo.config(state="readonly")
            else:
                self.drive_combo.config(state="disabled")

    def load_model(self):
        self.update_status("Status: Loading AI Model (ViT-B-32)...")
        try:
            self.model, _, self.preprocess = open_clip.create_model_and_transforms(
                "ViT-B-32",
                pretrained="openai"
            )
            self.model = self.model.to(self.device)
            self.model.eval()
            self.update_status("Status: Ready")
            self.root.after(0, lambda: self.search_btn.config(state="normal"))
        except Exception as e:
            self.update_status(f"Status: Model load failed - {e}")

    def update_status(self, msg):
        self.root.after(0, lambda: self.status_var.set(msg))

    def update_results_list(self, current_results):
        self.root.after(0, lambda: self._render_results(current_results))

    def _render_results(self, results):
        for widget in self.results_frame.winfo_children():
            widget.destroy()

        for i, (score, fname, fpath) in enumerate(results):
            text = f"{i+1}. {fname}  [Score: {score:.4f}]"
            lbl = tk.Label(
                self.results_frame,
                text=text,
                fg="blue",
                cursor="hand2",
                font=("Arial", 9, "underline")
            )
            lbl.pack(anchor="w", pady=2)
            lbl.bind("<Button-1>", lambda e, p=fpath: self.open_in_explorer(p))

    def open_in_explorer(self, path):
        if os.path.exists(path):
            if os.name == 'nt':
                subprocess.run(['explorer', '/select,', os.path.normpath(path)])
            elif sys.platform == 'darwin':
                subprocess.run(['open', '-R', path])
            else:
                subprocess.run(['xdg-open', os.path.dirname(path)])

    def process_file(self, filepath, prompt_vec):
        try:
            # Standard image processing
            image = Image.open(filepath).convert("RGB")

            img_tensor = self.preprocess(image).unsqueeze(0).to(self.device)
            with torch.no_grad():
                img_vec = self.model.encode_image(img_tensor)
                score = F.cosine_similarity(prompt_vec, img_vec).item()
                return score

        except Exception:
            # Silently skip files that aren't valid images or are unreadable
            pass

        return -1

    def start_search(self):
        prompt = self.prompt_entry.get().strip()
        if not prompt:
            messagebox.showwarning("Warning", "Please enter a search prompt.")
            return

        search_paths = []
        loc = self.location_var.get()

        if loc == "all_drives":
            search_paths = self.drives
        elif loc == "single_drive":
            search_paths = [self.drive_combo.get()]
        elif loc == "base_folder":
            folder = filedialog.askdirectory(title="Select Base Folder")
            if not folder:
                return
            search_paths = [folder]

        self.search_btn.config(state="disabled")
        self._render_results([])  # Clear old results

        threading.Thread(
            target=self.run_search,
            args=(prompt, search_paths),
            daemon=True
        ).start()

    def run_search(self, prompt, search_paths):
        text_tokens = open_clip.tokenize([prompt]).to(self.device)
        with torch.no_grad():
            prompt_vec = self.model.encode_text(text_tokens)

        top_results = []
        last_update_time = time.time()

        for base_path in search_paths:
            for root, dirs, files in os.walk(base_path):
                for f in files:
                    ext = os.path.splitext(f)[1].lower()

                    # Images only
                    if ext not in IMAGE_EXTS:
                        continue

                    full_path = os.path.join(root, f)

                    # Throttle UI updates to prevent GUI freeze
                    if time.time() - last_update_time > 0.1:
                        short_path = full_path if len(full_path) < 60 else "..." + full_path[-57:]
                        self.update_status(f"Scanning: {short_path}")
                        last_update_time = time.time()

                    score = self.process_file(full_path, prompt_vec)

                    if score > 0:
                        # Append and maintain only top 10 to save memory and time
                        if len(top_results) < 10 or score > top_results[-1][0]:
                            top_results.append((score, f, full_path))
                            top_results.sort(key=lambda x: x[0], reverse=True)
                            top_results = top_results[:10]
                            self.update_results_list(top_results)

        self.update_status("Status: Search Complete")
        self.root.after(0, lambda: self.search_btn.config(state="normal"))


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()

    # Pre-check CUDA requirement
    if not torch.cuda.is_available():
        messagebox.showerror(
            "Error",
            "Torch CUDA not installed.\nNVIDIA GPU and PyTorch for CUDA are required.\nExiting..."
        )
        sys.exit(1)

    root.deiconify()
    app = PromptSearchApp(root)
    root.mainloop()
