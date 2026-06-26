import cv2
import numpy as np

# ---------------------- 针对你这张图的调优参数 ----------------------
img_path = "water_under3.jpg"  # 替换成你的图片路径
# 自适应阈值参数（适配水下蓝绿色调）
block_size = 15
C = 5
# 形态学核大小（提取水平/垂直线条）
horizontal_kernel_size = 30
vertical_kernel_size = 30
# 霍夫线参数（针对框架线条优化）
rho = 1
theta = np.pi / 180
threshold = 128
min_line_length = 80
max_line_gap = 15
# ROI区域（只检测中间部分，过滤池底/顶部干扰）
roi_x1, roi_y1 = int(1332*0.01), int(960*0.01)
roi_x2, roi_y2 = int(1332*0.99), int(960*0.99)
# -------------------------------------------------------------------

def underwater_frame_optimized(img_path):
    # 读取图像
    img = cv2.imread(img_path)
    if img is None:
        print("图片读取失败！")
        return
    draw_img = img.copy()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # --- 1. 自适应阈值分割，比固定HSV更抗水下光线干扰 ---
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV,
        block_size, C
    )

    # --- 2. 形态学操作：分别提取水平和垂直线条 ---
    # 水平线核
    horizontal_kernel = np.ones((1, horizontal_kernel_size), np.uint8)
    horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)
    # 垂直线核
    vertical_kernel = np.ones((vertical_kernel_size, 1), np.uint8)
    vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)
    # 合并水平+垂直线条
    frame_mask = cv2.bitwise_or(horizontal_lines, vertical_lines)

    # --- 3. 只保留ROI区域，过滤池底反光/顶部干扰 ---
    roi_mask = np.zeros_like(frame_mask)
    roi_mask[roi_y1:roi_y2, roi_x1:roi_x2] = 255
    frame_mask = cv2.bitwise_and(frame_mask, roi_mask)

    # --- 4. 边缘检测+霍夫线变换，提取框架线条 ---
    edges = cv2.Canny(frame_mask, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(
        edges, rho, theta, threshold,
        minLineLength=min_line_length, maxLineGap=max_line_gap
    )

    # 绘制检测到的线条（红色）
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            cv2.line(draw_img, (x1, y1), (x2, y2), (0, 0, 255), 3)

    # --- 5. 轮廓法补全粗线条/框架边缘 ---
    contours, _ = cv2.findContours(frame_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if 100 < area < 5000:  # 过滤过小/过大的轮廓（池底反光会很大）
            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = max(w, h) / (min(w, h) + 1e-6)
            if aspect_ratio > 3:  # 只保留长宽比>3的细长线条
                cv2.drawContours(draw_img, [cnt], -1, (0, 0, 255), 2)

    # 显示和保存结果
    cv2.imshow("原始图", img)
    cv2.imshow("水平+垂直线条mask", frame_mask)
    cv2.imshow("最终识别结果", draw_img)
    cv2.imwrite("optimized_frame_result.jpg", draw_img)
    print("优化版识别完成！结果已保存")

    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    underwater_frame_optimized(img_path)