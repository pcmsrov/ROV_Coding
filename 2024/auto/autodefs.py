import time
import cv2
import numpy as np
from oepnc import Video
from pymavlink import mavutil

def init():
    master = mavutil.mavlink_connection('udpin:localhost:14445')
    print("waiting heartbeat")
    master.wait_heartbeat()
    print("confirmed")
    master.mav.command_long_send(master.target_system, master.target_component,
                                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0, 1, 0, 0, 0, 0, 0, 0)

    master.motors_armed_wait()

    cap = Video(port=4777)
    print("initalizing ")
    waited = 0
    while not cap.frame_available():
        waited += 1
        print("not available")

    print("starting stream")

    test = cap.frame()


def color(frame, start, end):
    captured_frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
    captured_frame_bgr = cv2.medianBlur(captured_frame_bgr, 3)
    captured_frame_lab = cv2.cvtColor(captured_frame_bgr, cv2.COLOR_BGR2Lab)    
    captured_frame_lab_red = cv2.inRange(captured_frame_lab, np.array(start), np.array(end))
    captured_frame_lab_red = cv2.GaussianBlur(captured_frame_lab_red, (5, 5), 2, 2)
    return captured_frame_lab_red

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

