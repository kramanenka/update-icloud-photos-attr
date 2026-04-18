"""
ui.py

Modern Tkinter GUI for the iCloud Photos Attribute Updater.
- Flat, light design with accent colour
- White log area with coloured text
- Last selected folder is remembered across runs (saved to settings.json)
"""

import json
import os
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk
from datetime import datetime

from src.processor import process_folder, load_failed_list

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_FOLDER   = r'c:\Documents\Photo\_NEW\iCloud Photos - test'
SETTINGS_FILE    = os.path.join(os.path.dirname(__file__), '..', 'settings.json')

_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(_APP_DIR, 'logs')

# Palette
C_BG          = '#f5f6f8'   # window background
C_SURFACE     = '#ffffff'   # card / panel background
C_BORDER      = '#dde1e7'   # subtle borders
C_ACCENT      = '#2563eb'   # primary blue
C_ACCENT_HOV  = '#1d4ed8'   # hover
C_TEXT        = '#1e293b'   # primary text
C_TEXT_MUTED  = '#64748b'   # secondary text
C_OK          = '#16a34a'   # green
C_SKIP        = '#d97706'   # amber
C_ERR         = '#dc2626'   # red
C_SEP         = '#94a3b8'   # separator / info


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_settings() -> dict:
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _save_settings(data: dict) -> None:
    try:
        existing = _load_settings()
        existing.update(data)
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(existing, f, indent=2)
    except Exception:
        pass


def _load_last_folder() -> str:
    data = _load_settings()
    folder = data.get('last_folder', '')
    if folder and os.path.isdir(folder):
        return folder
    return DEFAULT_FOLDER if os.path.isdir(DEFAULT_FOLDER) else ''


def _save_last_folder(folder: str) -> None:
    _save_settings({'last_folder': folder})


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('iCloud Photos Attribute Updater')
        self.configure(bg=C_BG)
        self.minsize(780, 560)
        self.resizable(True, True)
        self._apply_style()
        self._build_ui()
        self._center_window(900, 620)

    # ------------------------------------------------------------------
    # Style
    # ------------------------------------------------------------------

    def _apply_style(self):
        style = ttk.Style(self)
        style.theme_use('clam')

        style.configure('TProgressbar',
                         troughcolor=C_BORDER,
                         background=C_ACCENT,
                         bordercolor=C_BORDER,
                         lightcolor=C_ACCENT,
                         darkcolor=C_ACCENT,
                         thickness=6)

    def _center_window(self, w: int, h: int):
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f'{w}x{h}+{x}+{y}')

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        outer = tk.Frame(self, bg=C_BG)
        outer.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # ── Header ──────────────────────────────────────────────────────
        hdr = tk.Frame(outer, bg=C_BG)
        hdr.pack(fill=tk.X, pady=(0, 16))

        tk.Label(
            hdr, text='iCloud Photos Attribute Updater',
            bg=C_BG, fg=C_TEXT,
            font=('Segoe UI', 15, 'bold'),
        ).pack(side=tk.LEFT)

        tk.Label(
            hdr, text='Updates file timestamps from embedded metadata',
            bg=C_BG, fg=C_TEXT_MUTED,
            font=('Segoe UI', 9),
        ).pack(side=tk.LEFT, padx=(12, 0), pady=(4, 0))

        # ── Folder card ─────────────────────────────────────────────────
        card = tk.Frame(outer, bg=C_SURFACE, relief='flat', bd=1,
                        highlightbackground=C_BORDER, highlightthickness=1)
        card.pack(fill=tk.X, pady=(0, 14))

        inner = tk.Frame(card, bg=C_SURFACE)
        inner.pack(fill=tk.X, padx=14, pady=12)

        tk.Label(inner, text='Source folder', bg=C_SURFACE, fg=C_TEXT_MUTED,
                 font=('Segoe UI', 8)).grid(row=0, column=0, columnspan=3, sticky='w')

        self.folder_var = tk.StringVar(value=_load_last_folder())

        folder_entry = tk.Entry(
            inner, textvariable=self.folder_var,
            font=('Segoe UI', 10),
            bg=C_BG, fg=C_TEXT,
            relief='flat', bd=0,
            highlightbackground=C_BORDER, highlightthickness=1,
            disabledbackground=C_BG,
        )
        folder_entry.grid(row=1, column=0, sticky='ew', pady=(4, 0), ipady=5, padx=(0, 8))

        browse_btn = tk.Button(
            inner, text='Browse…',
            font=('Segoe UI', 9),
            bg=C_BG, fg=C_ACCENT,
            activebackground=C_BORDER, activeforeground=C_ACCENT,
            relief='flat', bd=1, cursor='hand2',
            highlightbackground=C_BORDER, highlightthickness=1,
            padx=10, pady=4,
            command=self._browse,
        )
        browse_btn.grid(row=1, column=1, sticky='e', pady=(4, 0))

        inner.columnconfigure(0, weight=1)

        # ── Progress bar ────────────────────────────────────────────────
        prog_frame = tk.Frame(outer, bg=C_BG)
        prog_frame.pack(fill=tk.X, pady=(0, 10))

        self.progress = ttk.Progressbar(prog_frame, orient=tk.HORIZONTAL, mode='determinate')
        self.progress.pack(fill=tk.X)

        # ── Bottom bar ──────────────────────────────────────────────────
        bottom = tk.Frame(outer, bg=C_BG)
        bottom.pack(fill=tk.X, side=tk.BOTTOM, pady=(8, 0))

        self.status_var = tk.StringVar(value='Ready')
        tk.Label(bottom, textvariable=self.status_var,
                 bg=C_BG, fg=C_TEXT_MUTED,
                 font=('Segoe UI', 9)).pack(side=tk.LEFT, expand=True, fill=tk.X)

        clear_btn = tk.Button(
            bottom, text='Clear log',
            font=('Segoe UI', 9),
            bg=C_BG, fg=C_TEXT_MUTED,
            activebackground=C_BORDER, activeforeground=C_TEXT,
            relief='flat', bd=1, cursor='hand2',
            highlightbackground=C_BORDER, highlightthickness=1,
            padx=12, pady=5,
            command=self._clear_log,
        )
        clear_btn.pack(side=tk.LEFT, padx=(0, 8))

        settings = _load_settings()

        self.only_selected_var = tk.BooleanVar(value=settings.get('only_selected', True))
        only_selected_cb = tk.Checkbutton(
            bottom, text='Selected files only',
            variable=self.only_selected_var,
            command=lambda: _save_settings({'only_selected': self.only_selected_var.get()}),
            bg=C_BG, fg=C_TEXT_MUTED,
            activebackground=C_BG, activeforeground=C_TEXT,
            selectcolor=C_BG,
            font=('Segoe UI', 9),
            relief='flat', bd=0, cursor='hand2',
        )
        only_selected_cb.pack(side=tk.LEFT, padx=(0, 6))

        self.recursive_var = tk.BooleanVar(value=settings.get('recursive', False))
        recursive_cb = tk.Checkbutton(
            bottom, text='Include subdirectories',
            variable=self.recursive_var,
            command=lambda: _save_settings({'recursive': self.recursive_var.get()}),
            bg=C_BG, fg=C_TEXT_MUTED,
            activebackground=C_BG, activeforeground=C_TEXT,
            selectcolor=C_BG,
            font=('Segoe UI', 9),
            relief='flat', bd=0, cursor='hand2',
        )
        recursive_cb.pack(side=tk.LEFT, padx=(0, 10))

        self.start_btn = tk.Button(
            bottom, text='▶   Start',
            font=('Segoe UI', 10, 'bold'),
            bg=C_ACCENT, fg='white',
            activebackground=C_ACCENT_HOV, activeforeground='white',
            relief='flat', bd=0, cursor='hand2',
            padx=20, pady=6,
            command=self._start,
        )
        self.start_btn.pack(side=tk.LEFT)

        # Hover effects
        _bind_hover(self.start_btn, C_ACCENT, C_ACCENT_HOV, 'white', 'white')

        # ── Log area ────────────────────────────────────────────────────
        log_card = tk.Frame(outer, bg=C_SURFACE,
                            highlightbackground=C_BORDER, highlightthickness=1)
        log_card.pack(fill=tk.BOTH, expand=True, pady=(0, 14))

        log_header = tk.Frame(log_card, bg=C_BG,
                              highlightbackground=C_BORDER, highlightthickness=0)
        log_header.pack(fill=tk.X)

        tk.Label(log_header, text='  Execution log', bg=C_BG, fg=C_TEXT_MUTED,
                 font=('Segoe UI', 8), pady=5).pack(side=tk.LEFT)

        self.log_box = scrolledtext.ScrolledText(
            log_card,
            state=tk.DISABLED,
            font=('Consolas', 9),
            wrap=tk.WORD,
            bg=C_SURFACE,
            fg=C_TEXT,
            relief='flat',
            bd=0,
            padx=10,
            pady=8,
            spacing1=1,
            spacing3=1,
        )
        self.log_box.pack(fill=tk.BOTH, expand=True)

        # Colour tags
        self.log_box.tag_config('ok',   foreground=C_OK,       font=('Consolas', 9))
        self.log_box.tag_config('skip', foreground=C_SKIP,     font=('Consolas', 9))
        self.log_box.tag_config('err',  foreground=C_ERR,      font=('Consolas', 9, 'bold'))
        self.log_box.tag_config('info', foreground=C_TEXT,     font=('Consolas', 9))
        self.log_box.tag_config('sep',  foreground=C_SEP,      font=('Consolas', 9))
        self.log_box.tag_config('sum',  foreground=C_ACCENT,   font=('Consolas', 9, 'bold'))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _browse(self):
        initial = self.folder_var.get().strip() or DEFAULT_FOLDER
        folder = filedialog.askdirectory(
            title='Select folder with photos/videos',
            initialdir=initial,
        )
        if folder:
            self.folder_var.set(folder)
            _save_last_folder(folder)

    def _clear_log(self):
        self.log_box.configure(state=tk.NORMAL)
        self.log_box.delete('1.0', tk.END)
        self.log_box.configure(state=tk.DISABLED)

    def _start(self):
        folder = self.folder_var.get().strip()
        if not folder:
            self._log('Please select a folder first.', tag='err')
            return

        _save_last_folder(folder)
        self.start_btn.configure(state=tk.DISABLED)
        self.progress['value'] = 0
        self.status_var.set('Processing…')
        self._clear_log()

        only_files = None
        if self.only_selected_var.get():
            only_files = load_failed_list()
            if not only_files:
                self._log('No files in selected_list.txt (app folder).', tag='skip')
                self.start_btn.configure(state=tk.NORMAL)
                return

        recursive = self.recursive_var.get()

        thread = threading.Thread(
            target=self._run_processing,
            args=(folder,),
            kwargs={'only_files': only_files, 'recursive': recursive},
            daemon=True,
        )
        thread.start()

    def _run_processing(self, folder: str, only_files=None, recursive=False):
        log_lines = []

        def log(msg: str):
            log_lines.append(msg)
            self.after(0, self._log, msg)

        def progress(current: int, total: int):
            pct = int(current / total * 100) if total else 0
            self.after(0, self._set_progress, pct)

        process_folder(folder, log_callback=log, progress_callback=progress,
                       only_files=only_files, recursive=recursive)
        self._save_log(log_lines)
        self.after(0, self._on_done)

    def _save_log(self, lines: list[str]):
        try:
            os.makedirs(LOGS_DIR, exist_ok=True)
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            log_path = os.path.join(LOGS_DIR, f'run_{timestamp}.log')
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
        except Exception:
            pass

    def _on_done(self):
        self.start_btn.configure(state=tk.NORMAL)
        self.progress['value'] = 100
        self.status_var.set('Finished')

    # ------------------------------------------------------------------
    # Log helpers
    # ------------------------------------------------------------------

    def _log(self, message: str, tag: str = None):
        if tag is None:
            tag = _auto_tag(message)
        self.log_box.configure(state=tk.NORMAL)
        self.log_box.insert(tk.END, message + '\n', tag)
        self.log_box.see(tk.END)
        self.log_box.configure(state=tk.DISABLED)

    def _set_progress(self, value: int):
        self.progress['value'] = value


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _auto_tag(message: str) -> str:
    if message.startswith('  ✓'):
        return 'ok'
    if message.startswith('  –'):
        return 'skip'
    if message.startswith('  ✗') or 'ERROR' in message:
        return 'err'
    if message.startswith('-') or message.startswith('='):
        return 'sep'
    if message.startswith('Done.'):
        return 'sum'
    return 'info'


def _bind_hover(widget, bg_normal, bg_hover, fg_normal, fg_hover):
    widget.bind('<Enter>', lambda _: widget.configure(bg=bg_hover, fg=fg_hover))
    widget.bind('<Leave>', lambda _: widget.configure(bg=bg_normal, fg=fg_normal))
