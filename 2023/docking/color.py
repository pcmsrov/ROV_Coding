import cv2
import matplotlib.pyplot as plt
import numpy as np
from oepnc import Video


cap = Video(port=4777)

while (1):

    # Take each frame
    frame = cap.frame()

    # Convert BGR to HSV
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # define range of red color in HSV
    lower_red = np.array([160, 50, 50])
    upper_red = np.array([180, 255, 255])

    # Threshold the HSV image to get only red colors
    mask = cv2.inRange(hsv, lower_red, upper_red)

    # Bitwise-AND mask and original image
    res = cv2.bitwise_and(frame, frame, mask=mask)

    # we are just adding 2 more channels on the mask so we can stack it along other images
    mask_3 = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

    # stacking up all three images together
    stacked = np.hstack((mask_3, frame, res))

    cv2.imshow('Result', cv2.resize(stacked, None, fx=0.8, fy=0.8))
    k = cv2.waitKey(1) & 0xFF
    if k == 27:
        break

cv2.destroyAllWindows()
cap.release()