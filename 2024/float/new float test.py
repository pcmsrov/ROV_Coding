import socket
import threading
import select
import PySimpleGUI as sg

layout = [[sg.Frame("Depth", [[sg.Text(text="Unable to obtain depth", key="-DEPTH-")]]),
           sg.Frame("Pressure", [[sg.Text(text="Unable to obtain pressure", key="-PRESSURE-")]])],
          [sg.Text(text="Unable to obtain time", key="-TIME-")],
          [sg.Button("Push"), sg.Button("Pull"), sg.Button("Dive")],
          [sg.StatusBar(text="Disconnected", key="-STAT-", text_color="#F55D30")],
          [sg.StatusBar(text="Currently no message", key="-MSG-", text_color="#d3d3d3")],
          [sg.StatusBar(text="Not connected to WiFi", key="-WIFI-", text_color="#F55D30")],
          [sg.StatusBar(text="The float is not conducting any actions", key="-ACT-", text_color="#d3d3d3")],
          [sg.Input(default_text="SSID", key="-SSID-")],
          [sg.Input(default_text="Password", key="-PWD-")],
          [sg.Button("Connect")]
          ]
window = sg.Window("Float Control", layout, element_justification='center')
window.read()
class floatcontrol():

    def __init__(self, address, port):
        self.is_resetting = True
        self.addr = address
        self.port = port
        self.x = threading.Thread(target=self.bluetooth_init)
        self.x.start()
        self.event, self.values = window.read()

    def bluetooth_init(self):
        while self.is_resetting:
            try:
                print("hi")
                self.bt_socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
                self.bt_socket.connect((self.addr, self.port))
                self.bt_socket.setblocking(0)
                window["-STAT-"].update("Connected", text_color="#00ff00")
                self.is_resetting = False
            except:
                self.bt_socket.close()

    def update(self):
        try:
            print('update lol!')
            if self.is_resetting:
                return
            ready = select.select([self.bt_socket], [], [], 3)
            if ready[0]:
                response = self.bt_socket.recv(100).decode("UTF-8").strip()
                if response != "":
                    repo = response.split("\n")
                    window["-TIME-"].update(repo[0])
                    window["-DEPTH-"].update(repo[1])
                    psi = float(repo[1]) * 1000 * 9.81
                    window["-PRESSURE-"].update(psi)
        except:
            window["-TIME-"].update("Unable to receive time", text_color="#F55D30")
            window["-DEPTH-"].update("Unable to receive depth", text_color="#F55D30")
            window["-PRESSURE-"].update("Unable  to calculate pressure", text_color="#F55D30")
            window["-STAT-"].update("Disconnected", text_color="#F55D30")
            self.is_resetting = True
            self.bt_socket.close()
            self.x = threading.Thread(target=self.bluetooth_init())
            self.x.start()

    def msg(self, cmd):
        try:
            self.bt_socket.send(bytes(cmd, 'UTF-8'))
        except:
            window["-MSG-"].update("Unable to send command", text_color="#b3b300")

    def diver(self):
        if self.event == "Push":
            self.msg("push")
        if self.event == "Pull":
            self.msg("pull")
        if self.event == "Dive":
            self.msg("dive")
        if self.event == "Connect":
            command = "wifi^{}^{}".format(self.values["-SSID-"][0], self.values["-PWD-"][0])
            self.msg(command)

if __name__ == "__main__":
    address = "EC:64:C9:5E:CF:3E"
    port = 1
    while True:
        boat = floatcontrol(address, port)

    window.close()
