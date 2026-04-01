"""
YOLOv11n training – run this to train the Green Crab model.
After training, best.pt is saved to runs/detect/train/weights/

Run from the project root (roboflow folder):
  python Program/import.py

Tweaks for better robustness:
- higher resolution training (imgsz=960)
- more epochs (200) so the model fits your ~120 images better
"""
from pathlib import Path
from ultralytics import YOLO

if __name__ == "__main__":
    # data.yaml path: project root (roboflow folder, not Program/)
    project_root = Path(__file__).resolve().parent.parent
    data_yaml = project_root / "Program" / "New-Version" / "data.yaml"
    if not data_yaml.exists():
        raise FileNotFoundError(f"data.yaml not found at {data_yaml}")
    # Use official name so Ultralytics auto-downloads weights (no local file needed)
    model = YOLO("yolo11n.pt")
    results = model.train(data=str(data_yaml), epochs=200, imgsz=960)


