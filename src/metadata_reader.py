"""
metadata_reader.py

Responsible for extracting the original creation date from photo/video files.

Priority order for date extraction:
  1. EXIF DateTimeOriginal (for JPEG, JPG, HEIC, TIFF)
  2. Windows Shell "Media created" property #208 (for MP4, MOV, AVI, etc.)
  3. Windows Shell "Date taken" property #12 (fallback for images)
  4. Date/time pattern parsed from the filename (last resort, all types)
"""

import os
import re
import piexif
from datetime import datetime
from typing import Optional

# Supported extensions and their processing category
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.heic', '.tiff', '.tif', '.png', '.bmp'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.m4v', '.3gp'}

# Shell property indices
SHELL_PROP_DATE_TAKEN = 12
SHELL_PROP_MEDIA_CREATED = 208

# Unicode direction/format marks that Windows inserts into shell strings
_UNICODE_JUNK = re.compile(r'[\u200e\u200f\u202a-\u202e\u2066-\u2069\u200b\u00a0]')


def _clean_shell_date(raw: str) -> str:
    """Remove Unicode formatting marks injected by Windows Shell."""
    return _UNICODE_JUNK.sub('', raw).strip()


def _parse_shell_date(raw: str) -> Optional[datetime]:
    """Parse a Windows Shell date string into a datetime object."""
    cleaned = _clean_shell_date(raw)
    if not cleaned:
        return None

    formats = [
        '%m/%d/%Y %I:%M %p',
        '%m/%d/%Y %H:%M',
        '%d/%m/%Y %I:%M %p',
        '%d/%m/%Y %H:%M',
        '%Y-%m-%d %H:%M:%S',
        '%Y:%m:%d %H:%M:%S',
    ]
    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue

    # Last resort: dateutil
    try:
        from dateutil import parser as du_parser
        return du_parser.parse(cleaned)
    except Exception:
        return None


def _get_shell_property(filename: str, prop_index: int, ns) -> Optional[str]:
    """Retrieve a shell namespace property value for a file using a pre-built namespace."""
    try:
        if ns is None:
            return None
        item = ns.ParseName(filename)
        if item is None:
            return None
        value = ns.GetDetailsOf(item, prop_index)
        return value if value else None
    except Exception:
        return None


def make_shell_namespace(folder: str):
    """Create a Shell namespace for the given folder. Returns None on failure."""
    try:
        import win32com.client
        sh = win32com.client.Dispatch('Shell.Application')
        return sh.Namespace(folder)
    except Exception:
        return None


def _read_exif_date(filepath: str) -> Optional[datetime]:
    """Extract DateTimeOriginal from EXIF data using piexif."""
    try:
        exif_data = piexif.load(filepath)
        for ifd in ('Exif', '0th'):
            if ifd in exif_data:
                tag = piexif.ExifIFD.DateTimeOriginal if ifd == 'Exif' else piexif.ImageIFD.DateTime
                raw = exif_data[ifd].get(tag)
                if raw:
                    dt_str = raw.decode('utf-8') if isinstance(raw, bytes) else raw
                    try:
                        return datetime.strptime(dt_str, '%Y:%m:%d %H:%M:%S')
                    except ValueError:
                        pass
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Filename-based date patterns (last resort)
# Each tuple: (regex, strptime_format)
# Patterns ordered from most to least specific (datetime → date-only)
# ---------------------------------------------------------------------------
_FILENAME_DATE_PATTERNS = [
    # Telegram: photo_2025-03-06 23.52.23  or  photo_2025-03-06_23.52.23
    (re.compile(r'(\d{4}-\d{2}-\d{2})[ _](\d{2})\.(\d{2})\.(\d{2})'), '%Y-%m-%d %H:%M:%S',
     lambda m: f'{m.group(1)} {m.group(2)}:{m.group(3)}:{m.group(4)}'),

    # Android / WhatsApp: IMG_20250306_235223  VID_20250306_235223  WA20250306-235223
    (re.compile(r'(?:IMG|VID|WA|PANO|BURST|MVIMG)[-_]?(\d{8})[-_](\d{6})'),
     '%Y%m%d %H%M%S',
     lambda m: f'{m.group(1)} {m.group(2)}'),

    # Screenshot_2025-03-06-23-52-23  or  Screenshot_20250306-235223
    (re.compile(r'[Ss]creenshot[_-](\d{4}-\d{2}-\d{2})-(\d{2}-\d{2}-\d{2})'),
     '%Y-%m-%d %H-%M-%S',
     lambda m: f'{m.group(1)} {m.group(2)}'),

    # Generic ISO datetime in name: 2025-03-06_23-52-23  or  2025-03-06T23:52:23
    (re.compile(r'(\d{4}-\d{2}-\d{2})[T_ ](\d{2})[:\-](\d{2})[:\-](\d{2})'),
     '%Y-%m-%d %H:%M:%S',
     lambda m: f'{m.group(1)} {m.group(2)}:{m.group(3)}:{m.group(4)}'),

    # Date only (least specific — use only if nothing else matches):
    # 2025-03-06  or  20250306
    (re.compile(r'(\d{4}-\d{2}-\d{2})'), '%Y-%m-%d', lambda m: m.group(1)),
    (re.compile(r'(\d{4})(\d{2})(\d{2})(?!\d)'), '%Y%m%d',
     lambda m: f'{m.group(1)}{m.group(2)}{m.group(3)}'),
]


def _date_from_filename(filename: str) -> Optional[datetime]:
    """Try to extract a datetime from common date/time patterns in a filename."""
    stem = os.path.splitext(filename)[0]
    for pattern, fmt, builder in _FILENAME_DATE_PATTERNS:
        m = pattern.search(stem)
        if m:
            try:
                return datetime.strptime(builder(m), fmt)
            except ValueError:
                continue
    return None


def get_original_date(filepath: str, shell_ns=None) -> Optional[tuple[datetime, str]]:
    """
    Attempt to extract the original media creation date from a file.

    Returns a (datetime, source) tuple if found, or None if no date can be determined.
    Source is one of: 'EXIF', 'Shell:DateTaken', 'Shell:MediaCreated', 'filename'

    Args:
        filepath:  Absolute path to the file.
        shell_ns:  Pre-built Shell namespace for the file's folder (from make_shell_namespace).
                   If None, shell properties are skipped.
    """
    ext = os.path.splitext(filepath)[1].lower()
    filename = os.path.basename(filepath)

    # --- Images: try EXIF first ---
    if ext in IMAGE_EXTENSIONS:
        dt = _read_exif_date(filepath)
        if dt:
            return dt, 'EXIF'
        raw = _get_shell_property(filename, SHELL_PROP_DATE_TAKEN, shell_ns)
        if raw:
            dt = _parse_shell_date(raw)
            if dt:
                return dt, 'Shell:DateTaken'

    # --- Videos: use Shell "Media created" property ---
    if ext in VIDEO_EXTENSIONS:
        raw = _get_shell_property(filename, SHELL_PROP_MEDIA_CREATED, shell_ns)
        if raw:
            dt = _parse_shell_date(raw)
            if dt:
                return dt, 'Shell:MediaCreated'

    # --- Last resort for all types: parse date from filename ---
    dt = _date_from_filename(filename)
    if dt:
        return dt, 'filename'

    return None

