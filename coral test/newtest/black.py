import cv2
import numpy as np

img = cv2.imread("water_under3.jpg")
copy_img = img.copy()
gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

# 自適應二值化，極強抗光照干擾
binary = cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,21,4)

# 去除細小噪點
kernel = np.ones((2,2),np.uint8)
binary = cv2.morphologyEx(binary,cv2.MORPH_CLOSE,kernel)

# 找所有輪廓，只保留面積最大=整個管架
contours,_ = cv2.findContours(binary,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
if contours:
    # 選最大面積輪廓
    max_cnt = max(contours,key=cv2.contourArea)
    # 外接矩形，直接框整個正面結構
    x,y,w,h = cv2.boundingRect(max_cnt)
    cv2.rectangle(copy_img,(x,y),(x+w,y+h),(0,0,255),3)
    # 繪製實際管架輪廓
    cv2.drawContours(copy_img,[max_cnt],-1,(0,0,255),2)

cv2.imshow("gray",gray)
cv2.imshow("binary",binary)
cv2.imshow("整體框架框選",copy_img)
cv2.imwrite("result1.jpg",copy_img)
cv2.waitKey(0)
cv2.destroyAllWindows()