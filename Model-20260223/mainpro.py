"""
YOLOv11n inference – run this AFTER training to use your Green Crab model.
Uses your webcam; circles each detection and shows the count. Press Q or ESC to quit.
"""
import sys
import cv2
from pathlib import Path
from ultralytics import YOLO

# Minimum confidence to show a detection (0.25 = show more; 0.5 = stricter). Lower if nothing is detected.
CONF_THRESH = 0.25
# Ask the model to return detections down to this confidence (so we can filter with CONF_THRESH above)
MODEL_CONF = 0.2
# Larger size = better detection when object is far/small (1280 recommended; use 960 if too slow)
IMGSZ = 960

# Prefer this camera index (external USB is often 1 or 2). Set to None to auto-detect.
CAMERA_INDEX = 1

# Use trained weights (run import.py first to train). Path works from Program/ or project root.
weights = Path(__file__).resolve().parent.parent / "runs" / "detect" / "train" / "weights" / "best.pt"
if not weights.exists():
    weights = Path("runs/detect/train/weights/best.pt")
if not weights.exists():
    raise FileNotFoundError(
        "Trained weights not found. Train first: run Program/import.py from the project root."
    )

model = YOLO(str(weights))

# Open camera: use CAMERA_INDEX first (external USB), otherwise auto-detect
def open_camera_at(index, backend):
    cap = cv2.VideoCapture(index, backend)
    if not cap.isOpened():
        return None
    ok, test_frame = cap.read()
    if not ok or test_frame is None:
        cap.release()
        return None
    return cap

camera = None
backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY

# Prefer external camera if CAMERA_INDEX is set
if CAMERA_INDEX is not None:
    camera = open_camera_at(CAMERA_INDEX, backend)
    if camera is not None:
        print(f"Using external camera (index {CAMERA_INDEX})")

if camera is None:
    # Try indices 0, 1, 2, ... until one opens
    for idx in range(5):
        camera = open_camera_at(idx, backend)
        if camera is not None:
            print(f"Using camera index {idx}")
            break
if camera is None and sys.platform == "win32":
    # Fallback: default backend
    for idx in range(5):
        camera = open_camera_at(idx, cv2.CAP_ANY)
        if camera is not None:
            print(f"Using camera index {idx} (default backend)")
            break
if camera is None:
    print("Error: No camera could be opened. If using external USB camera, set CAMERA_INDEX = 1 or 2 at the top of the script.")
    sys.exit(1)

camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

while camera.isOpened():
    success, frame = camera.read()
    if not success:
        continue  # skip this frame (e.g. temporary read error), try next

    results = model(frame, conf=MODEL_CONF, imgsz=IMGSZ, verbose=False)[0]
    boxes = results.boxes
    names = results.names  # e.g. {0: 'Green Crab'}

    count = 0
    for conf, xyxy, cls in zip(boxes.conf, boxes.xyxy, boxes.cls):
        if conf < CONF_THRESH:
            continue
        count += 1
        x1, y1, x2, y2 = map(int, xyxy)
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        radius = int(max(x2 - x1, y2 - y1) / 2 * 1.2)
        radius = max(radius, 20)
        label = names.get(int(cls), "?")
        cv2.circle(frame, (cx, cy), radius, (0, 255, 0), 2)
        cv2.putText(frame, f"{label} {conf:.0%}", (x1, y1 - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    count_text = f"Detected: {count} {list(names.values())[0] if names else 'object'}(s)  (conf>={CONF_THRESH})"
    cv2.putText(frame, count_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    cv2.imshow("Green Crab detector (Q or ESC to quit)", frame)
    key_code = cv2.waitKey(1)
    if key_code in [27, ord("q")]:
        break

camera.release()
cv2.destroyAllWindows() 