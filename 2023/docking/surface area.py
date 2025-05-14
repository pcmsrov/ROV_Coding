import numpy as np
import cv2

img = cv2.imread("among.jpg", cv2.IMREAD_GRAYSCALE)

assert img is not None, "no image"

ret, thresh = cv2.threshold(img, 127, 255, 0)

im2, contours, hierarchy = cv2.findContours(thresh, 1, 2)

cnt = contours[0]
M = cv2.moments(cnt)

print(M)

cx = int(M['m10']/M['m00'])
cy = int(M['m01']/M['m00'])

area = cv2.contourArea(cnt)
