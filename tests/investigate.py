"""Deep metadata investigation of skipped files."""
import os
import piexif
from PIL import Image
from PIL.ExifTags import TAGS

folder = r'c:\Documents\Photo\_NEW\iCloud Photos - test'
skipped = ['camphoto_1903590565.jpg', 'IMG_1025.JPG', 'NY открытка - 2024.1-1.png', 'photo_2025-03-06 23.52.23.jpeg']

for filename in skipped:
    filepath = os.path.join(folder, filename)
    print(f'\n{"="*60}')
    print(f'FILE: {filename}')
    print(f'{"="*60}')

    # 1. All shell properties
    print('\n--- Shell properties (non-empty) ---')
    try:
        import win32com.client
        sh = win32com.client.Dispatch('Shell.Application')
        ns = sh.Namespace(folder)
        item = ns.ParseName(filename)
        for i in range(320):
            val = ns.GetDetailsOf(item, i)
            if val:
                label = ns.GetDetailsOf(None, i)
                print(f'  [{i}] {label} = {val}')
    except Exception as e:
        print(f'  Error: {e}')

    # 2. Raw piexif dump
    print('\n--- piexif raw dump ---')
    try:
        exif = piexif.load(filepath)
        for ifd_name, ifd_data in exif.items():
            if isinstance(ifd_data, dict) and ifd_data:
                print(f'  IFD: {ifd_name}')
                for tag_id, value in ifd_data.items():
                    try:
                        tag_name = piexif.TAGS[ifd_name][tag_id]['name'] if ifd_name in piexif.TAGS and tag_id in piexif.TAGS[ifd_name] else tag_id
                    except Exception:
                        tag_name = tag_id
                    val_str = value.decode('utf-8', errors='replace') if isinstance(value, bytes) and len(value) < 200 else repr(value)[:120]
                    print(f'    {tag_name}: {val_str}')
    except Exception as e:
        print(f'  Error: {e}')

    # 3. PIL Image info
    print('\n--- PIL Image info ---')
    try:
        img = Image.open(filepath)
        info = img.info
        for k, v in info.items():
            print(f'  {k}: {repr(v)[:200]}')
        # PIL EXIF via getexif()
        try:
            exif_pil = img.getexif()
            if exif_pil:
                print('\n--- PIL getexif ---')
                for tag_id, value in exif_pil.items():
                    tag_name = TAGS.get(tag_id, tag_id)
                    print(f'  {tag_name}: {repr(value)[:120]}')
        except Exception as e2:
            print(f'  PIL getexif error: {e2}')
        img.close()
    except Exception as e:
        print(f'  Error: {e}')

    # 4. Filename date hint
    import re
    date_in_name = re.search(r'(\d{4}[-_]\d{2}[-_]\d{2})', filename)
    if date_in_name:
        print(f'\n--- Date in filename: {date_in_name.group(1)} ---')

