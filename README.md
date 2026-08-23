# 🤖 PIPPO — मेरा देसी दोस्त (AI Companion Robot)

> **PIPPO** is a curious, quick-witted, playfully mischievous AI companion robot with an authentic Indian festive interactive dashboard, real-time Hindi/Hinglish voice conversation, computer vision with face recognition, and hardware-ready remote control.

---

## 🌟 Features

- 🎭 **Interactive Indian Festive Dashboard**: Beautiful royal game UI with custom animated radar charts for emotions & personality, mood tracker, coins, and user profile.
- 💬 **Hindi Voice AI**: Speak into your microphone in Hindi or English. Powered by Google Gemini AI & ElevenLabs realistic voice synthesis.
- 👁️ **Computer Vision**: Real-time object detection (YOLOv8) + personal face recognition (OpenCV LBPH).
- 📡 **Remote Control**: Drive Pippo forward/backward/left/right via interactive on-screen D-pad or keyboard (`Arrow keys` / `WASD`). Sends real-time `1`/`0` boolean state to Python backend.
- 🪙 **Gamified Profile & Coins**: Earn coins, track levels, and customize mood and companion traits.

---

## 📁 Repository Structure

```text
├── frontend/
│   ├── index.html            # Main web UI dashboard & modals
│   ├── style.css             # Indian festive design system
│   ├── app.js                # Frontend logic & radar chart rendering
│   └── images/               # High-res robot & card assets
├── server.py                 # Flask bridge API (connects Web UI to Python scripts)
├── voice.py                  # Hindi Voice companion (Mic → Gemini → ElevenLabs)
├── vision.py                 # Vision system (YOLOv8 objects + OpenCV faces)
├── enroll_face.py            # One-time personal face trainer
├── haarcascade_frontalface_default.xml # Face detection cascade
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
└── .gitignore                # Git ignore rules
```

---

## 🚀 Full Setup Guide (Step-by-Step)

### 1. Prerequisites
- **Python 3.10 to 3.12** installed ([python.org](https://www.python.org/downloads/))
- A working **Microphone** and **Webcam**
- API Keys:
  - **Google Gemini API Key** (Free from [Google AI Studio](https://aistudio.google.com/))
  - **ElevenLabs API Key** (Free from [ElevenLabs](https://elevenlabs.io/))

---

### 2. Clone the Repository

```bash
git clone https://github.com/your-username/pippo.git
cd pippo
```

---

### 3. Create a Virtual Environment

#### Windows (PowerShell or CMD):
```powershell
python -m venv .venv
```

#### macOS / Linux:
```bash
python3 -m venv .venv
```

---

### 4. Activate the Virtual Environment

#### Windows (PowerShell):
If you get a script execution policy error, run this first:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

#### Windows (Command Prompt):
```cmd
.venv\Scripts\activate.bat
```

#### macOS / Linux:
```bash
source .venv/bin/activate
```

---

### 5. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> [!TIP]
> **Windows PyAudio Installation:**  
> If `pip install PyAudio` gives a build error on Windows, run:
> ```powershell
> pip install pipwin
> pipwin install pyaudio
> ```

> [!NOTE]
> **OpenCV Notice:** Make sure to use `opencv-contrib-python` (included in `requirements.txt`) rather than standard `opencv-python` to support local face recognition.

---

### 6. Configure Environment Variables (`.env`)

1. Copy `.env.example` to create `.env`:
   - **Windows:** `copy .env.example .env`
   - **macOS/Linux:** `cp .env.example .env`

2. Open `.env` in any text editor and paste your API keys:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

   # Optional customizations:
   # PIPPO_OWNER_NAME=Prakhar
   # PIPPO_CAMERA_INDEX=0
   ```

---

### 7. Teach PIPPO Your Face (Optional but Recommended)

Train Pippo to recognize you on camera:
```bash
python enroll_face.py "Your Name"
```
- Sit in good lighting, look at your webcam, and turn your head slightly until it captures ~30 samples.
- The trained model will be saved locally as `face_model.yml`.

---

## 🎮 Running PIPPO

### Start the Web Dashboard (Recommended)

Run the Flask server:
```bash
python server.py
```
Open your browser at:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

From the web interface, you can:
- 📡 **Drive Pippo**: Open **Remote Control** and use the D-Pad or `Arrow Keys` / `WASD`.
- 💬 **Talk**: Click **Talk to Pippo** → **Start Voice** to begin real-time voice chat.
- 📷 **Vision**: Click **Camera** → **Start Vision** to open the live YOLOv8 & Face Recognition feed.
- 🪙 **Coins & Profile**: Tap `+` to earn coins and customize Pippo's mood.

---

### Running Standalone Scripts Directly in Terminal

- **Voice Only:**
  ```bash
  python voice.py
  ```
  *(Say **"बंद करो"**, **"stop"**, or press `Ctrl+C` to exit)*

- **Camera Preview Only:**
  ```bash
  python vision.py
  ```
  *(Press `q` in the OpenCV window to exit)*

---

## 🛠️ API Reference

| Endpoint | Method | Description |
|---|---|---|
| `GET /` | `GET` | Serves the web dashboard |
| `POST /api/voice/start` | `POST` | Launches voice companion subprocess |
| `POST /api/voice/stop` | `POST` | Stops voice companion subprocess |
| `GET /api/voice/status` | `GET` | Returns `{ "running": bool }` |
| `POST /api/camera/start` | `POST` | Launches vision subprocess |
| `POST /api/camera/stop` | `POST` | Stops vision subprocess |
| `GET /api/camera/status` | `GET` | Returns `{ "running": bool }` |
| `POST /api/control` | `POST` | Sends `{ "direction": str, "pressed": bool }` |
| `GET /api/control/state` | `GET` | Returns `{ "forward": 0/1, "backward": 0/1, ... }` |
| `GET /api/mood` | `GET` | Fetches mood, emotions radar, and personality state |
| `POST /api/mood` | `POST` | Updates mood state |
| `POST /api/profile/coins` | `POST` | Updates user coins balance |

---

## ❓ Troubleshooting

| Issue | Solution |
|---|---|
| `Script execution is disabled` in PowerShell | Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and then run `.\.venv\Scripts\Activate.ps1`. |
| Microphone not recognized | Check Windows Sound settings and ensure microphone access is granted for Python. |
| `cv2.face` attribute missing | Run `pip uninstall opencv-python opencv-contrib-python -y` and reinstall with `pip install opencv-contrib-python`. |
| Gemini 401 Authentication Error | Ensure you are using a valid API key from Google AI Studio and that `google-genai` is installed. |

---

## 📜 License
This project is open-source under the MIT License.