"""
processor.py

Orchestrates the processing of all photo/video files in a selected folder.

Two-pass strategy:
  Pass 1 — for every file, try metadata / filename date first; if nothing is
            found, immediately fall back to the earliest of the file's existing
            Created / Modified filesystem timestamps.
  Pass 2 — for IMG_ files that are still without a date after Pass 1, infer
            from the nearest neighbor (by sorted filename) that does have one.
"""

import os
import re
from datetime import datetime
from typing import Callable, Optional
from src.metadata_reader import get_original_date, make_shell_namespace, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from src.file_updater import set_file_timestamps

SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
FAILED_LIST_FILENAME = 'selected_list.txt'
_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILED_LIST_PATH = os.path.join(_APP_DIR, FAILED_LIST_FILENAME)

_SEQ_RE = re.compile(r'(\d+)')


def _sequence_number(filename: str) -> int:
    """
    Extract the first run of digits from a filename stem as a sequence number.
    e.g.  IMG_1025.JPG  → 1025
          photo_2025-03-06 23.52.23.jpeg → 2025  (first number found)
    Returns 0 if no digits are present.
    """
    stem = os.path.splitext(filename)[0]
    m = _SEQ_RE.search(stem)
    return int(m.group(1)) if m else 0


def _find_nearest_neighbor_date(
    index: int,
    all_files: list[str],
    dates: dict[str, tuple[datetime, str]],
) -> Optional[tuple[datetime, str]]:
    """
    Walk outward from `index` in both directions through `all_files`
    (sorted by name) and return the date of the closest file that has one.
    Preference is given to files that share the same numeric prefix
    (e.g. IMG_1024 is a better neighbor for IMG_1025 than photo_2025-03-06).
    """
    target_seq = _sequence_number(all_files[index])
    best: Optional[tuple[datetime, str]] = None
    best_distance: tuple = (float('inf'), float('inf'))

    for i, filename in enumerate(all_files):
        if filename == all_files[index]:
            continue
        if filename not in dates:
            continue
        # Prefer files whose sequence number is close
        seq_dist = abs(_sequence_number(filename) - target_seq)
        idx_dist = abs(i - index)
        # Primary sort: sequence distance; secondary: index distance
        distance = (seq_dist, idx_dist)
        if distance < best_distance:
            best_distance = distance
            best = dates[filename]

    return best


def _filesystem_date(filepath: str) -> Optional[tuple[datetime, str]]:
    """Return the earliest of the file's Created and Modified timestamps."""
    try:
        ctime = os.path.getctime(filepath)
        mtime = os.path.getmtime(filepath)
        earliest = min(ctime, mtime)
        dt = datetime.fromtimestamp(earliest)
        source = 'filesystem:created' if ctime <= mtime else 'filesystem:modified'
        return dt, source
    except Exception:
        return None


def _save_failed_list(failed_files: list[tuple[str, str]]) -> None:
    if failed_files:
        with open(FAILED_LIST_PATH, 'w', encoding='utf-8') as f:
            f.write('# Files that failed during the last run. Edit freely — one filename per line.\n')
            for fname, _reason in failed_files:
                f.write(f'{fname}\n')
    else:
        try:
            os.remove(FAILED_LIST_PATH)
        except FileNotFoundError:
            pass


def load_failed_list() -> list[str]:
    """Return filenames from selected_list.txt in the app directory, or [] if absent."""
    try:
        with open(FAILED_LIST_PATH, 'r', encoding='utf-8') as f:
            return [
                line.split('\t')[0].strip()
                for line in f
                if line.strip() and not line.strip().startswith('#')
            ]
    except FileNotFoundError:
        return []


def _process_single_folder(
    folder: str,
    log_callback: Callable[[str], None],
    progress_callback: Callable[[int, int], None],
    only_files: Optional[set],
    global_counter: list,   # [current, total] mutable
) -> dict:
    """Process one folder and return its summary. Used by process_folder."""
    summary = {'total': 0, 'updated': 0, 'skipped': 0, 'failed': 0}

    all_supported = sorted([
        f for f in os.listdir(folder)
        if os.path.isfile(os.path.join(folder, f))
        and os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS
    ])

    if only_files is not None:
        all_files = [f for f in all_supported if f in only_files]
    else:
        all_files = all_supported

    if not all_files:
        return summary, []

    summary['total'] = len(all_files)

    # ── Pass 1 ────────────────────────────────────────────────────────
    dates: dict[str, tuple[datetime, str]] = {}
    read_errors: dict[str, str] = {}
    shell_ns = make_shell_namespace(folder)

    for filename in all_files:
        filepath = os.path.join(folder, filename)
        try:
            result = get_original_date(filepath, shell_ns=shell_ns)
            if not result:
                result = _filesystem_date(filepath)
            if result:
                dates[filename] = result
        except Exception as e:
            read_errors[filename] = str(e)

    # ── Pass 2: neighbor inference for IMG_ files ─────────────────────
    inferred: dict[str, tuple[datetime, str]] = {}
    neighbor_pool = all_supported
    neighbor_dates: dict[str, tuple[datetime, str]] = {}

    if only_files is not None:
        shell_ns_pool = make_shell_namespace(folder)
        for filename in neighbor_pool:
            filepath = os.path.join(folder, filename)
            try:
                result = get_original_date(filepath, shell_ns=shell_ns_pool)
                if not result:
                    result = _filesystem_date(filepath)
                if result:
                    neighbor_dates[filename] = result
            except Exception:
                pass
    else:
        neighbor_dates = dates

    for idx, filename in enumerate(all_files):
        if filename in dates or filename in read_errors:
            continue
        if not filename.upper().startswith('IMG_'):
            continue
        pool_idx = neighbor_pool.index(filename) if filename in neighbor_pool else idx
        neighbor = _find_nearest_neighbor_date(pool_idx, neighbor_pool, neighbor_dates)
        if neighbor:
            inferred[filename] = (neighbor[0], f'neighbor:{neighbor[1]}')

    # ── Apply ─────────────────────────────────────────────────────────
    failed_files: list[tuple[str, str]] = []

    for filename in all_files:
        filepath = os.path.join(folder, filename)
        global_counter[0] += 1
        if progress_callback:
            progress_callback(global_counter[0], global_counter[1])

        log_callback(f'[{global_counter[0]}/{global_counter[1]}] {filename}')

        if filename in read_errors:
            log_callback(f'  ✗ Error reading metadata: {read_errors[filename]}')
            failed_files.append((filename, read_errors[filename]))
            summary['failed'] += 1
            continue

        result = dates.get(filename) or inferred.get(filename)
        if result is None:
            log_callback('  – No date found anywhere. Skipped.')
            summary['skipped'] += 1
            continue

        dt, source = result
        try:
            set_file_timestamps(filepath, dt)
            log_callback(f'  ✓ {dt.strftime("%Y-%m-%d %H:%M:%S")}  [{source}]')
            summary['updated'] += 1
        except Exception as e:
            log_callback(f'  ✗ Error updating timestamps: {e}')
            failed_files.append((filename, str(e)))
            summary['failed'] += 1

    return summary, failed_files


def process_folder(
    folder: str,
    log_callback: Callable[[str], None],
    progress_callback: Callable[[int, int], None] = None,
    only_files: list[str] = None,
    recursive: bool = False,
) -> dict:
    """
    Process supported media files in the given folder.

    Args:
        folder:            Path to the folder to scan.
        log_callback:      Function(message: str) called for each log line.
        progress_callback: Optional Function(current: int, total: int).
        only_files:        If given, process only these filenames.
        recursive:         If True, also process all subdirectories.
    """
    summary = {'total': 0, 'updated': 0, 'skipped': 0, 'failed': 0}

    if not os.path.isdir(folder):
        log_callback(f'ERROR: Folder not found: {folder}')
        return summary

    only_set = set(only_files) if only_files is not None else None

    # Collect all folders to process
    if recursive:
        folders = []
        for root, dirs, _ in os.walk(folder):
            dirs.sort()
            folders.append(root)
    else:
        folders = [folder]

    # Count total files upfront for accurate progress
    total_files = 0
    for f in folders:
        supported = [
            x for x in os.listdir(f)
            if os.path.isfile(os.path.join(f, x))
            and os.path.splitext(x)[1].lower() in SUPPORTED_EXTENSIONS
        ]
        if only_set is not None:
            supported = [x for x in supported if x in only_set]
        total_files += len(supported)

    mode = 'Selected files' if only_set is not None else 'All files'
    sub_note = f', {len(folders)} folder(s)' if recursive else ''
    log_callback(f'{mode} — {total_files} file(s) found{sub_note} in: {folder}')
    log_callback('-' * 60)

    global_counter = [0, total_files]
    all_failed: list[tuple[str, str]] = []

    for sub_folder in folders:
        if recursive and sub_folder != folder:
            rel = os.path.relpath(sub_folder, folder)
            log_callback(f'📁 {rel}')

        result = _process_single_folder(
            sub_folder, log_callback, progress_callback, only_set, global_counter
        )
        if result:
            sub_summary, failed_files = result
            for key in summary:
                summary[key] += sub_summary[key]
            all_failed.extend(failed_files)

    log_callback('-' * 60)
    log_callback(
        f'Done. Updated: {summary["updated"]}  |  '
        f'Skipped: {summary["skipped"]}  |  '
        f'Failed: {summary["failed"]}  |  '
        f'Total: {summary["total"]}'
    )

    if all_failed:
        log_callback('')
        log_callback('Files with errors:')
        for fname, reason in all_failed:
            log_callback(f'  ✗ {fname}: {reason}')

    _save_failed_list(all_failed)
    if all_failed:
        log_callback(f'  → Error list saved to {FAILED_LIST_FILENAME}')

    return summary
