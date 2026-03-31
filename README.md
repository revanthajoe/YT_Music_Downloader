# 🎵 YouTube → High-Quality MP3 Downloader (CustomTkinter)

A modern desktop application built using **Python + CustomTkinter + yt-dlp**
that downloads YouTube videos and converts them into **high-quality MP3 audio**
while preserving audio fidelity.

This project focuses on:

✔ Clean & modern UI  
✔ High-bitrate audio extraction  
✔ Safe & stable Windows file handling  
✔ Duplicate-download protection  
✔ Performance-optimized FFmpeg conversion  

---

## 🏷️ Project Status

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-darkgreen)
![UI Toolkit](https://img.shields.io/badge/UI-CustomTkinter-orange)
![License](https://img.shields.io/badge/License-OpenSource-purple)

---


---

## 🚀 Features

### 🎯 Download Engine
- Downloads **best available audio stream**
- Converts audio using **FFmpeg**
- Ensures **no quality loss**
- Accurate progress bar
- Live speed monitor (KB/s)
- Total file size indicator

---

### 🛡 Safety & Stability

The app prevents:

✔ Invalid filename crashes  
✔ `WinError 32` file-lock issues  
✔ Rename conflicts  
✔ YouTube temp file errors  
✔ Overlong filename crashes  
✔ Duplicate file downloads  

Includes:

- Smart title sanitization
- Safe Windows-compatible filenames
- Temporary processing folder
- Auto-generated download-ID database

---

### 💡 UI / Usability

- Drag & Drop YouTube URLs
- Paste multiple links (one per line)
- Progress bar with speed & size
- Dark mode themed UI
- Double-click downloaded file to play
- Clean rounded card layout

---

## 📂 Project Structure
```
Music/
│
├── Music_Downloader.py → Main application
├── downloaded_ids.txt → Duplicate-protection database
│
├── ffmpeg/
│ └── ffmpeg.exe → Required FFmpeg binary
│
└── icon.ico → (Optional) App icon for EXE build
```

---

## 🧰 Requirements

Install dependencies:

```bash
pip install customtkinter tkinterdnd2 yt-dlp


