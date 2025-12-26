import customtkinter as ctk
from tkinter import filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES
import yt_dlp
import threading
import os, sys, shutil, re
import unicodedata

# ================= CONFIG =================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

BG = "#0b0b0b"
CARD = "#121212"
BORDER = "#1f1f1f"
TEXT = "#ffffff"
SUBTEXT = "#b3b3b3"
ACCENT = "#1db954"

DOWNLOADED_DB = "downloaded_ids.txt"

MAX_FILENAME_LEN = 120   # prevents Windows path crash

# ================= PATH FIX =================
def resource_path(relative):
    try:
        base = sys._MEIPASS
    except Exception:
        base = os.path.abspath(".")
    return os.path.join(base, relative)

FFMPEG_BIN = os.path.join(resource_path("ffmpeg"), "ffmpeg.exe")

# ================= DOWNLOADED DB =================
def load_downloaded_ids():
    if not os.path.exists(DOWNLOADED_DB):
        return set()
    with open(DOWNLOADED_DB, "r", encoding="utf-8") as f:
        return set(x.strip() for x in f if x.strip())

def save_downloaded_id(video_id):
    with open(DOWNLOADED_DB, "a", encoding="utf-8") as f:
        f.write(video_id + "\n")

# ================= FILENAME SANITIZERS =================
JUNK_WORDS = [
    "official video", "lyric video", "lyrics",
    "video song", "audio song", "full song",
    "hd", "4k", "8k", "remastered",
    "promo", "teaser", "trailer",
    "movie version", "song version"
]

def remove_emojis(text):
    return "".join(c for c in text if not unicodedata.category(c).startswith("So"))

def clean_title(name):

    name = remove_emojis(name)
    name = name.lower()

    for junk in JUNK_WORDS:
        name = name.replace(junk, "")

    name = re.sub(r"\s*\|\s*", " - ", name)
    name = re.sub(r"\s{2,}", " ", name)

    name = name.strip().title()

    return name


def safe_filename(name):

    name = clean_title(name)

    for ch in '<>:"/\\|?*':
        name = name.replace(ch, "")

    if len(name) > MAX_FILENAME_LEN:
        name = name[:MAX_FILENAME_LEN].rstrip()

    return name.strip()


# ================= APP =================
class App(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()

        self.urls = []
        self.index = 0
        self.download_path = ""

        self.title("YouTube → High Quality MP3")
        self.geometry("960x720")
        self.resizable(False, False)
        self.configure(bg=BG)

        self.build_ui()

    # ================= UI =================
    def build_ui(self):
        ctk.CTkLabel(
            self,
            text="YouTube → High Quality MP3",
            font=("Segoe UI", 22, "bold"),
            text_color=TEXT
        ).pack(pady=16)

        card_urls = self.card()
        ctk.CTkLabel(card_urls, text="Paste or Drag YouTube URLs", text_color=SUBTEXT).pack(anchor="w", padx=16)

        self.url_box = ctk.CTkTextbox(card_urls, height=100, fg_color=CARD, border_color=BORDER)
        self.url_box.pack(fill="x", padx=16, pady=10)
        self.url_box.drop_target_register(DND_FILES)
        self.url_box.dnd_bind("<<Drop>>", self.drop_urls)

        card_ctrl = self.card()
        ctk.CTkButton(card_ctrl, text="Select Download Folder", command=self.select_folder).pack(pady=6)

        self.folder_label = ctk.CTkLabel(card_ctrl, text="No folder selected", text_color=SUBTEXT)
        self.folder_label.pack()

        self.progress = ctk.CTkProgressBar(card_ctrl, fg_color=BORDER, progress_color=ACCENT)
        self.progress.pack(fill="x", padx=20, pady=10)
        self.progress.set(0)

        self.size_label = ctk.CTkLabel(card_ctrl, text="0 MB / 0 MB", text_color=SUBTEXT)
        self.size_label.pack()

        self.speed_label = ctk.CTkLabel(card_ctrl, text="Speed: calculating...", text_color=SUBTEXT)
        self.speed_label.pack()

        self.status_label = ctk.CTkLabel(card_ctrl, text="", text_color=SUBTEXT)
        self.status_label.pack(pady=4)

        ctk.CTkButton(self, text="Download MP3", height=42, command=self.start_download).pack(pady=12)

        card_files = self.card()
        ctk.CTkLabel(card_files, text="Downloaded Files (Double-click to Play)", text_color=SUBTEXT).pack(anchor="w", padx=16)

        self.files_box = ctk.CTkTextbox(card_files, height=160, fg_color=CARD, border_color=BORDER)
        self.files_box.pack(fill="x", padx=16, pady=10)
        self.files_box.bind("<Double-Button-1>", self.play_audio)

    def card(self):
        frame = ctk.CTkFrame(self, fg_color=CARD, border_color=BORDER, border_width=1, corner_radius=18)
        frame.pack(fill="x", padx=20, pady=10)
        return frame

    # ================= HELPERS =================
    def drop_urls(self, e):
        self.url_box.insert("end", e.data.replace("{", "").replace("}", "") + "\n")

    def select_folder(self):
        p = filedialog.askdirectory()
        if p:
            self.download_path = p
            self.folder_label.configure(text=p)

    # ================= PROGRESS =================
    def progress_hook(self, d):
        if d.get("status") == "downloading":
            downloaded = d.get("downloaded_bytes") or 0
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            speed = d.get("speed") or 0

            self.after(0, lambda: self.update_progress(downloaded, total, speed))

    def update_progress(self, downloaded, total, speed):
        if total > 0:
            self.progress.set(downloaded / total)
            self.size_label.configure(text=f"{downloaded/1024/1024:.2f} / {total/1024/1024:.2f} MB")
        else:
            self.progress.set(0)
            self.size_label.configure(text="Preparing...")

        self.speed_label.configure(
            text=f"Speed: {speed/1024:.2f} KB/s" if speed > 0 else "Speed: calculating..."
        )

        self.status_label.configure(text="Downloading...")

    # ================= DOWNLOAD =================
    def start_download(self):
        self.urls = [
            u.strip() for u in self.url_box.get("0.0","end").splitlines()
            if u.startswith("http")
        ]

        if not self.urls or not self.download_path:
            messagebox.showerror("Error", "Enter URLs and select folder")
            return

        self.index = 0
        self.files_box.delete("0.0","end")

        threading.Thread(target=self.download_next, daemon=True).start()

    def download_next(self):

        if self.index >= len(self.urls):
            self.after(0, lambda: messagebox.showinfo("Done", "All downloads completed"))
            return

        url = self.urls[self.index]
        downloaded_ids = load_downloaded_ids()

        temp_dir = os.path.join(self.download_path, ".temp")
        os.makedirs(temp_dir, exist_ok=True)

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(temp_dir, "%(id)s.%(ext)s"),

            "restrictfilenames": True,
            "nopart": True,
            "continuedl": False,

            "ffmpeg_location": FFMPEG_BIN,
            "progress_hooks": [self.progress_hook],

            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "0",
            }],

            "quiet": True,
            "no_warnings": True
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:

                info = ydl.extract_info(url, download=False)
                vid = info["id"]

                if vid in downloaded_ids:
                    self.after(0, lambda: self.status_label.configure(text="Already downloaded ✔"))
                    self.index += 1
                    self.download_next()
                    return

                info = ydl.extract_info(url, download=True)
                save_downloaded_id(vid)

                # Locate generated temp file
                temp_mp3 = None
                for f in os.listdir(temp_dir):
                    if f.startswith(vid) and f.endswith(".mp3"):
                        temp_mp3 = os.path.join(temp_dir, f)
                        break

                if not temp_mp3:
                    raise Exception("Downloaded audio file not found")

                # Final clean name
                safe_title = safe_filename(info["title"])
                final_mp3 = os.path.join(self.download_path, f"{safe_title}.mp3")

                # Rename inside temp first
                safe_temp = os.path.join(temp_dir, f"{safe_title}.mp3")
                os.replace(temp_mp3, safe_temp)

                # Move to output folder
                shutil.move(safe_temp, final_mp3)

            self.after(0, lambda: self.files_box.insert("end", final_mp3 + "\n"))

        except Exception as e:
            self.after(0, messagebox.showerror, "Download Error", str(e))

        self.index += 1
        self.download_next()

    # ================= PLAY =================
    def play_audio(self, _):
        p = self.files_box.get("insert linestart","insert lineend").strip()
        if os.path.exists(p):
            os.startfile(p)

# ================= RUN =================
if __name__ == "__main__":
    App().mainloop()
