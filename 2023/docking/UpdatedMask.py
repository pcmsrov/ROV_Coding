import cv2
import numpy as np


def FindGoal(frame, h):
    img_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # lower mask (0-10)
    lower_red = np.array([0, 100, 100])
    upper_red = np.array([10, 255, 255])
    mask = cv2.inRange(img_hsv, lower_red, upper_red)
    '''
    # upper mask (170-180)
    lower_red = np.array([0, 50, 50])
    upper_red = np.array([150, 255, 255])
    mask1 = cv2.inRange(img_hsv, lower_red, upper_red)

    # join my masks
    mask = mask0 + mask1
    '''

    cv2.boundingRect(mask)
    contours, hierarchies = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    return contours


cap = cv2.VideoCapture(0)
while True:
    # Checking
    _, vid = cap.read()

    if vid is None:
        print("Vid is None")
        continue

    height, width = vid.shape[:2]
    contours = FindGoal(vid, height)
    py = 0
    px = 0
    for i in contours:
        M = cv2.moments(i)
        if M['m00'] != 0:
            px = int(M['m10'] / M['m00'])
            py = int(M['m01'] / M['m00'])
            cv2.drawContours(vid, [i], -1, (0, 255, 0), 2)
            cv2.circle(vid, (px, py), 7, (0, 0, 255), -1)
            print(f"x: {px} y: {py}")
    cv2.imshow("vid", vid)
    if cv2.waitKey(16) in [ord('q'), 27]:
        break

cv2.destroyAllWindows()
