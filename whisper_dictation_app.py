# whisper_dictation_app.py

import os
import threading
import tempfile
import queue
import time
import sounddevice as sd
import numpy as np
import faster_whisper
import pyautogui
from pynput import keyboard as pynput_keyboard
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
import requests
import json
import soundfile as sf
from datetime import datetime
from tkinter import simpledialog
import winsound
from openai import OpenAI

import json


client = OpenAI()  # uses OPENAI_API_KEY from env

# --- Global Settings ---
settings = {
    "model_size": "base",
    "hotkey": "ctrl+shift+space",
    "hotkey_note": "ctrl+shift+1",
    "hotkey_email": "ctrl+shift+2",
    "hotkey_message": "ctrl+shift+3",
    "hotkey_popup": "ctrl+shift+4",
    "hotkey_cursor": "ctrl+shift+5",
    "hotkey_gpt": "ctrl+shift+6",
    "mode": "message",
    "output_method": "cursor",
    "recording_duration": 60,
    "use_gpt_cleanup": False,
    "transcription_method": "local"  # or "openai"
}

SETTINGS_FILE = "settings.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            settings.update(json.load(f))

def save_settings():
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)

load_settings()


popup_window = None  # Global handle

# --- Initialize Variables ---
recording_active = threading.Event()
q = queue.Queue()
stop_listening = threading.Event()
continuous_mode_running = threading.Event()
model = faster_whisper.WhisperModel(settings["model_size"], compute_type="int8", device="cpu")

# Ensure transcript folder exists
os.makedirs("transcripts", exist_ok=True)

def play_beep(frequency=1000, duration=150):
    try:
        winsound.Beep(frequency, duration)
    except:
        pass  # in case the system doesn’t support it

def handle_dictation():
    play_beep(1000, 150)
    audio = record_audio(duration=settings["recording_duration"])
    play_beep(600, 150)

    if len(audio) == 0:
        print("[No audio to transcribe]")
        return

    print("[Transcribing...]")
    text = transcribe(audio_data=audio)
    cleaned = clean_text(text)
    if settings["use_gpt_cleanup"]:
        print("[Enhancing with GPT...]")
        cleaned = gpt_cleanup(cleaned)
    formatted = apply_mode(cleaned) + " "
    save_transcript(formatted)
    if settings["output_method"] == "popup":
        show_popup_with_text(formatted)
    else:
        type_text_to_cursor(formatted)


# --- Logging ---
def save_transcript(text):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filepath = f"transcripts/transcript_{timestamp}.txt"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)
    with open("transcripts/transcript_log.txt", "a", encoding="utf-8") as log:
        log.write(f"[{timestamp}]\n{text}\n\n")

# --- Audio Capture ---
def audio_callback(indata, frames, time_info, status):
    q.put(indata.copy())

def transcribe_with_openai(audio_data=None, samplerate=16000):
    if not os.getenv("OPENAI_API_KEY"):
        print("[OpenAI key missing]")
        return "[OpenAI key missing]"

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        temp_path = f.name
    sf.write(temp_path, audio_data, samplerate)

    try:
        with open(temp_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        return transcript
    except Exception as e:
        return f"[OpenAI Transcription Error] {e}"
    finally:
        os.unlink(temp_path)


def record_audio(duration=10, samplerate=16000):
    audio = []
    recording_active.set()
    with sd.InputStream(samplerate=samplerate, channels=1, callback=audio_callback):
        start_time = time.time()
        while time.time() - start_time < duration:
            if stop_listening.is_set() or not recording_active.is_set():
                print("[Recording manually stopped]")
                break
            try:
                chunk = q.get(timeout=0.5)
                audio.append(chunk)
            except queue.Empty:
                continue
    recording_active.clear()

    if not audio:
        print("[No audio captured]")
        return np.array([])

    audio_np = np.concatenate(audio, axis=0)
    return audio_np.flatten()

# --- Transcription ---
def transcribe(audio_data=None, samplerate=16000, file_path=None):
    if settings.get("transcription_method") == "openai":
        return transcribe_with_openai(audio_data, samplerate)

    if file_path:
        segments, _ = model.transcribe(file_path)
    else:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
        sf.write(temp_path, audio_data, samplerate)
        segments, _ = model.transcribe(temp_path)
        os.unlink(temp_path)
    return " ".join([seg.text for seg in segments])


# --- Text Cleanup ---
def clean_text(text):
    import re
    text = re.sub(r"\b(um+|uh+|erm+)\b", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# --- GPT Enhancement ---
def gpt_cleanup(text):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return text + "\n\n[No API key found for GPT cleanup.]"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "Polish this transcript for grammar and readability."},
            {"role": "user", "content": text}
        ],
        "temperature": 0.4
    }
    try:
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"[GPT Cleanup Failed] {str(e)}"

# --- Format Modes ---
def apply_mode(text):
    if settings["mode"] == "email":
        return f"Hi,\n\n{text}\n\nRegards,"
    elif settings["mode"] == "note":
        return "- " + "\n- ".join(text.split(". "))
    return text

# --- Output Methods ---
def type_text_to_cursor(text):
    pyautogui.write(text, interval=0.01)


def show_popup_with_text(text):
    global popup_window

    def on_copy():
        popup_window.clipboard_clear()
        popup_window.clipboard_append(text)
        popup_window.destroy()

    # Close previous popup if it exists
    if popup_window and popup_window.winfo_exists():
        popup_window.destroy()

    popup_window = tk.Tk()
    popup_window.title("Transcript")
    popup_window.geometry("600x300")
    text_widget = tk.Text(popup_window, wrap="word")
    text_widget.insert("1.0", text)
    text_widget.pack(expand=True, fill="both")
    text_widget.focus()
    text_widget.tag_add("sel", "1.0", "end")
    tk.Button(popup_window, text="Copy & Close", command=on_copy).pack()
    popup_window.mainloop()


# --- Hotkey Triggered Dictation ---
def on_hotkey():
    if recording_active.is_set():
        # Second press — stop it
        recording_active.clear()
        print("[Hotkey pressed again — stopping early]")
        return
    if any(t.name == "DictationThread" for t in threading.enumerate()):
        print("[Dictation already running]")
        return

    print("[Dictation Triggered]")
    print("------------ Settings ------------")
    print(f"🧠 Engine: {'OpenAI' if settings.get('transcription_method') == 'openai' else 'Local'}")
    print(f"✏️ Mode: {settings.get('mode')}")
    print(f"📤 Output: {settings.get('output_method')}")
    print(f"🔄 GPT Cleanup: {'On' if settings.get('use_gpt_cleanup') else 'Off'}")
    print(f"⏱️ Duration: {settings.get('recording_duration')} sec")
    print("----------------------------------")

    threading.Thread(target=handle_dictation, daemon=True).start()



# --- File Transcription ---
def transcribe_file_dialog(icon, item):
    root = tk.Tk(); root.withdraw()
    file_path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.wav *.mp3 *.m4a")])
    if file_path:
        print(f"[Transcribing File] {file_path}")
        text = transcribe(file_path=file_path)
        cleaned = clean_text(text)
        if settings["use_gpt_cleanup"]:
            cleaned = gpt_cleanup(cleaned)
        formatted = apply_mode(cleaned) + " "
        show_popup_with_text(formatted)

# --- Continuous Mode ---
def toggle_continuous_mode(icon, item):
    if continuous_mode_running.is_set():
        continuous_mode_running.clear()
        print("[Continuous Mode Stopped]")
    else:
        continuous_mode_running.set()
        threading.Thread(target=run_continuous_mode, daemon=True).start()
        print("[Continuous Mode Started]")

def run_continuous_mode():
    print("[Continuous Mode Started]")
    while continuous_mode_running.is_set():
        play_beep(1000, 150)  # Optional: start beep
        audio = record_audio(duration=5)
        play_beep(600, 150)   # Optional: end beep

        text = transcribe(audio_data=audio)
        if text.strip():
            cleaned = clean_text(text)
            if settings["use_gpt_cleanup"]:
                cleaned = gpt_cleanup(cleaned)
            formatted = apply_mode(cleaned) + " "
            save_transcript(formatted)  # ✅ Save transcript
            if settings["output_method"] == "popup":
                show_popup_with_text(formatted)
            else:
                type_text_to_cursor(formatted)
        else:
            print("[No speech detected]")
        time.sleep(1)

    print("[Continuous Mode Stopped]")



# --- Tray Settings ---
def create_image():
    img = Image.new('RGB', (64, 64), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle([16, 16, 48, 48], fill=(255, 255, 255))
    return img

def set_mode_email(icon, item): settings["mode"] = "email"
def set_mode_note(icon, item): settings["mode"] = "note"
def set_mode_message(icon, item): settings["mode"] = "message"
def set_model_tiny(icon, item): settings["model_size"] = "tiny"; reload_model()
def set_model_base(icon, item): settings["model_size"] = "base"; reload_model()
def set_output_cursor(icon, item): settings["output_method"] = "cursor"
def set_output_popup(icon, item): settings["output_method"] = "popup"
def toggle_gpt_cleanup(icon, item): settings["use_gpt_cleanup"] = not settings["use_gpt_cleanup"]

def set_recording_duration(icon, item):
    def ask_duration():
        root = tk.Tk()
        root.withdraw()
        try:
            duration = simpledialog.askinteger(
                "Recording Duration",
                "How many seconds should the recording last?",
                minvalue=1,
                maxvalue=300,
                parent=root
            )
            if duration:
                settings["recording_duration"] = duration
                print(f"[Recording duration set to {duration} seconds]")
        finally:
            root.destroy()

    # Run on main thread (safe for tkinter)
    threading.Thread(target=ask_duration, daemon=True).start()

# --- Set Hotkey via Popup ---
def set_custom_hotkey(icon, item):
    def save_new_hotkey():
        action = dropdown_var.get()
        new_key = entry.get().strip().lower()
        if not new_key:
            root.destroy()
            return
        settings[action] = new_key
        save_settings()
        register_hotkeys()
        print(f"[Hotkey Updated] {action} = {new_key}")
        root.destroy()

    root = tk.Tk()
    root.title("Set Hotkey")
    root.geometry("400x200")

    dropdown_var = tk.StringVar(root)
    dropdown_var.set("hotkey")  # default

    tk.Label(root, text="Select Action:").pack(pady=5)
    tk.OptionMenu(root, dropdown_var, *[
        "hotkey", "hotkey_note", "hotkey_email",
        "hotkey_message", "hotkey_popup", "hotkey_cursor", "hotkey_gpt"
    ]).pack()

    tk.Label(root, text="Enter new hotkey (e.g. ctrl+shift+space):").pack(pady=5)
    entry = tk.Entry(root, font=("Arial", 14))
    entry.pack(pady=10)

    tk.Button(root, text="Save", command=save_new_hotkey).pack(pady=5)
    root.mainloop()


# --- Register All Hotkeys ---

hotkey_actions = {}

def format_hotkey(hotkey_str):
    parts = hotkey_str.split("+")
    return "+".join([f"<{key}>" if len(key) > 1 else key for key in parts])

def register_hotkeys():
    global hotkey_actions
    hotkey_actions = {
        settings["hotkey"]: on_hotkey,
        settings["hotkey_note"]: lambda: set_mode_note(None, None),
        settings["hotkey_email"]: lambda: set_mode_email(None, None),
        settings["hotkey_message"]: lambda: set_mode_message(None, None),
        settings["hotkey_popup"]: lambda: set_output_popup(None, None),
        settings["hotkey_cursor"]: lambda: set_output_cursor(None, None),
        settings["hotkey_gpt"]: lambda: toggle_gpt_cleanup(None, None),
        settings["hotkey_toggle_continuous"]: lambda: toggle_continuous_mode(None, None),
    }


    hotkey_combos = {
        format_hotkey(combo): action for combo, action in hotkey_actions.items()
    }

    listener = pynput_keyboard.GlobalHotKeys(hotkey_combos)
    listener.start()
    print(f"[Hotkey active] Press {settings['hotkey']} to dictate")

def reload_model():
    global model
    model = faster_whisper.WhisperModel(settings["model_size"], compute_type="int8", device="cpu")

def show_hotkey_list(icon, item):
    hotkeys_text = "\n".join([
        f"Main Dictation: {settings.get('hotkey', '')}",
        f"Mode → Note: {settings.get('hotkey_note', '')}",
        f"Mode → Email: {settings.get('hotkey_email', '')}",
        f"Mode → Message: {settings.get('hotkey_message', '')}",
        f"Output → Popup: {settings.get('hotkey_popup', '')}",
        f"Output → Cursor: {settings.get('hotkey_cursor', '')}",
        f"Toggle GPT Cleanup: {settings.get('hotkey_gpt', '')}",
        f"Toggle Continuous Mode: {settings.get('hotkey_toggle_continuous', '')}",
    ])
    
    # Proper window initialization & cleanup
    root = tk.OptionMenu(root, dropdown_var, *[
        "hotkey",
        "hotkey_note", "hotkey_email", "hotkey_message",
        "hotkey_popup", "hotkey_cursor", "hotkey_gpt",
        "hotkey_toggle_continuous"
    ]).pack()

    root.withdraw()
    messagebox.showinfo("Active Hotkeys", hotkeys_text, parent=root)
    root.destroy()


def quit_app(icon, item):
    icon.stop()
    os._exit(0)

def toggle_transcription_method(icon, item):
    current = settings["transcription_method"]
    settings["transcription_method"] = "openai" if current == "local" else "local"
    print(f"[Switched to {settings['transcription_method'].upper()} mode]")


# --- Tray Menu ---
def run_tray():
    menu = (
        item("Show Hotkeys", show_hotkey_list),
        item("Rebind Hotkey", set_custom_hotkey),
        item("Mode: Email", set_mode_email),
        item("Mode: Note", set_mode_note),
        item("Mode: Message", set_mode_message),
        item("Model: Tiny", set_model_tiny),
        item("Model: Base", set_model_base),
        item("Output: Cursor", set_output_cursor),
        item("Output: Popup", set_output_popup),
        item("Set Recording Duration", set_recording_duration),
        item("Toggle GPT Cleanup", toggle_gpt_cleanup),
        item("Transcribe File...", transcribe_file_dialog),
        item("Toggle Continuous Mode", toggle_continuous_mode),
        item("Toggle Transcription Engine", toggle_transcription_method),
        item("Quit", quit_app)
    )
    icon = pystray.Icon("Whisper", create_image(), "Whisper Dictation", menu)
    icon.run()

register_hotkeys()
threading.Thread(target=run_tray, daemon=True).start()

print("Whisper Dictation App is running... Use your hotkey or system tray.")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Exiting app")
    os._exit(0)
