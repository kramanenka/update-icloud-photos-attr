import win32com.client
import os

folder = r'c:\Documents\Photo\_NEW\iCloud Photos - test'
files = os.listdir(folder)

sh = win32com.client.Dispatch("Shell.Application")
ns = sh.Namespace(folder)

for f in files:
    item = ns.ParseName(f)
    print(f"=== {f} ===")
    for i in range(320):
        val = ns.GetDetailsOf(item, i)
        if val:
            label = ns.GetDetailsOf(None, i)
            print(f"  {i}: {label} = {val}")
    print()

