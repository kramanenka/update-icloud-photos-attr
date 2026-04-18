import win32com.client
import os

folder = r'C:\Documents\Photo\_NEW\test'
filename = 'video (107).mp4'

print('Folder exists:', os.path.isdir(folder))
print('File exists:', os.path.isfile(os.path.join(folder, filename)))

sh = win32com.client.Dispatch('Shell.Application')
# Namespace requires a real Windows path string, not forward slashes
ns = sh.Namespace(folder)
print('ns:', ns)

if ns:
    item = ns.ParseName(filename)
    print('item:', item)
    if item:
        for i in range(320):
            val = ns.GetDetailsOf(item, i)
            if val and val.strip():
                label = ns.GetDetailsOf(None, i)
                print(f'[{i}] {label}: {val}')
    else:
        print('ParseName returned None')
