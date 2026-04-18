# iCloud Photos Attribute Updater

A Windows desktop application that fixes the **Created** and **Modified** filesystem timestamps of photos and videos downloaded from iCloud, using the original date stored in the file's hidden metadata attributes.

## Why this tool exists

When photos/videos are exported from iCloud and copied to Windows, the filesystem **Date Created** and **Date Modified** are reset to the download/copy date — not the original capture date. The original date is still embedded in the file's metadata.

The app tries the following sources in priority order:

| Priority | Source | Applies to |
|----------|--------|------------|
| 1 | EXIF `DateTimeOriginal` | JPEG, JPG, HEIC, TIFF |
| 2 | Windows Shell **"Date taken"** property | Images (fallback) |
| 3 | Windows Shell **"Media created"** property | MP4, MOV, AVI, MKV, M4V, 3GP |
| 4 | Date/time pattern parsed from the **filename** | All types (last resort) |
| 5 | **Nearest neighbor inference** — borrows the date from the closest file (by sequence number) that does have one | All types (last resort) |

Filename patterns recognised include Telegram (`photo_2025-03-06 23.52.23.jpeg`), Android/WhatsApp (`IMG_20250306_235223.jpg`), screenshots, and generic ISO date formats.

Neighbor inference handles iPhone camera roll files such as `IMG_1025.JPG` whose EXIF was stripped — if `IMG_1025.HEIC` or `IMG_1026.HEIC` nearby carries a valid date, it is reused. The source in the log will show as `[neighbor:EXIF]` or `[neighbor:Shell:DateTaken]` etc.

Files with no recoverable date from any source are skipped and logged.

This tool updates the original files in-place — no copies are made.

---

## Project structure

```
update-icloud-photos-attr/
├── main.py                  # Entry point — run this to launch the app
├── requirements.txt         # Python dependencies
├── settings.json            # Last selected folder (auto-created on first run)
├── README.md
├── src/                     # Application source code
│   ├── __init__.py
│   ├── metadata_reader.py   # Extracts the original date from file metadata
│   ├── file_updater.py      # Applies timestamps to files via Win32 API
│   ├── processor.py         # Folder scanning & orchestration logic
│   └── ui.py                # Tkinter GUI
├── run.vbs                  # Double-click to launch the app (no console window)
└── tests/                   # Investigation & smoke-test scripts
    ├── test_run.py           # Runs the processor on the test folder (CLI)
    ├── inspect_meta.py       # Dumps all shell properties for each file
    ├── investigate.py        # Deep metadata dump (EXIF, PIL, shell)
    ├── investigate_xmp.py    # Checks for XMP date blocks in files
    └── check_timestamp.py    # Interprets numeric filename parts as timestamps
```

---

## Requirements

- **Windows 10 / 11** (uses Windows Shell COM and Win32 file APIs)
- **Python 3.9+**

---

## Installation

```bash
pip install -r requirements.txt
```

---

## Usage

```bash
python main.py
```

1. The last used folder is remembered and pre-filled automatically.
2. Click **Browse…** to pick a different folder if needed.
3. Click **▶ Start**.
4. Watch the live log. Each file will show one of:
   - ✓ `Timestamps updated → YYYY-MM-DD HH:MM:SS  [source]` — success, with the metadata source shown in brackets
   - `–` `No original date found in metadata or filename. Skipped.` — nothing recoverable
   - ✗ `Error …` — something went wrong (file locked, permission denied, etc.)
5. A summary line at the end shows totals for Updated / Skipped / Failed.

> **Note:** Only the selected folder is processed (not sub-folders).  
> **Note:** Original files are modified in-place — no copies are created.

---

## Log colour guide

| Colour | Meaning |
|--------|---------|
| 🟢 Green | Timestamp updated successfully |
| 🟡 Amber | File skipped (no date found anywhere) |
| 🔴 Red | Error reading metadata or updating file |
| 🔵 Blue bold | Summary line |
| Dark text | File names / info |
| Grey | Separator lines |
