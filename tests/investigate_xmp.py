"""Check XMP metadata in files with photoshop blocks."""
import os, re

folder = r'c:\Documents\Photo\_NEW\iCloud Photos - test'
files = ['camphoto_1903590565.jpg', 'IMG_1025.JPG']

for filename in files:
    filepath = os.path.join(folder, filename)
    print(f'\n=== {filename} ===')
    with open(filepath, 'rb') as f:
        data = f.read()
    # XMP is stored as plain XML text inside the file
    xmp_start = data.find(b'<x:xmpmeta')
    xmp_end   = data.find(b'</x:xmpmeta>')
    if xmp_start != -1 and xmp_end != -1:
        xmp_str = data[xmp_start:xmp_end + 12].decode('utf-8', errors='replace')
        # Print only date-related lines
        for line in xmp_str.splitlines():
            if any(k in line.lower() for k in ['date', 'creat', 'time', 'modif', 'tiff', 'exif']):
                print(' ', line.strip())
    else:
        print('  No XMP block found')

    # Also check for raw date patterns in first 64KB
    chunk = data[:65536].decode('latin-1', errors='replace')
    dates = re.findall(r'(\d{4}[:/\-]\d{2}[:/\-]\d{2}[\sT]\d{2}:\d{2}:\d{2})', chunk)
    if dates:
        print(f'  Raw date strings found: {dates}')

