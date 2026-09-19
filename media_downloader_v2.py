import os
import json
import shutil
import threading
import subprocess
import urllib.request
from io import BytesIO
from pathlib import Path

import customtkinter as ctk
from PIL import Image
from tkinter import filedialog, messagebox
import yt_dlp


# ============================================================
# CONFIG
# ============================================================

APP_NAME = "Media Downloader V2"
CONFIG_FILE = os.path.join(
    os.path.expanduser("~"),
    ".media_downloader_v2.json"
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ============================================================
# HELPERS
# ============================================================

def format_duration(seconds):
    if not seconds:
        return "Unknown"

    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return "Unknown"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"

    return f"{minutes}:{secs:02d}"


def human_size(size):
    if not size:
        return "Unknown"

    try:
        size = float(size)
    except (TypeError, ValueError):
        return "Unknown"

    units = ["B", "KB", "MB", "GB", "TB"]

    for unit in units:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024

    return f"{size:.1f} PB"


def human_speed(speed):
    if not speed:
        return ""

    try:
        return f"{float(speed) / 1024 / 1024:.2f} MB/s"
    except (TypeError, ValueError):
        return ""


def format_eta(eta):
    if eta is None:
        return ""

    try:
        eta = int(float(eta))
    except (TypeError, ValueError, OverflowError):
        return ""

    hours = eta // 3600
    minutes = (eta % 3600) // 60
    seconds = eta % 60

    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"

    return f"{minutes:02d}:{seconds:02d}"


# ============================================================
# MAIN APP
# ============================================================

class MediaDownloader(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title(APP_NAME)
        self.geometry("1050x820")
        self.minsize(950, 720)

        self.settings = self.load_settings()

        self.output_folder = self.settings.get(
            "output_folder",
            os.path.join(os.path.expanduser("~"), "Downloads")
        )

        self.video_info = None
        self.detected_formats = []
        self.format_lookup = {}

        self.queue = []
        self.queue_running = False
        self.cancel_requested = False

        self.thumbnail_image = None

        self.ffmpeg_available = (
            shutil.which("ffmpeg") is not None
        )

        self.build_ui()

    # ========================================================
    # SETTINGS
    # ========================================================

    def load_settings(self):

        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass

        return {}

    def save_settings(self):

        data = {
            "output_folder": self.output_folder,
            "preset": self.preset_menu.get(),
            "container": self.container_menu.get(),
            "audio_format": self.audio_menu.get()
        }

        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    # ========================================================
    # UI
    # ========================================================

    def build_ui(self):

        # ----------------------------------------------------
        # HEADER
        # ----------------------------------------------------

        header = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        header.pack(
            fill="x",
            padx=30,
            pady=(25, 10)
        )

        title = ctk.CTkLabel(
            header,
            text="MEDIA DOWNLOADER",
            font=ctk.CTkFont(
                size=30,
                weight="bold"
            )
        )
        title.pack(side="left")

        ffmpeg_text = (
            "FFmpeg: Ready"
            if self.ffmpeg_available
            else "FFmpeg: Not Found"
        )

        self.ffmpeg_label = ctk.CTkLabel(
            header,
            text=ffmpeg_text,
            text_color=(
                "#6edc8c"
                if self.ffmpeg_available
                else "#ff7777"
            )
        )
        self.ffmpeg_label.pack(side="right")

        # ----------------------------------------------------
        # URL BAR
        # ----------------------------------------------------

        url_frame = ctk.CTkFrame(self)
        url_frame.pack(
            fill="x",
            padx=30,
            pady=10
        )

        self.url_entry = ctk.CTkEntry(
            url_frame,
            height=45,
            placeholder_text="Paste a permitted YouTube URL..."
        )
        self.url_entry.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(15, 8),
            pady=15
        )

        analyze_button = ctk.CTkButton(
            url_frame,
            text="Analyze",
            width=120,
            height=45,
            command=self.start_analysis
        )
        analyze_button.pack(
            side="right",
            padx=(8, 15),
            pady=15
        )

        # ----------------------------------------------------
        # VIDEO INFORMATION
        # ----------------------------------------------------

        info_frame = ctk.CTkFrame(self)
        info_frame.pack(
            fill="x",
            padx=30,
            pady=10
        )

        self.thumbnail_label = ctk.CTkLabel(
            info_frame,
            text="No thumbnail",
            width=240,
            height=135
        )
        self.thumbnail_label.pack(
            side="left",
            padx=15,
            pady=15
        )

        metadata = ctk.CTkFrame(
            info_frame,
            fg_color="transparent"
        )
        metadata.pack(
            side="left",
            fill="both",
            expand=True,
            padx=10,
            pady=15
        )

        self.title_label = ctk.CTkLabel(
            metadata,
            text="Paste a URL and click Analyze",
            anchor="w",
            justify="left",
            font=ctk.CTkFont(
                size=18,
                weight="bold"
            ),
            wraplength=650
        )
        self.title_label.pack(
            anchor="w",
            pady=(5, 10)
        )

        self.channel_label = ctk.CTkLabel(
            metadata,
            text="Channel: —",
            anchor="w"
        )
        self.channel_label.pack(anchor="w")

        self.duration_label = ctk.CTkLabel(
            metadata,
            text="Duration: —",
            anchor="w"
        )
        self.duration_label.pack(anchor="w")

        self.resolution_label = ctk.CTkLabel(
            metadata,
            text="Best detected quality: —",
            anchor="w"
        )
        self.resolution_label.pack(anchor="w")

        # ----------------------------------------------------
        # DOWNLOAD OPTIONS
        # ----------------------------------------------------

        options_frame = ctk.CTkFrame(self)
        options_frame.pack(
            fill="x",
            padx=30,
            pady=10
        )

        # PRESET

        ctk.CTkLabel(
            options_frame,
            text="Preset"
        ).grid(
            row=0,
            column=0,
            padx=10,
            pady=(15, 5)
        )

        self.preset_menu = ctk.CTkOptionMenu(
            options_frame,
            values=[
                "Maximum Quality",
                "Editor Ready",
                "MP4 Compatibility",
                "Small File",
                "Audio Only"
            ],
            command=self.preset_changed
        )

        self.preset_menu.set(
            self.settings.get(
                "preset",
                "Maximum Quality"
            )
        )

        self.preset_menu.grid(
            row=1,
            column=0,
            padx=10,
            pady=(0, 15)
        )

        # QUALITY

        ctk.CTkLabel(
            options_frame,
            text="Quality"
        ).grid(
            row=0,
            column=1,
            padx=10,
            pady=(15, 5)
        )

        self.quality_menu = ctk.CTkOptionMenu(
            options_frame,
            values=["Analyze URL first"]
        )

        self.quality_menu.grid(
            row=1,
            column=1,
            padx=10,
            pady=(0, 15)
        )

        # CONTAINER

        ctk.CTkLabel(
            options_frame,
            text="Container"
        ).grid(
            row=0,
            column=2,
            padx=10,
            pady=(15, 5)
        )

        self.container_menu = ctk.CTkOptionMenu(
            options_frame,
            values=[
                "MKV",
                "MP4",
                "WebM"
            ]
        )

        self.container_menu.set(
            self.settings.get(
                "container",
                "MKV"
            )
        )

        self.container_menu.grid(
            row=1,
            column=2,
            padx=10,
            pady=(0, 15)
        )

        # AUDIO

        ctk.CTkLabel(
            options_frame,
            text="Audio"
        ).grid(
            row=0,
            column=3,
            padx=10,
            pady=(15, 5)
        )

        self.audio_menu = ctk.CTkOptionMenu(
            options_frame,
            values=[
                "MP3",
                "M4A",
                "FLAC",
                "WAV",
                "Opus"
            ]
        )

        self.audio_menu.set(
            self.settings.get(
                "audio_format",
                "MP3"
            )
        )

        self.audio_menu.grid(
            row=1,
            column=3,
            padx=10,
            pady=(0, 15)
        )

        # SIZE

        ctk.CTkLabel(
            options_frame,
            text="Estimated Size"
        ).grid(
            row=0,
            column=4,
            padx=10,
            pady=(15, 5)
        )

        self.size_label = ctk.CTkLabel(
            options_frame,
            text="Unknown"
        )

        self.size_label.grid(
            row=1,
            column=4,
            padx=10,
            pady=(0, 15)
        )

        options_frame.grid_columnconfigure(
            (0, 1, 2, 3, 4),
            weight=1
        )

        # ----------------------------------------------------
        # OUTPUT FOLDER
        # ----------------------------------------------------

        folder_frame = ctk.CTkFrame(self)
        folder_frame.pack(
            fill="x",
            padx=30,
            pady=10
        )

        self.folder_label = ctk.CTkLabel(
            folder_frame,
            text=self.output_folder,
            anchor="w"
        )

        self.folder_label.pack(
            side="left",
            fill="x",
            expand=True,
            padx=15,
            pady=15
        )

        ctk.CTkButton(
            folder_frame,
            text="Browse",
            width=100,
            command=self.choose_folder
        ).pack(
            side="right",
            padx=5,
            pady=10
        )

        ctk.CTkButton(
            folder_frame,
            text="Open Folder",
            width=110,
            command=self.open_folder
        ).pack(
            side="right",
            padx=5,
            pady=10
        )

        # ----------------------------------------------------
        # BUTTONS
        # ----------------------------------------------------

        buttons = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        buttons.pack(
            pady=10
        )

        self.add_queue_button = ctk.CTkButton(
            buttons,
            text="Add to Queue",
            width=150,
            height=42,
            command=self.add_to_queue
        )
        self.add_queue_button.pack(
            side="left",
            padx=5
        )

        self.download_button = ctk.CTkButton(
            buttons,
            text="Download Now",
            width=170,
            height=42,
            font=ctk.CTkFont(
                weight="bold"
            ),
            command=self.download_now
        )
        self.download_button.pack(
            side="left",
            padx=5
        )

        self.cancel_button = ctk.CTkButton(
            buttons,
            text="Cancel",
            width=100,
            height=42,
            fg_color="#555555",
            command=self.cancel_download
        )
        self.cancel_button.pack(
            side="left",
            padx=5
        )

        # ----------------------------------------------------
        # PROGRESS
        # ----------------------------------------------------

        self.progress = ctk.CTkProgressBar(
            self,
            width=800
        )
        self.progress.pack(
            pady=(15, 5)
        )
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(
            self,
            text="Ready"
        )
        self.status_label.pack(
            pady=(0, 10)
        )

        # ----------------------------------------------------
        # QUEUE
        # ----------------------------------------------------

        queue_frame = ctk.CTkFrame(self)
        queue_frame.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=(5, 20)
        )

        queue_header = ctk.CTkFrame(
            queue_frame,
            fg_color="transparent"
        )
        queue_header.pack(
            fill="x",
            padx=15,
            pady=(10, 5)
        )

        ctk.CTkLabel(
            queue_header,
            text="DOWNLOAD QUEUE",
            font=ctk.CTkFont(
                size=16,
                weight="bold"
            )
        ).pack(side="left")

        ctk.CTkButton(
            queue_header,
            text="Start Queue",
            width=110,
            command=self.start_queue
        ).pack(
            side="right",
            padx=5
        )

        ctk.CTkButton(
            queue_header,
            text="Clear",
            width=80,
            command=self.clear_queue
        ).pack(
            side="right",
            padx=5
        )

        self.queue_box = ctk.CTkTextbox(
            queue_frame,
            height=130
        )
        self.queue_box.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(5, 15)
        )

        self.queue_box.configure(
            state="disabled"
        )

        self.preset_changed(
            self.preset_menu.get()
        )

    # ========================================================
    # FOLDER
    # ========================================================

    def choose_folder(self):

        folder = filedialog.askdirectory(
            initialdir=self.output_folder
        )

        if folder:
            self.output_folder = folder
            self.folder_label.configure(
                text=folder
            )
            self.save_settings()

    def open_folder(self):

        os.makedirs(
            self.output_folder,
            exist_ok=True
        )

        try:
            os.startfile(
                self.output_folder
            )
        except Exception as e:
            messagebox.showerror(
                "Error",
                str(e)
            )

    # ========================================================
    # ANALYZER
    # ========================================================

    def start_analysis(self):

        url = self.url_entry.get().strip()

        if not url:
            messagebox.showerror(
                "Missing URL",
                "Paste a URL first."
            )
            return

        self.status_label.configure(
            text="Analyzing URL..."
        )

        self.title_label.configure(
            text="Analyzing..."
        )

        threading.Thread(
            target=self.analyze_url,
            args=(url,),
            daemon=True
        ).start()

    def analyze_url(self, url):

        try:

            options = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "noplaylist": True
            }

            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(
                    url,
                    download=False
                )

            self.video_info = info

            self.after(
                0,
                lambda: self.display_info(info)
            )

        except Exception as e:

            error = str(e)

            self.after(
                0,
                lambda text=error:
                messagebox.showerror(
                    "Analysis Error",
                    text
                )
            )

            self.after(
                0,
                lambda:
                self.status_label.configure(
                    text="Analysis failed."
                )
            )

    # ========================================================
    # DISPLAY VIDEO INFO
    # ========================================================

    def display_info(self, info):

        title = info.get(
            "title",
            "Unknown title"
        )

        channel = (
            info.get("channel")
            or info.get("uploader")
            or "Unknown"
        )

        duration = format_duration(
            info.get("duration")
        )

        self.title_label.configure(
            text=title
        )

        self.channel_label.configure(
            text=f"Channel: {channel}"
        )

        self.duration_label.configure(
            text=f"Duration: {duration}"
        )

        formats = info.get(
            "formats",
            []
        )

        self.build_format_list(
            formats
        )

        thumbnail = info.get(
            "thumbnail"
        )

        if thumbnail:

            threading.Thread(
                target=self.load_thumbnail,
                args=(thumbnail,),
                daemon=True
            ).start()

        self.status_label.configure(
            text="Analysis complete."
        )

    # ========================================================
    # FORMAT ANALYSIS
    # ========================================================

    def build_format_list(self, formats):

        video_formats = []

        for f in formats:

            if f.get("vcodec") == "none":
                continue

            height = f.get("height")

            if not height:
                continue

            fps = f.get("fps") or 0

            codec = f.get(
                "vcodec",
                "unknown"
            )

            format_id = f.get(
                "format_id"
            )

            filesize = (
                f.get("filesize")
                or
                f.get("filesize_approx")
            )

            video_formats.append({
                "height": int(height),
                "fps": float(fps or 0),
                "codec": codec,
                "format_id": format_id,
                "filesize": filesize,
                "ext": f.get("ext")
            })

        video_formats.sort(
            key=lambda x: (
                x["height"],
                x["fps"]
            ),
            reverse=True
        )

        self.detected_formats = video_formats
        self.format_lookup = {}

        labels = []
        seen = set()

        for f in video_formats:

            height = f["height"]
            fps = f["fps"]

            if fps:
                fps_text = (
                    str(int(fps))
                    if float(fps).is_integer()
                    else f"{fps:g}"
                )
                label = (
                    f"{height}p{fps_text}"
                )
            else:
                label = f"{height}p"

            # Keep UI simple by showing one entry
            # for each resolution/FPS combination.

            if label in seen:
                continue

            seen.add(label)

            codec_short = self.codec_name(
                f["codec"]
            )

            display = (
                f"{label} | {codec_short}"
            )

            labels.append(display)

            self.format_lookup[
                display
            ] = f

        if not labels:

            labels = [
                "Best Available"
            ]

        self.quality_menu.configure(
            values=labels
        )

        self.quality_menu.set(
            labels[0]
        )

        if video_formats:

            best = video_formats[0]

            fps = best["fps"]

            quality = (
                f"{best['height']}p"
            )

            if fps:
                quality += (
                    f" {int(fps)} FPS"
                )

            self.resolution_label.configure(
                text=(
                    "Best detected quality: "
                    + quality
                )
            )

        self.update_estimated_size()

    def codec_name(self, codec):

        codec = (
            codec or ""
        ).lower()

        if codec.startswith("av01"):
            return "AV1"

        if codec.startswith("vp9"):
            return "VP9"

        if codec.startswith("avc"):
            return "H.264"

        if codec.startswith("h264"):
            return "H.264"

        return codec.split(".")[0].upper()

    # ========================================================
    # THUMBNAIL
    # ========================================================

    def load_thumbnail(self, url):

        try:

            with urllib.request.urlopen(
                url,
                timeout=10
            ) as response:

                image_data = response.read()

            image = Image.open(
                BytesIO(image_data)
            )

            image.thumbnail(
                (240, 135)
            )

            ctk_image = ctk.CTkImage(
                light_image=image,
                dark_image=image,
                size=(240, 135)
            )

            self.thumbnail_image = ctk_image

            self.after(
                0,
                lambda:
                self.thumbnail_label.configure(
                    image=ctk_image,
                    text=""
                )
            )

        except Exception:
            pass

    # ========================================================
    # PRESETS
    # ========================================================

    def preset_changed(
        self,
        preset
    ):

        if preset == "Maximum Quality":

            self.container_menu.set(
                "MKV"
            )

        elif preset == "Editor Ready":

            self.container_menu.set(
                "MP4"
            )

        elif preset == "MP4 Compatibility":

            self.container_menu.set(
                "MP4"
            )

        elif preset == "Small File":

            self.container_menu.set(
                "MP4"
            )

        elif preset == "Audio Only":

            self.audio_menu.set(
                "MP3"
            )

        self.save_settings()

    # ========================================================
    # ESTIMATED SIZE
    # ========================================================

    def update_estimated_size(self):

        selected = self.quality_menu.get()

        data = self.format_lookup.get(
            selected
        )

        if not data:

            self.size_label.configure(
                text="Unknown"
            )
            return

        size = data.get(
            "filesize"
        )

        if size:

            self.size_label.configure(
                text="~" + human_size(size)
            )

        else:

            self.size_label.configure(
                text="Unknown"
            )

    # ========================================================
    # CREATE DOWNLOAD OPTIONS
    # ========================================================

    def create_download_options(self):

        preset = self.preset_menu.get()

        container = (
            self.container_menu
            .get()
            .lower()
        )

        options = {

            "outtmpl": os.path.join(
                self.output_folder,
                "%(title)s.%(ext)s"
            ),

            "windowsfilenames": True,

            "progress_hooks": [
                self.progress_hook
            ],

            "retries": 5,

            "fragment_retries": 5,

            "continuedl": True,

            "quiet": True,

            "no_warnings": True
        }

        # ----------------------------------------------------
        # AUDIO ONLY
        # ----------------------------------------------------

        if preset == "Audio Only":

            audio_format = (
                self.audio_menu
                .get()
                .lower()
            )

            options["format"] = (
                "bestaudio/best"
            )

            options[
                "postprocessors"
            ] = [
                {
                    "key":
                        "FFmpegExtractAudio",

                    "preferredcodec":
                        audio_format,

                    "preferredquality":
                        "320"
                }
            ]

            return options

        # ----------------------------------------------------
        # MAXIMUM QUALITY
        # ----------------------------------------------------

        if preset == "Maximum Quality":

            options["format"] = (
                "bestvideo*+bestaudio/best"
            )

            options[
                "merge_output_format"
            ] = container

            return options

        # ----------------------------------------------------
        # EDITOR READY
        # ----------------------------------------------------

        if preset == "Editor Ready":

            options["format"] = (
                "bestvideo[vcodec^=avc1]"
                "+bestaudio[acodec^=mp4a]/"
                "best[vcodec^=avc1]/best"
            )

            options[
                "merge_output_format"
            ] = "mp4"

            return options

        # ----------------------------------------------------
        # MP4 COMPATIBILITY
        # ----------------------------------------------------

        if preset == "MP4 Compatibility":

            options["format"] = (
                "bestvideo[ext=mp4]"
                "+bestaudio[ext=m4a]/"
                "best[ext=mp4]/best"
            )

            options[
                "merge_output_format"
            ] = "mp4"

            return options

        # ----------------------------------------------------
        # SMALL FILE
        # ----------------------------------------------------

        if preset == "Small File":

            options["format"] = (
                "bestvideo[height<=720]"
                "+bestaudio/"
                "best[height<=720]"
            )

            options[
                "merge_output_format"
            ] = "mp4"

            return options

        return options

    # ========================================================
    # DOWNLOAD NOW
    # ========================================================

    def download_now(self):

        url = self.url_entry.get().strip()

        if not url:

            messagebox.showerror(
                "Missing URL",
                "Paste a URL first."
            )
            return

        if not self.ffmpeg_available:

            preset = self.preset_menu.get()

            if preset in [
                "Maximum Quality",
                "Editor Ready",
                "MP4 Compatibility",
                "Audio Only"
            ]:

                messagebox.showwarning(
                    "FFmpeg Not Found",
                    (
                        "FFmpeg is not currently "
                        "available in PATH.\n\n"
                        "High-quality video merging "
                        "and audio conversion may fail."
                    )
                )

        self.cancel_requested = False

        threading.Thread(
            target=self.perform_download,
            args=(url,),
            daemon=True
        ).start()

    # ========================================================
    # PERFORM DOWNLOAD
    # ========================================================

    def perform_download(
        self,
        url
    ):

        try:

            self.after(
                0,
                lambda:
                self.status_label.configure(
                    text="Starting download..."
                )
            )

            self.after(
                0,
                lambda:
                self.progress.set(0)
            )

            options = (
                self.create_download_options()
            )

            with yt_dlp.YoutubeDL(
                options
            ) as ydl:

                ydl.download(
                    [url]
                )

            if not self.cancel_requested:

                self.after(
                    0,
                    lambda:
                    self.progress.set(1)
                )

                self.after(
                    0,
                    lambda:
                    self.status_label.configure(
                        text="Download complete!"
                    )
                )

        except Exception as e:

            if self.cancel_requested:

                self.after(
                    0,
                    lambda:
                    self.status_label.configure(
                        text="Download cancelled."
                    )
                )

            else:

                error = str(e)

                self.after(
                    0,
                    lambda text=error:
                    messagebox.showerror(
                        "Download Error",
                        text
                    )
                )

                self.after(
                    0,
                    lambda:
                    self.status_label.configure(
                        text="Download failed."
                    )
                )

    # ========================================================
    # PROGRESS HOOK
    # ========================================================

    def progress_hook(
        self,
        data
    ):

        if self.cancel_requested:

            raise Exception(
                "Download cancelled"
            )

        status = data.get(
            "status"
        )

        if status == "downloading":

            downloaded = data.get(
                "downloaded_bytes",
                0
            )

            total = (
                data.get("total_bytes")
                or
                data.get(
                    "total_bytes_estimate"
                )
            )

            progress_value = 0

            if total:

                try:

                    progress_value = (
                        float(downloaded)
                        / float(total)
                    )

                    progress_value = max(
                        0,
                        min(
                            progress_value,
                            1
                        )
                    )

                except Exception:

                    progress_value = 0

            speed = human_speed(
                data.get("speed")
            )

            eta = format_eta(
                data.get("eta")
            )

            if total:

                percent = (
                    progress_value * 100
                )

                text = (
                    f"{percent:.1f}%"
                )

            else:

                text = "Downloading"

            if speed:

                text += (
                    f"  |  {speed}"
                )

            if eta:

                text += (
                    f"  |  ETA {eta}"
                )

            self.after(
                0,
                lambda p=progress_value:
                self.progress.set(p)
            )

            self.after(
                0,
                lambda t=text:
                self.status_label.configure(
                    text=t
                )
            )

        elif status == "finished":

            self.after(
                0,
                lambda:
                self.status_label.configure(
                    text=(
                        "Download finished. "
                        "Processing..."
                    )
                )
            )

    # ========================================================
    # CANCEL
    # ========================================================

    def cancel_download(self):

        self.cancel_requested = True

        self.status_label.configure(
            text="Cancelling..."
        )

    # ========================================================
    # QUEUE
    # ========================================================

    def add_to_queue(self):

        url = self.url_entry.get().strip()

        if not url:

            messagebox.showerror(
                "Missing URL",
                "Paste a URL first."
            )
            return

        # Duplicate detection

        for item in self.queue:

            if item["url"] == url:

                messagebox.showinfo(
                    "Already Queued",
                    "This URL is already in the queue."
                )

                return

        title = url

        if self.video_info:

            title = self.video_info.get(
                "title",
                url
            )

        self.queue.append({
            "url": url,
            "title": title,
            "status": "Waiting"
        })

        self.refresh_queue()

    def refresh_queue(self):

        self.queue_box.configure(
            state="normal"
        )

        self.queue_box.delete(
            "1.0",
            "end"
        )

        if not self.queue:

            self.queue_box.insert(
                "end",
                "Queue is empty."
            )

        else:

            for index, item in enumerate(
                self.queue,
                start=1
            ):

                line = (
                    f"{index}. "
                    f"[{item['status']}] "
                    f"{item['title']}\n"
                )

                self.queue_box.insert(
                    "end",
                    line
                )

        self.queue_box.configure(
            state="disabled"
        )

    def clear_queue(self):

        if self.queue_running:

            messagebox.showwarning(
                "Queue Running",
                (
                    "Cancel the current download "
                    "before clearing the queue."
                )
            )
            return

        self.queue.clear()

        self.refresh_queue()

    def start_queue(self):

        if self.queue_running:
            return

        if not self.queue:

            messagebox.showinfo(
                "Queue Empty",
                "Add some URLs first."
            )
            return

        self.queue_running = True
        self.cancel_requested = False

        threading.Thread(
            target=self.process_queue,
            daemon=True
        ).start()

    def process_queue(self):

        try:

            for item in self.queue:

                if self.cancel_requested:
                    break

                if item["status"] == "Complete":
                    continue

                item["status"] = "Downloading"

                self.after(
                    0,
                    self.refresh_queue
                )

                try:

                    options = (
                        self.create_download_options()
                    )

                    with yt_dlp.YoutubeDL(
                        options
                    ) as ydl:

                        ydl.download(
                            [item["url"]]
                        )

                    if self.cancel_requested:

                        item["status"] = "Cancelled"

                    else:

                        item["status"] = "Complete"

                except Exception:

                    if self.cancel_requested:

                        item["status"] = "Cancelled"

                    else:

                        item["status"] = "Failed"

                self.after(
                    0,
                    self.refresh_queue
                )

            if not self.cancel_requested:

                self.after(
                    0,
                    lambda:
                    self.status_label.configure(
                        text="Queue complete!"
                    )
                )

        finally:

            self.queue_running = False

    # ========================================================
    # CLOSE
    # ========================================================

    def destroy(self):

        self.save_settings()

        super().destroy()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    app = MediaDownloader()

    app.mainloop()