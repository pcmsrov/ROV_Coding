import time
import cv2
import numpy as np
from oepnc import Video
from pymavlink import mavutil

master = mavutil.mavlink_connection('udpin:localhost:14445')
print("waiting heartbeat")
master.wait_heartbeat()
print("confirmed")
master.mav.command_long_send(master.target_system, master.target_component,
                             mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0, 1, 0, 0, 0, 0, 0, 0)

master.motors_armed_wait()

#this is the where the rov moves towards the velcro

def look_at(tilt, roll=0, pan=0):
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_DO_MOUNT_CONTROL,
        1,
        tilt,
        roll,
        pan,
        0, 0, 0,
        mavutil.mavlink.MAV_MOUNT_MODE_MAVLINK_TARGETING)

def set_rc_channel_pwm(channel_id, pwm=1500):
    if channel_id < 1 or channel_id > 18:
        print("mylls")
        return
    rc_channel_values = [65535 for _ in range(18)]
    rc_channel_values[channel_id - 1] = pwm
    master.mav.rc_channels_override_send(
        master.target_system,  # target_system
        master.target_component,  # target_component
        *rc_channel_values)

cap = Video(port=4777)
print("initalizing ")
waited = 0
while not cap.frame_available():
    waited += 1
    print("not available")

print("starting stream")

test = cap.frame()

height, width = 0, 0

determine = false

timer = time.time()

look_at(0)
time.sleep(0.1)

while True:
    current = time.time()
    if cap.frame_available():
        frame = cap.frame()

        captured_frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        captured_frame_bgr = cv2.medianBlur(captured_frame_bgr, 3)
        captured_frame_lab = cv2.cvtColor(captured_frame_bgr, cv2.COLOR_BGR2Lab)    
        captured_frame_lab_red = cv2.inRange(captured_frame_lab, np.array([20, 150, 150]), np.array([190, 255, 255]))
        captured_frame_lab_red = cv2.GaussianBlur(captured_frame_lab_red, (5, 5), 2, 2)

        greyscale = cv2.cvtColor(capframe, cv2.COLOR_BGR2GRAY)

        _, binary_image =  cv2.threshold(greyscale, 150, 255, cv2.THRESH_BINARY)

        all_contours, hierachy = cv2.findCounters(binary_image, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        centx, centy = 0, 0
        for contour in all_contours: 
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)

            if len(approx) == 4:
                x, y, w, h == cv2.boundingRect(approx)
                aspect_ratio = float(w) / h

                cv2.drawContours(frame, [approx], -1, (0, 255, 0), 3)
                centx = x + w/2 
                centy = y + h/2

        frame = cv2.circle(frame, (centx, centy), 3, (0, 255, 0), 3)
             
        if current <= timer + 10:
            set_rc_channel_pwm(5, 1500)
            depth = 1500 + ((-20 / 27) * np.power(centy, 1) + 400)
            lat = 1500 + ((5 / 12) * np.power(centx, 1) - 400)
            set_rc_channel_pwm(3, int(depth))
            set_rc_channel_pwm(6, int(lat))
            
        if current >= timer + 10:
            set_rc_channel_pwm(3, 1500)
            set_rc_channel_pwm(6, 1500)
            set_rc_channel_pwm(5, 1100)
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
