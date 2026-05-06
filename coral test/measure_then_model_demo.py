import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, TextBox
from matplotlib.lines import Line2D

# Fixed values (based on your edge definitions)
# HE = 30, FB = 15, BJ = 45, SJ = 25, TU = 30
WIDTH_Y = 30.0   # HE, BC, AD, FG ...
h1 = 15.0        # FB
L2 = 45.0        # BJ（固定 45，不由照片量測）
H3 = 25.0        # SJ
L3_INIT = 30.0   # TU
GAP12_INIT = 35.0
GAP23_INIT = 25.0
selected_vertices = ["A", "B", "C", "D", "J", "K", "BJ_MID", "CK_MID"]


class PipeMeasurer:
    """Measure unknown length from one image using a known reference."""

    def __init__(self):
        self.points = []
        self.original_image = None
        self.display_image = None
        self.reference_length_cm = None
        self.measured_length_cm = None

    def mouse_callback(self, event, x, y, flags, param):
        if event != cv2.EVENT_LBUTTONDOWN:
            return

        if len(self.points) >= 4:
            return

        self.points.append((x, y))
        cv2.circle(self.display_image, (x, y), 5, (0, 0, 255), -1)
        cv2.putText(
            self.display_image,
            str(len(self.points)),
            (x + 6, y - 6),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 255),
            2,
        )
        cv2.imshow("Measurement", self.display_image)

        if len(self.points) == 4 and self.reference_length_cm is not None:
            self._calculate_unknown_length()

    @staticmethod
    def _pixel_distance(p1, p2):
        return float(np.hypot(p2[0] - p1[0], p2[1] - p1[1]))

    def _calculate_unknown_length(self):
        known_px = self._pixel_distance(self.points[0], self.points[1])
        unknown_px = self._pixel_distance(self.points[2], self.points[3])

        if known_px <= 1e-8:
            print("已知長度像素距離過小，請重新點選。")
            return

        self.measured_length_cm = (unknown_px * self.reference_length_cm) / known_px
        print(f"量測完成，未知長度 = {self.measured_length_cm:.2f} cm")

    def run(self, image_path, target_label="Unknown"):
        self.original_image = cv2.imread(image_path)
        if self.original_image is None:
            raise FileNotFoundError(f"無法讀取圖片: {image_path}")

        self.points = []
        self.reference_length_cm = None
        self.measured_length_cm = None
        self.display_image = self.original_image.copy()
        cv2.namedWindow("Measurement", cv2.WINDOW_NORMAL)
        cv2.imshow("Measurement", self.display_image)
        cv2.setMouseCallback("Measurement", self.mouse_callback)

        print("=== 量測階段 ===")
        print(f"本次目標線段: {target_label}")
        print("點 1~2: 已知長度兩端；點 3~4: 未知長度兩端")
        print("按 r 輸入已知實際長度(cm)")
        print("按 c 清除點位重測")
        print("按 q 結束量測")

        while True:
            key = cv2.waitKey(30) & 0xFF

            if key == ord("q"):
                break
            if key == ord("c"):
                self.points.clear()
                self.measured_length_cm = None
                self.display_image = self.original_image.copy()
                cv2.imshow("Measurement", self.display_image)
                print("已清除點位，請重新點選。")
            elif key == ord("r"):
                try:
                    value = float(input("請輸入已知長度（cm）: ").strip())
                except ValueError:
                    print("輸入格式錯誤，請輸入數字。")
                    continue
                if value <= 0:
                    print("已知長度需大於 0。")
                    continue
                self.reference_length_cm = value
                print(f"參考長度已設定: {value:.2f} cm")
                if len(self.points) == 4:
                    self._calculate_unknown_length()

            if self.measured_length_cm is not None:
                print(f"{target_label} 量測已完成: {self.measured_length_cm:.2f} cm")
                break

        cv2.destroyAllWindows()
        return self.measured_length_cm


def compute_points(L1, L3, gap12, gap23):
    if abs(gap12 - gap23 - 10) > 1e-6:
        gap12 = gap23 + 10
    H2 = h1 + gap12
    return {
        "A": (0, 0, 0),
        "B": (L1, 0, 0),
        "C": (L1, WIDTH_Y, 0),
        "D": (0, WIDTH_Y, 0),
        "E": (0, 0, h1),
        "F": (L1, 0, h1),
        "G": (L1, WIDTH_Y, h1),
        "H": (0, WIDTH_Y, h1),
        "J": (L1 + L2, 0, 0),
        "K": (L1 + L2, WIDTH_Y, 0),
        "M": (L1, 0, H2),
        "N": (L1 + L2, 0, H2),
        "O": (L1 + L2, WIDTH_Y, H2),
        "P": (L1, WIDTH_Y, H2),
        "Q": (L1 + L2 + L3, 0, 0),
        "R": (L1 + L2 + L3, WIDTH_Y, 0),
        "S": (L1 + L2, 0, H3),
        "T": (L1 + L2 + L3, 0, H3),
        "U": (L1 + L2 + L3, WIDTH_Y, H3),
        "V": (L1 + L2, WIDTH_Y, H3),
    }


EDGES = [
    ("A", "B"), ("B", "C"), ("C", "D"), ("D", "A"),
    ("E", "F"), ("F", "G"), ("G", "H"), ("H", "E"),
    ("A", "E"), ("B", "F"), ("C", "G"), ("D", "H"),
    ("B", "J"), ("J", "K"), ("K", "C"),
    ("M", "N"), ("N", "O"), ("O", "P"), ("P", "M"),
    ("B", "M"), ("J", "N"), ("K", "O"), ("C", "P"),
    ("J", "Q"), ("Q", "R"), ("R", "K"),
    ("S", "T"), ("T", "U"), ("U", "V"), ("V", "S"),
    ("J", "S"), ("Q", "T"), ("R", "U"), ("K", "V"),
    ("M", "F"), ("P", "G"), ("N", "S"), ("O", "V"),
]


def show_model(
    initial_l1,
    initial_l3,
    measured_ab_cm,
    measured_jq_cm,
    measured_mb_cm,
    initial_gap12,
):
    """Open 3D model using measured AB -> L1, JQ -> L3, MB -> gap12; BJ=L2 fixed."""
    initial_l1 = float(np.clip(initial_l1, 0.0, 200.0))
    initial_l3 = float(np.clip(initial_l3, 0.0, 200.0))
    fig = plt.figure(figsize=(12, 9))
    ax = fig.add_subplot(111, projection="3d")
    plt.subplots_adjust(bottom=0.33)

    ax_l1 = plt.axes([0.2, 0.23, 0.6, 0.03], facecolor="lightgoldenrodyellow")
    ax_l3 = plt.axes([0.2, 0.19, 0.6, 0.03], facecolor="lightgoldenrodyellow")
    ax_g12 = plt.axes([0.2, 0.15, 0.6, 0.03], facecolor="lightgoldenrodyellow")
    ax_g23 = plt.axes([0.2, 0.11, 0.6, 0.03], facecolor="lightgoldenrodyellow")
    ax_text = plt.axes([0.2, 0.04, 0.4, 0.05])

    sli_l1 = Slider(ax_l1, "L1", 0, 200, valinit=initial_l1)
    sli_l3 = Slider(ax_l3, "L3", 0, 200, valinit=initial_l3)
    initial_gap12 = float(np.clip(initial_gap12, 20.0, 160.0))
    initial_gap23 = float(np.clip(initial_gap12 - 10.0, 10.0, 150.0))
    sli_g12 = Slider(ax_g12, "gap12", 20, 160, valinit=initial_gap12)
    sli_g23 = Slider(ax_g23, "gap23", 10, 150, valinit=initial_gap23)
    text_box = TextBox(
        ax_text,
        "Boxes (e.g. A,BJ_MID,CK_MID): ",
        initial="A,D,Q,R,M,N,BJ_MID,CK_MID",
        )

    def draw_box(corner1, corner2, color="red", linewidth=2):
        x1, y1, z1 = corner1
        x2, y2, z2 = corner2
        v = [
            (x1, y1, z1), (x2, y1, z1), (x2, y2, z1), (x1, y2, z1),
            (x1, y1, z2), (x2, y1, z2), (x2, y2, z2), (x1, y2, z2),
        ]
        edges_box = [
            (0, 1), (1, 2), (2, 3), (3, 0),
            (4, 5), (5, 6), (6, 7), (7, 4),
            (0, 4), (1, 5), (2, 6), (3, 7),
        ]
        for e0, e1 in edges_box:
            ax.plot3D(*zip(v[e0], v[e1]), color=color, linewidth=linewidth)

    def draw():
        global selected_vertices
        ax.clear()
        L1 = sli_l1.val
        L3 = sli_l3.val
        gap12 = sli_g12.val
        gap23 = sli_g23.val
        points = compute_points(L1, L3, gap12, gap23)
        marker_points = dict(points)
        marker_points["BJ_MID"] = tuple(
            (np.array(points["B"]) + np.array(points["J"])) / 2.0
        )
        marker_points["CK_MID"] = tuple(
            (np.array(points["C"]) + np.array(points["K"])) / 2.0
        )

        for a, b in EDGES:
            ax.plot3D(*zip(points[a], points[b]), color="black", linewidth=3)

        for label, coord in points.items():
            ax.text(*coord, f" {label}", fontsize=8, color="red")

        # Draw small wireframe cubes on selected vertices
        H2 = h1 + gap12
        bounds1 = (0, L1, 0, WIDTH_Y, 0, h1)
        bounds2 = (L1, L1 + L2, 0, WIDTH_Y, 0, H2)
        bounds3 = (L1 + L2, L1 + L2 + L3, 0, WIDTH_Y, 0, H3)
        vertex_to_cuboid = {
            "A": 1, "B": 2, "C": 2, "D": 1, "E": 1, "F": 1, "G": 1, "H": 1,
            "J": 2, "K": 2, "M": 2, "N": 2, "O": 2, "P": 2,
            "Q": 3, "R": 3, "S": 3, "T": 3, "U": 3, "V": 3,
        }

        for vertex in selected_vertices:
            if vertex not in marker_points:
                continue
            vx, vy, vz = marker_points[vertex]
            cuboid = vertex_to_cuboid.get(vertex, 2)
            if cuboid == 1:
                xmin, xmax, ymin, ymax, zmin, zmax = bounds1
            elif cuboid == 2:
                xmin, xmax, ymin, ymax, zmin, zmax = bounds2
            else:
                xmin, xmax, ymin, ymax, zmin, zmax = bounds3

            side = 10.0
            x1 = vx if abs(vx - xmin) < 1e-6 else max(vx - side, xmin)
            x2 = min(vx + side, xmax) if abs(vx - xmin) < 1e-6 else vx
            y1 = vy if abs(vy - ymin) < 1e-6 else max(vy - side, ymin)
            y2 = min(vy + side, ymax) if abs(vy - ymin) < 1e-6 else vy
            z1 = vz if abs(vz - zmin) < 1e-6 else max(vz - side, zmin)
            z2 = min(vz + side, zmax) if abs(vz - zmin) < 1e-6 else vz

            draw_box((x1, y1, z1), (x2, y2, z2), color="red", linewidth=2)
            ax.scatter(vx, vy, vz, color="red", s=40, zorder=10)

        xs = [p[0] for p in points.values()]
        ys = [p[1] for p in points.values()]
        zs = [p[2] for p in points.values()]
        margin = 5

        ax.set_xlim(min(xs) - margin, max(xs) + margin)
        ax.set_ylim(min(ys) - margin, max(ys) + margin)
        ax.set_zlim(min(zs) - margin, max(zs) + margin)
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_zlabel("Z")
        ax.set_title("Coral garden ridge modelling (AB, JQ, MB measured; BJ=45 fixed)")
        ax.set_box_aspect((max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)))
        ax.legend(
            handles=[Line2D([0], [0], color="red", lw=2, label="Selected vertex cube")],
            loc="upper left",
        )

        aq = L1 + L2 + L3
        ax.text2D(
            0.02,
            0.95,
            (
                f"Measured AB = {measured_ab_cm:.2f} cm | "
                f"JQ = {measured_jq_cm:.2f} cm | "
                f"MB = {measured_mb_cm:.2f} cm"
            ),
            transform=ax.transAxes,
            color="blue",
        )
        ax.text2D(
            0.02,
            0.90,
            (
                f"L1(AB)={L1:.2f} | L2(BJ)={L2:.2f} | L3(JQ)={L3:.2f} | "
                f"AQ={aq:.2f} | MB={h1 + gap12:.2f}"
            ),
            transform=ax.transAxes,
            color="blue",
        )
        fig.canvas.draw_idle()

    def on_change(_):
        # Keep the same coupling as original file: gap12 = gap23 + 10
        target_g12 = sli_g23.val + 10
        if abs(sli_g12.val - target_g12) > 0.1:
            sli_g12.set_val(np.clip(target_g12, 20, 160))
        draw()

    def submit_vertices(text):
        global selected_vertices
        text = text.strip()
        if not text:
            selected_vertices = []
        else:
            parts = [p.strip().upper() for p in text.split(",")]
            valid_points = compute_points(sli_l1.val, sli_l3.val, sli_g12.val, sli_g23.val)
            valid_names = set(valid_points.keys()) | {"BJ_MID", "CK_MID"}
            selected_vertices = [p for p in parts if p in valid_names]
        draw()

    sli_l1.on_changed(on_change)
    sli_l3.on_changed(on_change)
    sli_g12.on_changed(on_change)
    sli_g23.on_changed(on_change)
    text_box.on_submit(submit_vertices)

    draw()
    plt.show()


def main():
    print("模型預設長度：HE=30, FB=15, BJ=45（固定）, SJ=25, TU=30")
    print("流程：先輸入3張2D圖片，再進行量測，最後才輸出3D模型。")
    print("量測對應：① AB(圖1) → L1  ② JQ(圖2) → L3  ③ MB(圖3) → gap12（BJ=L2=45固定）")

    default_images = ["Rov photo1.png", "Rov photo2.png", "Rov photo3.png"]
    image_paths = []
    print("\n=== 圖片輸入階段（3張）===")
    for idx, default_path in enumerate(default_images, start=1):
        user_input = input(
            f"請輸入第{idx}張圖片路徑（直接 Enter 使用預設: {default_path}）: "
        ).strip()
        image_paths.append(user_input if user_input else default_path)

    measurer = PipeMeasurer()
    print("\n=== 2D識別/量測階段 ===")

    measured_ab = measurer.run(image_paths[0], target_label="AB")

    if measured_ab is None:
        print("未取得 AB 有效量測值，程式結束。")
        return

    measured_jq = measurer.run(image_paths[1], target_label="JQ")
    if measured_jq is None:
        print("未取得 JQ 有效量測值，程式結束。")
        return

    measured_mb = measurer.run(image_paths[2], target_label="MB")
    if measured_mb is None:
        print("未取得 MB 有效量測值，程式結束。")
        return

    # AB = L1；JQ = L3；MB = H2 = h1 + gap12 → gap12 = MB - h1
    initial_l1 = measured_ab
    initial_l3 = measured_jq
    initial_gap12 = measured_mb - h1

    print("\n=== 量測完成，開始建立3D模型 ===")
    print(f"AB(L1) = {initial_l1:.2f} cm, JQ(L3) = {initial_l3:.2f} cm, MB = {measured_mb:.2f} cm")

    show_model(
        initial_l1=initial_l1,
        initial_l3=initial_l3,
        measured_ab_cm=measured_ab,
        measured_jq_cm=measured_jq,
        measured_mb_cm=measured_mb,
        initial_gap12=initial_gap12,
    )


if __name__ == "__main__":
    main()