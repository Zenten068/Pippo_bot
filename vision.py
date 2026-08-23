import os
import json
import threading
import time
from pathlib import Path

import cv2

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False


FACE_MODEL_PATH = Path(__file__).parent / "face_model.yml"
FACE_LABELS_PATH = Path(__file__).parent / "face_labels.json"

_BUNDLED_CASCADE = Path(__file__).parent / "haarcascade_frontalface_default.xml"
if _BUNDLED_CASCADE.exists():
    CASCADE_PATH = str(_BUNDLED_CASCADE)
else:
    CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"

OBJECT_CONF_THRESHOLD = 0.5
FACE_CONFIDENCE_THRESHOLD = 70
CAMERA_INDEX = int(os.environ.get("PIPPO_CAMERA_INDEX", "0"))
LOOP_INTERVAL_SEC = 0.5
MAX_CONSECUTIVE_READ_FAILURES = 8


def open_camera(index=None):
    if index is None:
        index = CAMERA_INDEX

    backends = []
    if hasattr(cv2, "CAP_DSHOW"):
        backends.append(("DirectShow", cv2.CAP_DSHOW))
    backends.append(("default", None))
    if hasattr(cv2, "CAP_MSMF"):
        backends.append(("MSMF", cv2.CAP_MSMF))

    for name, api in backends:
        cap = None
        try:
            cap = cv2.VideoCapture(index, api) if api is not None else cv2.VideoCapture(index)
            if not cap.isOpened():
                cap.release()
                continue

            try:
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception:
                pass
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            ok = False
            for _ in range(8):
                ret, frame = cap.read()
                if ret and frame is not None:
                    ok = True
                    break
                time.sleep(0.05)

            if ok:
                return cap

            cap.release()
        except Exception:
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass

    return None


class VisionSystem:
    def __init__(self, camera_index=CAMERA_INDEX, detect_objects=True, recognize_faces=True):
        self.camera_index = camera_index
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._current_objects = []
        self._current_faces = []

        self.detect_objects_enabled = detect_objects and YOLO_AVAILABLE
        self.recognize_faces_enabled = recognize_faces and FACE_MODEL_PATH.exists()

        self.yolo_model = None
        if self.detect_objects_enabled:
            local_weights = Path(__file__).parent / "yolov8n.pt"
            weights = str(local_weights) if local_weights.exists() else "yolov8n.pt"
            self.yolo_model = YOLO(weights)

        self.face_recognizer = None
        self.face_labels = {}
        if self.recognize_faces_enabled:
            try:
                self.face_recognizer = cv2.face.LBPHFaceRecognizer_create()
                self.face_recognizer.read(str(FACE_MODEL_PATH))
                if FACE_LABELS_PATH.exists():
                    self.face_labels = json.loads(
                        FACE_LABELS_PATH.read_text(encoding="utf-8")
                    )
                else:
                    self.recognize_faces_enabled = False
            except Exception:
                self.recognize_faces_enabled = False

        self.face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
        if self.face_cascade.empty():
            self.recognize_faces_enabled = False

    def start(self):
        if not (self.detect_objects_enabled or self.recognize_faces_enabled):
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _loop(self):
        cap = open_camera(self.camera_index)
        if cap is None:
            self._running = False
            return

        consecutive_failures = 0
        try:
            while self._running:
                ret, frame = cap.read()
                if not ret or frame is None:
                    consecutive_failures += 1
                    if consecutive_failures >= MAX_CONSECUTIVE_READ_FAILURES:
                        cap.release()
                        time.sleep(0.3)
                        cap = open_camera(self.camera_index)
                        consecutive_failures = 0
                        if cap is None:
                            self._running = False
                            return
                    time.sleep(0.1)
                    continue

                consecutive_failures = 0
                _, objects, faces = self.process_and_annotate_frame(frame)

                with self._lock:
                    self._current_objects = objects
                    self._current_faces = faces

                time.sleep(LOOP_INTERVAL_SEC)
        finally:
            if cap is not None:
                cap.release()

    def process_and_annotate_frame(self, frame):
        annotated = frame.copy()
        found_objects = []
        found_faces = []

        if self.detect_objects_enabled and self.yolo_model is not None:
            try:
                results = self.yolo_model(frame, verbose=False)[0]
                names = results.names
                for box in results.boxes:
                    conf = float(box.conf[0])
                    if conf < OBJECT_CONF_THRESHOLD:
                        continue
                    cls_id = int(box.cls[0])
                    obj_name = names.get(cls_id, f"object_{cls_id}")
                    found_objects.append(obj_name)

                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    box_color = (0, 230, 100)
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), box_color, 2)

                    tag = f" {obj_name.upper()} {int(conf * 100)}% "
                    (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_DUPLEX, 0.45, 1)
                    ty1 = max(y1 - th - 6, 0)
                    cv2.rectangle(annotated, (x1, ty1), (x1 + tw, y1), box_color, -1)
                    cv2.putText(annotated, tag, (x1, y1 - 4), cv2.FONT_HERSHEY_DUPLEX, 0.45, (0, 20, 0), 1, cv2.LINE_AA)
            except Exception:
                pass

        if self.recognize_faces_enabled and self.face_cascade is not None and not self.face_cascade.empty():
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                detected = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
                for (x, y, fw, fh) in detected:
                    name = "Face"
                    if self.face_recognizer is not None:
                        roi = gray[y:y + fh, x:x + fw]
                        label_id, confidence = self.face_recognizer.predict(roi)
                        if confidence < FACE_CONFIDENCE_THRESHOLD:
                            name = self.face_labels.get(str(label_id), "Face")
                    found_faces.append(name)

                    box_color = (0, 150, 255)
                    cv2.rectangle(annotated, (x, y), (x + fw, y + fh), box_color, 2)

                    tag = f" 👤 {name.upper()} "
                    (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_DUPLEX, 0.45, 1)
                    ty1 = max(y - th - 6, 0)
                    cv2.rectangle(annotated, (x, ty1), (x + tw, y), box_color, -1)
                    cv2.putText(annotated, tag, (x, y - 4), cv2.FONT_HERSHEY_DUPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
            except Exception:
                pass

        with self._lock:
            self._current_objects = found_objects
            self._current_faces = found_faces

        return annotated, found_objects, found_faces

    def get_scene_description(self):
        with self._lock:
            objects = list(self._current_objects)
            faces = list(self._current_faces)

        parts = []
        if faces:
            seen = []
            for name in faces:
                if name not in seen:
                    seen.append(name)
            parts.append(f"Face(s) in view: {', '.join(seen)}")
        if objects:
            counts = {}
            for name in objects:
                counts[name] = counts.get(name, 0) + 1
            obj_bits = [
                f"{n} (x{c})" if c > 1 else n
                for n, c in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
            ]
            parts.append(f"Objects in view: {', '.join(obj_bits)}")
        return "; ".join(parts) if parts else None

    def owner_is_present(self, owner_name):
        with self._lock:
            return owner_name in self._current_faces


def _standalone_preview():
    vs = VisionSystem()
    cap = open_camera(vs.camera_index)
    if cap is None:
        print("Couldn't open the camera.")
        return

    win_title = "PIPPO Vision (YOLOv8 + Face Recognition) - press 'q' to quit"
    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                continue

            annotated, _, _ = vs.process_and_annotate_frame(frame)
            cv2.imshow(win_title, annotated)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                break
            try:
                if cv2.getWindowProperty(win_title, cv2.WND_PROP_VISIBLE) < 1:
                    break
            except Exception:
                pass
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    _standalone_preview()
