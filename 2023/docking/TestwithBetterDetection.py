import time

import cv2
import numpy as np
from oepnc import Video
from pymavlink import mavutil

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
timer = time.time()

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
       ret, captured_frame = cap.read()
       output_frame = captured_frame.copy()

       # Convert original image to BGR, since Lab is only available from BGR
       captured_frame_bgr = cv2.cvtColor(captured_frame, cv2.COLOR_BGRA2BGR)
       # First blur to reduce noise prior to color space conversion
       captured_frame_bgr = cv2.medianBlur(captured_frame_bgr, 3)
       # Convert to Lab color space, we only need to check one channel (a-channel) for red here
       captured_frame_lab = cv2.cvtColor(captured_frame_bgr, cv2.COLOR_BGR2Lab)
       # Threshold the Lab image, keep only the red pixels
       # Possible yellow threshold: [20, 110, 170][255, 140, 215]
       # Possible blue threshold: [20, 115, 70][255, 145, 120]
       captured_frame_lab_red = cv2.inRange(captured_frame_lab, np.array([20, 150, 150]), np.array([190, 255, 255]))
       # Second blur to reduce more noise, easier circle detection
       captured_frame_lab_red = cv2.GaussianBlur(captured_frame_lab_red, (5, 5), 2, 2)
       # Use the Hough transform to detect circles in the image
       circles = cv2.HoughCircles(captured_frame_lab_red, cv2.HOUGH_GRADIENT, 1, captured_frame_lab_red.shape[0] / 8,
                                  param1=100, param2=18, minRadius=5, maxRadius=60)

       # If we have extracted a circle, draw an outline
       # We only need to detect one circle here, since there will only be one reference object
       if circles is not None:
          circles = np.round(circles[0, :]).astype("int")
          cv2.circle(output_frame, center=(circles[0, 0], circles[0, 1]), radius=circles[0, 2], color=(0, 255, 0),
                     thickness=2)
          
          px, py = circles[0,0], circles[0, 1]
          if (px >= 800 and px <= 1040) and (py >= 495 and py <= 595):
              set_rc_channel_pwm(5, 1500)
              depth = 1500 + ((-20/27) * np.power(py, 1) + 400)
              lat = 1500 + ((5/12) * np.power(px, 1) - 400)
              set_rc_channel_pwm(3, int(depth))
              set_rc_channel_pwm(6, int(lat))
          else:
              set_rc_channel_pwm(5, 1600)



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

cap.release()
cv2.destroyAllWindows()
