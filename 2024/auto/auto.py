import time
import cv2
import numpy as np
from oepnc import Video
from pymavlink import mavutil
'''
███████ ██    ██ ███    ██  ██████ ████████ ██  ██████  ███    ██ ███████ 
██      ██    ██ ████   ██ ██         ██    ██ ██    ██ ████   ██ ██      
█████   ██    ██ ██ ██  ██ ██         ██    ██ ██    ██ ██ ██  ██ ███████ 
██      ██    ██ ██  ██ ██ ██         ██    ██ ██    ██ ██  ██ ██      ██ 
██       ██████  ██   ████  ██████    ██    ██  ██████  ██   ████ ███████ 
'''
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

height, width = 0, 0

timer = time.time()

look_at(0)
time.sleep(0.1)
determine = False
while True:
    current = time.time()
    if cap.frame_available():
        '''
        ██████  ██   ██  █████  ███████ ███████      ██████  ███    ██ ███████ 
        ██   ██ ██   ██ ██   ██ ██      ██          ██    ██ ████   ██ ██      
        ██████  ███████ ███████ ███████ █████       ██    ██ ██ ██  ██ █████   
        ██      ██   ██ ██   ██      ██ ██          ██    ██ ██  ██ ██ ██      
        ██      ██   ██ ██   ██ ███████ ███████      ██████  ██   ████ ███████
        '''
        #finding the center of the black pvc pipe

        frame = cap.frame()
        
        if current <= timer + 10:

            capframe = color(frame, [0, 0, 0], [0, 0, 29])
            
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

            #circling the center of the black pvc pipe
            frame = cv2.circle(frame, (centx, centy), 3, (0, 255, 0), 3)

            #pid controller
            depth = 1500 + ((-20/27) * np.power(centy, 1) + 400)
            lat = 1500 + ((5/12) * np.power(centx, 1) - 400)
            set_rc_channel_pwm(3, int(depth))
            set_rc_channel_pwm(6, int(lat))
            set_rc_channel_pwm(5, 1550)

            '''
        ██████  ██   ██  █████  ███████ ███████     ████████ ██     ██  ██████  
        ██   ██ ██   ██ ██   ██ ██      ██             ██    ██     ██ ██    ██ 
        ██████  ███████ ███████ ███████ █████          ██    ██  █  ██ ██    ██ 
        ██      ██   ██ ██   ██      ██ ██             ██    ██ ███ ██ ██    ██ 
        ██      ██   ██ ██   ██ ███████ ███████        ██     ███ ███   ██████                                         
                                                                        
        '''

        elif current <= timer + 25:
            look_at(-2500)
            time.sleep(0.1)
            captured_frame_lab_red = color(frame, [20, 150, 150], [190, 255, 255])
            #circles = cv2.HoughCircles(captured_frame_lab_red, cv2.HOUGH_GRADIENT, 1, captured_frame_lab_red.shape[0] / 8, param1=100, param2=18, minRadius=5, maxRadius=60)
            greyscale = cv2.cvtColor(capframe, cv2.COLOR_BGR2GRAY)

            _, binary_image =  cv2.threshold(greyscale, 150, 255, cv2.THRESH_BINARY)

            all_contours, hierachy = cv2.findCounters(binary_image, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)



            area = cv2.contourArea(all_contours)
            
            if area < 400 and determine == False:
                set_rc_channel_pwm(3, 1600)
            if area > 400 and determine == False:
                determine = True
                set_rc_channel_pwm(3, 1500)

            '''
        ██████  ██   ██  █████  ███████ ███████     ████████ ██   ██ ██████  ███████ ███████ 
        ██   ██ ██   ██ ██   ██ ██      ██             ██    ██   ██ ██   ██ ██      ██      
        ██████  ███████ ███████ ███████ █████          ██    ███████ ██████  █████   █████   
        ██      ██   ██ ██   ██      ██ ██             ██    ██   ██ ██   ██ ██      ██      
        ██      ██   ██ ██   ██ ███████ ███████        ██    ██   ██ ██   ██ ███████ ███████ 
                                                                                     
                                                                                     
        '''

        elif current <= timer + 35:
            look_at(0)
            time.sleep(0.1)
            #identifying red coral deployment area
            capframe = color(frame, [20, 150, 150], [190, 255, 255])
            
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

            #circling the center of the area
            frame = cv2.circle(frame, (centx, centy), 3, (0, 255, 0), 3)
            set_rc_channel_pwm(5, 1500)
            depth = 1500 + ((-20 / 27) * np.power(centy, 1) + 400)
            lat = 1500 + ((5 / 12) * np.power(centx, 1) - 400)
            set_rc_channel_pwm(3, int(depth))
            set_rc_channel_pwm(6, int(lat))

        elif current <= timer + 45:
            #lowering rov onto the area
            set_rc_channel_pwm(3, 1500)
            set_rc_channel_pwm(6, 1500)
            set_rc_channel_pwm(5, 1100)
            #releasing coral in the area 
            #TBD

        '''
        ███████ ███    ██ ██████  ██      ██ ███    ██ ███████ 
        ██      ████   ██ ██   ██ ██      ██ ████   ██ ██      
        █████   ██ ██  ██ ██   ██ ██      ██ ██ ██  ██ █████   
        ██      ██  ██ ██ ██   ██ ██      ██ ██  ██ ██ ██      
        ███████ ██   ████ ██████  ███████ ██ ██   ████ ███████ 
                                                       
                                                       '''
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
