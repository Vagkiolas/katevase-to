"""
Katevase To v1.6
Απλός YouTube downloader (βίντεο MP4 / ήχος MP3)
Simple YouTube downloader (MP4 video / MP3 audio)

ΤΡΕΞΙΜΟ / RUN:
    Διπλό κλικ στο "Katevase To.bat"   (ή / or: python katevase_to.py)
    ή το Katevase_To.exe               (or the .exe from Releases)

Τι χρειάζεται — τα βλέπεις και μέσα στο πρόγραμμα:
    yt-dlp    → το βάζει μόνο του
    ffmpeg    → το βάζει μόνο του με κουμπί
    Node.js   → χρειάζεται για αναλύσεις πάνω από 720p

ΝΕΑ ΣΤΗΝ 1.6:
    - Διόρθωση «This video is not available»: το yt-dlp πλέον χρειάζεται
      JavaScript runtime + το script EJS. Δίνουμε ρητά το Node.js (μόνο
      του το yt-dlp ενεργοποιεί μόνο το Deno) και επιτρέπουμε το EJS.

ΝΕΑ ΣΤΗΝ 1.5:
    - Επιλογή γλώσσας Ελληνικά / English (θυμάται την επιλογή)
    - Στο .exe η «Ενημέρωση» και η «Εγκατάσταση ffmpeg» δουλεύουν πλέον:
      μέσα σε .exe δεν υπάρχει pip, οπότε κατεβάζουμε απευθείας τα αρχεία
      σε φάκελο του χρήστη (%LOCALAPPDATA%\\KatevaseTo).
"""

import os
import sys
import json
import queue
import shutil
import zipfile
import threading
import subprocess
import webbrowser
import urllib.request
import tkinter as tk
from tkinter import ttk, filedialog
import tkinter.messagebox as mb

VERSION = "1.6"

# Τρέχουμε μέσα σε .exe του PyInstaller; Τότε το sys.executable είναι το
# ίδιο το .exe και ΔΕΝ υπάρχει pip — οι εγκαταστάσεις γίνονται αλλιώς.
FROZEN = getattr(sys, 'frozen', False)


# ══════════════════════════════════════════════════════════════════════
#  ΦΑΚΕΛΟΣ ΡΥΘΜΙΣΕΩΝ / ΔΕΔΟΜΕΝΩΝ
# ══════════════════════════════════════════════════════════════════════

if os.name == 'nt':
    APPDIR = os.path.join(os.environ.get('LOCALAPPDATA')
                          or os.path.expanduser('~'), 'KatevaseTo')
else:
    APPDIR = os.path.join(os.path.expanduser('~'), '.katevase_to')
os.makedirs(APPDIR, exist_ok=True)

SETTINGS_FILE = os.path.join(APPDIR, 'settings.json')
YTDLP_ZIP = os.path.join(APPDIR, 'yt-dlp.zip')        # ενημερωμένο yt-dlp (.exe)
FFMPEG_DIR = os.path.join(APPDIR, 'ffmpeg')           # ffmpeg που κατεβάσαμε (.exe)


def load_settings():
    try:
        with open(SETTINGS_FILE, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(**kw):
    s = load_settings()
    s.update(kw)
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════
#  ΜΕΤΑΦΡΑΣΕΙΣ
# ══════════════════════════════════════════════════════════════════════

STRINGS = {
    'el': {
        'lang_btn':       "EN",
        'btn_update':     "⟳ Ενημέρωση",
        'ff_notice':      "⚠  Λείπει το ffmpeg → μόνο 720p, χωρίς MP3",
        'ff_btn':         "Εγκατάσταση",
        'js_notice':      "⚠  Λείπει το Node.js → πολλά βίντεο δεν θα κατεβαίνουν",
        'js_btn':         "Κατέβασέ το",
        'lbl_link':       "Link",
        'btn_paste':      "Επικόλληση",
        'lbl_folder':     "Φάκελος",
        'btn_browse':     "Αλλαγή",
        'mode_video':     "Βίντεο  MP4",
        'mode_audio':     "Ήχος  MP3",
        'lbl_quality':    "Ποιότητα",
        'q_max':          "Μέγιστη",
        'cookie_chk':     "  Σύνδεση μέσω Firefox, αν το ζητήσει το YouTube",
        'cookie_hint_ok': "(κλείσε τον Firefox πριν το κατέβασμα)",
        'cookie_hint_no': "(δεν βρέθηκε Firefox σ' αυτό το PC)",
        'btn_go':         "ΚΑΤΕΒΑΣΜΑ",
        'btn_wait':       "ΠΕΡΙΜΕΝΕ...",
        'st_need_link':   "Βάλε πρώτα ένα link!",
        'st_connecting':  "Σύνδεση με YouTube...",
        'st_downloading': "Κατεβαίνει  {pct:.0f}%   ({done:.1f}/{total:.1f} MB)   {spd}",
        'st_merging':     "Ένωση βίντεο + ήχου... (λίγη υπομονή)",
        'st_retry':       "Το YouTube ζήτησε σύνδεση — ξαναδοκιμάζω με τα cookies του Firefox...",
        'st_done':        "Έτοιμο! Το {kind} αποθηκεύτηκε. ✅",
        'kind_mp3':       "MP3",
        'kind_audio':     "αρχείο ήχου",
        'kind_video':     "βίντεο",
        'st_updating':    "Ενημέρωση yt-dlp...",
        'st_dl_pct':      "Κατέβασμα... {pct:.0f}%",
        'st_updated':     "Ενημερώθηκε! Κλείσε και ξανάνοιξε το πρόγραμμα.",
        'st_update_fail': "Η ενημέρωση απέτυχε — έλεγξε τη σύνδεσή σου.",
        'st_ff_start':    "Κατέβασμα ffmpeg... (~30 MB, μια φορά μόνο)",
        'st_ff_ok':       "Το ffmpeg εγκαταστάθηκε! ✅",
        'st_ff_fail':     "Η εγκατάσταση απέτυχε — έλεγξε τη σύνδεσή σου.",
        'st_ff_notfound': "Εγκαταστάθηκε αλλά δεν το βρίσκω. Ξανάνοιξε το πρόγραμμα.",
        'st_ff_os':       "Η αυτόματη εγκατάσταση ffmpeg υπάρχει μόνο για Windows.",
        'st_error':       "Σφάλμα: {e}",
        'err_cookie_copy': "Δεν μπόρεσα να διαβάσω τα cookies — κλείσε τελείως τον Firefox και ξαναδοκίμασε.",
        'err_dpapi':      "Ο browser κρυπτογραφεί τα cookies του. Μόνο ο Firefox δουλεύει γι' αυτή τη δουλειά.",
        'err_bot':        "Το YouTube ζητάει σύνδεση. Εγκατέστησε Firefox, μπες στο YouTube μ' αυτόν, και τσέκαρε «Σύνδεση μέσω Firefox».",
        'err_outdated':   "Το yt-dlp είναι παλιό για τις τωρινές αλλαγές του YouTube. Πάτα «Ενημέρωση» πάνω δεξιά.",
        'err_private':    "Το βίντεο είναι ιδιωτικό.",
        'err_unavail':    "Το YouTube δεν δίνει το βίντεο. Πάτα «Ενημέρωση» πάνω δεξιά και ξαναδοκίμασε (μπορεί και να είναι μπλοκαρισμένο στην Ελλάδα).",
        'err_url':        "Το link δεν φαίνεται σωστό.",
        'err_ffmpeg':     "Λείπει το ffmpeg. Πάτα το κουμπί «Εγκατάσταση».",
        'err_format':     "Αυτή η ανάλυση δεν υπάρχει γι' αυτό το βίντεο. Δοκίμασε άλλη.",
        'dlg_miss_title': "Λείπει το yt-dlp",
        'dlg_miss_body':  "Το yt-dlp δεν βρέθηκε σ' αυτή την Python:\n\n{exe}\n\n"
                          "(Αν το είχες εγκαταστήσει, μπήκε σε άλλη Python του PC.)\n\n"
                          "Να το εγκαταστήσω τώρα εδώ;",
        'dlg_fail_title': "Απέτυχε",
        'dlg_fail_body':  "Η εγκατάσταση δεν ολοκληρώθηκε.\n\nΤρέξε χειροκίνητα στο cmd:\n\n{cmd}",
        'dlg_ok_title':   "Έτοιμο",
        'dlg_ok_body':    "Το yt-dlp εγκαταστάθηκε!\n\nΚλείσε αυτό και ξανάνοιξε το πρόγραμμα.",
    },
    'en': {
        'lang_btn':       "ΕΛ",
        'btn_update':     "⟳ Update",
        'ff_notice':      "⚠  ffmpeg missing → 720p max, no MP3",
        'ff_btn':         "Install",
        'js_notice':      "⚠  Node.js missing → many videos won't download",
        'js_btn':         "Get it",
        'lbl_link':       "Link",
        'btn_paste':      "Paste",
        'lbl_folder':     "Folder",
        'btn_browse':     "Change",
        'mode_video':     "Video  MP4",
        'mode_audio':     "Audio  MP3",
        'lbl_quality':    "Quality",
        'q_max':          "Best",
        'cookie_chk':     "  Sign in via Firefox if YouTube asks",
        'cookie_hint_ok': "(close Firefox before downloading)",
        'cookie_hint_no': "(Firefox not found on this PC)",
        'btn_go':         "DOWNLOAD",
        'btn_wait':       "PLEASE WAIT...",
        'st_need_link':   "Paste a link first!",
        'st_connecting':  "Connecting to YouTube...",
        'st_downloading': "Downloading  {pct:.0f}%   ({done:.1f}/{total:.1f} MB)   {spd}",
        'st_merging':     "Merging video + audio... (please wait)",
        'st_retry':       "YouTube asked for sign-in — retrying with Firefox cookies...",
        'st_done':        "Done! The {kind} was saved. ✅",
        'kind_mp3':       "MP3",
        'kind_audio':     "audio file",
        'kind_video':     "video",
        'st_updating':    "Updating yt-dlp...",
        'st_dl_pct':      "Downloading... {pct:.0f}%",
        'st_updated':     "Updated! Close and reopen the program.",
        'st_update_fail': "Update failed — check your connection.",
        'st_ff_start':    "Downloading ffmpeg... (~30 MB, one time only)",
        'st_ff_ok':       "ffmpeg installed! ✅",
        'st_ff_fail':     "Installation failed — check your connection.",
        'st_ff_notfound': "Installed, but I can't find it. Reopen the program.",
        'st_ff_os':       "Automatic ffmpeg install is only available on Windows.",
        'st_error':       "Error: {e}",
        'err_cookie_copy': "Couldn't read the cookies — fully close Firefox and try again.",
        'err_dpapi':      "This browser encrypts its cookies. Only Firefox works for this.",
        'err_bot':        "YouTube wants you to sign in. Install Firefox, sign in to YouTube with it, and tick «Sign in via Firefox».",
        'err_outdated':   "yt-dlp is too old for YouTube's latest changes. Press «Update» at the top right.",
        'err_private':    "This video is private.",
        'err_unavail':    "YouTube won't serve this video. Press «Update» at the top right and try again (it may also be blocked in your country).",
        'err_url':        "That link doesn't look right.",
        'err_ffmpeg':     "ffmpeg is missing. Press the «Install» button.",
        'err_format':     "This resolution isn't available for this video. Try another one.",
        'dlg_miss_title': "yt-dlp is missing",
        'dlg_miss_body':  "yt-dlp was not found in this Python:\n\n{exe}\n\n"
                          "(If you installed it, it went into another Python on this PC.)\n\n"
                          "Install it here now?",
        'dlg_fail_title': "Failed",
        'dlg_fail_body':  "Installation did not complete.\n\nRun this manually in cmd:\n\n{cmd}",
        'dlg_ok_title':   "Done",
        'dlg_ok_body':    "yt-dlp was installed!\n\nClose this and reopen the program.",
    },
}

LANG = load_settings().get('lang', 'el')
if LANG not in STRINGS:
    LANG = 'el'


def T(key, **kw):
    s = STRINGS[LANG].get(key) or STRINGS['el'][key]
    return s.format(**kw) if kw else s


# ══════════════════════════════════════════════════════════════════════
#  yt-dlp
#  - Σαν script: αν λείπει, το εγκαθιστά με pip στην ΙΔΙΑ Python
#    (sys.executable) — όχι σε όποια τύχει να βρει το σκέτο "pip".
#  - Σαν .exe: το yt-dlp είναι ήδη μέσα. Αν έχει γίνει «Ενημέρωση»,
#    προτιμάμε το νεότερο από το %LOCALAPPDATA%\KatevaseTo\yt-dlp.zip.
# ══════════════════════════════════════════════════════════════════════

def _pip_install(*packages):
    cmd = [sys.executable, "-m", "pip", "install", "-U", *packages]
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    return subprocess.run(cmd, capture_output=True, text=True,
                          timeout=600, creationflags=flags)


def _forget_ytdlp_modules():
    for m in [m for m in sys.modules if m == 'yt_dlp' or m.startswith('yt_dlp.')]:
        del sys.modules[m]


def _load_ytdlp():
    # Νεότερο yt-dlp που κατέβηκε από την «Ενημέρωση» (μόνο στο .exe).
    if FROZEN and os.path.isfile(YTDLP_ZIP):
        sys.path.insert(0, YTDLP_ZIP)
        try:
            import yt_dlp
            return yt_dlp
        except Exception:
            # Π.χ. το νέο yt-dlp θέλει κάτι που δεν είναι μέσα στο .exe —
            # γυρνάμε σιωπηλά στην ενσωματωμένη έκδοση.
            sys.path.remove(YTDLP_ZIP)
            _forget_ytdlp_modules()

    try:
        import yt_dlp
        return yt_dlp
    except ImportError:
        pass

    if FROZEN:      # δεν θα έπρεπε να συμβεί ποτέ — είναι μέσα στο .exe
        raise

    root = tk.Tk(); root.withdraw()
    ok = mb.askyesno(T('dlg_miss_title'), T('dlg_miss_body', exe=sys.executable))
    if not ok:
        root.destroy()
        sys.exit(1)

    r = _pip_install("yt-dlp[default]")
    root.destroy()

    root2 = tk.Tk(); root2.withdraw()
    if r.returncode != 0:
        mb.showerror(T('dlg_fail_title'),
                     T('dlg_fail_body', cmd=f'"{sys.executable}" -m pip install -U yt-dlp'))
        sys.exit(1)
    mb.showinfo(T('dlg_ok_title'), T('dlg_ok_body'))
    sys.exit(0)


yt_dlp = _load_ytdlp()
try:
    YTDLP_VER = yt_dlp.version.__version__
except Exception:
    YTDLP_VER = "?"


# ══════════════════════════════════════════════════════════════════════
#  ΡΥΘΜΙΣΕΙΣ ΕΜΦΑΝΙΣΗΣ
# ══════════════════════════════════════════════════════════════════════

C = {
    'bg':     '#12121a', 'panel':  '#1c1c28', 'field': '#262636',
    'line':   '#33334a', 'accent': '#ff2d55', 'hover': '#ff5c7a',
    'ok':     '#2ee6a8', 'warn':   '#ffb627', 'err':   '#ff4d5e',
    'txt':    '#ecebf5', 'dim':    '#8b8ba7',
}

F_TITLE = ("Segoe UI Semibold", 16)
F_SUB   = ("Consolas", 8)
F_LBL   = ("Segoe UI", 9)
F_FLD   = ("Segoe UI", 10)
F_BTN   = ("Segoe UI Semibold", 11)
F_ST    = ("Segoe UI", 9)

HERE = os.path.dirname(os.path.abspath(sys.argv[0]))
Q = queue.Queue()      # το thread μιλάει στο GUI ΜΟΝΟ μέσω αυτής


# ══════════════════════════════════════════════════════════════════════
#  ΑΝΙΧΝΕΥΣΗ ΕΡΓΑΛΕΙΩΝ
# ══════════════════════════════════════════════════════════════════════

def find_ffmpeg():
    """ffmpeg: PATH → φάκελος δίπλα στο πρόγραμμα → φάκελος KatevaseTo
       (εκεί το βάζει το .exe) → πακέτο imageio-ffmpeg (εκεί το βάζει το pip)."""
    p = shutil.which("ffmpeg")
    if p:
        return p
    for base in (os.path.join(HERE, "ffmpeg"), FFMPEG_DIR):
        for sub in ("ffmpeg.exe", os.path.join("bin", "ffmpeg.exe"), "ffmpeg"):
            cand = os.path.join(base, sub)
            if os.path.isfile(cand):
                return cand
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.isfile(exe):
            return exe
    except Exception:
        pass
    return None


def find_js():
    """Το yt-dlp χρειάζεται JavaScript runtime για να λύσει τους «γρίφους»
       του YouTube. Επιστρέφει {όνομα: {'path': ...}} για ό,τι βρεθεί.
       ΠΡΟΣΟΧΗ: το yt-dlp ενεργοποιεί μόνο του ΜΟΝΟ το Deno — το Node
       πρέπει να του το δώσουμε ρητά, αλλιώς το αγνοεί."""
    found = {}
    for name in ("deno", "node", "bun"):
        p = shutil.which(name)
        if p:
            found[name] = {'path': p}
    return found


def has_firefox():
    """Υπάρχει προφίλ Firefox μ' αποθηκευμένα cookies;
       Μόνο ο Firefox δουλεύει: τα Chromium (Chrome/Edge/Brave/Opera)
       κλειδώνουν πλέον τα cookies τους με App-Bound Encryption."""
    roots = [os.path.join(os.environ.get('APPDATA', ''), 'Mozilla', 'Firefox', 'Profiles'),
             os.path.expanduser('~/.mozilla/firefox'),
             os.path.expanduser('~/Library/Application Support/Firefox/Profiles')]
    for r in roots:
        if r and os.path.isdir(r):
            for d in os.listdir(r):
                if os.path.isfile(os.path.join(r, d, 'cookies.sqlite')):
                    return True
    return False


FFMPEG = find_ffmpeg()
JSRT = find_js()
FIREFOX = has_firefox()

# Μηνύματα που σημαίνουν "το YouTube ζητάει σύνδεση"
BOT_SIGNS = ('sign in to confirm', 'not a bot', 'confirm your age',
             'use --cookies', 'login required', 'age-restricted')


# ══════════════════════════════════════════════════════════════════════
#  ΚΑΤΕΒΑΣΜΑ ΑΡΧΕΙΩΝ (για το .exe, όπου δεν υπάρχει pip)
# ══════════════════════════════════════════════════════════════════════

def http_download(url, dest):
    """Κατεβάζει σε προσωρινό αρχείο και το μετονομάζει μόνο αν
       ολοκληρωθεί — έτσι ένα κομμένο κατέβασμα δεν χαλάει τίποτα."""
    tmp = dest + ".part"
    req = urllib.request.Request(url, headers={'User-Agent': f'KatevaseTo/{VERSION}'})
    with urllib.request.urlopen(req, timeout=60) as r, open(tmp, 'wb') as f:
        total = int(r.headers.get('Content-Length') or 0)
        done = 0
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if total:
                Q.put(('progress', done / total * 100))
                Q.put(('status', T('st_dl_pct', pct=done / total * 100), 'dim'))
    os.replace(tmp, dest)


def update_ytdlp_frozen():
    """Το επίσημο yt-dlp (χωρίς .exe) είναι zip με κώδικα Python, που
       η Python μπορεί να το φορτώσει απευθείας από το sys.path."""
    url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
    tmp = YTDLP_ZIP + ".new"
    http_download(url, tmp)
    if not zipfile.is_zipfile(tmp):
        os.remove(tmp)
        raise RuntimeError("downloaded file is not a valid yt-dlp package")
    os.replace(tmp, YTDLP_ZIP)


def install_ffmpeg_frozen():
    """Παίρνουμε το ffmpeg.exe από το wheel του imageio-ffmpeg στο PyPI —
       το ίδιο αρχείο που θα έβαζε το pip, χωρίς να χρειάζεται pip."""
    if os.name != 'nt':
        raise OSError(T('st_ff_os'))
    with urllib.request.urlopen("https://pypi.org/pypi/imageio-ffmpeg/json", timeout=30) as r:
        info = json.load(r)
    tag = 'win_amd64' if sys.maxsize > 2**32 else 'win32'
    wheel_url = next(f['url'] for f in info['urls']
                     if f['packagetype'] == 'bdist_wheel' and tag in f['filename'])

    wheel = os.path.join(APPDIR, 'imageio_ffmpeg.whl')
    http_download(wheel_url, wheel)
    try:
        with zipfile.ZipFile(wheel) as z:
            member = next(n for n in z.namelist()
                          if n.startswith('imageio_ffmpeg/binaries/ffmpeg')
                          and n.endswith('.exe'))
            os.makedirs(FFMPEG_DIR, exist_ok=True)
            out = os.path.join(FFMPEG_DIR, 'ffmpeg.exe')
            with z.open(member) as src, open(out + '.part', 'wb') as dst:
                shutil.copyfileobj(src, dst)
            os.replace(out + '.part', out)
    finally:
        os.remove(wheel)


# ══════════════════════════════════════════════════════════════════════
#  ΛΟΓΙΚΗ ΚΑΤΕΒΑΣΜΑΤΟΣ  (ξεχωριστό thread)
# ══════════════════════════════════════════════════════════════════════

def hook(d):
    if d['status'] == 'downloading':
        total = d.get('total_bytes') or d.get('total_bytes_estimate')
        done = d.get('downloaded_bytes', 0)
        pct = (done / total * 100) if total else 0
        spd = d.get('speed')
        spd_s = f"{spd/1048576:.1f} MB/s" if spd else "..."
        Q.put(('progress', pct))
        Q.put(('status', T('st_downloading', pct=pct, done=done / 1048576,
                           total=(total or 0) / 1048576, spd=spd_s), 'dim'))
    elif d['status'] == 'finished':
        Q.put(('progress', 99))
        Q.put(('status', T('st_merging'), 'dim'))


def build_opts(save_path, mode, height, use_cookies):
    """height: None = μέγιστη ποιότητα, αλλιώς αριθμός (π.χ. 1080)."""
    opts = {
        'outtmpl': os.path.join(save_path, '%(title).180B.%(ext)s'),
        'progress_hooks': [hook],
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'noprogress': True,
        'retries': 10,
        'fragment_retries': 10,
        'windowsfilenames': True,
    }

    if FFMPEG:
        opts['ffmpeg_location'] = FFMPEG
    if JSRT:
        opts['js_runtimes'] = JSRT
    # Το script που λύνει τους γρίφους του YouTube (EJS). Αν δεν είναι
    # εγκατεστημένο (π.χ. μέσα στο .exe), το yt-dlp το κατεβάζει από το
    # GitHub. Χωρίς αυτό πολλά βίντεο βγάζουν «This video is not available».
    opts['remote_components'] = ['ejs:github']
    if use_cookies:
        opts['cookiesfrombrowser'] = ('firefox',)

    if mode == 'audio':
        if FFMPEG:
            opts['format'] = 'bestaudio/best'
            opts['postprocessors'] = [{'key': 'FFmpegExtractAudio',
                                       'preferredcodec': 'mp3',
                                       'preferredquality': '192'}]
        else:
            opts['format'] = 'bestaudio[ext=m4a]/bestaudio'
    else:
        if not FFMPEG:
            opts['format'] = 'best[ext=mp4]/best'
        elif height is None:
            opts['format'] = 'bestvideo+bestaudio/best'
            opts['merge_output_format'] = 'mp4'
        else:
            opts['format'] = (f'bestvideo[height<={height}]+bestaudio/'
                              f'best[height<={height}]/best')
            opts['merge_output_format'] = 'mp4'

    return opts


def friendly_error(msg):
    m = msg.lower()
    if 'could not copy' in m and 'cookie' in m:
        return T('err_cookie_copy')
    if 'dpapi' in m or 'failed to decrypt' in m:
        return T('err_dpapi')
    if any(s in m for s in BOT_SIGNS):
        return T('err_bot')
    if 'unable to extract' in m or 'player response' in m:
        return T('err_outdated')
    if 'private video' in m:
        return T('err_private')
    if 'video unavailable' in m or 'video is not available' in m:
        return T('err_unavail')
    if 'is not a valid url' in m or 'unsupported url' in m:
        return T('err_url')
    if 'ffmpeg' in m:
        return T('err_ffmpeg')
    if 'requested format' in m:
        return T('err_format')
    return msg.replace('ERROR: ', '').strip()[:160]


def _attempt(url, save_path, mode, height, use_cookies):
    with yt_dlp.YoutubeDL(build_opts(save_path, mode, height, use_cookies)) as ydl:
        ydl.download([url])


def worker(url, save_path, mode, height, allow_cookies):
    try:
        os.makedirs(save_path, exist_ok=True)
        Q.put(('status', T('st_connecting'), 'dim'))

        # Πρώτα χωρίς cookies — είναι πιο γρήγορο και δουλεύει συνήθως.
        # Μόνο αν το YouTube ζητήσει σύνδεση, ξαναδοκιμάζουμε με Firefox.
        try:
            _attempt(url, save_path, mode, height, False)
        except Exception as first:
            if (allow_cookies and FIREFOX
                    and any(s in str(first).lower() for s in BOT_SIGNS)):
                Q.put(('status', T('st_retry'), 'warn'))
                Q.put(('progress', 0))
                _attempt(url, save_path, mode, height, True)
            else:
                raise

        Q.put(('progress', 100))
        kind = (T('kind_mp3') if FFMPEG else T('kind_audio')) if mode == 'audio' \
            else T('kind_video')
        Q.put(('status', T('st_done', kind=kind), 'ok'))
    except Exception as e:
        Q.put(('status', friendly_error(str(e)), 'err'))
    finally:
        Q.put(('done', None))


def updater():
    try:
        Q.put(('status', T('st_updating'), 'dim'))
        if FROZEN:
            update_ytdlp_frozen()
            ok = True
        else:
            ok = _pip_install("yt-dlp[default]").returncode == 0
        Q.put(('status', T('st_updated') if ok else T('st_update_fail'),
               'ok' if ok else 'err'))
    except Exception:
        Q.put(('status', T('st_update_fail'), 'err'))
    finally:
        Q.put(('done', None))


def ffmpeg_installer():
    global FFMPEG
    try:
        Q.put(('status', T('st_ff_start'), 'dim'))
        if FROZEN:
            install_ffmpeg_frozen()
        elif _pip_install("imageio-ffmpeg").returncode != 0:
            Q.put(('status', T('st_ff_fail'), 'err'))
            return
        found = find_ffmpeg()
        if found:
            FFMPEG = found
            Q.put(('refresh', None))
            Q.put(('status', T('st_ff_ok'), 'ok'))
        else:
            Q.put(('status', T('st_ff_notfound'), 'warn'))
    except OSError as e:
        Q.put(('status', str(e) if os.name != 'nt' else T('st_ff_fail'), 'err'))
    except Exception as e:
        Q.put(('status', T('st_error', e=e), 'err'))
    finally:
        Q.put(('done', None))


# ══════════════════════════════════════════════════════════════════════
#  ΠΑΡΑΘΥΡΟ
# ══════════════════════════════════════════════════════════════════════

win = tk.Tk()
win.title("Katevase To")
win.configure(bg=C['bg'])
win.geometry("620x500")
win.resizable(False, False)

# Εικονίδιο παραθύρου / taskbar: το icon.ico δίπλα στο .py, ή μέσα στο
# .exe (το PyInstaller το βάζει στο sys._MEIPASS με --add-data).
for _base in (getattr(sys, '_MEIPASS', None), HERE):
    _ico = os.path.join(_base, 'icon.ico') if _base else None
    if _ico and os.path.isfile(_ico):
        try:
            win.iconbitmap(default=_ico)
        except tk.TclError:
            pass
        break

st = ttk.Style()
st.theme_use('clam')
st.configure("TEntry", fieldbackground=C['field'], foreground=C['txt'],
             insertcolor=C['accent'], bordercolor=C['line'],
             lightcolor=C['line'], darkcolor=C['line'], borderwidth=1, padding=8)
st.configure("TCombobox", fieldbackground=C['field'], background=C['field'],
             foreground=C['txt'], arrowcolor=C['dim'], bordercolor=C['line'],
             lightcolor=C['line'], darkcolor=C['line'], borderwidth=1, padding=6)
st.map("TCombobox", fieldbackground=[('readonly', C['field'])],
       selectbackground=[('readonly', C['field'])],
       selectforeground=[('readonly', C['txt'])])
win.option_add('*TCombobox*Listbox.background', C['field'])
win.option_add('*TCombobox*Listbox.foreground', C['txt'])
win.option_add('*TCombobox*Listbox.selectBackground', C['accent'])
st.configure("P.Horizontal.TProgressbar", troughcolor=C['field'],
             background=C['accent'], bordercolor=C['bg'],
             lightcolor=C['accent'], darkcolor=C['accent'], thickness=6)

# Κάθε widget με κείμενο γράφεται εδώ μαζί με το κλειδί μετάφρασής του,
# ώστε η αλλαγή γλώσσας να τα ξαναγράφει όλα με μία κίνηση.
I18N = []


def tr(widget, key):
    I18N.append((widget, key))
    widget.config(text=T(key))
    return widget


def flat_btn(parent, key, cmd, bg, fg, font=F_LBL, padx=14, pady=7):
    b = tk.Button(parent, command=cmd, font=font, bg=bg, fg=fg,
                  activebackground=C['hover'], activeforeground='white',
                  relief='flat', bd=0, padx=padx, pady=pady,
                  cursor='hand2', highlightthickness=0)
    b.bind('<Enter>', lambda e: b.config(bg=C['hover']) if str(b['state']) == 'normal' else None)
    b.bind('<Leave>', lambda e: b.config(bg=bg) if str(b['state']) == 'normal' else None)
    return tr(b, key)


def lbl(parent, key=None, fg=C['dim'], font=F_LBL):
    w = tk.Label(parent, bg=parent['bg'], fg=fg, font=font)
    return tr(w, key) if key else w


# ── Header ────────────────────────────────────────────────────────────
head = tk.Frame(win, bg=C['bg'])
head.pack(fill='x', padx=26, pady=(20, 0))
tk.Label(head, text="Katevase To", bg=C['bg'], fg=C['txt'], font=F_TITLE).pack(side='left')
tk.Label(head, text=f" v{VERSION}", bg=C['bg'], fg=C['accent'], font=F_SUB).pack(side='left', pady=(7, 0))
tk.Label(head, text=f"  ·  yt-dlp {YTDLP_VER}", bg=C['bg'], fg=C['line'],
         font=F_SUB).pack(side='left', pady=(7, 0))

flat_btn(head, 'btn_update', lambda: start(updater),
         C['panel'], C['dim'], padx=10, pady=4).pack(side='right')
flat_btn(head, 'lang_btn', lambda: toggle_lang(),
         C['panel'], C['dim'], padx=10, pady=4).pack(side='right', padx=(0, 6))

tk.Frame(win, bg=C['line'], height=1).pack(fill='x', padx=26, pady=(12, 0))

# ── Περιοχή προειδοποιήσεων ──────────────────────────────────────────
notices = tk.Frame(win, bg=C['bg'])
notices.pack(fill='x', padx=26, pady=(12, 0))


def make_notice(text_key, btn_key, cmd, color):
    bar = tk.Frame(notices, bg=C['panel'])
    inner = tk.Frame(bar, bg=C['panel'])
    inner.pack(fill='x', padx=12, pady=9)
    tr(tk.Label(inner, bg=C['panel'], fg=color, font=F_LBL, justify='left'),
       text_key).pack(side='left')
    b = flat_btn(inner, btn_key, cmd, C['accent'], 'white', padx=12, pady=5)
    b.pack(side='right')
    return bar, b


ff_bar, ff_btn = make_notice('ff_notice', 'ff_btn',
                             lambda: start(ffmpeg_installer), C['warn'])
js_bar, js_btn = make_notice('js_notice', 'js_btn',
                             lambda: webbrowser.open("https://nodejs.org/en/download"),
                             C['warn'])

# ── Body ──────────────────────────────────────────────────────────────
body = tk.Frame(win, bg=C['bg'])
body.pack(fill='both', expand=True, padx=26, pady=(14, 0))
body.columnconfigure(1, weight=1)

lbl(body, 'lbl_link').grid(row=0, column=0, sticky='w', pady=(0, 3))
url_entry = ttk.Entry(body, font=F_FLD)
url_entry.grid(row=1, column=0, columnspan=2, sticky='ew', ipady=2)
flat_btn(body, 'btn_paste', lambda: paste(), C['panel'], C['txt'],
         padx=12, pady=6).grid(row=1, column=2, padx=(8, 0))

lbl(body, 'lbl_folder').grid(row=2, column=0, sticky='w', pady=(14, 3))
path_entry = ttk.Entry(body, font=F_FLD)
path_entry.grid(row=3, column=0, columnspan=2, sticky='ew', ipady=2)
path_entry.insert(0, os.path.join(os.path.expanduser("~"), "Downloads"))
flat_btn(body, 'btn_browse', lambda: browse(), C['panel'], C['txt'],
         padx=12, pady=6).grid(row=3, column=2, padx=(8, 0))

opts = tk.Frame(body, bg=C['bg'])
opts.grid(row=4, column=0, columnspan=3, sticky='ew', pady=(16, 0))

mode_var = tk.StringVar(value='video')


def mk_toggle(parent, key, value):
    return tr(tk.Radiobutton(parent, value=value, variable=mode_var,
                             command=lambda: refresh_mode(), indicatoron=False,
                             font=F_LBL, width=11, bg=C['panel'], fg=C['dim'],
                             selectcolor=C['accent'], activebackground=C['field'],
                             activeforeground=C['txt'], relief='flat', bd=0,
                             padx=8, pady=7, cursor='hand2', highlightthickness=0),
              key)


mk_toggle(opts, 'mode_video', 'video').pack(side='left')
mk_toggle(opts, 'mode_audio', 'audio').pack(side='left', padx=(6, 20))

# label + dropdown μαζί σε ΕΝΑ frame, ώστε να κρύβονται/εμφανίζονται μαζί.
qual_frame = tk.Frame(opts, bg=C['bg'])
lbl(qual_frame, 'lbl_quality').pack(side='left', padx=(0, 6))
HEIGHTS = [None, 2160, 1440, 1080, 720, 480]       # None = μέγιστη


def quality_labels():
    return [T('q_max') if h is None else f"{h}p" for h in HEIGHTS]


qual_var = tk.StringVar(value=T('q_max'))
qual_box = ttk.Combobox(qual_frame, textvariable=qual_var, state='readonly',
                        width=10, values=quality_labels())
qual_box.pack(side='left')


def selected_height():
    """Η επιλογή αποθηκεύεται ως αριθμός, όχι ως κείμενο — έτσι δεν
       επηρεάζεται από τη γλώσσα."""
    v = qual_var.get()
    return int(v[:-1]) if v.endswith('p') and v[:-1].isdigit() else None


# ── Cookies: ένα απλό τικ, και το πρόγραμμα αποφασίζει πότε το χρειάζεται
ck = tk.Frame(body, bg=C['bg'])
ck.grid(row=5, column=0, columnspan=3, sticky='ew', pady=(14, 0))

cookie_var = tk.BooleanVar(value=FIREFOX)
cookie_chk = tr(tk.Checkbutton(
    ck, variable=cookie_var, font=F_LBL, bg=C['bg'], fg=C['txt'],
    selectcolor=C['field'], activebackground=C['bg'],
    activeforeground=C['txt'], bd=0, highlightthickness=0,
    cursor='hand2', anchor='w'), 'cookie_chk')
cookie_chk.pack(side='left')

cookie_hint = lbl(ck, fg=C['line'], font=F_SUB)
cookie_hint.pack(side='left', padx=(8, 0))

# ── Footer ────────────────────────────────────────────────────────────
foot = tk.Frame(win, bg=C['bg'])
foot.pack(fill='x', side='bottom', padx=26, pady=(0, 18))

go_btn = tr(tk.Button(foot, command=lambda: go(), font=F_BTN,
                      bg=C['accent'], fg='white', activebackground=C['hover'],
                      activeforeground='white', relief='flat', bd=0, pady=11,
                      cursor='hand2', highlightthickness=0), 'btn_go')
go_btn.pack(fill='x')
go_btn.bind('<Enter>', lambda e: go_btn.config(bg=C['hover']) if str(go_btn['state']) == 'normal' else None)
go_btn.bind('<Leave>', lambda e: go_btn.config(bg=C['accent']) if str(go_btn['state']) == 'normal' else None)

status = tk.Label(foot, text="", bg=C['bg'], fg=C['dim'], font=F_ST,
                  wraplength=560, justify='center')
status.pack(fill='x', side='bottom', pady=(9, 0))

prog_var = tk.DoubleVar(value=0)
prog = ttk.Progressbar(foot, variable=prog_var, maximum=100,
                       style="P.Horizontal.TProgressbar")


# ══════════════════════════════════════════════════════════════════════
#  ΕΝΕΡΓΕΙΕΣ
# ══════════════════════════════════════════════════════════════════════

BUSY = False


def show_prog(on):
    # Πάντα ρητά πριν το status, αλλιώς το Tk το ξαναβάζει στο τέλος
    # του frame και φεύγει εκτός παραθύρου.
    prog.pack(fill='x', pady=(10, 0), before=status) if on else prog.pack_forget()


def refresh_mode():
    if mode_var.get() == 'video':
        qual_frame.pack(side='left')
    else:
        qual_frame.pack_forget()


def refresh_notices():
    for bar, missing in ((ff_bar, not FFMPEG), (js_bar, not JSRT)):
        bar.pack_forget()
        if missing:
            bar.pack(fill='x', pady=(0, 6))
    if FFMPEG:
        qual_box.config(values=quality_labels(), state='readonly')
    else:
        qual_box.config(values=["720p"], state='disabled')
        qual_var.set("720p")


def refresh_cookies():
    if FIREFOX:
        cookie_hint.config(text=T('cookie_hint_ok'))
    else:
        cookie_var.set(False)
        cookie_chk.config(state='disabled', fg=C['line'])
        cookie_hint.config(text=T('cookie_hint_no'))


def toggle_lang():
    global LANG
    h = selected_height()                     # κράτα την επιλεγμένη ποιότητα
    LANG = 'en' if LANG == 'el' else 'el'
    save_settings(lang=LANG)
    for w, key in I18N:
        w.config(text=T(key))
    if BUSY:
        go_btn.config(text=T('btn_wait'))
    refresh_cookies()
    refresh_notices()
    if FFMPEG:
        qual_var.set(T('q_max') if h is None else f"{h}p")
    status.config(text="")


def paste():
    try:
        url_entry.delete(0, tk.END)
        url_entry.insert(0, win.clipboard_get().strip())
    except tk.TclError:
        pass


def browse():
    f = filedialog.askdirectory()
    if f:
        path_entry.delete(0, tk.END)
        path_entry.insert(0, f)


def start(target, *args):
    global BUSY
    BUSY = True
    go_btn.config(state='disabled', bg=C['line'], text=T('btn_wait'))
    ff_btn.config(state='disabled', bg=C['line'])
    prog_var.set(0)
    show_prog(True)
    threading.Thread(target=target, args=args, daemon=True).start()


def go():
    url = url_entry.get().strip()
    if not url:
        status.config(text=T('st_need_link'), fg=C['err'])
        return
    path = path_entry.get().strip() or os.path.join(os.path.expanduser("~"), "Downloads")
    start(worker, url, path, mode_var.get(), selected_height(), cookie_var.get())


def pump():
    """Μόνο αυτή αγγίζει το GUI — τρέχει στο main thread."""
    global BUSY
    try:
        while True:
            kind, *rest = Q.get_nowait()
            if kind == 'status':
                status.config(text=rest[0], fg=C[rest[1]])
            elif kind == 'progress':
                prog_var.set(rest[0])
            elif kind == 'refresh':
                refresh_notices()
            elif kind == 'done':
                BUSY = False
                go_btn.config(state='normal', bg=C['accent'], text=T('btn_go'))
                ff_btn.config(state='normal', bg=C['accent'])
                show_prog(False)
    except queue.Empty:
        pass
    win.after(120, pump)


# ── Εκκίνηση ──────────────────────────────────────────────────────────
refresh_mode()
refresh_notices()
refresh_cookies()
url_entry.focus()
win.bind('<Return>', lambda e: go() if str(go_btn['state']) == 'normal' else None)
win.after(120, pump)
win.mainloop()
