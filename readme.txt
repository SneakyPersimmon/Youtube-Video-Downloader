Media Downloader V2

A Python desktop app for downloading YouTube videos and audio through a dark, easy-to-use interface. Preview a video, choose a download preset, and save it immediately or add it to a queue.

Built with CustomTkinter, yt-dlp, Pillow, and FFmpeg.

Features

Maximum-quality downloads request the best video and audio streams available to yt-dlp.

Five presets Maximum Quality, Editor Ready, MP4 Compatibility, Small File, and Audio Only.

Audio downloads choose MP3, M4A, FLAC, WAV, or Opus.

Video previews view the thumbnail, title, channel, duration, and highest detected resolution.

Format information inspect available resolution, frame rate, and codec combinations.

Download queue process URLs one at a time, with duplicate detection for identical URLs.

Progress tracking see download progress, transfer speed, and estimated time remaining when available.

Cancellation and retries cancel downloads, retry failed transfers, and attempt to resume existing partial downloads.

Local preferences save the output folder and download settings between sessions.

Requirements

The instructions below target Windows. The app's Open Folder button uses a Windows-specific function.

Component

Purpose

Python 3.10 or newer, with Tkinter

Runs the application and its desktop interface.

CustomTkinter

Provides the interface widgets and dark theme.

Pillow

Loads and displays video thumbnails.

yt-dlp, installed with its default dependencies

Retrieves video information and downloads media.

FFmpeg and ffprobe, available on PATH

Merge video and audio streams and process audio exports.

Deno, available on PATH

Supplies the JavaScript runtime used for full YouTube support.

The Python minimum and media-processing requirements follow yt-dlp's dependency documentation. An internet connection and sufficient free disk space are also required.

Installation on Windows

1. Install Python and the Python dependencies

Install Python for Windows with Tkinter support. Download this repository and open PowerShell in the folder containing youtube_downloader_v2.py.

Create a virtual environment and install the packages

py -m venv .venv
..venvScriptspython.exe -m pip install --upgrade pip
..venvScriptspython.exe -m pip install --upgrade customtkinter Pillow yt-dlp[default]

If py is unavailable but python works, use python -m venv .venv for the first command. The remaining commands use the environment's Python directly, so activation is unnecessary.

The default dependency group includes yt-dlp's YouTube challenge solver. See the official YouTube setup guide.

2. Install FFmpeg

Get a Windows build through the FFmpeg download page.

Extract the downloaded archive.

Add the folder containing ffmpeg.exe and ffprobe.exe to your Windows user PATH, for example Cffmpegbin.

Close and reopen PowerShell after changing PATH.

Verify both commands work

ffmpeg -version
ffprobe -version

Install the FFmpeg executables; the similarly named Python package does not provide the required tools. See yt-dlp's FFmpeg requirements.

3. Install Deno

Deno is the JavaScript runtime enabled by default in yt-dlp. Install a current release using the official Deno installation instructions. On Windows with WinGet available

winget install DenoLand.Deno

Open a new PowerShell window and check

deno --version

The executable must be available on PATH. Refer to yt-dlp's runtime setup guide for current runtime requirements.

4. Launch the app

From the folder containing the script, run

..venvScriptspython.exe .youtube_downloader_v2.py

The window is titled Media Downloader V2. The header should display FFmpeg Ready. This indicator checks for ffmpeg only; use the commands above to verify ffprobe and Deno separately.

Usage

Download a video

Paste a video URL into the URL field.

Click Analyze to load its details and available formats.

Choose a Preset from the table below.

Use Browse to select a destination, or keep the default Downloads folder.

Click Download Now.

Wait for Download complete!, then click Open Folder to access the result.

The Quality dropdown currently displays detected formats for reference. The selected preset determines the actual download; choosing a different Quality entry does not change it.

Download audio

Paste the URL and click Analyze.

Select Audio Only.

Choose MP3, M4A, FLAC, WAV, or Opus in the Audio dropdown.

Choose a destination and click Download Now.

Select the audio format after choosing the preset selecting Audio Only resets the audio choice to MP3. The Audio dropdown applies only to this preset. Converting to FLAC or WAV does not restore detail missing from the source audio.

Download several videos

Paste and analyze a URL, then click Add to Queue.

Repeat for each video. Analyzing each new URL keeps the displayed queue titles in sync.

Set the preset, relevant format options, and output folder.

Click Start Queue.

The queue runs sequentially and shows each item's status. Settings are read when each item starts; they are not saved separately when you add a URL. Keep the settings unchanged while the queue runs if you want consistent output.

Click Cancel to request that the active transfer stop and prevent subsequent queue items from starting. Once it has stopped, Start Queue retries unfinished items and skips entries marked Complete. Clear empties an idle queue. The queue is not saved when the app closes.

Run one direct download or one queue at a time.

Download presets

Preset

What it selects

Merge target or audio output

Maximum Quality

Best available video plus audio, with a fallback to a combined format.

MKV by default; the Container dropdown can select MP4 or WebM.

Editor Ready

Prefers H.264AVC video and AAC audio, with fallback formats if unavailable.

MP4.

MP4 Compatibility

Prefers MP4 video and M4A audio, with fallback formats if unavailable.

MP4.

Small File

Selects available video streams up to 720p, plus audio.

MP4.

Audio Only

Best available audio, extracted or converted with FFmpeg.

Selected audio format.

Video presets select existing streams rather than re-encoding video. A merge target applies when separate streams are combined; it does not guarantee conversion of every source file to that container. The Container dropdown affects Maximum Quality; the other video presets use MP4 as their merge target.

Editor Ready can select a lower resolution when H.264 is unavailable at the source's highest resolution, and its fallback is not guaranteed to use H.264. MP4 Compatibility selects by container rather than enforcing H.264. Small File limits resolution, not final file size. Available quality depends on the source and the formats yt-dlp can retrieve.

Output and saved settings

Downloads default to the Downloads folder inside your user home directory. Files use the video's title and resulting extension, with filenames adjusted for Windows.

Preferences are stored in your home directory as .media_downloader_v2.json, normally

%USERPROFILE%.media_downloader_v2.json

The file stores the output folder, preset, container, and audio format. Settings are saved when you change the preset, choose a folder, or close the app. A preset's defaults are reapplied at startup, so a custom container or audio choice may need to be selected again.

Current limitations

Manual quality selection the Quality dropdown is informational in this version; downloads follow the preset.

Estimated size the estimate comes from one analyzed video format, may exclude audio, and does not refresh when the Quality selection changes.

Playlist links analysis requests a single video, but downloading does not explicitly disable playlists. Use individual video links without a playlist parameter when you want one video.

Cancellation the request is checked during download progress updates. FFmpeg processing may finish before cancellation takes effect, and partial files may remain.

Resume support partial downloads can be resumed when the source and existing files allow it; there is no dedicated pauseresume control.

Queue status “Queue complete!” means the queue finished processing; individual rows can still show Failed.

Platform support the current Open Folder action is Windows-specific; macOS and Linux support is not established by this version.

Troubleshooting

Problem

What to try

ModuleNotFoundError for customtkinter, PIL, or yt_dlp

Repeat the dependency installation command, then launch with the same .venvScriptspython.exe interpreter.

Tkinter is missing

Install or repair Python with its TclTk component, then recreate the virtual environment if needed.

FFmpeg Not Found

Confirm both FFmpeg tools are on PATH, then restart the terminal and app. Detection runs at startup.

Analysis fails or expected YouTube formats are missing

Update yt-dlp using the command below, check deno --version, and confirm the video is accessible. The app has no sign-in or cookie-import interface.

A downloaded video is unsuitable for an editor

Try Editor Ready. Its H.264 preference may trade resolution for compatibility; fallback formats can still require conversion elsewhere.

Changing Quality has no effect

This is a current limitation. Choose a preset to change download behavior.

Progress reaches 100% but processing continues

Separate streams may still need to be downloaded, merged, or converted. Wait for completion.

A queue item fails without a detailed error

Try that URL with Download Now to display the download error.

Keep the downloader and its companion dependencies updated using the upstream pip update guidance

..venvScriptspython.exe -m pip install --upgrade yt-dlp[default]

Restart the app after updating.