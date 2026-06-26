import cv2
import numpy as np

img = cv2.imread("water_under4.jpg")
if img is None: exit()
copy_img = img.copy()
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# 1. 保持你最穩定的自適應二值化
binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                              cv2.THRESH_BINARY_INV, 21, 4)

# 2. 使用 RETR_CCOMP 找輪廓，這可以讓我們知道哪些輪廓裡面有“洞” (黑色部分)
# hierarchy [Next, Previous, First_Child, Parent]
contours, hierarchy = cv2.findContours(binary, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)

if hierarchy is not None:
    hierarchy = hierarchy[0]
    for i, cnt in enumerate(contours):
        # 關鍵點：我們只看「有子輪廓」的父輪廓，這代表它是“空心”的 (白夾黑)
        # 且父輪廓層級通常是第一層或沒有被包圍的
        if hierarchy[i][2] != -1: # 有子輪廓 (代表裡面有黑色區域)
            
            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = float(w) / h
            area = cv2.contourArea(cnt)
            
            if area < 60: continue # 忽略太小的噪點

            # 判斷是轉角還是水管
            is_structure = False
            
            # A. 識別轉角：小正方形 (1:1 比例)
            if 0.7 < aspect_ratio < 1.3 and w < 60:
                is_structure = True
                # 轉角處可以畫個小紅塊或短線
                cv2.rectangle(copy_img, (x, y), (x+w, y+h), (0, 0, 255), -1)
            
            # B. 識別水平水管
            elif w > 80 and aspect_ratio > 4:
                is_structure = True
                center_y = y + h // 2
                cv2.line(copy_img, (x, center_y), (x + w, center_y), (0, 0, 255), 4)
                
            # C. 識別垂直水管
            elif h > 80 and (1.0 / aspect_ratio) > 4:
                is_structure = True
                center_x = x + w // 2
                cv2.line(copy_img, (center_x, y), (center_x, y + h), (0, 0, 255), 4)

# 3. 顯示結果
cv2.imshow("Binary (White-Black-White)", binary)
cv2.imshow("Pipe Network (Red Lines)", copy_img)
cv2.waitKey(0)
cv2.destroyAllWindows()