""" YOLOv11n Green Crab 偵測器 - 穩定精準版 v3.2
改進：亮度平均值評測 + 全局縮放，讓不同光線場景統一到相近亮度再做偵測
"""

import cv2
import numpy as np
from pathlib import Path
from ultralytics import YOLO
import json
import time

# region agent log (原版保留)
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

# ★調整參數：更嚴格，減少誤檢
CONF_THRESH = 0.15      # 強偵測閾值（綠圈）
MODEL_CONF = 0.08       # 最低信心（弱偵測）
MIN_AREA = 200          # 最小面積過濾（防小雜訊）
MAX_AREA_RATIO = 0.3    # 最大佔比（防背景誤檢）
IOU_THRESH = 0.5        # NMS重疊閾值

IMGSZ = 960

# --- 亮度評測 + 全局平均亮度縮放 ---
TARGET_GRAY = 130.0   # 想要統一到的灰階平均亮度 (0~255)
GRAY_LOW = 90.0       # 過暗判定門檻
GRAY_HIGH = 170.0     # 過亮判定門檻


def measure_gray(frame):
    """回傳 (mean_gray, pct_under, pct_over)"""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
    mean_gray = float(np.mean(gray))
    pct_under = float(np.mean(gray < 40.0))   # 很暗的比例
    pct_over = float(np.mean(gray > 215.0))   # 很亮的比例
    return mean_gray, pct_under, pct_over


def light_adaptive_normalize(frame):
    """
    1) 先算目前灰階平均亮度 mean_gray
    2) 判斷 DARK / OVER / OK
    3) 若過暗/過亮：整張圖乘上同一個縮放係數，讓平均亮度接近 TARGET_GRAY
       （不改尺寸、不裁切，只調整亮度）
    """
    mean_gray, pct_under, pct_over = measure_gray(frame)

    if mean_gray < GRAY_LOW:
        bright_type = "DARK"
    elif mean_gray > GRAY_HIGH:
        bright_type = "OVER"
    else:
        bright_type = "OK"

    # 只有過暗或過亮才調整；正常就保持原圖
    if bright_type != "OK" and mean_gray > 1e-6:
        scale = float(TARGET_GRAY / mean_gray)
    else:
        scale = 1.0

    frame_f = frame.astype(np.float32) * scale
    frame_f = np.clip(frame_f, 0, 255).astype(np.uint8)

    new_mean_gray, _, _ = measure_gray(frame_f)

    info = {
        "orig_mean_gray": mean_gray,
        "new_mean_gray": new_mean_gray,
        "bright_type": bright_type,
        "scale": scale,
        "pct_under": pct_under,
        "pct_over": pct_over,
    }
    return frame_f, info


# ★嚴格尺寸/位置過濾，減少誤檢
def strict_filter(detections, frame_shape):
    """尺寸 + 位置過濾，減少誤檢"""
    filtered = []
    h, w = frame_shape[:2]

    for conf, box, cls in detections:
        x1, y1, x2, y2 = box
        area = (x2 - x1) * (y2 - y1)
        area_ratio = area / (h * w)

        # 尺寸過濾
        if area < MIN_AREA or area_ratio > MAX_AREA_RATIO:
            continue

        # 邊緣過濾（避免截斷目標）
        if (x1 < 20 or y1 < 20 or x2 > w - 20 or y2 > h - 20):
            conf *= 0.8  # 邊緣懲罰

        filtered.append((conf, box, cls))

    return filtered


# ★簡單 NMS 去重
def simple_nms(detections, iou_thresh=IOU_THRESH):
    """簡單NMS去重"""
    if not detections:
        return []

    detections = sorted(detections, key=lambda x: x[0], reverse=True)
    keep = []

    for conf, box1, cls1 in detections:
        if conf < MODEL_CONF:
            continue

        keep_box = True
        for k_conf, k_box, k_cls in keep:
            if cls1 != k_cls:
                continue  # 不同類別不抑制

            # IoU計算
            x1a, y1a, x2a, y2a = box1
            x1b, y1b, x2b, y2b = k_box
            xi1 = max(x1a, x1b)
            yi1 = max(y1a, y1b)
            xi2 = min(x2a, x2b)
            yi2 = min(y2a, y2b)
            inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)
            box1_area = (x2a - x1a) * (y2a - y1a)
            box2_area = (x2b - x1b) * (y2b - y1b)
            denom = (box1_area + box2_area - inter_area)
            iou = inter_area / denom if denom > 0 else 0.0

            if iou > iou_thresh:
                keep_box = False
                break

        if keep_box:
            keep.append((conf, box1, cls1))

    return keep


# 載入模型
weights = Path(__file__).resolve().parent.parent / "runs" / "detect" / "train" / "weights" / "best.pt"
if not weights.exists():
    weights = Path("runs/detect/train/weights/best.pt")
if not weights.exists():
    raise FileNotFoundError("Trained weights not found.")
model = YOLO(str(weights))
_log(
    "H0",
    "v3.2-stable",
    "Loaded Stable Brightness v3.2",
    {
        "CONF_THRESH": CONF_THRESH,
        "MODEL_CONF": MODEL_CONF,
        "MIN_AREA": MIN_AREA,
        "IOU_THRESH": IOU_THRESH,
        "TARGET_GRAY": TARGET_GRAY,
        "GRAY_LOW": GRAY_LOW,
        "GRAY_HIGH": GRAY_HIGH,
    },
)

# 收集圖片
program_dir = Path(__file__).resolve().parent
image_paths = sorted(
    list(program_dir.glob("*.jpg"))
    + list(program_dir.glob("*.jpeg"))
    + list(program_dir.glob("*.png"))
)
if not image_paths:
    raise FileNotFoundError(f"No images in {program_dir}")

for image_path in image_paths:
    _log("H1", "v3.2:loop", "Stable processing", {"image": str(image_path)})

    frame = cv2.imread(str(image_path))
    if frame is None:
        print(f"Warning: could not load {image_path}")
        continue

    # 亮度評測 + 全局縮放（不改尺寸）
    frame_inference, bright_info = light_adaptive_normalize(frame)
    draw_frame = frame_inference.copy()

    # 在左上角顯示亮度資訊
    cv2.putText(
        draw_frame,
        f"G:{bright_info['orig_mean_gray']:.1f}->{bright_info['new_mean_gray']:.1f} {bright_info['bright_type']} x{bright_info['scale']:.2f}",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
    )

    # 推理
    results = model(frame_inference, conf=MODEL_CONF, imgsz=IMGSZ, verbose=False)[0]
    boxes = results.boxes
    names = results.names

    # 轉換為 list + 過濾 + NMS
    raw_detections = []
    if boxes is not None:
        for conf, xyxy, cls in zip(boxes.conf, boxes.xyxy, boxes.cls):
            raw_detections.append((float(conf), tuple(map(int, xyxy)), int(cls)))

    filtered_detections = strict_filter(raw_detections, frame.shape)
    final_detections = simple_nms(filtered_detections)

    # 精準統計
    strong_count = sum(1 for conf, _, _ in final_detections if conf >= CONF_THRESH)
    weak_count = len(final_detections) - strong_count
    total = len(final_detections)

    _log(
        "H2",
        "v3.2:results",
        "Precision results",
        {
            "image": str(image_path),
            "raw": len(raw_detections),
            "filtered": len(filtered_detections),
            "final": total,
            "strong": strong_count,
            "weak": weak_count,
        },
    )

    # 畫圈（用過濾後結果）
    for conf, xyxy, cls in final_detections:
        x1, y1, x2, y2 = xyxy
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        radius = max(20, int(max(x2 - x1, y2 - y1) / 2 * 1.2))
        label = names.get(cls, "?")

        if conf >= CONF_THRESH:
            color = (0, 255, 0)   # 強偵測：綠圈
            thickness = 3
        else:
            color = (0, 255, 255)  # 弱偵測：黃圈
            thickness = 1

        cv2.circle(draw_frame, (cx, cy), radius, color, thickness)
        cv2.putText(
            draw_frame,
            f"{label} {conf:.0%}",
            (x1, y1 - 6),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
        )

    count_text = f"{image_path.name} | Total:{total} Strong:{strong_count} Weak:{weak_count}"
    cv2.putText(draw_frame, count_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    # 顯示（OpenCV 只是把視窗放大顯示，不會裁切原圖）
    cv2.imshow("Green Crab detector (brightness-normalized image)", draw_frame)
    key_code = cv2.waitKey(0) & 0xFF
    if key_code in [27, ord("q"), ord("Q")]:
        break

cv2.destroyAllWindows()