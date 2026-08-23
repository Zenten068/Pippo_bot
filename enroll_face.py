import os
import sys
import json
from pathlib import Path

import cv2
import numpy as np

from vision import open_camera

SAMPLES_NEEDED = 30
FACE_MODEL_PATH = Path(__file__).parent / "face_model.yml"
FACE_LABELS_PATH = Path(__file__).parent / "face_labels.json"
CAMERA_INDEX = int(os.environ.get("PIPPO_CAMERA_INDEX", "0"))

_BUNDLED_CASCADE = Path(__file__).parent / "haarcascade_frontalface_default.xml"
if _BUNDLED_CASCADE.exists():
    CASCADE_PATH = str(_BUNDLED_CASCADE)
else:
    CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"


def main():
    if len(sys.argv) < 2:
        print('Usage: python enroll_face.py "Your Name"')
        sys.exit(1)
    name = " ".join(sys.argv[1:]).strip()

    labels = {}
    if FACE_LABELS_PATH.exists():
        try:
            labels = json.loads(FACE_LABELS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            labels = {}

    existing_id = next((label_id for label_id, n in labels.items() if n == name), None)
    if existing_id is not None:
        label_id = int(existing_id)
    else:
        label_id = max((int(k) for k in labels.keys()), default=-1) + 1

    cascade = cv2.CascadeClassifier(CASCADE_PATH)
    if cascade.empty():
        sys.exit(1)

    if not hasattr(cv2, "face"):
        sys.exit(1)

    cap = open_camera(CAMERA_INDEX)
    if cap is None:
        sys.exit(1)

    samples = []
    try:
        while len(samples) < SAMPLES_NEEDED:
            ret, frame = cap.read()
            if not ret:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

            for (x, y, w, h) in faces:
                samples.append(gray[y:y + h, x:x + w])
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, f"{len(samples)}/{SAMPLES_NEEDED}", (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                break

            cv2.imshow("Enrolling your face — press q to cancel", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()

    if len(samples) < 10:
        sys.exit(1)

    try:
        recognizer = cv2.face.LBPHFaceRecognizer_create()
    except AttributeError:
        sys.exit(1)

    label_ids = np.array([label_id] * len(samples))

    if FACE_MODEL_PATH.exists():
        recognizer.read(str(FACE_MODEL_PATH))
        recognizer.update(samples, label_ids)
    else:
        recognizer.train(samples, label_ids)

    recognizer.save(str(FACE_MODEL_PATH))
    labels[str(label_id)] = name
    FACE_LABELS_PATH.write_text(json.dumps(labels, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
