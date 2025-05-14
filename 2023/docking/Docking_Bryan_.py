import numpy as np
import cv2
from oepnc import Video
from pymavlink import mavutil
from datetime import datetime
from datetime import timezone
import time

master = mavutil.mavlink_connection('udpin:localhost:14445')
print("waiting heartbeat")
master.wait_heartbeat()
print("confirmed")
master.mav.command_long_send(master.target_system, master.target_component, mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0, 1, 0, 0, 0, 0, 0, 0)

master.motors_armed_wait()

def set_rc_channel_pwm(channel_id, pwm=1500):
    if channel_id < 1 or channel_id > 18:
        print("mylls")
        return

    rc_channel_values = [65535 for _ in range(18)]
    rc_channel_values[channel_id - 1] = pwm
    master.mav.rc_channels_override_send(
        master.target_system,                # target_system
        master.target_component,             # target_component
        *rc_channel_values)

def docking(current, buffer=1):
    tim = time.time()
    set_rc_channel_pwm(5, 1600)
    time.sleep(0.1)
    if tim >= current + buffer:
        print("break")
        set_rc_channel_pwm(5, 1500)
        # master.mav.command_long_send(master.target_system, master.target_component, mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0, 0, 0, 0, 0, 0, 0, 0)
        # master.motors_disarmed_wait()
        print("o")
        exit()

# initialize the video capture object
cap = Video(port=4777)
print("initalizing ")
waited = 0
while not cap.frame_available():
    waited += 1
    print("not available")

print("starting stream")
current = time.time()

test = cap.frame()
# grab the width, height, and fps of the frames in the video stream.
    # frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    # frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    # fps = int(cap.get(cv2.CAP_PROP_FPS))
height, width = 0, 0

current = time.time()
'''
while True:
    tim = time.time()
    set_rc_channel_pwm(3, 1100)
    if tim >= current + 10:
        print("break")
        time.sleep(0.1)
        set_rc_channel_pwm(3, 1500)
        # master.mav.command_long_send(master.target_system, master.target_com  ponent, mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0, 0, 0, 0, 0, 0, 0, 0)
        # master.motors_disarmed_wait()
        print("o")
        break
'''
while True:
    if cap.frame_available():
        frame = cap.frame()
        height, width = frame.shape[:2]
        # convert from BGR to HSV color space
        img_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)


        # lower mask (0-10)
        lower_red = np.array([0, 100, 100])
        upper_red = np.array([10, 255, 255])
        mask0 = cv2.inRange(img_hsv, lower_red, upper_red)

        '''
        # upper mask (170-180)
        lower_red = np.array([170, 50, 50])
        upper_red = np.array([180, 255, 255])
        mask1 = cv2.inRange(img_hsv, lower_red, upper_red)
        '''
        # join my masks
        mask = mask0 #+ mask1

        bbox = cv2.boundingRect(mask)
        contours, hierarchies = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        cx = 0
        cy = 0
        for i in contours:
            print("in contours loop")
            M = cv2.moments(i)
            if M['m00'] != 0:
                cx = int(M['m10']/M['m00'])
                cy = int(M['m01']/M['m00'])
                cv2.drawContours(frame, [i], -1, (0, 255, 0), 2)
                cv2.circle(frame, (cx, cy), 7, (0, 0, 255), -1)
                print(f"x: {cx} y: {cy}")
        # if we get a bounding box, use it to draw a rectangle on theqq image
        # if bbox is not None:
        #     x, y, w, h = bbox
        #     cv2.rectangle(frame, (x, y)q (x + w, y + h), (0, 255, 0), 2)
        # else:
        #     print("Object not detected")
        # pwm signal "3" negative = sink
        # pwm signal "6" positive = right

        #
        # if cy <= 450:
        #     set_rc_channel_pwm(3, 1600)
        # if cy >= 630:
        #     set_rc_channel_pwm(3, 1300)
        # if cx <= 800:
        #     set_rc_channel_pwm(6, 1450)
        # if cx >= 1120:
        #     set_rc_channel_pwm(6, 1550)
        # if (cy >= 450 and cy <= 630) and (c x >= 800 and cx <= 1120):
        #     set_rc_channel_pwm(3, 1500)
        #     set_rc_channel_pwm(6, 1500)
        #     set_rc_channel_pwm(5, 1600)
        #
        # set_rc_channel_pwm(5, 1500)

        # if (cx >= 880 and cy >= 495) and (cx <= 1040 and cy <= 595):
        #     set_rc_channel_pwm(5, 1550)
        # else:
        depth = 1500 + ((-20/27) * np.power(cy, 1) + 400)
        lat = 1500 + ((5/12) * np.power(cx, 1) - 400)
        set_rc_channel_pwm(3, int(depth))
        set_rc_channel_pwm(6, int(lat))
        set_rc_channel_pwm(5, 1550)


        print("frame")
        cv2.line(frame, (880, 495), (880, 595), (255, 0, 0), 1)
        cv2.line(frame, (1040, 495), (1040, 595), (255, 0, 0), 1)
        cv2.line(frame, (880, 495), (1040, 495), (255, 0, 0), 1)
        cv2.line(frame, (880, 595), (1040, 595), (255, 0, 0), 1)
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

print(height, width)
cap.release()
cv2.destroyAllWindows()
