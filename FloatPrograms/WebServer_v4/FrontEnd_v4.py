import sys
import requests
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QLabel
from PyQt5.QtCore import QTimer
from datetime import datetime
from collections import deque
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import re

#to Do
#send debug mode ture false
#UI, 3:7
#data, write CSV

#---------- Change Here ----------
#in get paramemters wrong, change it, and restart the front end program 

#float motor time adjuest, in miliseconds
companyID = "RN99"
descendTime = 8300
ascendTime = 9300

#debug
executeAscendTime = 10 * 1000  #10sec before ascending, count from starting desending

#Competition
#executeAscendTime = 120 * 1000  #2min / 120s before ascending, count from starting desending

DEBUG_MODE = True  # 设置为true时启用详细调试信息
#---------- Change Here ----------



class TimeDataClient(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MATE Float, Mosasaurus PCMS")
        self.setGeometry(100, 100, 1000, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Left control panel
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setFixedWidth(400)  # Set fixed width for left panel
        
        # Create labels
        self.status_label = QLabel("Status: Not Connected")
        left_layout.addWidget(self.status_label)
        
        # Create buttons
        self.init_connect_button = QPushButton("Initial Connection")
        self.init_connect_button.clicked.connect(self.initial_connection)
        left_layout.addWidget(self.init_connect_button)
        
        self.fetch_button = QPushButton("Fetch Data")
        self.fetch_button.clicked.connect(self.fetch_data)
        left_layout.addWidget(self.fetch_button)
        
        self.plot_button = QPushButton("Show Depth Chart")
        self.plot_button.clicked.connect(self.plot_depth_data)
        left_layout.addWidget(self.plot_button)
        
        # Add Go button
        self.go_button = QPushButton("Start Vertical Profiling")
        self.go_button.clicked.connect(self.start_motor)
        left_layout.addWidget(self.go_button)
        
        # Add test and force stop buttons
        test_buttons_layout = QHBoxLayout()
        
        self.test_pull_button = QPushButton("Test Pull")
        self.test_pull_button.clicked.connect(self.test_pull)
        test_buttons_layout.addWidget(self.test_pull_button)
        
        self.test_push_button = QPushButton("Test Push")
        self.test_push_button.clicked.connect(self.test_push)
        test_buttons_layout.addWidget(self.test_push_button)
        
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
        test_buttons_layout.addWidget(self.force_stop_button)
        
        left_layout.addLayout(test_buttons_layout)
        
        # Create text display area
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        font = self.text_display.font()
        font.setPointSize(12)  # Set font size to 12 points
        self.text_display.setFont(font)
        left_layout.addWidget(self.text_display)
        
        # Right chart area
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Create matplotlib chart
        self.figure = Figure(figsize=(6, 4))
        self.canvas = FigureCanvas(self.figure)
        right_layout.addWidget(self.canvas)
        
        # Add left and right panels to main layout
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 1)
        
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
        ax.plot(self.time_data, self.depth_data, 'b-')
        
        # Set chart title and labels
        ax.set_title('Depth vs Time')
        ax.set_xlabel('Time (UTC)')
        ax.set_ylabel('Depth (meters)')
        
        # Rotate x-axis labels to prevent overlap
        plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
        
        # Adjust layout
        self.figure.tight_layout()
        
        # Refresh canvas
        self.canvas.draw()
        
    def initial_connection(self):
        try:
            # Get current UTC time
            utc_time = datetime.utcnow().strftime("%H:%M:%S")
            
            # Prepare data to send
            data = {
                "utc_time": utc_time,
                "descend_time": descendTime,
                "ascend_time": ascendTime,
                "execute_ascend_time": executeAscendTime,
                "debug_mode": DEBUG_MODE,
                "company_id": companyID
            }
            
            # Send initial connection request
            response = requests.post(f"{self.server_url}/init", json=data)
            
            if response.status_code == 200:
                self.status_label.setText("Status: Initial Connection Successful")
                self.is_connected = True
                # Add initial connection information to text display
                self.text_display.append("=== Initial Connection Information ===")
                self.text_display.append(f"Company ID: {companyID}")
                self.text_display.append(f"UTC Time: {utc_time}")
                self.text_display.append(f"Descend Time: {descendTime}ms")
                self.text_display.append(f"Ascend Time: {ascendTime}ms")
                self.text_display.append(f"Wait Time: {executeAscendTime}ms")
                self.text_display.append(f"Debug Mode: {'Enabled' if DEBUG_MODE else 'Disabled'}")
                self.text_display.append("====================\n")
            else:
                self.status_label.setText("Status: Initial Connection Failed")
                self.text_display.append("Initial connection failed, please try again.")
                
        except requests.exceptions.RequestException:
            self.status_label.setText("Status: Connection Failed")
            self.text_display.append("Unable to connect to server, please ensure ESP32 is running in AP mode.")
        
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
            else:
                self.text_display.append(f"Start failed: {response.text}")
                self.text_display.append(f"Status code: {response.status_code}")
                self.status_label.setText("Status: Motor Control Start Failed")
        except requests.exceptions.RequestException as e:
            self.text_display.append(f"Connection error: {str(e)}")
            self.text_display.append("Unable to connect to server, please ensure ESP32 is running in AP mode.")
            self.status_label.setText("Status: Connection Failed")

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

    def force_stop(self):
        """Force stop function"""
        try:
            response = requests.post(f"{self.server_url}/motor/force/stop")
            if response.status_code == 200:
                self.text_display.append("Force stop command sent")
            else:
                self.text_display.append(f"Force stop failed: {response.text}")
        except requests.exceptions.RequestException:
            self.text_display.append("Unable to connect to server")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TimeDataClient()
    window.show()
    sys.exit(app.exec_()) 