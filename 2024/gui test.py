import serial
from serial import Serial
import PySimpleGUI as sg



ser = serial.Serial('COM3', 115200, timeout=1)
read = False

sg.theme('DarkAmber')
layout = [  [sg.InputText(), sg.Button('Empfindlichkeit einstellen')],
            [sg.Button('start'), sg.Button('end')] ]

window = sg.Window('Window Title', layout)



while True:
    event, values = window.read()

    if read == True:
        reading = ser.readline()
        print(reading[0:256])

    if event == "start":
        read = True

    if event == sg.WIN_CLOSED or event == 'end':
        break

window.close()