import sys
import requests
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QTextEdit, QLabel
from PyQt5.QtCore import QTimer
from datetime import datetime
from collections import deque

class TimeDataClient(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("时间数据客户端")
        self.setGeometry(100, 100, 600, 400)
        
        # 创建中央部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 创建标签
        self.status_label = QLabel("状态: 未连接")
        layout.addWidget(self.status_label)
        
        # 创建按钮
        self.fetch_button = QPushButton("获取数据")
        self.fetch_button.clicked.connect(self.fetch_data)
        layout.addWidget(self.fetch_button)
        
        # 创建文本显示区域
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        layout.addWidget(self.text_display)
        
        # 服务器地址
        self.server_url = "http://192.168.4.1"  # ESP32的默认AP IP地址
        
        # 创建固定大小的FIFO队列，最多存储180个元素
        self.max_size = 180
        self.time_data_queue = deque(maxlen=self.max_size)
        
    def parse_time(self, time_str):
        """将时间字符串转换为datetime对象"""
        try:
            return datetime.strptime(time_str, "%H:%M:%S")
        except ValueError:
            return None
        
    def fetch_data(self):
        try:
            # 获取数据
            response = requests.get(f"{self.server_url}/data")
            if response.status_code == 200:
                data = response.json()
                
                # 将新数据添加到FIFO队列中
                for time_str in data:
                    if time_str:  # 确保不是空字符串
                        self.time_data_queue.append(time_str)
                
                # 显示数据
                self.text_display.clear()
                self.text_display.append("时间数据列表 (FIFO顺序):")
                
                # 将队列转换为列表并显示
                time_list = list(self.time_data_queue)
                for time_str in time_list:
                    self.text_display.append(time_str)
                
                # 显示数据统计
                self.text_display.append(f"\n当前数据点数量: {len(self.time_data_queue)}")
                self.text_display.append(f"最大容量: {self.max_size}")
                
                self.status_label.setText("状态: 已连接")
            else:
                self.status_label.setText("状态: 服务器响应错误")
        except requests.exceptions.RequestException:
            self.status_label.setText("状态: 连接失败")
            self.text_display.clear()
            self.text_display.append("无法连接到服务器，请确保ESP32已启动并处于AP模式。")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TimeDataClient()
    window.show()
    sys.exit(app.exec_())
