import keyboard
import os
import glob
import time

os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'

offset = float(input('enter offset:'))

def read_temp_raw():
        f = open(device_file, 'r')
        lines = f.readlines()
        f.close()
        return lines

def read_temp():
        lines = read_temp_raw()
        while lines[0].strip()[-3:] != 'YES':
                time.sleep(0.2)
                lines = read_temp_raw()
        equals_pos = lines[1].find('t=')
        if equals_pos != -1:
                temp_string = lines[1][equals_pos+2:]
                temp_c = (float(temp_string) / 1000.0) + offset
                temp_n = (float(temp_string) / 1000.0)
                return temp_c, temp_n

while True:
        joe = list(read_temp())
        table = [['Temp', 'Temp w/ Offset', 'Offset'], [joe[1], joe[0], offset]]
        try:
            if keyboard.is_pressed('o'):
                for row in table:
                        print('| {:1} | {:^4} | {:>4} |'.format(*row))
        except:
                pass
        time.sleep(1)
