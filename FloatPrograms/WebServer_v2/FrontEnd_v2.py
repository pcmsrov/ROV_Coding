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

#float motor time adjuest, in miliseconds
descendTime = 7300
accendTime = 7300

class TimeDataClient(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("时间数据客户端")
        self.setGeometry(100, 100, 1000, 600)
        
        # 创建中央部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧控制面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 创建标签
        self.status_label = QLabel("状态: 未连接")
        left_layout.addWidget(self.status_label)
        
        # 创建按钮
        self.init_connect_button = QPushButton("初始连接")
        self.init_connect_button.clicked.connect(self.initial_connection)
        left_layout.addWidget(self.init_connect_button)
        
        self.fetch_button = QPushButton("获取数据")
        self.fetch_button.clicked.connect(self.fetch_data)
        left_layout.addWidget(self.fetch_button)
        
        self.plot_button = QPushButton("显示深度图表")
        self.plot_button.clicked.connect(self.plot_depth_data)
        left_layout.addWidget(self.plot_button)
        
        # 创建文本显示区域
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        left_layout.addWidget(self.text_display)
        
        # 右侧图表区域
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 创建matplotlib图表
        self.figure = Figure(figsize=(6, 4))
        self.canvas = FigureCanvas(self.figure)
        right_layout.addWidget(self.canvas)
        
        # 添加左右面板到主布局
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 1)
        
        # 服务器地址
        self.server_url = "http://192.168.4.1"  # ESP32的默认AP IP地址
        
        # 创建固定大小的FIFO队列，最多存储180个元素
        self.max_size = 180
        self.time_data_queue = deque(maxlen=self.max_size)
        
        # 存储深度数据
        self.depth_data = []
        self.time_data = []
        
        # 连接状态标志
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
        """绘制深度数据图表"""
        if not self.depth_data:
            self.text_display.append("没有可用的深度数据")
            return
            
        # 清除旧图表
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        # 绘制深度数据
        ax.plot(self.time_data, self.depth_data, 'b-')
        
        # 设置图表标题和标签
        ax.set_title('深度随时间变化')
        ax.set_xlabel('时间 (UTC)')
        ax.set_ylabel('深度 (米)')
        
        # 旋转x轴标签以防重叠
        plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
        
        # 调整布局
        self.figure.tight_layout()
        
        # 刷新画布
        self.canvas.draw()
        
    def initial_connection(self):
        try:
            # 获取当前UTC时间
            utc_time = datetime.utcnow().strftime("%H:%M:%S")
            
            # 准备发送的数据
            data = {
                "utc_time": utc_time,
                "descend_time": descendTime,
                "accend_time": accendTime
            }
            
            # 发送初始连接请求
            response = requests.post(f"{self.server_url}/init", json=data)
            
            if response.status_code == 200:
                self.status_label.setText("状态: 初始连接成功")
                self.is_connected = True
                # 在文本显示区域添加初始连接信息
                self.text_display.append("=== 初始连接信息 ===")
                self.text_display.append(f"UTC时间: {utc_time}")
                self.text_display.append(f"下降时间: {descendTime}ms")
                self.text_display.append(f"上升时间: {accendTime}ms")
                self.text_display.append("==================\n")
            else:
                self.status_label.setText("状态: 初始连接失败")
                self.text_display.append("初始连接失败，请重试。")
                
        except requests.exceptions.RequestException:
            self.status_label.setText("状态: 连接失败")
            self.text_display.append("无法连接到服务器，请确保ESP32已启动并处于AP模式。")
        
    def fetch_data(self):
        try:
            # 获取数据
            response = requests.get(f"{self.server_url}/data")
            if response.status_code == 200:
                data = response.json()
                
                if data:  # 只有在有数据时才显示
                    # 将新数据添加到FIFO队列中
                    for time_str in data:
                        if time_str:  # 确保不是空字符串
                            self.time_data_queue.append(time_str)
                            # 直接添加新数据到显示区域
                            self.text_display.append(time_str)
                            
                            # 提取深度和时间数据
                            depth = self.extract_depth(time_str)
                            time = self.extract_time(time_str)
                            if depth is not None and time is not None:
                                self.depth_data.append(depth)
                                self.time_data.append(time)
                    
                    # 更新状态标签
                    self.status_label.setText(f"状态: 已连接 (数据点: {len(self.time_data_queue)})")
                
                self.status_label.setText("状态: 已连接")
            else:
                self.status_label.setText("状态: 服务器响应错误")
        except requests.exceptions.RequestException:
            self.status_label.setText("状态: 连接失败")
            self.text_display.append("无法连接到服务器，请确保ESP32已启动并处于AP模式。")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TimeDataClient()
    window.show()
    sys.exit(app.exec_()) 