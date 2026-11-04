"""
Katevase To v1.3
Απλός YouTube downloader (βίντεο MP4 / ήχος MP3)

ΤΡΕΞΙΜΟ:
    Διπλό κλικ στο "Katevase To.bat"
    (ή: py -3.14 katevase_to_1.3.py)

Τι χρειάζεται — τα βλέπεις και μέσα στο πρόγραμμα:
    yt-dlp    → το βάζει μόνο του
    ffmpeg    → το βάζει μόνο του με κουμπί
    Node.js   → χρειάζεται για αναλύσεις πάνω από 720p
"""

import os
import sys
import queue
import shutil
import threading
import subprocess
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog
import tkinter.messagebox as mb


# ══════════════════════════════════════════════════════════════════════
#  ΕΛΕΓΧΟΣ ΒΙΒΛΙΟΘΗΚΩΝ
#  Αν λείπει το yt-dlp, το εγκαθιστά στην ΙΔΙΑ Python που τρέχει τώρα
#  (sys.executable) — όχι σε όποια τύχει να βρει το σκέτο "pip".
# ══════════════════════════════════════════════════════════════════════

def _pip_install(*packages):
    cmd = [sys.executable, "-m", "pip", "install", "-U", *packages]
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    return subprocess.run(cmd, capture_output=True, text=True,
                          timeout=600, creationflags=flags)


def _ensure_ytdlp():
    try:
        import yt_dlp  # noqa: F401
        return
    except ImportError:
        pass

    root = tk.Tk(); root.withdraw()
    ok = mb.askyesno(
        "Λείπει το yt-dlp",
        "Το yt-dlp δεν βρέθηκε σ' αυτή την Python:\n\n"
        f"{sys.executable}\n\n"
        "(Αν το είχες εγκαταστήσει, μπήκε σε άλλη Python του PC.)\n\n"
        "Να το εγκαταστήσω τώρα εδώ;")
    if not ok:
        sys.exit(1)

    r = _pip_install("yt-dlp")
    root.destroy()

    if r.returncode != 0:
        root2 = tk.Tk(); root2.withdraw()
        mb.showerror("Απέτυχε",
                     "Η εγκατάσταση δεν ολοκληρώθηκε.\n\n"
                     "Τρέξε χειροκίνητα στο cmd:\n\n"
                     f'"{sys.executable}" -m pip install -U yt-dlp')
        sys.exit(1)

    root3 = tk.Tk(); root3.withdraw()
    mb.showinfo("Έτοιμο", "Το yt-dlp εγκαταστάθηκε!\n\n"
                          "Κλείσε αυτό και ξανάνοιξε το πρόγραμμα.")
    sys.exit(0)


_ensure_ytdlp()
import yt_dlp


# ══════════════════════════════════════════════════════════════════════
#  ΡΥΘΜΙΣΕΙΣ
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
    """ffmpeg: PATH → φάκελος δίπλα στο script → πακέτο imageio-ffmpeg."""
    p = shutil.which("ffmpeg")
    if p:
        return p
    for sub in ("ffmpeg.exe", os.path.join("bin", "ffmpeg.exe"), "ffmpeg"):
        cand = os.path.join(HERE, "ffmpeg", sub)
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
    """Το yt-dlp χρειάζεται JavaScript runtime για να ξεκλειδώσει τις
       μεγάλες αναλύσεις. Node.js ή Deno — ό,τι βρεθεί."""
    return shutil.which("node") or shutil.which("deno")


FFMPEG = find_ffmpeg()
JSRT = find_js()


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
        Q.put(('status', f"Κατεβαίνει  {pct:.0f}%   "
                         f"({done/1048576:.1f}/{(total or 0)/1048576:.1f} MB)   "
                         f"{spd_s}", 'dim'))
    elif d['status'] == 'finished':
        Q.put(('progress', 99))
        Q.put(('status', "Ένωση βίντεο + ήχου... (λίγη υπομονή)", 'dim'))


def build_opts(save_path, mode, quality, browser):
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

    if browser and browser.startswith("Firefox"):
        opts['cookiesfrombrowser'] = ('firefox',)
    elif browser and browser != "— κανένας —":
        opts['cookiesfrombrowser'] = (browser.split()[0].lower(),)

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
        elif quality == 'Μέγιστη':
            opts['format'] = 'bestvideo+bestaudio/best'
            opts['merge_output_format'] = 'mp4'
        else:
            h = quality.replace('p', '')
            opts['format'] = (f'bestvideo[height<={h}]+bestaudio/'
                              f'best[height<={h}]/best')
            opts['merge_output_format'] = 'mp4'

    return opts


def friendly_error(msg):
    m = msg.lower()
    if 'could not copy' in m and 'cookie' in m:
        return ("Το Chrome κλειδώνει τα cookies του και δεν μπορώ να τα "
                "διαβάσω. Διάλεξε Firefox, ή άσε «κανένας».")
    if 'dpapi' in m or 'failed to decrypt' in m:
        return ("Το Chrome κρυπτογραφεί πλέον τα cookies του και κανένα "
                "εξωτερικό πρόγραμμα δεν τα διαβάζει. Χρησιμοποίησε Firefox.")
    if 'sign in to confirm' in m or 'not a bot' in m:
        return ("Το YouTube μπλόκαρε το αίτημα. Διάλεξε Firefox στο πεδίο "
                "«Cookies» (συνδεδεμένος στο YouTube) και ξαναδοκίμασε.")
    if 'unable to extract' in m or 'player response' in m:
        return ("Το yt-dlp είναι παλιό για τις τωρινές αλλαγές του YouTube. "
                "Πάτα «Ενημέρωση» πάνω δεξιά.")
    if 'private video' in m:
        return "Το βίντεο είναι ιδιωτικό."
    if 'video unavailable' in m:
        return "Το βίντεο δεν είναι διαθέσιμο (ή μπλοκαρισμένο στην Ελλάδα)."
    if 'is not a valid url' in m or 'unsupported url' in m:
        return "Το link δεν φαίνεται σωστό."
    if 'ffmpeg' in m:
        return "Λείπει το ffmpeg. Πάτα το κουμπί «Εγκατάσταση ffmpeg»."
    if 'requested format' in m:
        return "Αυτή η ανάλυση δεν υπάρχει γι' αυτό το βίντεο. Δοκίμασε άλλη."
    return msg.replace('ERROR: ', '').strip()[:160]


def worker(url, save_path, mode, quality, browser):
    try:
        os.makedirs(save_path, exist_ok=True)
        Q.put(('status', "Σύνδεση με YouTube...", 'dim'))
        with yt_dlp.YoutubeDL(build_opts(save_path, mode, quality, browser)) as ydl:
            ydl.download([url])
        Q.put(('progress', 100))
        kind = ("MP3" if FFMPEG else "αρχείο ήχου") if mode == 'audio' else "βίντεο"
        Q.put(('status', f"Έτοιμο! Το {kind} αποθηκεύτηκε. ✅", 'ok'))
    except Exception as e:
        Q.put(('status', friendly_error(str(e)), 'err'))
    finally:
        Q.put(('done', None))


def updater():
    try:
        Q.put(('status', "Ενημέρωση yt-dlp...", 'dim'))
        r = _pip_install("yt-dlp")
        Q.put(('status',
               "Ενημερώθηκε! Κλείσε και ξανάνοιξε το πρόγραμμα." if r.returncode == 0
               else "Η ενημέρωση απέτυχε — έλεγξε τη σύνδεσή σου.",
               'ok' if r.returncode == 0 else 'err'))
    except Exception as e:
        Q.put(('status', f"Η ενημέρωση απέτυχε: {e}", 'err'))
    finally:
        Q.put(('done', None))


def ffmpeg_installer():
    global FFMPEG
    try:
        Q.put(('status', "Κατέβασμα ffmpeg... (~30 MB, μια φορά μόνο)", 'dim'))
        r = _pip_install("imageio-ffmpeg")
        if r.returncode != 0:
            Q.put(('status', "Η εγκατάσταση απέτυχε — έλεγξε τη σύνδεσή σου.", 'err'))
            return
        found = find_ffmpeg()
        if found:
            FFMPEG = found
            Q.put(('refresh', None))
            Q.put(('status', "Το ffmpeg εγκαταστάθηκε! ✅", 'ok'))
        else:
            Q.put(('status', "Εγκαταστάθηκε αλλά δεν το βρίσκω. "
                             "Ξανάνοιξε το πρόγραμμα.", 'warn'))
    except Exception as e:
        Q.put(('status', f"Σφάλμα: {e}", 'err'))
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


def flat_btn(parent, text, cmd, bg, fg, font=F_LBL, padx=14, pady=7):
    b = tk.Button(parent, text=text, command=cmd, font=font, bg=bg, fg=fg,
                  activebackground=C['hover'], activeforeground='white',
                  relief='flat', bd=0, padx=padx, pady=pady,
                  cursor='hand2', highlightthickness=0)
    b.bind('<Enter>', lambda e: b.config(bg=C['hover']) if str(b['state']) == 'normal' else None)
    b.bind('<Leave>', lambda e: b.config(bg=bg) if str(b['state']) == 'normal' else None)
    return b


def lbl(parent, text, fg=C['dim'], font=F_LBL):
    return tk.Label(parent, text=text, bg=parent['bg'], fg=fg, font=font)


# ── Header ────────────────────────────────────────────────────────────
head = tk.Frame(win, bg=C['bg'])
head.pack(fill='x', padx=26, pady=(20, 0))
tk.Label(head, text="Katevase To", bg=C['bg'], fg=C['txt'], font=F_TITLE).pack(side='left')
tk.Label(head, text=" v1.3", bg=C['bg'], fg=C['accent'], font=F_SUB).pack(side='left', pady=(7, 0))
flat_btn(head, "⟳ Ενημέρωση", lambda: start(updater),
         C['panel'], C['dim'], padx=10, pady=4).pack(side='right')

tk.Frame(win, bg=C['line'], height=1).pack(fill='x', padx=26, pady=(12, 0))

# ── Περιοχή προειδοποιήσεων ──────────────────────────────────────────
notices = tk.Frame(win, bg=C['bg'])
notices.pack(fill='x', padx=26, pady=(12, 0))


def make_notice(text, btn_text, cmd, color):
    bar = tk.Frame(notices, bg=C['panel'])
    inner = tk.Frame(bar, bg=C['panel'])
    inner.pack(fill='x', padx=12, pady=9)
    tk.Label(inner, text=text, bg=C['panel'], fg=color,
             font=F_LBL, justify='left').pack(side='left')
    b = flat_btn(inner, btn_text, cmd, C['accent'], 'white', padx=12, pady=5)
    b.pack(side='right')
    return bar, b


ff_bar, ff_btn = make_notice("⚠  Λείπει το ffmpeg → μόνο 720p, χωρίς MP3",
                             "Εγκατάσταση", lambda: start(ffmpeg_installer),
                             C['warn'])

js_bar, js_btn = make_notice("⚠  Λείπει το Node.js → το YouTube κρύβει τα 1080p+",
                             "Κατέβασέ το",
                             lambda: webbrowser.open("https://nodejs.org/en/download"),
                             C['warn'])

# ── Body ──────────────────────────────────────────────────────────────
body = tk.Frame(win, bg=C['bg'])
body.pack(fill='both', expand=True, padx=26, pady=(14, 0))
body.columnconfigure(1, weight=1)

lbl(body, "Link").grid(row=0, column=0, sticky='w', pady=(0, 3))
url_entry = ttk.Entry(body, font=F_FLD)
url_entry.grid(row=1, column=0, columnspan=2, sticky='ew', ipady=2)
flat_btn(body, "Επικόλληση", lambda: paste(), C['panel'], C['txt'],
         padx=12, pady=6).grid(row=1, column=2, padx=(8, 0))

lbl(body, "Φάκελος").grid(row=2, column=0, sticky='w', pady=(14, 3))
path_entry = ttk.Entry(body, font=F_FLD)
path_entry.grid(row=3, column=0, columnspan=2, sticky='ew', ipady=2)
path_entry.insert(0, os.path.join(os.path.expanduser("~"), "Downloads"))
flat_btn(body, "Αλλαγή", lambda: browse(), C['panel'], C['txt'],
         padx=12, pady=6).grid(row=3, column=2, padx=(8, 0))

opts = tk.Frame(body, bg=C['bg'])
opts.grid(row=4, column=0, columnspan=3, sticky='ew', pady=(16, 0))

mode_var = tk.StringVar(value='video')


def mk_toggle(parent, text, value):
    return tk.Radiobutton(parent, text=text, value=value, variable=mode_var,
                          command=lambda: refresh_mode(), indicatoron=False,
                          font=F_LBL, width=11, bg=C['panel'], fg=C['dim'],
                          selectcolor=C['accent'], activebackground=C['field'],
                          activeforeground=C['txt'], relief='flat', bd=0,
                          padx=8, pady=7, cursor='hand2', highlightthickness=0)


mk_toggle(opts, "Βίντεο  MP4", 'video').pack(side='left')
mk_toggle(opts, "Ήχος  MP3", 'audio').pack(side='left', padx=(6, 20))

qual_lbl = lbl(opts, "Ποιότητα")
qual_lbl.pack(side='left', padx=(0, 6))
qual_var = tk.StringVar(value="Μέγιστη")
ALL_Q = ["Μέγιστη", "2160p", "1440p", "1080p", "720p", "480p"]
qual_box = ttk.Combobox(opts, textvariable=qual_var, state='readonly',
                        width=10, values=ALL_Q)
qual_box.pack(side='left')

ck = tk.Frame(body, bg=C['bg'])
ck.grid(row=5, column=0, columnspan=3, sticky='ew', pady=(12, 0))
lbl(ck, "Cookies από").pack(side='left', padx=(0, 8))
ck_var = tk.StringVar(value="— κανένας —")
ttk.Combobox(ck, textvariable=ck_var, state='readonly', width=22,
             values=["— κανένας —", "Firefox  (δουλεύει)",
                     "Chrome  (δεν δουλεύει πια)",
                     "Edge  (δεν δουλεύει πια)",
                     "Brave  (δεν δουλεύει πια)"]).pack(side='left')
lbl(ck, "← μόνο αν σου βγάζει μπλόκο", fg=C['line'],
    font=F_SUB).pack(side='left', padx=(8, 0))

# ── Footer ────────────────────────────────────────────────────────────
foot = tk.Frame(win, bg=C['bg'])
foot.pack(fill='x', side='bottom', padx=26, pady=(0, 18))

go_btn = tk.Button(foot, text="ΚΑΤΕΒΑΣΜΑ", command=lambda: go(), font=F_BTN,
                   bg=C['accent'], fg='white', activebackground=C['hover'],
                   activeforeground='white', relief='flat', bd=0, pady=11,
                   cursor='hand2', highlightthickness=0)
go_btn.pack(fill='x')
go_btn.bind('<Enter>', lambda e: go_btn.config(bg=C['hover']) if str(go_btn['state']) == 'normal' else None)
go_btn.bind('<Leave>', lambda e: go_btn.config(bg=C['accent']) if str(go_btn['state']) == 'normal' else None)

status = tk.Label(foot, text="", bg=C['bg'], fg=C['dim'], font=F_ST,
                  wraplength=560, justify='center')
status.pack(fill='x', side='bottom', pady=(9, 0))

prog_var = tk.DoubleVar(value=0)
prog = ttk.Progressbar(foot, variable=prog_var, maximum=100,
                       style="P.Horizontal.TProgressbar")
# ΔΙΟΡΘΩΣΗ: παλιά έκανα pack_forget() και μετά pack() σκέτο — το Tk το
# ξανάβαζε στο ΤΕΛΟΣ του frame, κάτω από το status, εκτός παραθύρου.
# Τώρα μπαίνει πάντα ρητά πριν το status.


# ══════════════════════════════════════════════════════════════════════
#  ΕΝΕΡΓΕΙΕΣ
# ══════════════════════════════════════════════════════════════════════

def show_prog(on):
    if on:
        prog.pack(fill='x', pady=(10, 0), before=status)
    else:
        prog.pack_forget()


def refresh_mode():
    if mode_var.get() == 'video':
        qual_lbl.pack(side='left', padx=(0, 6), before=qual_box)
        qual_box.pack(side='left')
    else:
        qual_lbl.pack_forget()
        qual_box.pack_forget()


def refresh_notices():
    for bar, missing in ((ff_bar, not FFMPEG), (js_bar, not JSRT)):
        bar.pack_forget()
        if missing:
            bar.pack(fill='x', pady=(0, 6))
    if FFMPEG:
        qual_box.config(values=ALL_Q, state='readonly')
    else:
        qual_box.config(values=["720p"], state='disabled')
        qual_var.set("720p")


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
    go_btn.config(state='disabled', bg=C['line'], text="ΠΕΡΙΜΕΝΕ...")
    ff_btn.config(state='disabled', bg=C['line'])
    prog_var.set(0)
    show_prog(True)
    threading.Thread(target=target, args=args, daemon=True).start()


def go():
    url = url_entry.get().strip()
    if not url:
        status.config(text="Βάλε πρώτα ένα link!", fg=C['err'])
        return
    path = path_entry.get().strip() or os.path.join(os.path.expanduser("~"), "Downloads")
    start(worker, url, path, mode_var.get(), qual_var.get(), ck_var.get())


def pump():
    """Μόνο αυτή αγγίζει το GUI — τρέχει στο main thread."""
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
                go_btn.config(state='normal', bg=C['accent'], text="ΚΑΤΕΒΑΣΜΑ")
                ff_btn.config(state='normal', bg=C['accent'])
                show_prog(False)
    except queue.Empty:
        pass
    win.after(120, pump)


# ── Εκκίνηση ──────────────────────────────────────────────────────────
refresh_mode()
refresh_notices()
url_entry.focus()
win.bind('<Return>', lambda e: go() if str(go_btn['state']) == 'normal' else None)
win.after(120, pump)
win.mainloop()
