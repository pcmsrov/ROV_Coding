#!/usr/bin/env python3
r"""
pvc_detection_diagnostic.py

Diagnostic tool for underwater MATE ROV coral garden images.

Purpose:
    This script does NOT perform final measurement.
    It outputs many intermediate masks so you can visually check which method
    actually captures:
        1. red square targets
        2. white PVC pipes
        3. bottom horizontal PVC pipe

Recommended command:
    python -u .\pvc_detection_diagnostic.py --input .\Rov-photot1.jpg --out .\diag_out --auto-crop-ui

Batch test all images in a folder:
    python -u .\pvc_detection_diagnostic.py --input .\test_images --out .\diag_out --auto-crop-ui

If you want to force a central region:
    python -u .\pvc_detection_diagnostic.py --input .\Rov-photot1.jpg --out .\diag_out --auto-crop-ui --roi 0,40,1280,650
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Dict, List, Tuple

import cv2
import numpy as np


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


def log(msg: str) -> None:
    print(msg, flush=True)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def parse_roi(text: str):
    if not text:
        return None
    parts = [int(float(p.strip())) for p in text.split(",")]
    if len(parts) != 4:
        raise ValueError("--roi must be x,y,w,h")
    return tuple(parts)


def crop_roi(img: np.ndarray, roi):
    if roi is None:
        return img, (0, 0, img.shape[1], img.shape[0])
    x, y, w, h = roi
    ih, iw = img.shape[:2]
    x = max(0, min(x, iw - 1))
    y = max(0, min(y, ih - 1))
    w = max(1, min(w, iw - x))
    h = max(1, min(h, ih - y))
    return img[y:y + h, x:x + w].copy(), (x, y, w, h)


def auto_crop_screenshot_ui(img: np.ndarray):
    h, w = img.shape[:2]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    row_bright = gray.mean(axis=1)
    row_sat = hsv[:, :, 1].mean(axis=1)
    ui_like = (row_bright > 155) & (row_sat < 85)

    top = 0
    for i in range(min(h // 4, 130)):
        if ui_like[i]:
            top = i + 1
        elif top > 0 and i > top + 8:
            break

    bottom = h
    for i in range(h - 1, max(h * 3 // 4, 0), -1):
        if ui_like[i]:
            bottom = i
        elif bottom < h and i < bottom - 8:
            break

    if top > h * 0.18:
        top = 0
    if h - bottom > h * 0.20:
        bottom = h
    if bottom - top < h * 0.55:
        return img, (0, 0, w, h)
    return img[top:bottom, 0:w].copy(), (0, top, w, bottom - top)


def gray_world_white_balance(bgr: np.ndarray) -> np.ndarray:
    img = bgr.astype(np.float32)
    means = img.reshape(-1, 3).mean(axis=0)
    gray_mean = means.mean()
    scale = gray_mean / np.maximum(means, 1.0)
    return np.clip(img * scale, 0, 255).astype(np.uint8)


def standardize_underwater(bgr: np.ndarray) -> np.ndarray:
    wb = gray_world_white_balance(bgr)
    lab = cv2.cvtColor(wb, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l2 = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8)).apply(l)
    enhanced = cv2.cvtColor(cv2.merge([l2, a, b]), cv2.COLOR_LAB2BGR)

    gray = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
    mean = float(gray.mean())
    gamma = 0.72 if mean < 75 else 0.86 if mean < 110 else 1.0
    table = np.array([((i / 255.0) ** gamma) * 255 for i in range(256)], dtype=np.uint8)
    return cv2.bilateralFilter(cv2.LUT(enhanced, table), d=5, sigmaColor=45, sigmaSpace=45)


def make_red_masks(bgr: np.ndarray) -> Dict[str, np.ndarray]:
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)

    # Strict red: fewer false positives, may miss dark red boards.
    strict = cv2.bitwise_or(
        cv2.inRange(hsv, np.array([0, 65, 40]), np.array([13, 255, 255])),
        cv2.inRange(hsv, np.array([167, 65, 40]), np.array([180, 255, 255])),
    )

    # Relaxed red: better for underwater dark/purple/orange red, more false positives.
    relaxed = cv2.bitwise_or(
        cv2.inRange(hsv, np.array([0, 35, 25]), np.array([18, 255, 255])),
        cv2.inRange(hsv, np.array([158, 35, 25]), np.array([180, 255, 255])),
    )

    # LAB red-ish: OpenCV LAB A channel larger means red/magenta direction.
    l_chan, a_chan, b_chan = cv2.split(lab)
    lab_red = ((a_chan > np.percentile(a_chan, 82)) & (l_chan > 25)).astype(np.uint8) * 255

    kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    out = {}
    for name, mask in {
        "red_hsv_strict": strict,
        "red_hsv_relaxed": relaxed,
        "red_lab_a_percentile": lab_red,
    }.items():
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_open, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_close, iterations=2)
        out[name] = mask

    # Combined red mask: better for underwater scenes where one color space
    # catches dark red boards and another catches orange/purple shifted boards.
    combined = cv2.bitwise_or(out["red_hsv_relaxed"], out["red_lab_a_percentile"])
    combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel_open, iterations=1)
    combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel_close, iterations=2)
    out["red_combined_relaxed_lab"] = combined
    return out


def find_red_boxes(mask: np.ndarray, img_shape) -> List[Dict]:
    h, w = img_shape[:2]
    area_img = h * w
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for cnt in contours:
        area = float(cv2.contourArea(cnt))
        if area < area_img * 0.00008 or area > area_img * 0.15:
            continue
        x, y, bw, bh = cv2.boundingRect(cnt)
        if bw < 8 or bh < 8:
            continue
        aspect = bw / max(float(bh), 1.0)
        fill = area / max(float(bw * bh), 1.0)
        # Underwater red boards can look like perspective rectangles, but
        # extremely thin regions are usually labels, UI, ropes, or false color.
        if not (0.45 <= aspect <= 2.3 and fill >= 0.20):
            continue
        # Prefer square-ish targets, but do not require a perfect square.
        square_score = min(aspect, 1.0 / max(aspect, 1e-6))
        boxes.append({
            "x": int(x),
            "y": int(y),
            "w": int(bw),
            "h": int(bh),
            "area": area,
            "aspect": float(aspect),
            "fill": float(fill),
            "square_score": float(square_score),
            "confidence": float(0.45 * min(fill / 0.75, 1.0) + 0.55 * square_score),
        })
    boxes.sort(key=lambda b: (b["confidence"], b["area"]), reverse=True)
    return boxes


def draw_boxes(bgr: np.ndarray, boxes: List[Dict], color=(0, 255, 0)) -> np.ndarray:
    out = bgr.copy()
    for i, b in enumerate(boxes, start=1):
        x, y, w, h = b["x"], b["y"], b["w"], b["h"]
        cv2.rectangle(out, (x, y), (x + w, y + h), color, 2)
        cv2.putText(out, f"R{i}", (x, max(18, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    return out


def make_pvc_masks(bgr: np.ndarray) -> Dict[str, np.ndarray]:
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    l_chan = lab[:, :, 0]
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]

    # Classic white mask.
    hsv_white_strict = ((v > 105) & (s < 105)).astype(np.uint8) * 255

    # Relaxed underwater white/cyan PVC mask.
    hsv_white_relaxed = ((v > 70) & (s < 185)).astype(np.uint8) * 255

    # LAB brightness mask: catches light PVC even if color shifted.
    lab_l_percentile = (l_chan > np.percentile(l_chan, 72)).astype(np.uint8) * 255

    # Adaptive local brightness: useful when global threshold misses pipes.
    lab_l_clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(l_chan)
    adaptive = cv2.adaptiveThreshold(
        lab_l_clahe,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        41,
        -4,
    )

    # Morphological top-hat emphasizes bright thin structures.
    gray_clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (45, 5))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 45))
    tophat_h = cv2.morphologyEx(gray_clahe, cv2.MORPH_TOPHAT, horizontal_kernel)
    tophat_v = cv2.morphologyEx(gray_clahe, cv2.MORPH_TOPHAT, vertical_kernel)
    _, tophat_h_bin = cv2.threshold(tophat_h, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    _, tophat_v_bin = cv2.threshold(tophat_v, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    masks = {
        "pvc_hsv_white_strict": hsv_white_strict,
        "pvc_hsv_white_relaxed": hsv_white_relaxed,
        "pvc_lab_l_percentile": lab_l_percentile,
        "pvc_adaptive_l": adaptive,
        "pvc_tophat_horizontal": tophat_h_bin,
        "pvc_tophat_vertical": tophat_v_bin,
    }

    open_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    close_k = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 5))
    cleaned = {}
    for name, mask in masks.items():
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, open_k, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, close_k, iterations=1)
        cleaned[name] = mask

    combined = cv2.bitwise_or(cleaned["pvc_hsv_white_relaxed"], cleaned["pvc_lab_l_percentile"])
    combined = cv2.bitwise_or(combined, cleaned["pvc_adaptive_l"])
    cleaned["pvc_combined_relaxed"] = combined
    return cleaned


def hough_horizontal(mask: np.ndarray, min_line_ratio=0.06, max_gap_ratio=0.04):
    h, w = mask.shape[:2]
    edges = cv2.Canny(mask, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=max(18, int(min(h, w) * 0.035)),
        minLineLength=max(25, int(w * min_line_ratio)),
        maxLineGap=max(15, int(w * max_gap_ratio)),
    )
    result = []
    if lines is not None:
        for item in lines:
            x1, y1, x2, y2 = [int(v) for v in item[0]]
            angle = math.degrees(math.atan2(y2 - y1, x2 - x1)) % 180
            length = math.hypot(x2 - x1, y2 - y1)
            if angle <= 14 or angle >= 166:
                result.append((x1, y1, x2, y2, length, angle))
    result.sort(key=lambda x: x[4], reverse=True)
    return result[:50]


def line_y_mid(line) -> float:
    x1, y1, x2, y2, _length, _angle = line
    return (y1 + y2) / 2.0


def line_x_interval(line) -> Tuple[int, int]:
    x1, _y1, x2, _y2, _length, _angle = line
    return min(x1, x2), max(x1, x2)


def interval_overlap_ratio(a: Tuple[int, int], b: Tuple[int, int]) -> float:
    a1, a2 = a
    b1, b2 = b
    overlap = max(0, min(a2, b2) - max(a1, b1))
    denom = max(1, min(a2 - a1, b2 - b1))
    return overlap / denom


def filter_dense_horizontal_lines(
    lines,
    image_shape,
    y_cluster_tol: int = 12,
    duplicate_y_tol: int = 8,
    duplicate_overlap: float = 0.55,
    max_dense_cluster_lines: int = 5,
):
    """
    Filter Hough horizontal lines using the observation from field tests:
    real PVC normally produces one or two nearby edge lines, but noisy areas
    produce many red Hough lines stacked in almost the same local position.

    Strategy:
    1. Group lines by similar y position.
    2. If a y group has too many close lines, mark it as dense_noise.
    3. Within non-noise groups, remove near-duplicate overlapping lines.

    Returns:
        kept_lines, rejected_lines
    """
    if not lines:
        return [], []

    h, _w = image_shape[:2]
    sorted_lines = sorted(lines, key=line_y_mid)
    groups: List[List] = []

    for line in sorted_lines:
        y = line_y_mid(line)
        placed = False
        for group in groups:
            gy = float(np.median([line_y_mid(g) for g in group]))
            if abs(y - gy) <= y_cluster_tol:
                group.append(line)
                placed = True
                break
        if not placed:
            groups.append([line])

    kept = []
    rejected = []
    for group in groups:
        ys = np.array([line_y_mid(g) for g in group], dtype=np.float32)
        y_span = float(ys.max() - ys.min()) if len(ys) else 0.0
        group_is_dense_noise = len(group) > max_dense_cluster_lines and y_span <= y_cluster_tol * 1.5

        # Extra penalty near the bottom because pool floor grid/reflection often
        # creates dense stacked horizontal line clusters.
        group_y = float(np.median(ys)) if len(ys) else 0.0
        near_floor = group_y > 0.82 * h
        if near_floor and len(group) >= 4:
            group_is_dense_noise = True

        if group_is_dense_noise:
            rejected.extend(group)
            continue

        # Non-maximum suppression inside this y group.
        group_sorted = sorted(group, key=lambda x: x[4], reverse=True)
        group_kept = []
        for line in group_sorted:
            y = line_y_mid(line)
            xint = line_x_interval(line)
            duplicate = False
            for existing in group_kept:
                ey = line_y_mid(existing)
                eint = line_x_interval(existing)
                if abs(y - ey) <= duplicate_y_tol and interval_overlap_ratio(xint, eint) >= duplicate_overlap:
                    duplicate = True
                    break
            if duplicate:
                rejected.append(line)
            else:
                group_kept.append(line)
        kept.extend(group_kept)

    kept.sort(key=lambda x: x[4], reverse=True)
    rejected.sort(key=lambda x: x[4], reverse=True)
    return kept, rejected


def draw_lines(bgr: np.ndarray, lines) -> np.ndarray:
    out = bgr.copy()
    for i, (x1, y1, x2, y2, length, angle) in enumerate(lines, start=1):
        cv2.line(out, (x1, y1), (x2, y2), (0, 0, 255), 3)
        if i <= 15:
            cv2.putText(out, f"H{i}", (x1, max(18, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)
    return out


def draw_kept_rejected_lines(bgr: np.ndarray, kept, rejected) -> np.ndarray:
    """
    Green = kept after dense-cluster filtering.
    Gray  = rejected dense/duplicate lines.
    """
    out = bgr.copy()
    for x1, y1, x2, y2, _length, _angle in rejected:
        cv2.line(out, (x1, y1), (x2, y2), (120, 120, 120), 2)
    for i, (x1, y1, x2, y2, _length, _angle) in enumerate(kept, start=1):
        cv2.line(out, (x1, y1), (x2, y2), (0, 255, 0), 3)
        if i <= 15:
            cv2.putText(out, f"K{i}", (x1, max(18, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
    return out


def bottom_roi(img: np.ndarray, y_start_ratio=0.50, y_end_ratio=0.92):
    h, w = img.shape[:2]
    y1 = int(h * y_start_ratio)
    y2 = int(h * y_end_ratio)
    return img[y1:y2, :].copy(), y1, y2


def make_contact_sheet(items: List[Tuple[str, np.ndarray]], cell_w=360) -> np.ndarray:
    prepared = []
    for title, img in items:
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        h, w = img.shape[:2]
        scale = cell_w / max(w, 1)
        cell_h = int(h * scale)
        resized = cv2.resize(img, (cell_w, cell_h))
        cv2.rectangle(resized, (0, 0), (cell_w, 28), (0, 0, 0), -1)
        cv2.putText(resized, title[:42], (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
        prepared.append(resized)

    if not prepared:
        return np.zeros((100, cell_w, 3), dtype=np.uint8)

    rows = []
    for i in range(0, len(prepared), 2):
        row_imgs = prepared[i:i + 2]
        max_h = max(im.shape[0] for im in row_imgs)
        padded = []
        for im in row_imgs:
            if im.shape[0] < max_h:
                pad = np.zeros((max_h - im.shape[0], im.shape[1], 3), dtype=np.uint8)
                im = np.vstack([im, pad])
            padded.append(im)
        if len(padded) == 1:
            padded.append(np.zeros_like(padded[0]))
        rows.append(np.hstack(padded))
    return np.vstack(rows)


def process_one(image_path: Path, out_root: Path, auto_crop_ui: bool, roi_text: str) -> Dict:
    out_dir = out_root / image_path.stem
    ensure_dir(out_dir)

    img = cv2.imread(str(image_path))
    if img is None:
        raise RuntimeError(f"OpenCV cannot read {image_path}")

    cv2.imwrite(str(out_dir / "00_original.jpg"), img)

    working = img
    ui_crop = (0, 0, img.shape[1], img.shape[0])
    if auto_crop_ui:
        working, ui_crop = auto_crop_screenshot_ui(working)
    cv2.imwrite(str(out_dir / "01_after_ui_crop.jpg"), working)

    roi = parse_roi(roi_text)
    working, roi_info = crop_roi(working, roi)
    cv2.imwrite(str(out_dir / "02_working_roi.jpg"), working)

    std = standardize_underwater(working)
    cv2.imwrite(str(out_dir / "03_standardized.jpg"), std)

    red_masks = make_red_masks(std)
    pvc_masks = make_pvc_masks(std)

    summary = {
        "image": str(image_path),
        "output_dir": str(out_dir),
        "ui_crop_xywh": ui_crop,
        "roi_xywh_after_ui_crop": roi_info,
        "red_candidates": {},
        "horizontal_line_counts": {},
    }

    contact_items = [
        ("working_roi", working),
        ("standardized", std),
    ]

    # Red masks and boxes.
    for name, mask in red_masks.items():
        cv2.imwrite(str(out_dir / f"10_{name}.png"), mask)
        boxes = find_red_boxes(mask, std.shape)
        summary["red_candidates"][name] = boxes
        boxed = draw_boxes(std, boxes, (0, 255, 0))
        cv2.imwrite(str(out_dir / f"11_{name}_boxes.jpg"), boxed)
        contact_items.append((name, mask))
        contact_items.append((f"{name}_boxes", boxed))

    # PVC masks.
    for name, mask in pvc_masks.items():
        cv2.imwrite(str(out_dir / f"20_{name}.png"), mask)
        lines = hough_horizontal(mask)
        kept_lines, rejected_lines = filter_dense_horizontal_lines(lines, std.shape)
        summary["horizontal_line_counts"][name] = len(lines)
        summary.setdefault("filtered_horizontal_line_counts", {})[name] = {
            "raw": len(lines),
            "kept": len(kept_lines),
            "rejected": len(rejected_lines),
        }
        overlay = draw_lines(std, lines)
        cv2.imwrite(str(out_dir / f"21_{name}_horizontal_lines.jpg"), overlay)
        filtered_overlay = draw_kept_rejected_lines(std, kept_lines, rejected_lines)
        cv2.imwrite(str(out_dir / f"22_{name}_horizontal_lines_filtered.jpg"), filtered_overlay)
        contact_items.append((name, mask))
        contact_items.append((f"{name}_hough", overlay))
        contact_items.append((f"{name}_filtered", filtered_overlay))

    # Bottom ROI diagnostics.
    btm_img, y1, y2 = bottom_roi(std)
    cv2.imwrite(str(out_dir / "30_bottom_roi.jpg"), btm_img)
    bottom_items = [("bottom_roi", btm_img)]
    bottom_summary = {}
    for name, mask in pvc_masks.items():
        btm_mask = mask[y1:y2, :]
        cv2.imwrite(str(out_dir / f"31_bottom_{name}.png"), btm_mask)
        lines = hough_horizontal(btm_mask, min_line_ratio=0.05, max_gap_ratio=0.06)
        kept_lines, rejected_lines = filter_dense_horizontal_lines(lines, btm_mask.shape)
        bottom_summary[name] = len(lines)
        summary.setdefault("bottom_filtered_horizontal_line_counts", {})[name] = {
            "raw": len(lines),
            "kept": len(kept_lines),
            "rejected": len(rejected_lines),
        }

        # Draw bottom lines back on bottom image.
        overlay = btm_img.copy()
        for i, (x1, yy1, x2, yy2, length, angle) in enumerate(lines[:20], start=1):
            cv2.line(overlay, (x1, yy1), (x2, yy2), (0, 0, 255), 3)
            if i <= 10:
                cv2.putText(overlay, f"B{i}", (x1, max(18, yy1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)
        cv2.imwrite(str(out_dir / f"32_bottom_{name}_horizontal_lines.jpg"), overlay)
        filtered_overlay = draw_kept_rejected_lines(btm_img, kept_lines, rejected_lines)
        cv2.imwrite(str(out_dir / f"33_bottom_{name}_horizontal_lines_filtered.jpg"), filtered_overlay)
        bottom_items.append((f"bottom_{name}", btm_mask))
        bottom_items.append((f"bottom_{name}_lines", overlay))
        bottom_items.append((f"bottom_{name}_filtered", filtered_overlay))

    summary["bottom_horizontal_line_counts"] = bottom_summary

    contact = make_contact_sheet(contact_items[:20], cell_w=420)
    cv2.imwrite(str(out_dir / "90_contact_sheet_main.jpg"), contact)
    bottom_contact = make_contact_sheet(bottom_items[:14], cell_w=420)
    cv2.imwrite(str(out_dir / "91_contact_sheet_bottom.jpg"), bottom_contact)

    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def list_images(input_path: Path) -> List[Path]:
    if input_path.is_file():
        return [input_path]
    if input_path.is_dir():
        return sorted([p for p in input_path.iterdir() if p.suffix.lower() in IMAGE_EXTS])
    raise FileNotFoundError(f"Input not found: {input_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnostic masks for underwater PVC and red square detection.")
    parser.add_argument("--input", required=True, help="Input image file or folder.")
    parser.add_argument("--out", default="pvc_diag_out", help="Output folder.")
    parser.add_argument("--auto-crop-ui", action="store_true", help="Crop screenshot UI title/task bars.")
    parser.add_argument("--roi", default="", help="Optional crop after UI crop: x,y,w,h")
    args = parser.parse_args()

    input_path = Path(args.input)
    out_root = Path(args.out)
    ensure_dir(out_root)

    images = list_images(input_path)
    if not images:
        log("No images found.")
        return 2

    all_summaries = []
    log(f"Processing {len(images)} image(s)...")
    for image in images:
        log(f"Processing: {image}")
        try:
            all_summaries.append(process_one(image, out_root, args.auto_crop_ui, args.roi))
        except Exception as exc:
            log(f"ERROR on {image}: {exc}")
            all_summaries.append({"image": str(image), "error": str(exc)})

    (out_root / "all_summary.json").write_text(json.dumps(all_summaries, ensure_ascii=False, indent=2), encoding="utf-8")

    log("")
    log("Done. For each image, check:")
    log("  90_contact_sheet_main.jpg")
    log("  91_contact_sheet_bottom.jpg")
    log("  summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
