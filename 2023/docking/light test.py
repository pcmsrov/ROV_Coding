from pymavlink import mavutil
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
    set_rc_channel_pwm(9, 1600)
    time.sleep(0.1)
    if tim >= current + buffer:
        print("break")
        set_rc_channel_pwm(9, 1500)
        # master.mav.command_long_send(master.target_system, master.target_component, mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0, 0, 0, 0, 0, 0, 0, 0)
        # master.motors_disarmed_wait()
        print("o")
        exit()


current = time.time()
while True:
    docking(current, 4)