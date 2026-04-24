WebServer -> ESP32燒錄, 使用Arduino IDE
    COM, 板類型 ESP32 Dev Module
FrontEnd -> PC運行，前端控制介面

---
front end
install python lib

pip install requests
pip install PyQt5
pip install matplotlib

---
Trouble Shooting
只有電池時Wifi不出現，接上USB線後Wifi又會出現
    電池電量不足，更換電池即可解決



---

Issue? ----------
每次initial connect??
WIFI都重連??


To Do ----------
clear data button?
float data buffer 5min?


Last run, without timer, switch only?
>= 3min, ESP32 buffer size 15min? 5min
program test, preparation days

Depth Sensor Calibration
first get data, set as offset

show data table, side scroll

antena, 延長線，螺絲

電壓檢測

狀態指示燈


===== Float Pinout, Editable Files =====
https://docs.google.com/presentation/d/1oLM84ONJYGD7PrpeK730wvq_iQj6tmpVg91eRsLw3xo/edit?usp=sharing



----- Attention -----
DVR8871 Pin soldering Loose?
IN1, IN2, GND
焊盤太小?

----- Depth Sensor, BlueRobotics -----
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

Install Library
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