"""
filename_patterns.py

All filename-based date patterns used to extract dates from filenames.
Add new patterns here — no other files need to be changed.

Each entry is a dict with:
    name:    Human-readable label shown in the log as source
    regex:   Regular expression to match the date/time in the filename stem
    builder: Lambda(match) → date string
    fmt:     strptime format string for the date string built above
"""

import re

FILENAME_DATE_PATTERNS = [
    # ── Telegram ─────────────────────────────────────────────────────────
    # photo_2025-03-06 23.52.23  or  photo_2025-03-06_23.52.23
    {
        'name': 'Telegram',
        'regex': re.compile(r'(\d{4}-\d{2}-\d{2})[ _](\d{2})\.(\d{2})\.(\d{2})'),
        'builder': lambda m: f'{m.group(1)} {m.group(2)}:{m.group(3)}:{m.group(4)}',
        'fmt': '%Y-%m-%d %H:%M:%S',
    },

    # ── Android / WhatsApp ───────────────────────────────────────────────
    # IMG_20250306_235223  VID_20250306_235223  WA20250306-235223
    {
        'name': 'Android/WhatsApp',
        'regex': re.compile(r'(?:IMG|VID|WA|PANO|BURST|MVIMG)[-_]?(\d{8})[-_](\d{6})'),
        'builder': lambda m: f'{m.group(1)} {m.group(2)}',
        'fmt': '%Y%m%d %H%M%S',
    },

    # ── Screenshot ───────────────────────────────────────────────────────
    # Screenshot_2025-03-06-23-52-23
    {
        'name': 'Screenshot',
        'regex': re.compile(r'[Ss]creenshot[_-](\d{4}-\d{2}-\d{2})-(\d{2}-\d{2}-\d{2})'),
        'builder': lambda m: f'{m.group(1)} {m.group(2)}',
        'fmt': '%Y-%m-%d %H-%M-%S',
    },

    # ── Generic ISO datetime ─────────────────────────────────────────────
    # 2025-03-06_23-52-23  or  2025-03-06T23:52:23
    {
        'name': 'ISO-datetime',
        'regex': re.compile(r'(\d{4}-\d{2}-\d{2})[T_ ](\d{2})[:\-](\d{2})[:\-](\d{2})'),
        'builder': lambda m: f'{m.group(1)} {m.group(2)}:{m.group(3)}:{m.group(4)}',
        'fmt': '%Y-%m-%d %H:%M:%S',
    },

    # ── DD-MM-YYYY_HH-MM-SS ──────────────────────────────────────────────
    # file_28@27-05-2025_20-16-42.mp4  audio_1@12-12-2023_00-49-01.ogg
    {
        'name': 'DD-MM-YYYY',
        'regex': re.compile(r'(\d{2})-(\d{2})-(\d{4})_(\d{2})-(\d{2})-(\d{2})'),
        'builder': lambda m: f'{m.group(1)}-{m.group(2)}-{m.group(3)} {m.group(4)}:{m.group(5)}:{m.group(6)}',
        'fmt': '%d-%m-%Y %H:%M:%S',
    },

    # ── Date only (least specific, last resort) ──────────────────────────
    # 2025-03-06
    {
        'name': 'date-only-ISO',
        'regex': re.compile(r'(\d{4}-\d{2}-\d{2})'),
        'builder': lambda m: m.group(1),
        'fmt': '%Y-%m-%d',
    },
    # 20250306
    {
        'name': 'date-only-compact',
        'regex': re.compile(r'(\d{4})(\d{2})(\d{2})(?!\d)'),
        'builder': lambda m: f'{m.group(1)}{m.group(2)}{m.group(3)}',
        'fmt': '%Y%m%d',
    },
]

