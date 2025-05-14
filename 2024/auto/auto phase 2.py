import time
import cv2
import numpy as np
import autodefs as auto 
from autodefs import set_rc_channel_pwm
from oepnc import Video
from pymavlink import mavutil

auto.init()

height, width = 0, 0

determine = false

timer = time.time()

auto.look_at(-2500)
time.sleep(0.1)

while True:
    current = time.time()
    if cap.frame_available():
        frame = cap.frame()


        captured_frame_lab_red = auto.color(frame, [20, 150, 150], [190, 255, 255])
        #circles = cv2.HoughCircles(captured_frame_lab_red, cv2.HOUGH_GRADIENT, 1, captured_frame_lab_red.shape[0] / 8, param1=100, param2=18, minRadius=5, maxRadius=60)
        greyscale = cv2.cvtColor(capframe, cv2.COLOR_BGR2GRAY)

        _, binary_image =  cv2.threshold(greyscale, 150, 255, cv2.THRESH_BINARY)

        all_contours, hierachy = cv2.findCounters(binary_image, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)



        area = cv2.contourArea(all_contours)
        
        if area < 400 and determine == false:
            set_rc_channel_pwm(3, 1600)
        if area > 400 and determine == false:
            determine = true
            set_rc_channel_pwm(3, 1500)

            
        cv2.imshow('frame', frame)
        if not cap.frame_available():
            print("tears")

    # write the frame to the output file
    if cv2.waitKey(1) == ord('q'):
        time.sleep(0.1)
        set_rc_channel_pwm(3, 1500)
        set_rc_channel_pwm(6, 1500)
        set_rc_channel_pwm(5, 1500)
        break

cap.release()
cv2.destroyAllWindows()
