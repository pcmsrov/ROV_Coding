from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import cv2
import matplotlib.pyplot as plt
import numpy as np


# Coral Garden 项目默认配置（可按现场数据微调）
DEFAULT_CONFIG: dict[str, Any] = {
    "front_image": "coral_front.jpg",
    "back_image": "coral_back.jpg",
    "output_dir": "outputs",
    "red_hsv_ranges": [
        {"lower": [0, 120, 70], "upper": [12, 255, 255]},
        {"lower": [170, 120, 70], "upper": [180, 255, 255]},
    ],
    "contour_min_area": 3000,
    "square_min_area": 80,
    "square_aspect_ratio_range": [0.75, 1.30],
    "depth_cm": 30.0,
    "known_length_cm": 10.0,
    "show_windows": False,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Coral Garden 水下水管二维识别 + CAD三维重建数据输出流程"
    )
    parser.add_argument("--front", default=DEFAULT_CONFIG["front_image"], help="正面照片路径")
    parser.add_argument("--back", default=DEFAULT_CONFIG["back_image"], help="背面照片路径")
    parser.add_argument(
        "--known-length-cm",
        type=float,
        default=DEFAULT_CONFIG["known_length_cm"],
        help="图中已知参考实长(cm)，用于像素换算",
    )
    parser.add_argument(
        "--known-length-px",
        type=float,
        default=None,
        help="图中已知参考像素长度(px)。若不提供，将在正面图交互点击2点自动量测。",
    )
    parser.add_argument(
        "--depth-cm",
        type=float,
        default=DEFAULT_CONFIG["depth_cm"],
        help="模型向后拉伸深度(cm)",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_CONFIG["output_dir"],
        help="输出目录",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="是否显示可视化窗口",
    )
    return parser.parse_args()


def read_image(path: str) -> np.ndarray:
    image = cv2.imread(path)
    if image is None:
        raise FileNotFoundError(f"无法读取图片: {path}")
    return image


def _pixel_distance(p1: tuple[int, int], p2: tuple[int, int]) -> float:
    return float(np.hypot(p2[0] - p1[0], p2[1] - p1[1]))


def measure_known_length_px(image: np.ndarray, known_length_cm: float) -> float:
    """
    参考 measure_then_model_demo.py 的像素比例法：
    在图上点击已知长度两端点，自动换算像素距离。
    """
    points: list[tuple[int, int]] = []
    canvas = image.copy()
    win = "Calibration - click 2 points for known length"

    def mouse_callback(event: int, x: int, y: int, flags: int, param: Any) -> None:
        del flags, param
        if event != cv2.EVENT_LBUTTONDOWN or len(points) >= 2:
            return
        points.append((x, y))
        cv2.circle(canvas, (x, y), 5, (0, 0, 255), -1)
        cv2.putText(
            canvas,
            str(len(points)),
            (x + 6, y - 6),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 255),
            2,
        )
        if len(points) == 2:
            cv2.line(canvas, points[0], points[1], (0, 255, 255), 2)
            known_px = _pixel_distance(points[0], points[1])
            cv2.putText(
                canvas,
                f"known={known_length_cm:.2f}cm -> {known_px:.2f}px",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 255),
                2,
            )
        cv2.imshow(win, canvas)

    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.imshow(win, canvas)
    cv2.setMouseCallback(win, mouse_callback)
    print("=== 像素比例标定 ===")
    print("请在正面图点击已知长度的两个端点（左键）")
    print("按 c 清除重选，按 Enter 确认，按 q 退出")

    known_px = None
    while True:
        key = cv2.waitKey(30) & 0xFF
        if key == ord("q"):
            break
        if key == ord("c"):
            points.clear()
            canvas = image.copy()
            cv2.imshow(win, canvas)
            print("已清除点位，请重新点击。")
            continue
        if key in (13, 10):  # Enter
            if len(points) < 2:
                print("至少需要 2 个点，请继续点击。")
                continue
            known_px = _pixel_distance(points[0], points[1])
            if known_px <= 1e-8:
                print("像素距离过小，请重选。")
                continue
            break

    cv2.destroyWindow(win)
    if known_px is None:
        raise RuntimeError("未完成像素标定（用户取消）。")
    return known_px


def measure_reference_and_three_segments(image: np.ndarray) -> dict[str, Any]:
    """
    交互量测流程：
    1) 先点 2 点作为已知参考段，并输入现实长度(cm)
    2) 再量测 3 条未知段（每条都点 2 点）
    """
    points: list[tuple[int, int]] = []
    canvas = image.copy()
    win = "Measure 4 segments (ref + 3 unknown)"
    stage = 0  # 0=reference, 1..3 unknown segments
    stage_names = ["REF", "L1", "L2", "L3"]
    pixel_lengths: list[float] = []
    measured_cm: list[float] = []
    known_length_cm: float | None = None

    def redraw() -> None:
        cv2.imshow(win, canvas)

    def draw_stage_text() -> None:
        msg = (
            f"Stage: {stage_names[stage]} | Click 2 points | Enter=confirm | c=clear pair | q=quit"
        )
        cv2.rectangle(canvas, (0, 0), (canvas.shape[1], 40), (20, 20, 20), -1)
        cv2.putText(canvas, msg, (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

    def mouse_callback(event: int, x: int, y: int, flags: int, param: Any) -> None:
        del flags, param
        if event != cv2.EVENT_LBUTTONDOWN or len(points) >= 2:
            return
        points.append((x, y))
        cv2.circle(canvas, (x, y), 5, (0, 0, 255), -1)
        cv2.putText(
            canvas,
            str(len(points)),
            (x + 6, y - 6),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 255),
            2,
        )
        if len(points) == 2:
            cv2.line(canvas, points[0], points[1], (0, 255, 255), 2)
        draw_stage_text()
        redraw()

    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(win, mouse_callback)
    draw_stage_text()
    redraw()
    print("=== 交互量测开始 ===")
    print("流程：先量基准段(2点)->输入现实长度，再量 3 条未知段(每条2点)")

    while True:
        key = cv2.waitKey(30) & 0xFF
        if key == ord("q"):
            break
        if key == ord("c"):
            points.clear()
            canvas = image.copy()
            draw_stage_text()
            redraw()
            print(f"已清除当前段点位：{stage_names[stage]}")
            continue
        if key not in (13, 10):  # Enter
            continue
        if len(points) < 2:
            print("当前段至少需要 2 个点。")
            continue

        px_len = _pixel_distance(points[0], points[1])
        if px_len <= 1e-8:
            print("像素长度过小，请重选。")
            continue

        pixel_lengths.append(px_len)
        tag = stage_names[stage]
        print(f"{tag} 像素长度: {px_len:.2f}px")

        if stage == 0:
            while True:
                try:
                    v = float(input("请输入基准段现实长度(cm): ").strip())
                except ValueError:
                    print("输入格式错误，请输入数字。")
                    continue
                if v <= 0:
                    print("现实长度需大于 0。")
                    continue
                known_length_cm = v
                measured_cm.append(v)
                break
        else:
            assert known_length_cm is not None
            cm = (px_len * known_length_cm) / pixel_lengths[0]
            measured_cm.append(cm)
            print(f"{tag} 计算长度: {cm:.3f} cm")

        if stage == 3:
            break
        stage += 1
        points.clear()
        canvas = image.copy()
        draw_stage_text()
        redraw()

    cv2.destroyWindow(win)
    if len(measured_cm) < 4 or known_length_cm is None:
        raise RuntimeError("量测未完成。")

    return {
        "reference_cm": measured_cm[0],
        "segment_labels": ["L1", "L2", "L3"],
        "segment_lengths_cm": [round(measured_cm[1], 3), round(measured_cm[2], 3), round(measured_cm[3], 3)],
        "pixel_lengths": [round(v, 3) for v in pixel_lengths],
        "scale_cm_per_px": known_length_cm / pixel_lengths[0],
    }


def _rotate_points(pts: np.ndarray, angle_rad: float) -> np.ndarray:
    c = float(np.cos(angle_rad))
    s = float(np.sin(angle_rad))
    rot = np.array([[c, -s], [s, c]], dtype=np.float32)
    return (rot @ pts.T).T


def simplify_orthogonal_contour(
    contour_px: list[list[int]], epsilon_ratio: float = 0.01
) -> list[list[float]]:
    cnt = np.array(contour_px, dtype=np.float32).reshape(-1, 1, 2)
    peri = cv2.arcLength(cnt, True)
    eps = max(2.0, epsilon_ratio * peri)
    approx = cv2.approxPolyDP(cnt, eps, True).reshape(-1, 2)
    if len(approx) < 4:
        approx = cnt.reshape(-1, 2)

    rect = cv2.minAreaRect(approx.astype(np.float32))
    angle_deg = rect[2]
    angle_rad = np.deg2rad(angle_deg)
    rot = _rotate_points(approx, -angle_rad)
    ortho = rot.copy()

    for i in range(1, len(ortho)):
        dx = rot[i, 0] - ortho[i - 1, 0]
        dy = rot[i, 1] - ortho[i - 1, 1]
        if abs(dx) >= abs(dy):
            ortho[i, 1] = ortho[i - 1, 1]
        else:
            ortho[i, 0] = ortho[i - 1, 0]

    ortho_back = _rotate_points(ortho, angle_rad)

    cleaned: list[list[float]] = []
    for p in ortho_back:
        if not cleaned:
            cleaned.append([float(p[0]), float(p[1])])
            continue
        if np.hypot(p[0] - cleaned[-1][0], p[1] - cleaned[-1][1]) >= 1.5:
            cleaned.append([float(p[0]), float(p[1])])

    if len(cleaned) >= 3:
        p0 = np.array(cleaned[0], dtype=np.float32)
        p1 = np.array(cleaned[-1], dtype=np.float32)
        if np.linalg.norm(p0 - p1) < 2.0:
            cleaned.pop()
    return cleaned


def render_front_shape_preview(
    original: np.ndarray, poly_px: list[list[float]], title: str = "Front 2D shape"
) -> tuple[np.ndarray, np.ndarray]:
    """
    输出两张 2D 图：
    1) 叠加在原图上的角点/线框
    2) 白底纯线框（便于确认几何形状）
    """
    overlay = original.copy()
    h, w = original.shape[:2]
    clean = np.ones((h, w, 3), dtype=np.uint8) * 255

    if len(poly_px) < 3:
        return overlay, clean

    pts = np.array(poly_px, dtype=np.int32)
    n = len(pts)
    labels = generate_vertex_labels(n)

    for i in range(n):
        j = (i + 1) % n
        p1 = tuple(pts[i].tolist())
        p2 = tuple(pts[j].tolist())
        cv2.line(overlay, p1, p2, (255, 0, 255), 3)
        cv2.line(clean, p1, p2, (0, 0, 0), 2)

    for i, p in enumerate(pts):
        pp = tuple(p.tolist())
        cv2.circle(overlay, pp, 5, (0, 255, 255), -1)
        cv2.circle(clean, pp, 4, (0, 0, 255), -1)
        cv2.putText(overlay, labels[i], (pp[0] + 6, pp[1] - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
        cv2.putText(clean, labels[i], (pp[0] + 6, pp[1] - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 180), 2)

    cv2.putText(overlay, title, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 255), 2)
    cv2.putText(clean, title, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (30, 30, 30), 2)
    return overlay, clean


def generate_vertex_labels(n: int) -> list[str]:
    labels = []
    for i in range(n):
        if i < 26:
            labels.append(chr(ord("A") + i))
        else:
            labels.append(f"A{i-25}")
    return labels


def show_rotatable_3d_structure_from_front(
    front_poly_cm: list[list[float]], depth_cm: float, measured_segments: dict[str, Any] | None
) -> None:
    if len(front_poly_cm) < 3:
        raise ValueError("前视轮廓点不足，无法生成3D结构。")

    labels = generate_vertex_labels(len(front_poly_cm))
    fig = plt.figure(figsize=(10, 7))
    ax = fig.add_subplot(111, projection="3d")

    for i in range(len(front_poly_cm)):
        j = (i + 1) % len(front_poly_cm)
        x1, y1 = front_poly_cm[i]
        x2, y2 = front_poly_cm[j]
        # front
        ax.plot3D([x1, x2], [y1, y2], [0, 0], color="#1f77b4", linewidth=2.4)
        # back
        ax.plot3D([x1, x2], [y1, y2], [depth_cm, depth_cm], color="#ff7f0e", linewidth=2.0)
        # extrude
        ax.plot3D([x1, x1], [y1, y1], [0, depth_cm], color="#2ca02c", linewidth=1.8)

        edge_name = f"{labels[i]}{labels[j]}"
        edge_len = float(np.hypot(x2 - x1, y2 - y1))
        mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        ax.text(mx, my, 0.0, f"{edge_name}={edge_len:.2f}", fontsize=8, color="navy")

    for i, (x, y) in enumerate(front_poly_cm):
        ax.scatter(x, y, 0, c="red", s=20)
        ax.scatter(x, y, depth_cm, c="darkred", s=20)
        ax.text(x, y, 0, labels[i], color="darkred", fontsize=9)
        ax.text(x, y, depth_cm, labels[i].lower(), color="maroon", fontsize=9)

    pts = np.array(front_poly_cm, dtype=np.float32)
    min_x, max_x = float(pts[:, 0].min()), float(pts[:, 0].max())
    min_y, max_y = float(pts[:, 1].min()), float(pts[:, 1].max())
    ax.set_xlim(min_x - 2, max_x + 2)
    ax.set_ylim(min_y - 2, max_y + 2)
    ax.set_zlim(0, depth_cm + 5)
    ax.set_xlabel("X (cm)")
    ax.set_ylabel("Y (cm)")
    ax.set_zlabel("Z (cm)")
    title = "Front-line extruded 3D model (drag to rotate)"
    if measured_segments is not None:
        vals = measured_segments["segment_lengths_cm"]
        title += f" | L1={vals[0]:.2f}, L2={vals[1]:.2f}, L3={vals[2]:.2f}"
    ax.set_title(title)
    ax.set_box_aspect((max(max_x - min_x, 1.0), max(max_y - min_y, 1.0), depth_cm))
    plt.tight_layout()
    plt.show()


def preprocess_underwater(image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    denoise = cv2.GaussianBlur(image, (5, 5), 0)
    lab = cv2.cvtColor(denoise, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
    l_enhanced = clahe.apply(l)
    enhanced = cv2.cvtColor(cv2.merge((l_enhanced, a, b)), cv2.COLOR_LAB2BGR)
    gray = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
    return enhanced, gray


def detect_main_contour(gray: np.ndarray, min_area: float) -> np.ndarray | None:
    edges = cv2.Canny(gray, 50, 150)
    kernel = np.ones((3, 3), np.uint8)
    edges = cv2.dilate(edges, kernel, iterations=1)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    large = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]
    if not large:
        return None
    return max(large, key=cv2.contourArea)


def detect_red_square_marks(
    image: np.ndarray,
    hsv_ranges: list[dict[str, list[int]]],
    min_area: float,
    ratio_range: tuple[float, float],
) -> tuple[list[dict[str, Any]], np.ndarray]:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask_total = np.zeros(hsv.shape[:2], dtype=np.uint8)
    for item in hsv_ranges:
        lower = np.array(item["lower"], dtype=np.uint8)
        upper = np.array(item["upper"], dtype=np.uint8)
        mask_total = cv2.bitwise_or(mask_total, cv2.inRange(hsv, lower, upper))

    kernel = np.ones((3, 3), np.uint8)
    mask_total = cv2.morphologyEx(mask_total, cv2.MORPH_OPEN, kernel, iterations=1)
    mask_total = cv2.morphologyEx(mask_total, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(mask_total, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    marks: list[dict[str, Any]] = []
    for idx, cnt in enumerate(contours):
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue

        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
        if len(approx) != 4:
            continue

        x, y, w, h = cv2.boundingRect(approx)
        ratio = w / max(h, 1)
        if not (ratio_range[0] <= ratio <= ratio_range[1]):
            continue

        cx = int(x + w / 2)
        cy = int(y + h / 2)
        marks.append(
            {
                "id": f"R{idx+1}",
                "bbox": [int(x), int(y), int(w), int(h)],
                "center_px": [cx, cy],
                "area_px2": float(area),
            }
        )
    return marks, mask_total


def contour_to_points(contour: np.ndarray) -> list[list[int]]:
    pts = contour.reshape(-1, 2)
    return [[int(x), int(y)] for x, y in pts]


def convert_to_real(points: list[list[int]], scale_cm_per_px: float) -> list[list[float]]:
    return [[round(x * scale_cm_per_px, 3), round(y * scale_cm_per_px, 3)] for x, y in points]


def annotate_result(
    original: np.ndarray,
    contour: np.ndarray | None,
    marks: list[dict[str, Any]],
) -> np.ndarray:
    canvas = original.copy()
    if contour is not None:
        cv2.drawContours(canvas, [contour], -1, (255, 255, 0), 3)
        x, y, w, h = cv2.boundingRect(contour)
        cv2.rectangle(canvas, (x, y), (x + w, y + h), (0, 255, 255), 2)
        cv2.putText(
            canvas,
            "Main_Contour",
            (x, max(y - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 255),
            2,
        )

    for mark in marks:
        x, y, w, h = mark["bbox"]
        cx, cy = mark["center_px"]
        cv2.rectangle(canvas, (x, y), (x + w, y + h), (0, 0, 255), 2)
        cv2.circle(canvas, (cx, cy), 3, (255, 255, 255), -1)
        cv2.putText(
            canvas,
            mark["id"],
            (x, max(y - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 0, 255),
            2,
        )
    return canvas


def save_csv(path: Path, rows: list[dict[str, Any]], headers: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def order_quad_points(pts: np.ndarray) -> np.ndarray:
    sums = pts.sum(axis=1)
    diffs = np.diff(pts, axis=1).reshape(-1)
    tl = pts[np.argmin(sums)]
    br = pts[np.argmax(sums)]
    tr = pts[np.argmin(diffs)]
    bl = pts[np.argmax(diffs)]
    return np.array([tl, tr, br, bl], dtype=np.float32)


def build_labeled_model_vertices(
    contour_cm: list[list[float]], depth_cm: float
) -> tuple[dict[str, list[float]], list[tuple[str, str]]]:
    labels = generate_vertex_labels(len(contour_cm))
    vertices: dict[str, list[float]] = {}
    edges: list[tuple[str, str]] = []
    for i, (x, y) in enumerate(contour_cm):
        front = labels[i]
        back = labels[i].lower()
        vertices[front] = [float(x), float(y), 0.0]
        vertices[back] = [float(x), float(y), float(depth_cm)]

    n = len(labels)
    for i in range(n):
        j = (i + 1) % n
        edges.append((labels[i], labels[j]))
        edges.append((labels[i].lower(), labels[j].lower()))
        edges.append((labels[i], labels[i].lower()))
    return vertices, edges


def edge_lengths_by_letters(
    vertices: dict[str, list[float]],
    edges: list[tuple[str, str]],
) -> list[dict[str, Any]]:
    out = []
    for a, b in edges:
        p1 = np.array(vertices[a], dtype=np.float32)
        p2 = np.array(vertices[b], dtype=np.float32)
        length = float(np.linalg.norm(p2 - p1))
        out.append({"edge": f"{a}{b}", "length_cm": round(length, 3)})
    return out


def save_model_preview_image(
    output_path: Path,
    vertices: dict[str, list[float]],
    edges: list[tuple[str, str]],
) -> None:
    pts = np.array(list(vertices.values()), dtype=np.float32)
    x_all, y_all, z_all = pts[:, 0], pts[:, 1], pts[:, 2]

    def project(x: float, y: float, z: float) -> tuple[float, float]:
        px = x + 0.65 * z
        py = y - 0.35 * z
        return px, py

    projected = {k: project(v[0], v[1], v[2]) for k, v in vertices.items()}
    proj_pts = np.array(list(projected.values()), dtype=np.float32)
    min_xy = proj_pts.min(axis=0)
    max_xy = proj_pts.max(axis=0)
    w = int(max(max_xy[0] - min_xy[0] + 120, 720))
    h = int(max(max_xy[1] - min_xy[1] + 120, 520))
    canvas = np.ones((h, w, 3), dtype=np.uint8) * 250

    def to_canvas(pt: tuple[float, float]) -> tuple[int, int]:
        x = int(pt[0] - min_xy[0] + 60)
        y = int(pt[1] - min_xy[1] + 60)
        return x, y

    for a, b in edges:
        p1 = to_canvas(projected[a])
        p2 = to_canvas(projected[b])
        cv2.line(canvas, p1, p2, (30, 30, 30), 2)
        mx, my = int((p1[0] + p2[0]) / 2), int((p1[1] + p2[1]) / 2)
        cv2.putText(canvas, f"{a}{b}", (mx + 3, my - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (90, 60, 200), 1)

    for label, p in projected.items():
        cp = to_canvas(p)
        cv2.circle(canvas, cp, 4, (0, 0, 255), -1)
        cv2.putText(
            canvas,
            label,
            (cp[0] + 6, cp[1] - 6),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 0, 180),
            2,
        )

    cv2.putText(
        canvas,
        "Coral model preview (corner points + letter labels)",
        (20, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (20, 20, 20),
        2,
    )
    cv2.imwrite(str(output_path), canvas)


def write_simple_dxf(
    path: Path,
    contour_cm: list[list[float]],
    marks_cm: list[dict[str, float]],
    depth_cm: float,
) -> None:
    if not contour_cm:
        return

    lines = [
        "0",
        "SECTION",
        "2",
        "ENTITIES",
    ]

    for i in range(len(contour_cm)):
        x1, y1 = contour_cm[i]
        x2, y2 = contour_cm[(i + 1) % len(contour_cm)]
        lines += [
            "0",
            "LINE",
            "8",
            "FRONT_CONTOUR",
            "10",
            str(x1),
            "20",
            str(y1),
            "30",
            "0.0",
            "11",
            str(x2),
            "21",
            str(y2),
            "31",
            "0.0",
        ]
        lines += [
            "0",
            "LINE",
            "8",
            "BACK_CONTOUR",
            "10",
            str(x1),
            "20",
            str(y1),
            "30",
            str(depth_cm),
            "11",
            str(x2),
            "21",
            str(y2),
            "31",
            str(depth_cm),
        ]
        lines += [
            "0",
            "LINE",
            "8",
            "EXTRUDE_EDGE",
            "10",
            str(x1),
            "20",
            str(y1),
            "30",
            "0.0",
            "11",
            str(x1),
            "21",
            str(y1),
            "31",
            str(depth_cm),
        ]

    for item in marks_cm:
        lines += [
            "0",
            "POINT",
            "8",
            "RED_MARKS",
            "10",
            str(item["x_cm"]),
            "20",
            str(item["y_cm"]),
            "30",
            "0.0",
        ]
        lines += [
            "0",
            "POINT",
            "8",
            "RED_MARKS",
            "10",
            str(item["x_cm"]),
            "20",
            str(item["y_cm"]),
            "30",
            str(depth_cm),
        ]

    lines += ["0", "ENDSEC", "0", "EOF"]
    path.write_text("\n".join(lines), encoding="utf-8")


def process_single_view(
    image_path: str,
    config: dict[str, Any],
    output_dir: Path,
    tag: str,
    known_length_px: float | None,
    known_length_cm: float,
) -> dict[str, Any]:
    img = read_image(image_path)
    enhanced, gray = preprocess_underwater(img)
    contour = detect_main_contour(gray, config["contour_min_area"])
    marks, red_mask = detect_red_square_marks(
        enhanced,
        config["red_hsv_ranges"],
        config["square_min_area"],
        tuple(config["square_aspect_ratio_range"]),
    )

    if contour is None:
        raise RuntimeError(f"{tag} 视图未识别到有效主体轮廓，请检查图像质量和阈值参数。")

    x, y, w, h = cv2.boundingRect(contour)
    auto_known_px = float(max(w, h))
    ref_px = known_length_px if known_length_px else auto_known_px
    scale_cm_per_px = known_length_cm / ref_px

    contour_px = contour_to_points(contour)
    contour_cm = convert_to_real(contour_px, scale_cm_per_px)
    model_front_poly_px = simplify_orthogonal_contour(contour_px)
    model_front_poly_cm = [
        [round(p[0] * scale_cm_per_px, 3), round(p[1] * scale_cm_per_px, 3)]
        for p in model_front_poly_px
    ]

    marks_cm = []
    mark_rows = []
    for mark in marks:
        mx, my = mark["center_px"]
        mxc = round(mx * scale_cm_per_px, 3)
        myc = round(my * scale_cm_per_px, 3)
        marks_cm.append({"id": mark["id"], "x_cm": mxc, "y_cm": myc})
        mark_rows.append(
            {
                "id": mark["id"],
                "x_px": mx,
                "y_px": my,
                "x_cm": mxc,
                "y_cm": myc,
                "bbox": str(mark["bbox"]),
                "area_px2": round(mark["area_px2"], 2),
            }
        )

    vis = annotate_result(img, contour, marks)
    front_overlay, front_clean = render_front_shape_preview(
        img, model_front_poly_px, title=f"{tag} 2D front-line"
    )
    cv2.imwrite(str(output_dir / f"{tag}_annotated.jpg"), vis)
    cv2.imwrite(str(output_dir / f"{tag}_enhanced.jpg"), enhanced)
    cv2.imwrite(str(output_dir / f"{tag}_red_mask.jpg"), red_mask)
    cv2.imwrite(str(output_dir / f"{tag}_shape_overlay.jpg"), front_overlay)
    cv2.imwrite(str(output_dir / f"{tag}_shape_preview.jpg"), front_clean)
    save_csv(
        output_dir / f"{tag}_red_marks.csv",
        mark_rows,
        headers=["id", "x_px", "y_px", "x_cm", "y_cm", "bbox", "area_px2"],
    )

    if config["show_windows"]:
        cv2.imshow(f"{tag}_original", img)
        cv2.imshow(f"{tag}_annotated", vis)
        cv2.imshow(f"{tag}_shape_overlay", front_overlay)
        cv2.imshow(f"{tag}_shape_preview", front_clean)

    return {
        "tag": tag,
        "image_path": image_path,
        "scale_cm_per_px": scale_cm_per_px,
        "known_length_cm": known_length_cm,
        "known_length_px": ref_px,
        "contour_bbox_px": [int(x), int(y), int(w), int(h)],
        "contour_points_px": contour_px,
        "contour_points_cm": contour_cm,
        "model_front_poly_px": model_front_poly_px,
        "model_front_poly_cm": model_front_poly_cm,
        "red_marks": mark_rows,
    }


def build_report(
    front_data: dict[str, Any],
    back_data: dict[str, Any],
    depth_cm: float,
    model_vertices: dict[str, list[float]],
    model_edge_lengths: list[dict[str, Any]],
    measured_segments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    fw = front_data["contour_bbox_px"][2] * front_data["scale_cm_per_px"]
    fh = front_data["contour_bbox_px"][3] * front_data["scale_cm_per_px"]
    bw = back_data["contour_bbox_px"][2] * back_data["scale_cm_per_px"]
    bh = back_data["contour_bbox_px"][3] * back_data["scale_cm_per_px"]
    width_diff_cm = abs(fw - bw)
    height_diff_cm = abs(fh - bh)

    return {
        "project_name": "Coral Garden 水下水管结构二维识别+CAD三维重建",
        "depth_cm": depth_cm,
        "front_view": front_data,
        "back_view": back_data,
        "model_vertices_cm": model_vertices,
        "model_edge_lengths_cm": model_edge_lengths,
        "measured_segments_cm": measured_segments["segment_lengths_cm"] if measured_segments else None,
        "validation": {
            "width_diff_cm": round(width_diff_cm, 3),
            "height_diff_cm": round(height_diff_cm, 3),
            "suggestion": (
                "差异在 2cm 内可直接建模，超过 2cm 建议复拍或重新标定。"
                if max(width_diff_cm, height_diff_cm) > 2
                else "正背面尺寸一致性良好，可进入 CAD 三维重建。"
            ),
        },
    }


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    config = DEFAULT_CONFIG.copy()
    config["depth_cm"] = args.depth_cm
    config["known_length_cm"] = args.known_length_cm
    config["show_windows"] = args.show

    known_length_px = args.known_length_px
    measured_segments = None
    if known_length_px is None:
        front_for_calibration = read_image(args.front)
        measured_segments = measure_reference_and_three_segments(front_for_calibration)
        known_length_px = measured_segments["pixel_lengths"][0]
        args.known_length_cm = measured_segments["reference_cm"]
        print(
            f"标定完成：{args.known_length_cm:.2f} cm 对应 {known_length_px:.2f} px，"
            f"比例={args.known_length_cm / known_length_px:.6f} cm/px"
        )
        print("三段量测结果：")
        for lab, val in zip(measured_segments["segment_labels"], measured_segments["segment_lengths_cm"]):
            print(f"  {lab}: {val:.3f} cm")

    front_data = process_single_view(
        args.front,
        config,
        output_dir,
        tag="front",
        known_length_px=known_length_px,
        known_length_cm=args.known_length_cm,
    )
    back_data = process_single_view(
        args.back,
        config,
        output_dir,
        tag="back",
        known_length_px=known_length_px,
        known_length_cm=args.known_length_cm,
    )

    show_rotatable_3d_structure_from_front(
        front_data["model_front_poly_cm"], args.depth_cm, measured_segments
    )

    model_vertices, model_edges = build_labeled_model_vertices(
        front_data["model_front_poly_cm"], args.depth_cm
    )
    model_edge_lengths = edge_lengths_by_letters(model_vertices, model_edges)
    save_model_preview_image(output_dir / "model_preview.jpg", model_vertices, model_edges)

    report = build_report(
        front_data,
        back_data,
        depth_cm=args.depth_cm,
        model_vertices=model_vertices,
        model_edge_lengths=model_edge_lengths,
        measured_segments=measured_segments,
    )
    report_path = output_dir / "reconstruction_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    write_simple_dxf(
        output_dir / "coral_reconstruction.dxf",
        front_data["model_front_poly_cm"],
        [
            {"id": m["id"], "x_cm": m["x_cm"], "y_cm": m["y_cm"]}
            for m in front_data["red_marks"]
        ],
        depth_cm=args.depth_cm,
    )

    print("识别与重建数据输出完成。")
    print(f"- 报告文件: {report_path}")
    print(f"- CAD草图: {output_dir / 'coral_reconstruction.dxf'}")
    print(f"- 正面标注图: {output_dir / 'front_annotated.jpg'}")
    print(f"- 正面2D叠加图: {output_dir / 'front_shape_overlay.jpg'}")
    print(f"- 正面2D线框图: {output_dir / 'front_shape_preview.jpg'}")
    print(f"- 背面标注图: {output_dir / 'back_annotated.jpg'}")
    print(f"- 模型预览图: {output_dir / 'model_preview.jpg'}")
    print("- 主要边长（两字母表示）:")
    for item in model_edge_lengths:
        print(f"  {item['edge']}: {item['length_cm']:.3f} cm")

    if args.show:
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()