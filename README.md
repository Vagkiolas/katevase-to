# Katevase To

A desktop YouTube downloader (MP4 video / MP3 audio) built for **non-technical users**. I originally made it for my mum, so the goal was: paste a link, press one button, and never open a terminal.

*"Κατέβασέ το" = "Download it" in Greek. The interface is available in **Greek (default) and English**.*

![Katevase To screenshot](screenshot.png)

## Features

- **Video (MP4)** up to 4K with a quality picker, or **audio only (MP3, 192 kbps)**
- **Self-healing setup:** missing dependencies are detected at startup and installed with one click
  - `yt-dlp` is installed into the *same* Python interpreter that runs the app (`sys.executable`), which avoids the classic "installed it, but into another Python" problem
  - `ffmpeg` is fetched through `imageio-ffmpeg`, with no manual PATH editing
  - a missing Node.js/Deno runtime (needed by yt-dlp for 1080p+) is flagged with a download link
- **Graceful degradation:** without ffmpeg it still works (progressive MP4 up to 720p, M4A audio)
- **Automatic sign-in fallback:** it tries first without cookies. Only if YouTube asks for sign-in ("confirm you're not a bot") does it retry with the local Firefox session cookies
- **Human-readable errors:** yt-dlp exceptions are mapped to plain-language messages that tell the user what to do next
- **One-click yt-dlp update** for when YouTube changes break downloads. It works in the `.exe` too (see below)
- **Bilingual UI (Ελληνικά / English):** switch with one click; the choice is remembered

## Design notes

- **Thread-safe GUI:** downloads run in a background thread that never touches Tkinter directly. The thread posts messages to a `queue.Queue`, and the main thread polls the queue with `after()` to update the progress bar and status.
- **Updating a frozen app:** inside a PyInstaller `.exe` there is no `pip`, and `sys.executable` points to the `.exe` itself. In that mode the app downloads the official pure-Python `yt-dlp` zipapp to `%LOCALAPPDATA%\KatevaseTo` and puts it first on `sys.path` at startup, so the newer version overrides the bundled one. If it fails to import, the app falls back to the bundled version. ffmpeg is extracted from the `imageio-ffmpeg` wheel on PyPI, so it's the same binary pip would install, just without pip. Downloads go to a temporary file and are renamed only when complete.
- **Internationalisation:** every text widget is registered with a translation key, so switching language re-labels the whole UI in place. Values that drive logic, such as the quality setting, are stored language-independently.
- **Why only Firefox for cookies:** Chromium-based browsers (Chrome, Edge, Brave, Opera) now protect cookies with App-Bound Encryption, so external tools can no longer read them.

## Installation

Requires Python 3.9+ on Windows (it should also run on Linux/macOS).

```bash
git clone https://github.com/Vagkiolas/katevase-to.git
cd katevase-to
pip install -r requirements.txt
```

## Usage

Double-click **`Katevase To.bat`**, or run:

```bash
python katevase_to.py
```

1. Paste the link (**Επικόλληση**)
2. Choose **Βίντεο MP4** or **Ήχος MP3**, and a quality
3. Press **ΚΑΤΕΒΑΣΜΑ**. Files are saved to `Downloads` by default.

A standalone Windows `.exe` (no Python needed) is available under [Releases](https://github.com/Vagkiolas/katevase-to/releases).

## Version history

| Version | Changes |
|---|---|
| **v1.5** | English/Greek language switch (remembered); update & ffmpeg install now work in the standalone `.exe`; yt-dlp version shown in header |
| **v1.4** | Automatic Firefox-cookie retry; cookie checkbox replaces browser list; fixed quality menu vanishing after MP3 ↔ MP4 toggle |
| **v1.3** | Node.js/Deno detection for 1080p+; notice panel for missing tools; progress-bar layout fix; `.bat` launcher |
| **v1.2** | MP4/MP3 downloads, quality selection, auto-install of yt-dlp & ffmpeg, friendly errors |

## Building the .exe

```bash
pip install -U pyinstaller "yt-dlp[default]"
python -m PyInstaller --noconfirm --onefile --windowed --name Katevase_To --collect-all yt_dlp --collect-all yt_dlp_ejs katevase_to.py
```

The executable is created in `dist/`.

## Built with

Python · Tkinter · [yt-dlp](https://github.com/yt-dlp/yt-dlp) · FFmpeg (via [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg)) · PyInstaller

## Disclaimer

For personal use only. Please respect YouTube's Terms of Service and the rights of content creators.
