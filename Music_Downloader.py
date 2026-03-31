import customtkinter as ctk
from tkinterdnd2 import TkinterDnD, DND_FILES
import yt_dlp
import threading
import concurrent.futures
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
class App(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)

        self.urls = []
        self.download_path = ""
        self.is_cancelled = False
        self.active_downloads = {}

        self.title("Music Downloader")
        self.geometry("960x720")
        self.resizable(False, False)
        self.configure(bg=BG)

        self.build_ui()

    # ================= UI =================
    def build_ui(self):
        ctk.CTkLabel(
            self,
            text="Music Downloader",
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

        # Settings row
        settings_frame = ctk.CTkFrame(card_ctrl, fg_color="transparent")
        settings_frame.pack(fill="x", padx=16, pady=6)

        ctk.CTkLabel(settings_frame, text="Format:", text_color=SUBTEXT).pack(side="left", padx=(0,5))
        self.format_var = ctk.StringVar(value="mp3")
        self.format_menu = ctk.CTkOptionMenu(settings_frame, variable=self.format_var, values=["mp3", "m4a", "wav"], width=80)
        self.format_menu.pack(side="left")



        # Buttons row
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=12)

        self.btn_download = ctk.CTkButton(btn_frame, text="Download", height=42, command=self.start_download)
        self.btn_download.pack(side="left", padx=10)

        self.btn_cancel = ctk.CTkButton(btn_frame, text="Cancel", height=42, fg_color="#d32f2f", hover_color="#b71c1c", command=self.cancel_download)
        self.btn_cancel.pack(side="left", padx=10)

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
    def show_message(self, title, message, is_error=False):
        top = ctk.CTkToplevel(self)
        top.title(title)
        top.geometry("400x200")
        top.attributes("-topmost", True)
        top.grab_set()
        
        color = "#ff5252" if is_error else "#4caf50"
        ctk.CTkLabel(top, text=title, font=("Segoe UI", 18, "bold"), text_color=color).pack(pady=(20, 5))
        ctk.CTkLabel(top, text=message, wraplength=350, font=("Segoe UI", 14)).pack(pady=10, padx=20)
        ctk.CTkButton(top, text="OK", command=top.destroy, width=120).pack(pady=(10, 20))

    def show_error(self, title, message):
        self.show_message(title, message, is_error=True)

    def show_info(self, title, message):
        self.show_message(title, message, is_error=False)

    def drop_urls(self, e):
        self.url_box.insert("end", e.data.replace("{", "").replace("}", "") + "\n")

    def select_folder(self):
        p = ctk.filedialog.askdirectory()
        if p:
            self.download_path = p
            self.folder_label.configure(text=p)

    # ================= PROGRESS =================
    def progress_hook(self, d):
        tid = threading.get_ident()
        if d.get("status") == "downloading":
            downloaded = d.get("downloaded_bytes") or 0
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            speed = d.get("speed") or 0

            self.active_downloads[tid] = (downloaded, total, speed)

            ag_dl = sum(x[0] for x in self.active_downloads.values())
            ag_tot = sum(x[1] for x in self.active_downloads.values())
            ag_sp = sum(x[2] for x in self.active_downloads.values())

            self.after(0, lambda: self.update_progress(ag_dl, ag_tot, ag_sp))
        elif d.get("status") == "finished":
            if tid in self.active_downloads:
                del self.active_downloads[tid]

    def update_progress(self, downloaded, total, speed):
        if total > 0:
            self.progress.set(min(1.0, downloaded / max(1, total)))
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
            self.show_error("Error", "Enter URLs and select folder")
            return

        self.files_box.delete("0.0","end")
        self.is_cancelled = False
        self.btn_download.configure(state="disabled")

        threading.Thread(target=self.download_manager, daemon=True).start()

    def cancel_download(self):
        self.is_cancelled = True
        self.status_label.configure(text="Cancelling...")

    def download_manager(self):
        downloaded_ids = load_downloaded_ids()
        temp_dir = os.path.join(self.download_path, ".temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        fmt = self.format_var.get()
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for url in self.urls:
                futures.append(executor.submit(self.download_single, url, fmt, temp_dir, downloaded_ids))

            for future in concurrent.futures.as_completed(futures):
                if self.is_cancelled:
                    break
                try:
                    res = future.result()
                    if res:
                        self.after(0, self.files_box.insert, "end", res + "\n")
                except Exception as e:
                    self.after(0, self.show_error, "Download Error", str(e))

        self.active_downloads.clear()

        if self.is_cancelled:
            self.after(0, lambda: self.status_label.configure(text="Cancelled"))
            self.after(0, lambda: self.progress.set(0))
        else:
            self.after(0, lambda: self.show_info("Done", "All downloads completed"))
            self.after(0, lambda: self.status_label.configure(text="Finished"))
            self.after(0, lambda: self.progress.set(1.0))
            
        self.after(0, lambda: self.btn_download.configure(state="normal"))

    def download_single(self, url, fmt, temp_dir, downloaded_ids):
        if self.is_cancelled:
            return None

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(temp_dir, "%(id)s.%(ext)s"),
            "noplaylist": True,
            "restrictfilenames": True,
            "nopart": True,
            "continuedl": False,
            "ffmpeg_location": FFMPEG_BIN,
            "progress_hooks": [self.progress_hook],
            "quiet": True,
            "no_warnings": True
        }

        postprocessors = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": fmt,
                "preferredquality": "0",
            }
        ]
        
        # WAV doesn't support embedding thumbnails
        if fmt != "wav":
            postprocessors.append({"key": "EmbedThumbnail"})
            ydl_opts["writethumbnail"] = True
            
        postprocessors.append({"key": "FFmpegMetadata"})
        ydl_opts["postprocessors"] = postprocessors

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            vid = info.get("id", "")

            if vid and vid in downloaded_ids:
                return None

            if self.is_cancelled:
                return None

            info = ydl.extract_info(url, download=True)
            if vid:
                save_downloaded_id(vid)

            # Locate generated temp file
            temp_file = None
            for f in os.listdir(temp_dir):
                if f.startswith(vid) and f.endswith(f".{fmt}"):
                    temp_file = os.path.join(temp_dir, f)
                    break

            if not temp_file:
                raise Exception(f"Downloaded audio file not found for {url}")

            safe_title = safe_filename(info.get("title", vid))
            final_file = os.path.join(self.download_path, f"{safe_title}.{fmt}")

            safe_temp = os.path.join(temp_dir, f"{safe_title}.{fmt}")
            if os.path.abspath(temp_file) != os.path.abspath(safe_temp):
                if os.path.exists(safe_temp):
                    os.remove(safe_temp)
                os.replace(temp_file, safe_temp)

            if os.path.abspath(safe_temp) != os.path.abspath(final_file):
                if os.path.exists(final_file):
                    os.remove(final_file)
                shutil.move(safe_temp, final_file)

        return final_file

    # ================= PLAY =================
    def play_audio(self, _):
        p = self.files_box.get("insert linestart","insert lineend").strip()
        if os.path.exists(p):
            os.startfile(p)

# ================= RUN =================
if __name__ == "__main__":
    App().mainloop()
