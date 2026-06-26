"""
MATE Float / Mosasaurus PCMS - PC FrontEnd (PyQt5)

這支程式提供一個桌面 GUI，用來連線 ESP32（AP 模式下通常是 `192.168.4.1`），並完成：
- **初始化/更新參數**：POST `/init`
- **抓取資料**：GET `/data`（回傳字串陣列，內含 UTC 時間與深度資訊）
- **啟動/測試/強制停止馬達**：POST `/motor/...`
- **繪圖**：將解析出的 Depth vs Time 以 Matplotlib 顯示

注意：本檔以「加註解」為主，避免改動任何既有行為。
"""

import sys
import requests
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QTextEdit, QLabel, 
                            QLineEdit, QFormLayout, QSpinBox, QCheckBox,
                            QSplitter)   
from PyQt5.QtCore import QTimer, QTime
from datetime import datetime
from collections import deque
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvasz
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import re

# TODO（待辦項目）
# - 伺服端/協定：確認 debug mode / use timer 參數命名是否與 ESP32 端一致
# - UI：版面與比例（原註記 3:7）
# - 資料：將抓到的資料寫入 CSV（目前僅顯示與繪圖）

# ---------- 可調參數區（改完需重啟前端程式） ----------
# 這裡的預設值會用來初始化 UI 表單（使用者也可在介面中改）
# 註：UI 以「秒」輸入，送到 ESP32 時會轉成「毫秒」
companyID = "RN19"  # 公司/裝置識別碼（會送到 `/init`）

#time unit, second
descendTime = 20  # 下潛時間（秒）
ascendTime = 30   # 上升時間（秒）
waitTime = 120    # 底部等待時間（秒）

debugMode = False  # True 時請伺服端輸出較多除錯資訊（由 `/init` 傳入）
useTimer = False   # True 時啟用前端計時器顯示（由 `/init` 傳入）
# ---------- 可調參數區結束 ----------



class TimeDataClient(QMainWindow):
    """
    主視窗：控制面板 + 資料顯示 + 深度曲線圖。

    左側：連線/更新參數、抓取資料、馬達控制、文字輸出。
    右側：Matplotlib 圖表（Depth vs Time），附帶縮放/平移工具列。
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MATE Float, Mosasaurus PCMS")
        self.setGeometry(100, 100, 1000, 600)
        
        # Set default font size
        default_font = self.font()
        default_font.setPointSize(12)
        self.setFont(default_font)
        
        # 建立中央 widget 與主布局（左右兩欄）
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        
        # 分割器：允許使用者拖拉調整左右面板比例
        splitter = QSplitter()
        splitter.setHandleWidth(5)  # 设置分割线宽度
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #cccccc;
            }
            QSplitter::handle:hover {
                background-color: #999999;
            }
        """)
        
        # 左側控制面板：參數、按鈕、文字輸出
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)  # 添加内边距
        
        # 狀態列：連線/資料點數/馬達狀態
        self.status_label = QLabel("Status: Not Connected")
        self.status_label.setFont(default_font)
        left_layout.addWidget(self.status_label)
        
        # 參數輸入表單（秒為單位，送出時會轉換成毫秒）
        param_form = QFormLayout()
        
        # Company ID：識別用字串
        self.company_id_input = QLineEdit(companyID)
        self.company_id_input.setFont(default_font)
        param_form.addRow("Company ID:", self.company_id_input)
        
        # Descend Time：下潛時間（秒）
        self.descend_time_input = QSpinBox()
        self.descend_time_input.setRange(1, 300)
        self.descend_time_input.setValue(descendTime)
        self.descend_time_input.setSuffix(" sec")
        self.descend_time_input.setFont(default_font)
        param_form.addRow("DescendTime:", self.descend_time_input)
        
        # Wait Time：等待時間（秒）
        self.wait_time_input = QSpinBox()
        self.wait_time_input.setRange(1, 300)
        self.wait_time_input.setValue(waitTime)
        self.wait_time_input.setSuffix(" sec")
        self.wait_time_input.setFont(default_font)
        param_form.addRow("WaitTime:", self.wait_time_input)
        
        # Ascend Time：上升時間（秒）
        self.ascend_time_input = QSpinBox()
        self.ascend_time_input.setRange(1, 300)
        self.ascend_time_input.setValue(ascendTime)
        self.ascend_time_input.setSuffix(" sec")
        self.ascend_time_input.setFont(default_font)
        param_form.addRow("AscendTime:", self.ascend_time_input)
        
        # 勾選項：Use Timer / Debug Mode
        checkbox_layout = QHBoxLayout()
        
        # Use Timer：前端是否顯示計時器（並同步送到伺服端）
        self.use_timer_checkbox = QCheckBox("Use Timer")
        self.use_timer_checkbox.setChecked(useTimer)
        self.use_timer_checkbox.stateChanged.connect(self.on_use_timer_changed)
        self.use_timer_checkbox.setFont(default_font)
        checkbox_layout.addWidget(self.use_timer_checkbox)
        
        # Debug Mode：伺服端是否啟用較多除錯輸出（並同步送到伺服端）
        self.debugMode_checkbox = QCheckBox("Debug Mode")
        self.debugMode_checkbox.setChecked(debugMode)
        self.debugMode_checkbox.stateChanged.connect(self.on_debugMode_changed)
        self.debugMode_checkbox.setFont(default_font)
        checkbox_layout.addWidget(self.debugMode_checkbox)
        
        # Add checkbox layout to form
        param_form.addRow("", checkbox_layout)
        
        # Add form to left layout
        left_layout.addLayout(param_form)
        
        # 單一按鈕：首次連線與後續更新參數都走同一個 `/init`
        self.connection_button = QPushButton("Connect/Update Parameters")
        self.connection_button.clicked.connect(self.handle_connection)
        self.connection_button.setFont(default_font)
        left_layout.addWidget(self.connection_button)
        
        # 抓取資料：呼叫 `/data` 並更新文字與圖表
        self.fetch_button = QPushButton("Fetch Data")
        self.fetch_button.clicked.connect(self.fetch_data)
        self.fetch_button.setFont(default_font)
        left_layout.addWidget(self.fetch_button)
        
        # 啟動垂直剖面（馬達流程）與計時器顯示
        go_layout = QHBoxLayout()
        self.go_button = QPushButton("Start Vertical Profiling")
        self.go_button.clicked.connect(self.start_motor)
        self.go_button.setFont(default_font)
        go_layout.addWidget(self.go_button)
        
        # 計時器顯示（若伺服端流程啟動，前端每秒更新一次）
        self.timer_label = QLabel("00:00:00")
        self.timer_label.setStyleSheet("font-size: 12px; font-weight: bold;")
        self.timer_label.setFont(default_font)
        go_layout.addWidget(self.timer_label)
        left_layout.addLayout(go_layout)
        
        # 馬達測試與強制停止（緊急停止）
        test_buttons_layout = QVBoxLayout()  # 改为垂直布局
        
        # 第一行：Pull All / Push All / Force Stop
        first_row_layout = QHBoxLayout()
        
        self.test_pull_all_button = QPushButton("Pull All")
        self.test_pull_all_button.clicked.connect(self.test_pull_all)
        self.test_pull_all_button.setFont(default_font)
        first_row_layout.addWidget(self.test_pull_all_button)
        
        self.test_push_all_button = QPushButton("Push All")
        self.test_push_all_button.clicked.connect(self.test_push_all)
        self.test_push_all_button.setFont(default_font)
        first_row_layout.addWidget(self.test_push_all_button)
        
        self.force_stop_button = QPushButton("Force Stop")
        self.force_stop_button.clicked.connect(self.force_stop)
        self.force_stop_button.setStyleSheet("""
            QPushButton {
                background-color: #ff4444;
                color: white;
                border: none;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #ff6666;
            }
            QPushButton:pressed {
                background-color: #cc0000;
            }
        """)
        self.force_stop_button.setFont(default_font)
        first_row_layout.addWidget(self.force_stop_button)
        
        # 第二行：Test Pull / Test Push
        second_row_layout = QHBoxLayout()
        
        self.test_pull_button = QPushButton("Test Pull")
        self.test_pull_button.clicked.connect(self.test_pull)
        self.test_pull_button.setFont(default_font)
        second_row_layout.addWidget(self.test_pull_button)
        
        self.test_push_button = QPushButton("Test Push")
        self.test_push_button.clicked.connect(self.test_push)
        self.test_push_button.setFont(default_font)
        second_row_layout.addWidget(self.test_push_button)
        
        # 添加两行布局到主测试按钮布局
        test_buttons_layout.addLayout(first_row_layout)
        test_buttons_layout.addLayout(second_row_layout)
        
        left_layout.addLayout(test_buttons_layout)
        
        # 文字輸出區：顯示回傳資料與狀態訊息
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setFont(default_font)
        left_layout.addWidget(self.text_display)
        
        # 右側圖表區：深度曲線圖 + 工具列
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)  # 添加内边距
        
        # Matplotlib：使用 Qt canvas 內嵌顯示
        self.figure = Figure(figsize=(6, 4))
        self.canvas = FigureCanvasz(self.figure)
        right_layout.addWidget(self.canvas)
        
        # 工具列：縮放/平移/存圖等
        self.toolbar = NavigationToolbar(self.canvas, right_panel)
        right_layout.addWidget(self.toolbar)
        
        # 将面板添加到分割器
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        
        # 设置初始大小比例（40:60）
        splitter.setSizes([400, 600])
        
        # 将分割器添加到主布局
        main_layout.addWidget(splitter)
        
        # 设置分割器可以拉伸
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        # 伺服端位址（ESP32 AP 模式的預設 IP）
        self.server_url = "http://192.168.4.1"  # Default ESP32 AP IP address
        
        # FIFO 佇列：最多保留 180 筆原始字串資料（用於顯示/狀態）
        self.max_size = 180
        self.time_data_queue = deque(maxlen=self.max_size)
        
        # 繪圖資料：從原始字串解析出 Depth 與 UTC Time（用於 plot）
        self.depth_data = []
        self.time_data = []
        
        # 連線狀態：用來區分「首次連線」與「更新參數」的 UI 呈現
        self.is_connected = False
        
        # 前端計時器：馬達流程開始後每秒更新顯示（不影響伺服端流程）
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.elapsed_time = QTime(0, 0)
        self.is_timer_running = False
        
    def extract_depth(self, data_str):
        """
        從伺服端回傳的單筆字串中解析深度（公尺）。

        預期格式範例：`"12:34:56 UTC ... 3.21 meters ..."`
        回傳：
        - float：深度（meters）
        - None：找不到符合格式的深度
        """
        match = re.search(r'(\d+\.\d+)\s+meters', data_str)
        if match:
            return float(match.group(1))
        return None
        
    def extract_time(self, data_str):
        """
        從伺服端回傳的單筆字串中解析 UTC 時間（hh:mm:ss）。

        預期格式範例：`"12:34:56 UTC ..."`
        回傳：
        - str：`"HH:MM:SS"`
        - None：找不到符合格式的時間
        """
        match = re.search(r'(\d{2}:\d{2}:\d{2})\s+UTC', data_str)
        if match:
            return match.group(1)
        return None
        
    def plot_depth_data(self):
        """
        繪製 Depth vs Time 圖表。

        - X 軸：UTC 時間字串（由 `extract_time` 取得）
        - Y 軸：深度（公尺），並反轉 Y 軸使「越深」往下
        """
        if not self.depth_data:
            self.text_display.append("No depth data available")
            return
            
        # Clear old chart
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        # Plot depth data
        ax.plot(self.time_data, self.depth_data, 'b-', linewidth=2)
        
        # Set chart title and labels
        ax.set_title('Depth vs Time')
        ax.set_xlabel('Time (UTC)')
        ax.set_ylabel('Depth (meters)')
        
        # Invert y-axis since depth increases downward
        ax.invert_yaxis()
        
        # Add grid
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # Rotate x-axis labels to prevent overlap
        plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
        
        # Adjust layout to prevent label cutoff
        self.figure.tight_layout()
        
        # Set initial view to show all data
        ax.set_xlim(0, len(self.time_data))
        
        # Refresh canvas
        self.canvas.draw()
        
    def on_debugMode_changed(self, state):
        """Debug Mode 勾選狀態改變時，同步更新 `/init` 參數。"""
        global debugMode
        debugMode = bool(state)
        if self.is_connected:
            self.handle_connection()  # Automatically update parameters when debug mode changes
            
    def on_use_timer_changed(self, state):
        """Use Timer 勾選狀態改變時，同步更新 `/init` 參數。"""
        if self.is_connected:
            self.handle_connection()  # Automatically update parameters when use timer changes
            
    def handle_connection(self):
        """
        首次連線 / 更新參數。

        送出 POST `/init`，內容包含：
        - `utc_time`：目前 UTC 時間（HH:MM:SS）
        - `descend_time` / `wait_time` / `ascend_time`：毫秒
        - `debug_mode` / `use_timer` / `company_id`
        """
        try:
            # Get current UTC time
            utc_time = datetime.utcnow().strftime("%H:%M:%S")
            
            # Get values from input fields
            company_id = self.company_id_input.text()
            descend_time = self.descend_time_input.value() * 1000  # Convert to milliseconds
            wait_time = self.wait_time_input.value() * 1000
            ascend_time = self.ascend_time_input.value() * 1000
            
            # Prepare data to send
            data = {
                "utc_time": utc_time,
                "descend_time": descend_time,
                "ascend_time": ascend_time,
                "wait_time": wait_time,
                "debug_mode": self.debugMode_checkbox.isChecked(),
                "use_timer": self.use_timer_checkbox.isChecked(),
                "company_id": company_id
            }
            
            # Send request
            response = requests.post(f"{self.server_url}/init", json=data)
            
            if response.status_code == 200:
                if not self.is_connected:
                    self.status_label.setText("Status: Initial Connection Successful")
                    self.is_connected = True
                    self.text_display.append("=== Initial Connection Information ===")
                else:
                    self.status_label.setText("Status: Parameters Updated Successfully")
                    self.text_display.append("=== Parameters Updated ===")
                
                self.text_display.append(f"Company ID: {company_id}")
                self.text_display.append(f"UTC Time: {utc_time}")
                self.text_display.append(f"Descend Time: {descend_time}ms")
                self.text_display.append(f"Ascend Time: {ascend_time}ms")
                self.text_display.append(f"Wait Time: {wait_time}ms")
                self.text_display.append(f"Debug Mode: {'Enabled' if self.debugMode_checkbox.isChecked() else 'Disabled'}")
                self.text_display.append(f"Use Timer: {'Enabled' if self.use_timer_checkbox.isChecked() else 'Disabled'}")
                self.text_display.append("====================\n")
            else:
                self.status_label.setText("Status: Connection Failed")
                self.text_display.append("Connection failed, please try again.")
                self.is_connected = False
                
        except requests.exceptions.RequestException:
            self.status_label.setText("Status: Connection Failed")
            self.text_display.append("Unable to connect to server, please ensure ESP32 is running in AP mode.")
            self.is_connected = False
            
    def fetch_data(self):
        """
        從伺服端抓取資料並更新 UI。

        - GET `/data` 取得字串陣列
        - 逐筆加入 FIFO 佇列與文字顯示區
        - 嘗試解析 depth/time，成功則追加到繪圖序列並重畫
        """
        try:
            # Get data
            response = requests.get(f"{self.server_url}/data")
            if response.status_code == 200:
                data = response.json()
                
                if data:  # Only display if there is data
                    # Add new data to FIFO queue
                    for time_str in data:
                        if time_str:  # Ensure not empty string
                            self.time_data_queue.append(time_str)
                            # Directly add new data to display area
                            self.text_display.append(time_str)
                            
                            # Extract depth and time data
                            depth = self.extract_depth(time_str)
                            time = self.extract_time(time_str)
                            if depth is not None and time is not None:
                                self.depth_data.append(depth)
                                self.time_data.append(time)
                                
                                # Update chart if we have new data
                                if len(self.depth_data) > 1:
                                    self.plot_depth_data()
                    
                    # Update status label
                    self.status_label.setText(f"Status: Connected (Data Points: {len(self.time_data_queue)})")
                
                self.status_label.setText("Status: Connected")
            else:
                self.status_label.setText("Status: Server Response Error")
        except requests.exceptions.RequestException:
            self.status_label.setText("Status: Connection Failed")
            self.text_display.append("Unable to connect to server, please ensure ESP32 is running in AP mode.")

    def start_motor(self):
        """
        啟動垂直剖面（馬達控制）流程。

        - POST `/motor/start`
        - 成功後啟動前端計時器（每秒更新）
        """
        try:
            self.text_display.append("Attempting to start motor control...")
            response = requests.post(f"{self.server_url}/motor/start")
            if response.status_code == 200:
                self.text_display.append("Motor control started successfully")
                self.status_label.setText("Status: Motor Control Running")
                # Start timer
                self.elapsed_time = QTime(0, 0)
                self.timer.start(1000)  # Update every second
                self.is_timer_running = True
            else:
                self.text_display.append(f"Start failed: {response.text}")
                self.text_display.append(f"Status code: {response.status_code}")
                self.status_label.setText("Status: Motor Control Start Failed")
        except requests.exceptions.RequestException as e:
            self.text_display.append(f"Connection error: {str(e)}")
            self.text_display.append("Unable to connect to server, please ensure ESP32 is running in AP mode.")
            self.status_label.setText("Status: Connection Failed")

    def update_timer(self):
        """每秒更新一次前端計時器顯示。"""
        self.elapsed_time = self.elapsed_time.addSecs(1)
        self.timer_label.setText(self.elapsed_time.toString("hh:mm:ss"))

    def test_pull(self):
        """馬達測試：Pull（單次）。POST `/motor/test/pull`。"""
        try:
            response = requests.post(f"{self.server_url}/motor/test/pull")
            if response.status_code == 200:
                self.text_display.append("Test pull started")
            else:
                self.text_display.append(f"Test pull failed: {response.text}")
        except requests.exceptions.RequestException:
            self.text_display.append("Unable to connect to server")

    def test_push(self):
        """馬達測試：Push（單次）。POST `/motor/test/push`。"""
        try:
            response = requests.post(f"{self.server_url}/motor/test/push")
            if response.status_code == 200:
                self.text_display.append("Test push started")
            else:
                self.text_display.append(f"Test push failed: {response.text}")
        except requests.exceptions.RequestException:
            self.text_display.append("Unable to connect to server")

    def test_pull_all(self):
        """馬達測試：Pull All。POST `/motor/test/pullall`。"""
        try:
            response = requests.post(f"{self.server_url}/motor/test/pullall")
            if response.status_code == 200:
                self.text_display.append("Test pull all started")
            else:
                self.text_display.append(f"Test pull all failed: {response.text}")
        except requests.exceptions.RequestException:
            self.text_display.append("Unable to connect to server")

    def test_push_all(self):
        """馬達測試：Push All。POST `/motor/test/pushall`。"""
        try:
            response = requests.post(f"{self.server_url}/motor/test/pushall")
            if response.status_code == 200:
                self.text_display.append("Test push all started")
            else:
                self.text_display.append(f"Test push all failed: {response.text}")
        except requests.exceptions.RequestException:
            self.text_display.append("Unable to connect to server")

    def force_stop(self):
        """
        緊急停止：強制停止馬達流程。

        - POST `/motor/force/stop`
        - 若前端計時器正在跑，會同步停止（避免誤導）
        """
        try:
            response = requests.post(f"{self.server_url}/motor/force/stop")
            if response.status_code == 200:
                self.text_display.append("Force stop command sent")
                # Stop timer
                if self.is_timer_running:
                    self.timer.stop()
                    self.is_timer_running = False
            else:
                self.text_display.append(f"Force stop failed: {response.text}")
        except requests.exceptions.RequestException:
            self.text_display.append("Unable to connect to server")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TimeDataClient()
    window.show()
    sys.exit(app.exec_()) 