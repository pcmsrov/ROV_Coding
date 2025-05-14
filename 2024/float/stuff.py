import sys, socket, time, select, threading

from PyQt6 import QtWidgets, QtGui, QtCore

class FloatControlUI(QtWidgets.QMainWindow):
    def __init__(self, BT_addr, BT_port):
        super(QtWidgets.QMainWindow, self).__init__()
        # 視窗初始化
        self.setWindowTitle('Float Control')
        self.resize(400, 200)
        self.setUpdatesEnabled(True)

        # 主排板初始化
        self.pageLayout = QtWidgets.QVBoxLayout()
        widget = QtWidgets.QWidget()
        widget.setLayout(self.pageLayout)
        self.setCentralWidget(widget)

        # UI初始化
        self.connection()
        self.wifi_connection()
        self.response()
        self.response = ""
        self.depth()
        self.depth = ""
        self.action()
        self.action = ""
        self.cmd_btn()
        self.wifi()

        # 初始化用於UI更新的計時器
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)

        # 藍牙初始化
        self.is_resetting = True
        self.BT_addr = BT_addr
        self.BT_port = BT_port
        self.x = threading.Thread(target=self.bluetooth_init)
        self.x.start()

        # 啟動每秒一次(1000ms)的計時器
        self.timer.start(1000)

    def bluetooth_init(self):
        # 重復直到成功連線
        while self.is_resetting:
            try:
                # 嘗試連接到藍牙裝置
                self.BT_socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
                self.BT_socket.connect((self.BT_addr, self.BT_port))
                self.BT_socket.setblocking(0)
                # 成功連接後改變UI（若連接失敗將跳到except）
                self.connection_status_label.setText("Connected")
                self.connection_status_label.setStyleSheet('''
                    color:green;
                    font-size:20px;
                    font-weight:bold;
                ''')
                self.is_resetting = False
            except:
                # 失敗時重置socket連線
                self.BT_socket.close()

    def update(self):
        try:
            # 重連藍牙時將不會更新UI
            if self.is_resetting:
                return
            # 等待直到獲取到回應
            ready = select.select([self.BT_socket], [], [], 3)
            if ready[0]:
                # 讀取回應（若連線失敗將跳到except）
                response = self.BT_socket.recv(100).decode("UTF-8").strip()

                if response != '':
                    # 有時會收到兩個相同回應，因此只要第一個
                    self.response = response.split("\n")[0]
                    print(self.response)
                    # 更新UI
                    self.response_label.setText(self.response)
                    # if len(self.response) >= 2:
                    #     self.depth_response_label.setText(self.response[1])
        except:
            # 改變UI
            self.response_label.setText("Failed to obtain time")
            self.connection_status_label.setText("Disconnected")
            self.connection_status_label.setStyleSheet('''
                color:red;
                font-size:20px;
                font-weight:bold;
            ''')
            # 重置藍牙Socket
            self.is_resetting = True
            self.BT_socket.close()
            # 將重置藍牙的任務交到self.x線程執行（否則會導致UI卡住）
            self.x = threading.Thread(target=self.bluetooth_init)
            self.x.start()

    def sendCommand(self, cmd, type):
        try:
            # 傳送文字訊息到 float( 只能是byte )，傳送失敗將跳到execpt
            self.BT_socket.send(bytes(cmd, 'UTF-8'))
        except:
            # 失敗後改變UI
            if type == "wifi":
                self.wifi_connection_status_label.setText("Failed to connect WiFi")

    def connection(self):
        # 以下為UI部分
        connection_label = QtWidgets.QLabel('Bluetooth Connection:', self)
        connection_label.setStyleSheet('''
            font-size:20px; 
            font-weight:bold;
        ''')
        self.connection_status_label = QtWidgets.QLabel('Disconnected', self)
        self.connection_status_label.setStyleSheet('''
            color:red; 
            font-size:20px; 
            font-weight:bold;
        ''')

        # 將橫向排版加入到主排版
        connectionLayout = QtWidgets.QHBoxLayout()
        connectionLayout.addWidget(connection_label)
        connectionLayout.addWidget(self.connection_status_label)
        connectionLayout.addStretch()
        self.pageLayout.addLayout(connectionLayout)
    def wifi_connection(self):

        # 以下為UI部分
        wifi_connection_label = QtWidgets.QLabel('Wifi Connection:', self)
        wifi_connection_label.setStyleSheet('''
            font-size:20px; 
            font-weight:bold;
        ''')
        self.wifi_connection_status_label = QtWidgets.QLabel('Disconnected', self)
        self.wifi_connection_status_label.setStyleSheet('''
            color:red; 
            font-size:20px; 
            font-weight:bold;
        ''')

        # 將橫向排版加入到主排版
        connectionLayout = QtWidgets.QHBoxLayout()
        connectionLayout.addWidget(wifi_connection_label)
        connectionLayout.addWidget(self.wifi_connection_status_label)
        connectionLayout.addStretch()
        self.pageLayout.addLayout(connectionLayout)
    def response(self):
        # 以下為UI部分
        self.response_label = QtWidgets.QLabel("Failed to obtain time", self)
        self.response_label.setFixedHeight(60)
        self.response_label.setStyleSheet('''
            border: 2px dashed #6f6f6f;
            font-size:22px;
            font-weight:bold;
        ''')
        # 將元件加入到主排版
        self.pageLayout.addWidget(self.response_label)

    def depth(self):
        # 以下為UI部分
        self.depth_response_label = QtWidgets.QLabel("Failed to obtain depth and pressure ", self)
        self.depth_response_label.setFixedHeight(60)
        self.depth_response_label.setStyleSheet('''
            border: 2px dashed #6f6f6f;
            font-size:22px;
            font-weight:bold;
        ''')
        # 將元件加入到主排版
        self.pageLayout.addWidget(self.depth_response_label)

    def action(self):
        self.action_response_label = QtWidgets.QLabel("Actions not being conducted", self)
        self.action_response_label.setFixedHeight(60)
        self.action_response_label.setStyleSheet('''
            border: 2px dashed #6f6f6f;
            font-size:22px;
            font-weight:bold;
        ''')
        self.pageLayout.addWidget(self.action_response_label)
    def cmd_btn(self):
        # 以下為UI部分
        push_btn = QtWidgets.QPushButton('Push', self)
        pull_btn = QtWidgets.QPushButton('Pull', self)
        dive_btn = QtWidgets.QPushButton('Start Diving!', self)
        push_btn.setFixedHeight(60)
        pull_btn.setFixedHeight(60)
        dive_btn.setFixedHeight(60)

        # 按鍵被點擊後傳送指令到float，lambda使函數作為connect()的參數而非運行
        push_btn.clicked.connect(lambda: self.sendCommand("push"))
        pull_btn.clicked.connect(lambda: self.sendCommand("pull"))
        dive_btn.clicked.connect(lambda: self.sendCommand("dive"))

        # 將橫向排版加入到主排版
        cmdBtnLayout = QtWidgets.QHBoxLayout()
        cmdBtnLayout.addWidget(push_btn)
        cmdBtnLayout.addWidget(pull_btn)
        cmdBtnLayout.addWidget(dive_btn)
        self.pageLayout.addLayout(cmdBtnLayout)

    def wifi(self):
        # 以下為UI部分
        ssid_label = QtWidgets.QLabel('WiFi SSID:', self)
        ssid_label.setStyleSheet('''
            font-size:13px;
            font-weight:bold;
        ''')
        ssid_input = QtWidgets.QLineEdit(self)
        password_label = QtWidgets.QLabel('Password:', self)
        password_label.setStyleSheet('''
            font-size:13px;
            font-weight:bold;
        ''')
        password_input = QtWidgets.QLineEdit(self)
        connect_btn = QtWidgets.QPushButton('Connect', self)

        # 按鍵被點擊後運行sendCommand()，lambda使函數作為connect()的參數而非運行
        command = "wifi^{}^{}".format(ssid_input.text(), password_input.text())
        connect_btn.clicked.connect(lambda: self.sendCommand(command, "wifi"))

        # 將橫向排版加入到主排版
        wifiLayout = QtWidgets.QHBoxLayout()
        wifiLayout.addWidget(ssid_label)
        wifiLayout.addWidget(ssid_input)
        wifiLayout.addWidget(password_label)
        wifiLayout.addWidget(password_input)
        wifiLayout.addWidget(connect_btn)
        self.pageLayout.addLayout(wifiLayout)


if __name__ == '__main__':
    # 藍牙裝置設定
    BT_addr = "EC:64:C9:5E:CF:3E"
    BT_port = 1  # 預設為1，不用改

    # UI設定
    app = QtWidgets.QApplication(sys.argv)
    ui = FloatControlUI(BT_addr=BT_addr, BT_port=BT_port)
    ui.show()

    # 執行程式（開啟"Float Control"視窗）
    sys.exit(app.exec())
