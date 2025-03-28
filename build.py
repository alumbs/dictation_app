import os
import platform
import subprocess

APP_NAME = "WhisperDictationApp"

def build_windows():
    print("🔧 Building for Windows...")
    cmd = [
        "pyinstaller",
        "--onefile",
        "--noconsole",
        "--name", APP_NAME,
        "whisper_dictation_app.py"
    ]
    subprocess.run(cmd)

def build_mac():
    print("🍎 Building for macOS...")
    with open("setup.py", "w") as f:
        f.write(f"""
from setuptools import setup

APP = ['whisper_dictation_app.py']
OPTIONS = {{
    'argv_emulation': True,
    'packages': ['sounddevice', 'faster_whisper', 'numpy', 'requests', 'tkinter'],
}}

setup(
    app=APP,
    options={{'py2app': OPTIONS}},
    setup_requires=['py2app'],
)
        """)
    subprocess.run(["python3", "setup.py", "py2app"])

if __name__ == "__main__":
    if platform.system() == "Windows":
        build_windows()
    elif platform.system() == "Darwin":
        build_mac()
    else:
        print("❌ Unsupported OS")
