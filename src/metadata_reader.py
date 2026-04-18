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
from src.filename_patterns import FILENAME_DATE_PATTERNS

# Supported extensions and their processing category
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.heic', '.tiff', '.tif', '.png', '.bmp'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.m4v', '.3gp', '.ogg'}

# Shell property indices
SHELL_PROP_DATE_TAKEN = 12
SHELL_PROP_MEDIA_CREATED = 208

# Unicode direction/format marks that Windows inserts into shell strings
_UNICODE_JUNK = re.compile(r'[\u200e\u200f\u202a-\u202e\u2066-\u2069\u200b\u00a0]')


def _clean_shell_date(raw: str) -> str:
    return _UNICODE_JUNK.sub('', raw).strip()


def _parse_shell_date(raw: str) -> Optional[datetime]:
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
    try:
        from dateutil import parser as du_parser
        return du_parser.parse(cleaned)
    except Exception:
        return None


def _get_shell_property(filename: str, prop_index: int, ns) -> Optional[str]:
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
        return sh.Namespace(os.path.normpath(folder))
    except Exception:
        return None


def _read_exif_date(filepath: str) -> Optional[datetime]:
    """Extract DateTimeOriginal from EXIF. Supports JPEG/TIFF via piexif, HEIC via pillow-heif."""
    ext = os.path.splitext(filepath)[1].lower()

    if ext == '.heic':
        try:
            import pillow_heif
            from PIL import Image
            pillow_heif.register_heif_opener()
            img = Image.open(filepath)
            exif_data = img.getexif()
            if exif_data:
                for tag_id in (36867, 306):   # DateTimeOriginal, DateTime
                    val = exif_data.get(tag_id)
                    if val:
                        try:
                            return datetime.strptime(val, '%Y:%m:%d %H:%M:%S')
                        except ValueError:
                            pass
        except Exception:
            pass
        return None

    try:
        exif_data = piexif.load(filepath)
        for ifd, tag in (('Exif', piexif.ExifIFD.DateTimeOriginal),
                         ('0th',  piexif.ImageIFD.DateTime)):
            if ifd in exif_data:
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


def _date_from_filename(filename: str) -> Optional[datetime]:
    """Try to extract a datetime from filename using patterns in filename_patterns.py."""
    stem = os.path.splitext(filename)[0]
    for entry in FILENAME_DATE_PATTERNS:
        m = entry['regex'].search(stem)
        if m:
            try:
                return datetime.strptime(entry['builder'](m), entry['fmt'])
            except ValueError:
                continue
    return None


def get_original_date(filepath: str, shell_ns=None) -> Optional[tuple[datetime, str]]:
    """
    Attempt to extract the original media creation date from a file.

    Returns a (datetime, source) tuple or None.
    Source is one of: 'EXIF', 'Shell:DateTaken', 'Shell:MediaCreated', 'filename:<pattern>'
    """
    ext = os.path.splitext(filepath)[1].lower()
    filename = os.path.basename(filepath)

    # --- Images: EXIF first, then Shell ---
    if ext in IMAGE_EXTENSIONS:
        dt = _read_exif_date(filepath)
        if dt:
            return dt, 'EXIF'
        raw = _get_shell_property(filename, SHELL_PROP_DATE_TAKEN, shell_ns)
        if raw:
            dt = _parse_shell_date(raw)
            if dt:
                return dt, 'Shell:DateTaken'

    # --- Videos/audio: Shell "Media created" ---
    if ext in VIDEO_EXTENSIONS:
        raw = _get_shell_property(filename, SHELL_PROP_MEDIA_CREATED, shell_ns)
        if raw:
            dt = _parse_shell_date(raw)
            if dt:
                return dt, 'Shell:MediaCreated'

    # --- Last resort: filename pattern ---
    stem = os.path.splitext(filename)[0]
    for entry in FILENAME_DATE_PATTERNS:
        m = entry['regex'].search(stem)
        if m:
            try:
                dt = datetime.strptime(entry['builder'](m), entry['fmt'])
                return dt, f'filename:{entry["name"]}'
            except ValueError:
                continue

    return None
