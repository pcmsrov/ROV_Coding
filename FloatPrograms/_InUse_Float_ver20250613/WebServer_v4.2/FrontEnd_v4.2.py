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
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import re

#to Do
#send debug mode ture false
#UI, 3:7
#data, write CSV

#---------- Change Here ----------
#in get paramemters wrong, change it, and restart the front end program 

#float motor time adjuest, in miliseconds
companyID = "RN008"

#time unit, second
descendTime = 20
ascendTime = 30
waitTime = 30

debugMode = False  # 设置为true时启用详细调试信息
useTimer = False
#---------- Change Here ----------



class TimeDataClient(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MATE Float, Mosasaurus PCMS")
        self.setGeometry(100, 100, 1000, 600)
        
        # Set default font size
        default_font = self.font()
        default_font.setPointSize(12)
        self.setFont(default_font)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        
        # 创建分割器
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
        
        # Left control panel
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)  # 添加内边距
        
        # Create labels
        self.status_label = QLabel("Status: Not Connected")
        self.status_label.setFont(default_font)
        left_layout.addWidget(self.status_label)
        
        # Create parameter input form
        param_form = QFormLayout()
        
        # Company ID input
        self.company_id_input = QLineEdit(companyID)
        self.company_id_input.setFont(default_font)
        param_form.addRow("Company ID:", self.company_id_input)
        
        # Descend Time input (in seconds)
        self.descend_time_input = QSpinBox()
        self.descend_time_input.setRange(1, 300)
        self.descend_time_input.setValue(descendTime)
        self.descend_time_input.setSuffix(" sec")
        self.descend_time_input.setFont(default_font)
        param_form.addRow("DescendTime:", self.descend_time_input)
        
        # Wait Time input (in seconds)
        self.wait_time_input = QSpinBox()
        self.wait_time_input.setRange(1, 300)
        self.wait_time_input.setValue(waitTime)
        self.wait_time_input.setSuffix(" sec")
        self.wait_time_input.setFont(default_font)
        param_form.addRow("WaitTime:", self.wait_time_input)
        
        # Ascend Time input (in seconds)
        self.ascend_time_input = QSpinBox()
        self.ascend_time_input.setRange(1, 300)
        self.ascend_time_input.setValue(ascendTime)
        self.ascend_time_input.setSuffix(" sec")
        self.ascend_time_input.setFont(default_font)
        param_form.addRow("AscendTime:", self.ascend_time_input)
        
        # Create horizontal layout for checkboxes
        checkbox_layout = QHBoxLayout()
        
        # Use Timer toggle (left)
        self.use_timer_checkbox = QCheckBox("Use Timer")
        self.use_timer_checkbox.setChecked(useTimer)
        self.use_timer_checkbox.stateChanged.connect(self.on_use_timer_changed)
        self.use_timer_checkbox.setFont(default_font)
        checkbox_layout.addWidget(self.use_timer_checkbox)
        
        # Debug Mode toggle (right)
        self.debugMode_checkbox = QCheckBox("Debug Mode")
        self.debugMode_checkbox.setChecked(debugMode)
        self.debugMode_checkbox.stateChanged.connect(self.on_debugMode_changed)
        self.debugMode_checkbox.setFont(default_font)
        checkbox_layout.addWidget(self.debugMode_checkbox)
        
        # Add checkbox layout to form
        param_form.addRow("", checkbox_layout)
        
        # Add form to left layout
        left_layout.addLayout(param_form)
        
        # Create single button for both initial connection and parameter update
        self.connection_button = QPushButton("Connect/Update Parameters")
        self.connection_button.clicked.connect(self.handle_connection)
        self.connection_button.setFont(default_font)
        left_layout.addWidget(self.connection_button)
        
        # Create buttons
        self.fetch_button = QPushButton("Fetch Data")
        self.fetch_button.clicked.connect(self.fetch_data)
        self.fetch_button.setFont(default_font)
        left_layout.addWidget(self.fetch_button)
        
        # Add Go button and timer in horizontal layout
        go_layout = QHBoxLayout()
        self.go_button = QPushButton("Start Vertical Profiling")
        self.go_button.clicked.connect(self.start_motor)
        self.go_button.setFont(default_font)
        go_layout.addWidget(self.go_button)
        
        # Add timer label
        self.timer_label = QLabel("00:00:00")
        self.timer_label.setStyleSheet("font-size: 12px; font-weight: bold;")
        self.timer_label.setFont(default_font)
        go_layout.addWidget(self.timer_label)
        left_layout.addLayout(go_layout)
        
        # Add test and force stop buttons
        test_buttons_layout = QVBoxLayout()  # 改为垂直布局
        
        # 第一行：Test Pull, Test Push 和 Force Stop
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
        
        # 第二行：Pull All 和 Push All
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
        
        # Create text display area
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setFont(default_font)
        left_layout.addWidget(self.text_display)
        
        # Right chart area
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)  # 添加内边距
        
        # Create matplotlib chart
        self.figure = Figure(figsize=(6, 4))
        self.canvas = FigureCanvas(self.figure)
        right_layout.addWidget(self.canvas)
        
        # Add navigation toolbar for zooming and panning
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
        
        # Server address
        self.server_url = "http://192.168.4.1"  # Default ESP32 AP IP address
        
        # Create fixed-size FIFO queue, maximum 180 elements
        self.max_size = 180
        self.time_data_queue = deque(maxlen=self.max_size)
        
        # Store depth data
        self.depth_data = []
        self.time_data = []
        
        # Connection status flag
        self.is_connected = False
        
        # Initialize timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.elapsed_time = QTime(0, 0)
        self.is_timer_running = False
        
    def extract_depth(self, data_str):
        """从数据字符串中提取深度值"""
        match = re.search(r'(\d+\.\d+)\s+meters', data_str)
        if match:
            return float(match.group(1))
        return None
        
    def extract_time(self, data_str):
        """从数据字符串中提取时间值"""
        match = re.search(r'(\d{2}:\d{2}:\d{2})\s+UTC', data_str)
        if match:
            return match.group(1)
        return None
        
    def plot_depth_data(self):
        """Plot depth data chart"""
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
        """Handle debug mode checkbox state change"""
        global debugMode
        debugMode = bool(state)
        if self.is_connected:
            self.handle_connection()  # Automatically update parameters when debug mode changes
            
    def on_use_timer_changed(self, state):
        """Handle use timer checkbox state change"""
        if self.is_connected:
            self.handle_connection()  # Automatically update parameters when use timer changes
            
    def handle_connection(self):
        """Handle both initial connection and parameter update"""
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
        """Start motor control"""
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
        """Update timer display"""
        self.elapsed_time = self.elapsed_time.addSecs(1)
        self.timer_label.setText(self.elapsed_time.toString("hh:mm:ss"))

    def test_pull(self):
        """Test pull function"""
        try:
            response = requests.post(f"{self.server_url}/motor/test/pull")
            if response.status_code == 200:
                self.text_display.append("Test pull started")
            else:
                self.text_display.append(f"Test pull failed: {response.text}")
        except requests.exceptions.RequestException:
            self.text_display.append("Unable to connect to server")

    def test_push(self):
        """Test push function"""
        try:
            response = requests.post(f"{self.server_url}/motor/test/push")
            if response.status_code == 200:
                self.text_display.append("Test push started")
            else:
                self.text_display.append(f"Test push failed: {response.text}")
        except requests.exceptions.RequestException:
            self.text_display.append("Unable to connect to server")

    def test_pull_all(self):
        """Test pull all function"""
        try:
            response = requests.post(f"{self.server_url}/motor/test/pullall")
            if response.status_code == 200:
                self.text_display.append("Test pull all started")
            else:
                self.text_display.append(f"Test pull all failed: {response.text}")
        except requests.exceptions.RequestException:
            self.text_display.append("Unable to connect to server")

    def test_push_all(self):
        """Test push all function"""
        try:
            response = requests.post(f"{self.server_url}/motor/test/pushall")
            if response.status_code == 200:
                self.text_display.append("Test push all started")
            else:
                self.text_display.append(f"Test push all failed: {response.text}")
        except requests.exceptions.RequestException:
            self.text_display.append("Unable to connect to server")

    def force_stop(self):
        """Force stop function"""
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