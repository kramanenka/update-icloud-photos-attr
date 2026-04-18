"""
file_updater.py

Responsible for updating the filesystem timestamps (created, modified)
of a file to a given datetime value.
"""

import pywintypes
import win32file
import win32con
from datetime import datetime


def set_file_timestamps(filepath: str, dt: datetime) -> None:
    """
    Set both the Created and Modified timestamps of a file to the given datetime.

    Args:
        filepath: Absolute path to the file.
        dt:       The datetime to apply.

    Raises:
        OSError: If the file cannot be opened or timestamps cannot be set.
    """
    # Convert datetime to Windows FILETIME (a pywintypes.datetime-compatible object)
    win_time = pywintypes.Time(dt)

    handle = win32file.CreateFile(
        filepath,
        win32con.GENERIC_WRITE,
        win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE,
        None,
        win32con.OPEN_EXISTING,
        win32con.FILE_ATTRIBUTE_NORMAL,
        None,
    )
    try:
        win32file.SetFileTime(handle, win_time, win_time, win_time)
    finally:
        handle.Close()
