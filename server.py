import subprocess
import sys
import os
import threading
import json
import time
import cv2
from flask import Flask, jsonify, send_from_directory, request, Response
from flask_cors import CORS

app = Flask(__name__, static_folder="frontend", static_url_path="")
CORS(app)

voice_process = None
vision_process = None

control_state = {
    "forward": 0,
    "backward": 0,
    "left": 0,
    "right": 0,
}

mood_state = {
    "mood": "HAPPY",
    "emotions": {
        "happy": 75,
        "curious": 85,
        "excited": 60,
        "hungry": 20,
        "sleepy": 10,
        "sad": 5,
    },
    "personality": {
        "brave": 70,
        "friendly": 90,
        "funny": 80,
        "smart": 75,
        "lazy": 15,
        "curious": 85,
    },
    "trait": "ADVENTUROUS",
}

user_profile = {
    "name": "Prakhar",
    "title": "Pippo's Dost",
    "level": 7,
    "coins": 256,
}

PYTHON = sys.executable
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
venv_python = os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe")
if os.path.exists(venv_python):
    PYTHON = venv_python

_stream_lock = threading.Lock()
_stream_cap = None
_camera_active = False
_vision_instance = None
_latest_meta = {
    "objects": [],
    "faces": [],
    "fps": 0,
}

def _get_vision():
    global _vision_instance
    if _vision_instance is None:
        try:
            from vision import VisionSystem
            _vision_instance = VisionSystem()
        except Exception:
            _vision_instance = None
    return _vision_instance

def _open_camera_capture():
    global _stream_cap
    if _stream_cap is not None and _stream_cap.isOpened():
        return _stream_cap
    try:
        from vision import open_camera
        cap = open_camera(0)
    except Exception:
        cap = None
    if cap is None or not cap.isOpened():
        for api in ([cv2.CAP_DSHOW] if hasattr(cv2, "CAP_DSHOW") else []) + [None]:
            try:
                cap = cv2.VideoCapture(0, api) if api is not None else cv2.VideoCapture(0)
                if cap.isOpened():
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    break
            except Exception:
                cap = None
    _stream_cap = cap
    return _stream_cap

def _release_camera_capture():
    global _stream_cap
    if _stream_cap is not None:
        try:
            _stream_cap.release()
        except Exception:
            pass
        _stream_cap = None

def _get_stream_frame():
    global _stream_cap, _latest_meta
    with _stream_lock:
        if not _camera_active:
            return None
        cap = _open_camera_capture()
        if cap is None or not cap.isOpened():
            return None
        ret, frame = cap.read()
        if not ret or frame is None:
            return None

    vs = _get_vision()
    if vs is not None:
        try:
            annotated, objects, faces = vs.process_and_annotate_frame(frame)
            _latest_meta["objects"] = objects
            _latest_meta["faces"] = faces
            return annotated
        except Exception:
            return frame
    return frame

def _mjpeg_generator():
    last_t = time.time()
    while True:
        if not _camera_active:
            time.sleep(0.1)
            continue
        frame = _get_stream_frame()
        if frame is None:
            time.sleep(0.06)
            continue

        now = time.time()
        dt = now - last_t
        if dt > 0:
            _latest_meta["fps"] = round(1.0 / dt, 1)
        last_t = now

        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ok:
            continue
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
               + buf.tobytes() + b"\r\n")
        time.sleep(0.03)

@app.route("/video_feed")
def video_feed():
    return Response(
        _mjpeg_generator(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )

@app.route("/")
def index():
    return send_from_directory("frontend", "index.html")

@app.route("/api/voice/start", methods=["POST"])
def voice_start():
    global voice_process
    if voice_process and voice_process.poll() is None:
        return jsonify({"status": "already_running"})
    try:
        voice_process = subprocess.Popen(
            [PYTHON, os.path.join(BASE_DIR, "voice.py")],
            cwd=BASE_DIR
        )
        return jsonify({"status": "started", "pid": voice_process.pid})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/voice/stop", methods=["POST"])
def voice_stop():
    global voice_process
    if voice_process and voice_process.poll() is None:
        voice_process.terminate()
        try:
            voice_process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            voice_process.kill()
        voice_process = None
        return jsonify({"status": "stopped"})
    return jsonify({"status": "not_running"})

@app.route("/api/voice/status", methods=["GET"])
def voice_status():
    running = voice_process is not None and voice_process.poll() is None
    return jsonify({"running": running})

@app.route("/api/camera/start", methods=["POST"])
def camera_start():
    global _camera_active
    with _stream_lock:
        _camera_active = True
    threading.Thread(target=_get_vision, daemon=True).start()
    return jsonify({"status": "started", "active": True})

@app.route("/api/camera/stop", methods=["POST"])
def camera_stop():
    global _camera_active, _latest_meta
    with _stream_lock:
        _camera_active = False
        _release_camera_capture()
        _latest_meta = {"objects": [], "faces": [], "fps": 0}
    return jsonify({"status": "stopped", "active": False})

@app.route("/api/camera/status", methods=["GET"])
def camera_status():
    return jsonify({
        "running": _camera_active,
        "objects": _latest_meta.get("objects", []),
        "faces": _latest_meta.get("faces", []),
        "fps": _latest_meta.get("fps", 0),
    })

@app.route("/api/control", methods=["POST"])
def control():
    data = request.get_json(force=True)
    direction = data.get("direction", "")
    pressed = bool(data.get("pressed", False))

    if direction in control_state:
        control_state[direction] = 1 if pressed else 0

    return jsonify({"status": "ok", "control": control_state})

@app.route("/api/control/state", methods=["GET"])
def control_get_state():
    return jsonify(control_state)

@app.route("/api/mood", methods=["GET"])
def get_mood():
    return jsonify(mood_state)

@app.route("/api/mood", methods=["POST"])
def set_mood():
    data = request.get_json(force=True)
    mood_state.update(data)
    return jsonify({"status": "ok", "mood": mood_state})

@app.route("/api/profile", methods=["GET"])
def get_profile():
    return jsonify(user_profile)

@app.route("/api/profile/coins", methods=["POST"])
def update_coins():
    data = request.get_json(force=True)
    delta = int(data.get("delta", 0))
    user_profile["coins"] = max(0, user_profile["coins"] + delta)
    return jsonify({"status": "ok", "coins": user_profile["coins"]})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
