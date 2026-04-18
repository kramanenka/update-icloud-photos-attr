"""Quick smoke-test: run processor on the test folder and print results."""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.processor import process_folder

def log(msg):
    print(msg)

folder = r'c:\Documents\Photo\_NEW\iCloud Photos - test'
process_folder(folder, log_callback=log)
