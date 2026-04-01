"""
YOLOv11n inference – run this AFTER training to use your Green Crab model.
Uses saved photos instead of a live camera.

How to use:
- Put your photos in the Program folder (same place as this script).
- Supported formats: .jpg, .jpeg, .png
- Run from project root:
    python Program/mainpro.py
- Use any key to go to next image, or Q / ESC to exit.
"""
import cv2
from pathlib import Path
from ultralytics import YOLO

# region agent log
import json, time  # noqa: E401
LOG_PATH = Path(__file__).resolve().parent.parent / "debug-462331.log"
SESSION_ID = "462331"
def _log(hypothesisId: str, location: str, message: str, data: dict, runId: str = "pre-fix"):
    payload = {
        "sessionId": SESSION_ID,
        "runId": runId,
        "hypothesisId": hypothesisId,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass
# endregion

# Minimum confidence for a *strong* detection
# 調低一點，讓更多黃色圈升級成綠色圈
CONF_THRESH = 0.10
# Ask the model to return detections down to this confidence (更弱的也先抓出來)
MODEL_CONF = 0.05
# Larger size = better detection when object is far/small (1280 recommended; use 960 if too slow)
IMGSZ = 960

# Use trained weights (run import.py first to train). Path works from Program/ or project root.
weights = Path(__file__).resolve().parent.parent / "runs" / "detect" / "train" / "weights" / "best.pt"
if not weights.exists():
    weights = Path("runs/detect/train/weights/best.pt")
if not weights.exists():
    raise FileNotFoundError(
        "Trained weights not found. Train first: run Program/import.py from the project root."
    )

model = YOLO(str(weights))
_log("H0", "mainpro.py:weights", "Loaded model weights", {"weights": str(weights), "CONF_THRESH": CONF_THRESH, "MODEL_CONF": MODEL_CONF, "IMGSZ": IMGSZ})

# Collect all images in the Program folder (same directory as this script)
program_dir = Path(__file__).resolve().parent
image_paths = sorted(
    list(program_dir.glob("*.jpg"))
    + list(program_dir.glob("*.jpeg"))
    + list(program_dir.glob("*.png"))
)

if not image_paths:
    raise FileNotFoundError(
        f"No images found in {program_dir}. Put some .jpg / .jpeg / .png files there."
    )

for image_path in image_paths:
    _log("H1", "mainpro.py:loop", "Processing image", {"image": str(image_path)})
    frame = cv2.imread(str(image_path))
    if frame is None:
        print(f"Warning: could not load image {image_path}, skipping.")
        _log("H1", "mainpro.py:imread", "Could not load image", {"image": str(image_path)})
        continue

    results = model(frame, conf=MODEL_CONF, imgsz=IMGSZ, verbose=False)[0]
    boxes = results.boxes
    names = results.names  # e.g. {0: 'Green Crab'}

    strong_count = 0
    weak_count = 0
    total_boxes = int(len(boxes)) if boxes is not None else 0
    confs = [float(x) for x in (boxes.conf.tolist() if boxes is not None and boxes.conf is not None else [])]
    _log("H2", "mainpro.py:pred", "Raw prediction summary", {
        "image": str(image_path),
        "shape": {"h": int(frame.shape[0]), "w": int(frame.shape[1])},
        "total_boxes": total_boxes,
        "conf_min": min(confs) if confs else None,
        "conf_max": max(confs) if confs else None,
        "conf_top5": sorted(confs, reverse=True)[:5],
    })

    for conf, xyxy, cls in zip(boxes.conf, boxes.xyxy, boxes.cls):
        x1, y1, x2, y2 = map(int, xyxy)
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        radius = int(max(x2 - x1, y2 - y1) / 2 * 1.2)
        radius = max(radius, 20)
        label = names.get(int(cls), "?")

        if conf >= CONF_THRESH:
            strong_count += 1
            color = (0, 255, 0)      # 強偵測：綠色粗圈
            thickness = 3
        elif conf >= MODEL_CONF:
            weak_count += 1
            color = (0, 255, 255)    # 弱偵測：黃色細圈，幫你看模型「想」在哪裡
            thickness = 1
        else:
            continue

        cv2.circle(frame, (cx, cy), radius, color, thickness)
        cv2.putText(frame, f"{label} {conf:.0%}", (x1, y1 - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    total = strong_count + weak_count
    _log("H3", "mainpro.py:counts", "Counts after filtering", {
        "image": str(image_path),
        "strong": strong_count,
        "weak": weak_count,
        "total_shown": total
    })
    count_text = (
        f"{image_path.name}  |  Total: {total}  Strong: {strong_count}  Weak: {weak_count}  "
        f"(strong>= {CONF_THRESH}, weak>= {MODEL_CONF})"
    )
    cv2.putText(frame, count_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    cv2.imshow("Green Crab detector (Any key=next, Q or ESC=quit)", frame)
    key_code = cv2.waitKey(0) & 0xFF
    if key_code in [27, ord("q"), ord("Q")]:
        break

cv2.destroyAllWindows()