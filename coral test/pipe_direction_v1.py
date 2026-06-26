#!/usr/bin/env python3
r"""
pipe_direction_v1.py
--------------------
水管方向判斷診斷程序（橫管 + 豎管 + 雜訊清理）

主要改進（相對 pvc_detection_diagnostic.py）：
  1. 橫豎 Top-hat 分開做，不混用 kernel
  2. 高光遮蔽（反光區 inpaint）在前處理最前面
  3. 角度容差：橫管 ±15°，豎管 75°–105°
  4. Skeleton（骨架化）取代 Hough 作為主要線段來源
     - 如無 cv2.ximgproc，自動回退到 erode 近似 skeleton
  5. 線段合併：同方向、鄰近、重疊的碎段合併成一條
  6. 橫豎接入點互相驗證（豎管底端 x 應在橫管端點附近）
  7. 紅色方塊：HSV 擴展水下範圍 + RGB dominance + LAB a-channel 投票

用法：
    python -u pipe_direction_v1.py --input image.jpg --out diag_out
    python -u pipe_direction_v1.py --input test_images/ --out diag_out --auto-crop-ui
    python -u pipe_direction_v1.py --input image.jpg --out diag_out --roi 0,40,1280,650

輸出（每張圖一個子資料夾）：
    00_original.jpg
    01_highlight_removed.jpg      高光遮蔽結果
    02_standardized.jpg           白平衡 + CLAHE
    10_tophat_h.jpg               橫向 Top-hat（橫管增強）
    11_tophat_v.jpg               豎向 Top-hat（豎管增強）
    12_h_pipe_mask.jpg            橫管 mask（形態學清理後）
    13_v_pipe_mask.jpg            豎管 mask（形態學清理後）
    20_h_skeleton.jpg             橫管骨架
    21_v_skeleton.jpg             豎管骨架
    22_h_lines_raw.jpg            橫管原始線段
    23_v_lines_raw.jpg            豎管原始線段
    24_h_lines_merged.jpg         橫管合併後（紅=最終保留）
    25_v_lines_merged.jpg         豎管合併後
    26_cross_validated.jpg        橫豎接入點互相驗證結果
    30_red_hsv.jpg                紅色 HSV mask
    31_red_rgb_dominance.jpg      紅色 RGB dominance mask
    32_red_lab_a.jpg              紅色 LAB a-channel mask
    33_red_voted.jpg              三通道投票後 mask
    34_red_boxes.jpg              最終紅色方塊框
    90_summary.jpg                總覽 contact sheet
"""

from __future__ import annotations

import argparse
import math
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


# ──────────────────────────────────────────────
# 工具函數
# ──────────────────────────────────────────────

def log(msg: str) -> None:
    print(msg, flush=True)


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def parse_roi(text: str) -> Optional[Tuple[int, int, int, int]]:
    if not text:
        return None
    parts = [int(float(x.strip())) for x in text.split(",")]
    if len(parts) != 4:
        raise ValueError("--roi 格式：x,y,w,h")
    return tuple(parts)


def apply_roi(img: np.ndarray, roi: Optional[Tuple]) -> Tuple[np.ndarray, Tuple]:
    if roi is None:
        h, w = img.shape[:2]
        return img, (0, 0, w, h)
    x, y, w, h = roi
    ih, iw = img.shape[:2]
    x, y = max(0, x), max(0, y)
    w = min(w, iw - x)
    h = min(h, ih - y)
    return img[y:y+h, x:x+w].copy(), (x, y, w, h)


def auto_crop_ui(img: np.ndarray) -> np.ndarray:
    """自動裁去截圖上下的 UI 工具欄"""
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
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
        return img
    return img[top:bottom, :].copy()


# ──────────────────────────────────────────────
# 前處理：高光遮蔽 + 白平衡 + CLAHE
# ──────────────────────────────────────────────

def remove_highlight(bgr: np.ndarray, threshold: int = 235, radius: int = 9) -> np.ndarray:
    """
    偵測過亮的高光區域（水面反光、強燈光白斑），
    用 inpaint 填補，避免後續標準化被高光拉偏。
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    _, highlight_mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
    # 稍微膨脹，把反光邊緣也包進去
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (radius, radius))
    highlight_mask = cv2.dilate(highlight_mask, kernel, iterations=1)
    # 高光區域佔比太大時跳過 inpaint（否則會扭曲整張圖）
    ratio = highlight_mask.sum() / 255 / (bgr.shape[0] * bgr.shape[1])
    if ratio > 0.30:
        return bgr
    result = cv2.inpaint(bgr, highlight_mask, inpaintRadius=7, flags=cv2.INPAINT_TELEA)
    return result


def standardize_underwater(bgr: np.ndarray) -> np.ndarray:
    """
    Percentile-based 白平衡 + CLAHE。
    使用 5th–95th percentile 避免高光/暗角拉偏。
    """
    result = bgr.astype(np.float32)
    for c in range(3):
        ch = result[:, :, c]
        lo = float(np.percentile(ch, 5))
        hi = float(np.percentile(ch, 95))
        if hi > lo:
            result[:, :, c] = np.clip((ch - lo) / (hi - lo) * 255.0, 0, 255)
    result = result.astype(np.uint8)

    lab = cv2.cvtColor(result, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


# ──────────────────────────────────────────────
# 水管 mask：橫豎分開 Top-hat + 形態學清理
# ──────────────────────────────────────────────

def make_directional_pipe_masks(
    bgr: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    返回 (tophat_h, tophat_v, mask_h_clean, mask_v_clean)

    mask_h_clean：橫管 mask（形態學開運算 + 橫向閉運算）
    mask_v_clean：豎管 mask（形態學開運算 + 豎向閉運算）

    關鍵：橫豎使用不同 kernel，不混用。
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    gray_eq = clahe.apply(gray)

    # Top-hat：找比背景亮的細長亮帶
    # 橫向 kernel：寬長窄高，強調橫管
    k_tophat_h = cv2.getStructuringElement(cv2.MORPH_RECT, (55, 5))
    # 豎向 kernel：窄寬長高，強調豎管
    k_tophat_v = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 55))

    tophat_h = cv2.morphologyEx(gray_eq, cv2.MORPH_TOPHAT, k_tophat_h)
    tophat_v = cv2.morphologyEx(gray_eq, cv2.MORPH_TOPHAT, k_tophat_v)

    # Otsu 二值化
    _, mask_h = cv2.threshold(tophat_h, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    _, mask_v = cv2.threshold(tophat_v, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 橫管清理：
    #   開運算(3×3) 去掉孤立噪聲點
    #   橫向閉運算(65×5) 連接橫向碎片
    #   連通組件過濾：面積和寬度都要夠
    open_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    close_h_k = cv2.getStructuringElement(cv2.MORPH_RECT, (65, 5))
    close_v_k = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 65))

    mask_h_clean = cv2.morphologyEx(mask_h, cv2.MORPH_OPEN, open_k, iterations=1)
    mask_h_clean = cv2.morphologyEx(mask_h_clean, cv2.MORPH_CLOSE, close_h_k, iterations=1)
    mask_h_clean = filter_components(mask_h_clean, min_area=200, min_width=40, min_height=0)

    mask_v_clean = cv2.morphologyEx(mask_v, cv2.MORPH_OPEN, open_k, iterations=1)
    mask_v_clean = cv2.morphologyEx(mask_v_clean, cv2.MORPH_CLOSE, close_v_k, iterations=1)
    # 豎管連通過濾：高度要夠，長寬比要細長
    mask_v_clean = filter_components(
        mask_v_clean,
        min_area=150,
        min_height=int(bgr.shape[0] * 0.10),
        min_aspect_ratio=2.5,
    )

    return tophat_h, tophat_v, mask_h_clean, mask_v_clean


def filter_components(
    binary: np.ndarray,
    min_area: int = 0,
    min_width: int = 0,
    min_height: int = 0,
    min_aspect_ratio: float = 0.0,
    max_aspect_ratio: float = 9999.0,
) -> np.ndarray:
    """連通組件過濾，保留符合條件的組件"""
    num, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    out = np.zeros_like(binary)
    for i in range(1, num):
        w = stats[i, cv2.CC_STAT_WIDTH]
        h = stats[i, cv2.CC_STAT_HEIGHT]
        area = stats[i, cv2.CC_STAT_AREA]
        aspect = h / max(w, 1)
        if area < min_area:
            continue
        if w < min_width:
            continue
        if h < min_height:
            continue
        if aspect < min_aspect_ratio or aspect > max_aspect_ratio:
            continue
        out[labels == i] = 255
    return out


# ──────────────────────────────────────────────
# 骨架化：skeleton / 近似 skeleton
# ──────────────────────────────────────────────

def skeletonize(binary: np.ndarray) -> np.ndarray:
    """
    優先用 cv2.ximgproc.thinning（需要 opencv-contrib）。
    如無，用迭代 erode 近似（速度較慢，效果可接受）。
    """
    if binary.max() == 0:
        return binary.copy()

    try:
        # opencv-contrib 版本
        skeleton = cv2.ximgproc.thinning(binary, thinningType=cv2.ximgproc.THINNING_ZHANGSUEN)
        return skeleton
    except AttributeError:
        pass

    # 回退：迭代 erode 近似骨架
    skeleton = np.zeros_like(binary)
    img = binary.copy()
    kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    max_iter = 50
    for _ in range(max_iter):
        eroded = cv2.erode(img, kernel)
        opened = cv2.dilate(eroded, kernel)
        diff = cv2.subtract(img, opened)
        skeleton = cv2.bitwise_or(skeleton, diff)
        img = eroded.copy()
        if img.max() == 0:
            break
    return skeleton


# ──────────────────────────────────────────────
# 線段提取：從骨架 / mask 提取有向線段
# ──────────────────────────────────────────────

def extract_lines_from_mask(
    mask: np.ndarray,
    direction: str,           # 'horizontal' or 'vertical'
    img_shape: Tuple[int, int],
) -> List[Dict]:
    """
    使用 HoughLinesP，但限制 theta 範圍在目標方向。
    direction='horizontal'：角度容差 ±15°
    direction='vertical'：角度容差 75°–105°

    返回線段列表，每個元素：
    {x1, y1, x2, y2, length, angle_deg, cx, cy}
    """
    h, w = img_shape[:2]
    edges = cv2.Canny(mask, 30, 100, apertureSize=3)

    if direction == "horizontal":
        min_len = max(25, int(w * 0.05))
        max_gap = max(20, int(w * 0.05))
    else:
        min_len = max(20, int(h * 0.08))
        max_gap = max(15, int(h * 0.05))

    raw = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=max(15, int(min(h, w) * 0.025)),
        minLineLength=min_len,
        maxLineGap=max_gap,
    )

    lines = []
    if raw is None:
        return lines

    for item in raw:
        x1, y1, x2, y2 = [int(v) for v in item[0]]
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        angle = math.degrees(math.atan2(abs(dy), abs(dx)))  # 0°=水平, 90°=垂直

        if direction == "horizontal":
            # 角度容差 ±15°（即 angle <= 15°）
            if angle > 15.0:
                continue
        else:
            # 垂直方向：angle 75°–105°（atan2 這裡 angle > 75°）
            if angle < 72.0:
                continue

        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        lines.append(dict(x1=x1, y1=y1, x2=x2, y2=y2,
                          length=length, angle_deg=angle,
                          cx=cx, cy=cy))

    lines.sort(key=lambda l: l["length"], reverse=True)
    return lines


# ──────────────────────────────────────────────
# 線段合併：同方向鄰近碎段合併
# ──────────────────────────────────────────────

def merge_lines(
    lines: List[Dict],
    direction: str,
    y_tol: int = 18,    # 橫管：y 中心容差
    x_tol: int = 18,    # 豎管：x 中心容差
    gap_tol: int = 50,  # 允許的端點間距（像素）
) -> List[Dict]:
    """
    把同方向、鄰近、在同一主軸位置上的碎段合併成一條線。

    橫管合併條件：
      - y 中心差 < y_tol
      - x 區間有重疊或 gap < gap_tol

    豎管合併條件：
      - x 中心差 < x_tol
      - y 區間有重疊或 gap < gap_tol
    """
    if not lines:
        return []

    # 用 Union-Find 做分組
    n = len(lines)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        parent[find(i)] = find(j)

    for i in range(n):
        for j in range(i + 1, n):
            a, b = lines[i], lines[j]
            if direction == "horizontal":
                # y 主軸對齊
                if abs(a["cy"] - b["cy"]) > y_tol:
                    continue
                # x 區間鄰近
                ax_min = min(a["x1"], a["x2"])
                ax_max = max(a["x1"], a["x2"])
                bx_min = min(b["x1"], b["x2"])
                bx_max = max(b["x1"], b["x2"])
                overlap = min(ax_max, bx_max) - max(ax_min, bx_min)
                gap = max(bx_min - ax_max, ax_min - bx_max)
                if overlap >= 0 or gap <= gap_tol:
                    union(i, j)
            else:
                # x 主軸對齊
                if abs(a["cx"] - b["cx"]) > x_tol:
                    continue
                # y 區間鄰近
                ay_min = min(a["y1"], a["y2"])
                ay_max = max(a["y1"], a["y2"])
                by_min = min(b["y1"], b["y2"])
                by_max = max(b["y1"], b["y2"])
                overlap = min(ay_max, by_max) - max(ay_min, by_min)
                gap = max(by_min - ay_max, ay_min - by_max)
                if overlap >= 0 or gap <= gap_tol:
                    union(i, j)

    # 每個群只保留一條「代表線段」（橫/豎方向的 span）
    groups: Dict[int, List[Dict]] = {}
    for i, line in enumerate(lines):
        root = find(i)
        groups.setdefault(root, []).append(line)

    merged = []
    for group in groups.values():
        if direction == "horizontal":
            # 代表線：y 取 median，x 取整個群的最小到最大
            ys = [(l["y1"] + l["y2"]) / 2.0 for l in group]
            y_med = int(np.median(ys))
            xs = [l["x1"] for l in group] + [l["x2"] for l in group]
            x_min, x_max = min(xs), max(xs)
            length = x_max - x_min
            merged.append(dict(
                x1=x_min, y1=y_med, x2=x_max, y2=y_med,
                length=float(length), angle_deg=0.0,
                cx=(x_min + x_max) / 2.0, cy=float(y_med),
                n_merged=len(group),
            ))
        else:
            xs = [(l["x1"] + l["x2"]) / 2.0 for l in group]
            x_med = int(np.median(xs))
            ys = [l["y1"] for l in group] + [l["y2"] for l in group]
            y_min, y_max = min(ys), max(ys)
            length = y_max - y_min
            merged.append(dict(
                x1=x_med, y1=y_min, x2=x_med, y2=y_max,
                length=float(length), angle_deg=90.0,
                cx=float(x_med), cy=(y_min + y_max) / 2.0,
                n_merged=len(group),
            ))

    merged.sort(key=lambda l: l["length"], reverse=True)
    return merged


# ──────────────────────────────────────────────
# 橫豎接入點互相驗證
# ──────────────────────────────────────────────

def cross_validate_pipes(
    h_lines: List[Dict],
    v_lines: List[Dict],
    img: np.ndarray,
    x_tol: int = 55,
    y_tol: int = 55,
) -> Tuple[List[Dict], List[Dict], np.ndarray]:
    """
    豎管底端 x 應在某條橫管的 x 範圍內（±x_tol）。
    橫管端點 x 應在某條豎管的 x 附近（±x_tol）。

    返回：
      h_validated, v_validated, vis_img
    """
    vis = img.copy()

    # 先畫所有橫管（藍色）
    for l in h_lines:
        cv2.line(vis, (l["x1"], l["y1"]), (l["x2"], l["y2"]), (200, 180, 0), 2)

    # 先畫所有豎管（灰色）
    for l in v_lines:
        cv2.line(vis, (l["x1"], l["y1"]), (l["x2"], l["y2"]), (160, 160, 160), 2)

    if not h_lines or not v_lines:
        return h_lines, v_lines, vis

    # 豎管驗證：底端 x 是否鄰近某條橫管端點
    def v_has_anchor(v: Dict) -> bool:
        vx = v["cx"]
        vy_bottom = max(v["y1"], v["y2"])
        for h in h_lines:
            # 豎管 x 在橫管的 x 範圍內
            hx_min = min(h["x1"], h["x2"]) - x_tol
            hx_max = max(h["x1"], h["x2"]) + x_tol
            # 橫管 y 接近豎管底端或頂端
            hy = h["cy"]
            vy_top = min(v["y1"], v["y2"])
            if hx_min <= vx <= hx_max:
                # 橫管在豎管上方（豎管從橫管向上）或在豎管下方
                if abs(hy - vy_bottom) < y_tol or abs(hy - vy_top) < y_tol:
                    return True
        return False

    # 橫管驗證：端點 x 附近是否有豎管
    def h_has_anchor(h: Dict) -> bool:
        for vx_end in [h["x1"], h["x2"]]:
            for v in v_lines:
                if abs(v["cx"] - vx_end) < x_tol:
                    return True
        return False

    v_validated = []
    for v in v_lines:
        if v_has_anchor(v):
            v_validated.append(v)
            cv2.line(vis, (v["x1"], v["y1"]), (v["x2"], v["y2"]), (0, 255, 0), 3)
            cv2.putText(vis, f"V({v['n_merged']})",
                        (v["x1"] + 5, (v["y1"] + v["y2"]) // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        else:
            # 豎管候選但沒有接入點 → 橙色（可疑）
            cv2.line(vis, (v["x1"], v["y1"]), (v["x2"], v["y2"]), (0, 128, 255), 2)

    h_validated = []
    for h in h_lines:
        if h_has_anchor(h):
            h_validated.append(h)
            cv2.line(vis, (h["x1"], h["y1"]), (h["x2"], h["y2"]), (255, 0, 0), 3)
            cv2.putText(vis, f"H({h['n_merged']})",
                        (h["x1"], h["y1"] - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
        else:
            cv2.line(vis, (h["x1"], h["y1"]), (h["x2"], h["y2"]), (200, 180, 0), 2)

    # 圖例
    cv2.putText(vis, "Blue=H-validated  Green=V-validated  Orange=V-no-anchor  Cyan=H-no-anchor",
                (8, vis.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

    return h_validated, v_validated, vis


# ──────────────────────────────────────────────
# 紅色方塊識別：三通道投票
# ──────────────────────────────────────────────

def make_red_masks(bgr: np.ndarray) -> Dict[str, np.ndarray]:
    """
    三種方法各出一張 mask，後面投票合併。

    1. HSV：擴展水下版本（包含暗橙/暗紅）
    2. RGB dominance：R 通道顯著高於 max(G,B)
    3. LAB a-channel：a > percentile 判斷紅色偏向
    """
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)

    # ── HSV 紅色（普通 + 水下暗紅/橙紅）──
    # 普通紅色
    r1 = cv2.inRange(hsv, np.array([0,   80, 40]),  np.array([12,  255, 255]))
    r2 = cv2.inRange(hsv, np.array([165, 80, 40]),  np.array([180, 255, 255]))
    # 水下暗紅 / 橙紅（飽和度和亮度都放寬）
    r3 = cv2.inRange(hsv, np.array([0,   40, 20]),  np.array([20,  255, 160]))
    r4 = cv2.inRange(hsv, np.array([155, 40, 20]),  np.array([180, 255, 160]))
    mask_hsv = cv2.bitwise_or(cv2.bitwise_or(r1, r2), cv2.bitwise_or(r3, r4))
    # 去小噪聲
    open_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask_hsv = cv2.morphologyEx(mask_hsv, cv2.MORPH_OPEN, open_k)

    # ── RGB dominance ──
    b = bgr[:, :, 0].astype(np.float32)
    g = bgr[:, :, 1].astype(np.float32)
    r = bgr[:, :, 2].astype(np.float32)
    red_dom = (r - np.maximum(g, b) > 22).astype(np.uint8)
    norm_r = r / (r + g + b + 1e-5)
    norm_mask = (norm_r > 0.42).astype(np.uint8)
    mask_rgb = (red_dom & norm_mask).astype(np.uint8) * 255
    mask_rgb = cv2.morphologyEx(mask_rgb, cv2.MORPH_OPEN, open_k)

    # ── LAB a-channel ──
    a_chan = lab[:, :, 1].astype(np.float32)
    a_thresh = float(np.percentile(a_chan, 88))
    mask_lab = (a_chan > a_thresh).astype(np.uint8) * 255
    mask_lab = cv2.morphologyEx(mask_lab, cv2.MORPH_OPEN, open_k)

    return {
        "red_hsv":           mask_hsv,
        "red_rgb_dominance": mask_rgb,
        "red_lab_a":         mask_lab,
    }


def vote_red_mask(masks: Dict[str, np.ndarray], min_votes: int = 2) -> np.ndarray:
    """三張 mask 投票，至少 min_votes 個同意才算紅色"""
    stack = np.stack([
        (masks["red_hsv"] > 0).astype(np.uint8),
        (masks["red_rgb_dominance"] > 0).astype(np.uint8),
        (masks["red_lab_a"] > 0).astype(np.uint8),
    ], axis=0)
    voted = (stack.sum(axis=0) >= min_votes).astype(np.uint8) * 255
    close_k = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    voted = cv2.morphologyEx(voted, cv2.MORPH_CLOSE, close_k, iterations=1)
    return voted


def find_red_boxes(
    voted_mask: np.ndarray,
    img: np.ndarray,
    pvc_mask: np.ndarray,
    pvc_nearby_px: int = 60,
) -> Tuple[np.ndarray, List[Dict]]:
    """
    在投票 mask 上找矩形候選，過濾條件：
      - 面積在合理範圍
      - 形狀接近矩形（fill ratio）
      - 長寬比放寬（容許傾斜視角）
      - 附近有 PVC mask（避免孤立紅色誤判）

    返回 (標注圖, 方塊資訊列表)
    """
    h, w = img.shape[:2]
    vis = img.copy()
    boxes = []

    contours, _ = cv2.findContours(voted_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 80 or area > w * h * 0.08:
            continue

        x, y, bw, bh = cv2.boundingRect(cnt)
        if bw == 0 or bh == 0:
            continue

        aspect = max(bw, bh) / max(min(bw, bh), 1)
        if aspect > 3.5:
            continue  # 太細長不是方塊

        fill = area / max(bw * bh, 1)
        if fill < 0.30:
            continue  # 形狀太破碎

        # PVC 鄰近驗證
        if pvc_mask is not None:
            x1e = max(0, x - pvc_nearby_px)
            y1e = max(0, y - pvc_nearby_px)
            x2e = min(w, x + bw + pvc_nearby_px)
            y2e = min(h, y + bh + pvc_nearby_px)
            nearby_pvc = pvc_mask[y1e:y2e, x1e:x2e]
            if nearby_pvc.sum() == 0:
                continue  # 附近沒有 PVC，可能是誤判

        cv2.rectangle(vis, (x, y), (x + bw, y + bh), (0, 255, 0), 2)
        cv2.putText(vis, f"R {bw}x{bh}", (x, max(16, y - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        boxes.append(dict(x=x, y=y, w=bw, h=bh, area=float(area), fill=float(fill)))

    return vis, boxes


# ──────────────────────────────────────────────
# 繪圖工具
# ──────────────────────────────────────────────

def draw_lines_on(img: np.ndarray, lines: List[Dict],
                   color=(0, 0, 255), thickness=2, label_prefix="L") -> np.ndarray:
    vis = img.copy()
    for i, l in enumerate(lines, start=1):
        cv2.line(vis, (l["x1"], l["y1"]), (l["x2"], l["y2"]), color, thickness)
        mid_x = int((l["x1"] + l["x2"]) / 2)
        mid_y = int((l["y1"] + l["y2"]) / 2)
        label = f"{label_prefix}{i}"
        if "n_merged" in l:
            label += f"(m{l['n_merged']})"
        cv2.putText(vis, label, (mid_x, max(16, mid_y - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)
    return vis


def contact_sheet(items: List[Tuple[str, np.ndarray]], cell_w: int = 420) -> np.ndarray:
    prepared = []
    for title, img in items:
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        h, w = img.shape[:2]
        scale = cell_w / max(w, 1)
        resized = cv2.resize(img, (cell_w, max(1, int(h * scale))))
        cv2.rectangle(resized, (0, 0), (cell_w, 28), (0, 0, 0), -1)
        cv2.putText(resized, title[:48], (6, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        prepared.append(resized)

    rows = []
    for i in range(0, len(prepared), 2):
        pair = prepared[i:i+2]
        mh = max(p.shape[0] for p in pair)
        padded = []
        for p in pair:
            if p.shape[0] < mh:
                pad = np.zeros((mh - p.shape[0], p.shape[1], 3), dtype=np.uint8)
                p = np.vstack([p, pad])
            padded.append(p)
        if len(padded) == 1:
            padded.append(np.zeros_like(padded[0]))
        rows.append(np.hstack(padded))
    return np.vstack(rows)


# ──────────────────────────────────────────────
# 主流程
# ──────────────────────────────────────────────

def process_one(image_path: Path, out_dir: Path, do_auto_crop: bool, roi_text: str) -> Dict:
    ensure_dir(out_dir)
    log(f"  Processing: {image_path.name}")

    img_orig = cv2.imread(str(image_path))
    if img_orig is None:
        raise RuntimeError(f"無法讀取圖片：{image_path}")
    cv2.imwrite(str(out_dir / "00_original.jpg"), img_orig)

    # 前處理
    img = img_orig.copy()
    if do_auto_crop:
        img = auto_crop_ui(img)

    roi = parse_roi(roi_text)
    img, _ = apply_roi(img, roi)

    img_hl = remove_highlight(img, threshold=235)
    cv2.imwrite(str(out_dir / "01_highlight_removed.jpg"), img_hl)

    img_std = standardize_underwater(img_hl)
    cv2.imwrite(str(out_dir / "02_standardized.jpg"), img_std)

    # 水管 mask（橫豎分開）
    tophat_h, tophat_v, mask_h, mask_v = make_directional_pipe_masks(img_std)
    cv2.imwrite(str(out_dir / "10_tophat_h.jpg"), tophat_h)
    cv2.imwrite(str(out_dir / "11_tophat_v.jpg"), tophat_v)
    cv2.imwrite(str(out_dir / "12_h_pipe_mask.jpg"), mask_h)
    cv2.imwrite(str(out_dir / "13_v_pipe_mask.jpg"), mask_v)

    # 骨架化
    skel_h = skeletonize(mask_h)
    skel_v = skeletonize(mask_v)
    cv2.imwrite(str(out_dir / "20_h_skeleton.jpg"), skel_h)
    cv2.imwrite(str(out_dir / "21_v_skeleton.jpg"), skel_v)

    # 線段提取（從骨架）
    h_raw = extract_lines_from_mask(skel_h, "horizontal", img_std.shape)
    v_raw = extract_lines_from_mask(skel_v, "vertical", img_std.shape)

    # 也從原 mask 提取（補充骨架遺漏）
    h_raw += extract_lines_from_mask(mask_h, "horizontal", img_std.shape)
    v_raw += extract_lines_from_mask(mask_v, "vertical", img_std.shape)

    vis_h_raw = draw_lines_on(img_std, h_raw, color=(0, 0, 255), label_prefix="H")
    vis_v_raw = draw_lines_on(img_std, v_raw, color=(255, 80, 0), label_prefix="V")
    cv2.imwrite(str(out_dir / "22_h_lines_raw.jpg"), vis_h_raw)
    cv2.imwrite(str(out_dir / "23_v_lines_raw.jpg"), vis_v_raw)

    # 線段合併
    h_merged = merge_lines(h_raw, "horizontal", y_tol=20, gap_tol=55)
    v_merged = merge_lines(v_raw, "vertical",   x_tol=20, gap_tol=45)

    vis_h_merged = draw_lines_on(img_std, h_merged, color=(0, 200, 0), thickness=3, label_prefix="HM")
    vis_v_merged = draw_lines_on(img_std, v_merged, color=(0, 150, 255), thickness=3, label_prefix="VM")
    cv2.imwrite(str(out_dir / "24_h_lines_merged.jpg"), vis_h_merged)
    cv2.imwrite(str(out_dir / "25_v_lines_merged.jpg"), vis_v_merged)

    # 橫豎接入點互相驗證
    h_val, v_val, vis_cross = cross_validate_pipes(h_merged, v_merged, img_std)
    cv2.imwrite(str(out_dir / "26_cross_validated.jpg"), vis_cross)

    # 紅色方塊
    red_masks = make_red_masks(img_std)
    for name, m in red_masks.items():
        cv2.imwrite(str(out_dir / f"30_{name}.jpg"), m)

    voted = vote_red_mask(red_masks, min_votes=2)
    cv2.imwrite(str(out_dir / "33_red_voted.jpg"), voted)

    # 使用橫管+豎管合併 mask 作為 PVC 鄰近驗證
    pvc_any = cv2.bitwise_or(mask_h, mask_v)
    vis_boxes, red_box_list = find_red_boxes(voted, img_std, pvc_any)
    cv2.imwrite(str(out_dir / "34_red_boxes.jpg"), vis_boxes)

    # Contact sheet
    sheet_items = [
        ("01_highlight_removed", img_hl),
        ("02_standardized", img_std),
        ("10_tophat_h", tophat_h),
        ("11_tophat_v", tophat_v),
        ("12_h_pipe_mask", mask_h),
        ("13_v_pipe_mask", mask_v),
        ("20_h_skeleton", skel_h),
        ("21_v_skeleton", skel_v),
        ("22_h_lines_raw", vis_h_raw),
        ("23_v_lines_raw", vis_v_raw),
        ("24_h_lines_merged", vis_h_merged),
        ("25_v_lines_merged", vis_v_merged),
        ("26_cross_validated", vis_cross),
        ("33_red_voted", voted),
        ("34_red_boxes", vis_boxes),
    ]
    sheet = contact_sheet(sheet_items, cell_w=440)
    cv2.imwrite(str(out_dir / "90_summary.jpg"), sheet)

    summary = {
        "image": str(image_path),
        "h_lines_raw": len(h_raw),
        "v_lines_raw": len(v_raw),
        "h_lines_merged": len(h_merged),
        "v_lines_merged": len(v_merged),
        "h_validated": len(h_val),
        "v_validated": len(v_val),
        "red_boxes": red_box_list,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log(f"    H raw={len(h_raw)} merged={len(h_merged)} validated={len(h_val)}")
    log(f"    V raw={len(v_raw)} merged={len(v_merged)} validated={len(v_val)}")
    log(f"    Red boxes: {len(red_box_list)}")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="水管方向判斷診斷程序（橫管+豎管+紅色方塊）"
    )
    parser.add_argument("--input",      required=True,   help="輸入圖片或資料夾")
    parser.add_argument("--out",        default="pipe_diag_out", help="輸出資料夾")
    parser.add_argument("--auto-crop-ui", action="store_true",  help="自動裁去截圖 UI 欄")
    parser.add_argument("--roi",        default="",      help="手動 ROI：x,y,w,h")
    args = parser.parse_args()

    input_path = Path(args.input)
    out_root   = Path(args.out)
    ensure_dir(out_root)

    if input_path.is_file():
        images = [input_path]
    elif input_path.is_dir():
        images = sorted([p for p in input_path.iterdir()
                         if p.suffix.lower() in IMAGE_EXTS])
    else:
        log(f"ERROR: 找不到輸入：{input_path}")
        return 2

    if not images:
        log("沒有找到圖片")
        return 2

    log(f"共 {len(images)} 張圖片")
    all_summaries = []
    for img_path in images:
        sub_dir = out_root / img_path.stem
        try:
            s = process_one(img_path, sub_dir, args.auto_crop_ui, args.roi)
            all_summaries.append(s)
        except Exception as e:
            log(f"  ERROR: {e}")
            all_summaries.append({"image": str(img_path), "error": str(e)})

    (out_root / "all_summary.json").write_text(
        json.dumps(all_summaries, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    log("")
    log("完成。每張圖請看：")
    log("  26_cross_validated.jpg  ← 最重要：橫豎接入點驗證")
    log("  24_h_lines_merged.jpg   ← 橫管合併結果")
    log("  25_v_lines_merged.jpg   ← 豎管合併結果")
    log("  34_red_boxes.jpg        ← 紅色方塊")
    log("  90_summary.jpg          ← 全覽")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
