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

timer = time.time()


while True:
    current = time.time()
    if cap.frame_available():
        frame = cap.frame()
        output_frame = frame.copy()

        captured_frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        captured_frame_bgr = cv2.medianBlur(captured_frame_bgr, 3)
        captured_frame_lab = cv2.cvtColor(captured_frame_bgr, cv2.COLOR_BGR2Lab)    
        captured_frame_lab_red = cv2.inRange(captured_frame_lab, np.array([20, 150, 150]), np.array([190, 255, 255]))
        captured_frame_lab_red = cv2.GaussianBlur(captured_frame_lab_red, (5, 5), 2, 2)
        circles = cv2.HoughCircles(captured_frame_lab_red, cv2.HOUGH_GRADIENT, 1, captured_frame_lab_red.shape[0] / 8,
                                   param1=100, param2=18, minRadius=5, maxRadius=60)

        if circles is not None:
            print("found circles")
            circles = np.round(circles[0, :]).astype("int")
            cv2.circle(frame, center=(circles[0, 0], circles[0, 1]), radius=circles[0, 2], color=(0, 255, 0),
                       thickness=2)
            if current <= timer + 10:
                px, py = circles[0, 0], circles[0, 1]
                set_rc_channel_pwm(5, 1500)
                depth = 1500 + ((-20 / 27) * np.power(py, 1) + 400)
                lat = 1500 + ((5 / 12) * np.power(px, 1) - 400)
                set_rc_channel_pwm(3, int(depth))
                set_rc_channel_pwm(6, int(lat))
                
            if current >= timer + 10:
                set_rc_channel_pwm(3, 1500)
                set_rc_channel_pwm(6, 1500)
                set_rc_channel_pwm(5, 1900)


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
