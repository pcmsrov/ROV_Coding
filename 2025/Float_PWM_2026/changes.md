## 2026 Request

2 Vertical Profile
Float maintains a depth of 2.5 meters for 30 seconds – 5 points
Float maintains a depth of 40 cm for 30 seconds

After recovery, float communicates with (transmits data autonomously to) the
station

The float must communicate (i.e., transmit) the following information to the mission station,
referred to as the defined data packet:
• Company number (provided by MATE a few weeks prior to the competition)
• Time data (UTC or local or float time [float time would be time since float starts recording])
• Pressure data and/or depth data
• Any additional data as required by the company to complete this task


Pressure/depth data must correlate to a set time transmitted from the float. For example, a defined
data packet from RANGER 01 could be:
RN01 1:51:42 UTC 9.8 kpa 1.00 meters

Successfully communicating all data
packets is defined as showing the station judge one data packet from every **5 seconds** of both
vertical profiles.



---
## Version Detail




---
## Hardware
using ESP32-S, Arduino IDE, select ESP32 Dev Module

### Float Pinout, Editable Files
https://docs.google.com/presentation/d/1oLM84ONJYGD7PrpeK730wvq_iQj6tmpVg91eRsLw3xo/edit?usp=sharing


### Connection
Depth Sensor, BlueRobotics
Connector Pinout	
1 - Red / Vin
2 - Green / SCL
3 - White / SDA
4 - Black / GND

Bar30, red
Pressure: 1021.40 mbar
Temperature: 26.00 deg C
Depth: 0.09 m
Altitude: -67.59 m above mean sea level

### Depth Senesor, Install Library
Open Arduino IDE
Sketch > Include Lib > Manage Library
Search: MS5837
Find: BlueRobotic MS5837 Library, by BlueRobotics
Version 1.1.1

Don't use lib from BlueRobotics Website (version 1.0)
data no correct, sealevel depth -9.8m


----- EPS32 Notes -----
Button, GP36 Pullup fail
GP4, GP19, GP18 OK 



### Other Hardware Issues
DVR8871 Pin soldering Loose?
IN1, IN2, GND
焊盤太小?



--- 
## Others Stuffs
Rename file name, Float_PWM_2026
change from webServer_4.2, 2025 version program


Add depth offset in .ino

Add Force stop
to stop TestPushAll and TestPullAll Function

### issue??
每次initial connect??
WIFI都重連??


### To Do
clear data button?
float data buffer 5min?

電壓檢測
Battery State

狀態指示燈

### Notes
>= 3min, ESP32 buffer size 15min? 5min
program test, preparation days

Depth Sensor Calibration
first get data, set as offset

---



















