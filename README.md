# 🧠 Whisper Dictation App (Windows)

A lightweight voice-to-text app that uses OpenAI Whisper (offline) with optional GPT cleanup. Transcribe your speech using a hotkey, continuous mode, or audio files—and output to text fields or a popup.

---

## ✨ Features

- 🎙️ **Hotkey Dictation** (Default: Ctrl+Shift+Space)
- 🔁 **Continuous Listening Mode**
- 📁 **Audio File Transcription**
- ✂️ **Filler Word Removal**
- 🧠 **Optional GPT Cleanup (OpenAI API)**
- 🧾 **Mode Presets:** Email, Note, Message
- 🖱️ **Tray Settings:** Model, Output, Duration, Cleanup Toggle
- 🖥️ **Outputs:** Insert text at cursor or show popup for copy

---

## 🧰 Installation (with [`uv`](https://github.com/astral-sh/uv))

### 1. Create Environment
```bash
uv venv whisper-env
```

### 2. Activate Environment
**PowerShell:**
```bash
.\whisper-env\Scripts\Activate.ps1
```

### 3. Install Dependencies
```bash
uv pip install faster-whisper sounddevice pyautogui keyboard pystray pillow numpy requests
```

or 
```bash
uv pip install -r pyproject.toml
```

### 4. Install ffmpeg (required for audio file transcription)
- Download from: https://www.gyan.dev/ffmpeg/builds/
- Extract and add the `bin` folder to your system `PATH`.

Test it:
```bash
ffmpeg -version
```

---

## 🚀 Run the App

```bash
python whisper_dictation_app.py
```

🖥️ You’ll see a tray icon and a console log.  
🧠 Use your hotkey to start dictating!

---

## 🛠️ Tray Menu Features

- **Switch Modes**: Message, Email, Note
- **Switch Models**: Tiny or Base (local Whisper)
- **Output to**: Cursor or Popup
- **Set Duration**: Customize mic recording length
- **Toggle GPT Cleanup**: Requires `OPENAI_API_KEY`
- **Transcribe Audio File**: Select `.wav`, `.mp3`, or `.m4a`
- **Toggle Continuous Mode**: Auto-listens every 5 sec
- **Quit**: Exit the app

---

## 🔐 Optional GPT Cleanup (Polish Text)

To enable GPT cleanup:

1. Get your OpenAI API key from https://platform.openai.com/account/api-keys
2. Set it in your terminal:
```bash
$env:OPENAI_API_KEY="sk-..."
```
3. Toggle GPT Cleanup from the tray.

---

## ✅ Recommended Use

- Dictating emails, notes, or blog posts
- Voice journaling or interviews
- File-based transcription
- Auto-cleaning messy speech into text

# 🧪 To Build:
Run:

```bash
python build.py
```

You’ll get:

✅ dist/WhisperDictationApp.exe on Windows

✅ dist/WhisperDictationApp.app on Mac