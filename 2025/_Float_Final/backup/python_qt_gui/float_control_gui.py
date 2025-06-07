#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
浮標控制系統 - Qt GUI界面

此程式提供與ESP32 WebServer通信的圖形界面，用於控制浮標上升/下潛
並顯示深度數據和歷史記錄圖表。

@author: Thomas Team
@version: 1.0.0
"""

import sys
import json
import time
from datetime import datetime
import requests
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                            QHBoxLayout, QWidget, QLabel, QGroupBox, QGridLayout,
                            QLineEdit, QMessageBox, QTabWidget, QTextEdit, QSplitter)
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QIcon
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
import numpy as np

# 默認ESP32 WebServer的IP地址
DEFAULT_ESP32_IP = "192.168.4.1"

class DepthDataCollector(QThread):
    """
    後台線程，用於收集深度數據
    
    @signal data_received: 當從ESP32接收到新數據時發出此信號
    """
    data_received = pyqtSignal(dict)
    
    def __init__(self, ip_address):
        """
        初始化數據收集器
        
        @param ip_address: ESP32的IP地址
        """
        super().__init__()
        self.ip_address = ip_address
        self.is_running = True
        
    def run(self):
        """
        線程主循環，每秒從ESP32獲取一次深度數據
        """
        while self.is_running:
            try:
                # 請求ESP32的狀態API
                response = requests.get(f"http://{self.ip_address}/status", timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    # 添加當前系統時間戳
                    data['timestamp'] = datetime.now()
                    self.data_received.emit(data)
            except Exception as e:
                print(f"連接ESP32時出錯: {e}")
            
            # 每秒更新一次
            time.sleep(1)
    
    def stop(self):
        """
        停止數據收集
        """
        self.is_running = False
        self.wait()

class DepthPlot(FigureCanvas):
    """
    深度數據圖表
    
    顯示深度隨時間變化的折線圖
    """
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        """
        初始化圖表
        """
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        
        # 設置圖表格式
        self.axes.set_title('深度變化圖')
        self.axes.set_xlabel('時間')
        self.axes.set_ylabel('深度 (米)')
        self.axes.grid(True)
        
        # 數據存儲
        self.timestamps = []
        self.depths = []
        
        # 設置自動格式化X軸日期
        self.axes.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        self.fig.autofmt_xdate()

    def update_plot(self, timestamp, depth):
        """
        更新圖表數據
        
        @param timestamp: 數據時間戳
        @param depth: 深度數據
        """
        # 只保留最近30個數據點
        if len(self.timestamps) > 30:
            self.timestamps = self.timestamps[-30:]
            self.depths = self.depths[-30:]
            
        self.timestamps.append(timestamp)
        self.depths.append(depth)
        
        # 重新繪製圖表
        self.axes.clear()
        self.axes.plot(self.timestamps, self.depths, 'b-o')
        self.axes.set_title('深度變化圖')
        self.axes.set_xlabel('時間')
        self.axes.set_ylabel('深度 (米)')
        self.axes.grid(True)
        
        # 設置Y軸範圍
        if self.depths:
            min_depth = max(0, min(self.depths) - 0.5)
            max_depth = max(self.depths) + 0.5
            self.axes.set_ylim(min_depth, max_depth)
        
        # 設置X軸格式
        self.axes.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        self.fig.autofmt_xdate()
        
        self.draw()

class FloatControlGUI(QMainWindow):
    """
    浮標控制系統主窗口
    """
    def __init__(self):
        """
        初始化主窗口
        """
        super().__init__()
        
        # 窗口設置
        self.setWindowTitle('浮標控制系統')
        self.setGeometry(100, 100, 800, 600)
        
        # ESP32的IP地址
        self.esp32_ip = DEFAULT_ESP32_IP
        
        # 數據記錄
        self.data_log = []
        
        # 連接狀態
        self.is_connected = False
        
        # 創建UI元素
        self.init_ui()
        
        # 啟動數據收集線程
        self.start_data_collection()
    
    def init_ui(self):
        """
        初始化用戶界面
        """
        # 主佈局
        main_layout = QVBoxLayout()
        
        # 頂部控制面板
        control_panel = self.create_control_panel()
        main_layout.addLayout(control_panel)
        
        # 選項卡窗口
        tab_widget = QTabWidget()
        
        # 圖表選項卡
        graph_tab = QWidget()
        graph_layout = QVBoxLayout()
        self.depth_plot = DepthPlot(width=7, height=4)
        graph_layout.addWidget(self.depth_plot)
        graph_tab.setLayout(graph_layout)
        tab_widget.addTab(graph_tab, "深度圖表")
        
        # 數據日誌選項卡
        log_tab = QWidget()
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        log_tab.setLayout(log_layout)
        tab_widget.addTab(log_tab, "數據日誌")
        
        main_layout.addWidget(tab_widget)
        
        # 創建主窗口部件
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        # 狀態欄
        self.statusBar().showMessage('未連接到ESP32')
    
    def create_control_panel(self):
        """
        創建控制面板
        
        @return: 控制面板佈局
        """
        control_layout = QVBoxLayout()
        
        # 連接設置
        connection_group = QGroupBox("連接設置")
        connection_layout = QHBoxLayout()
        
        ip_label = QLabel("ESP32 IP:")
        self.ip_input = QLineEdit(self.esp32_ip)
        self.ip_input.setFixedWidth(150)
        connect_button = QPushButton("連接")
        connect_button.clicked.connect(self.connect_esp32)
        
        # 添加連接狀態指示燈
        self.connection_status = QLabel("●")
        self.connection_status.setStyleSheet("color: red; font-size: 20px;")
        self.connection_status.setToolTip("未連接")
        
        connection_layout.addWidget(ip_label)
        connection_layout.addWidget(self.ip_input)
        connection_layout.addWidget(connect_button)
        connection_layout.addWidget(self.connection_status)
        connection_layout.addStretch()
        connection_group.setLayout(connection_layout)
        
        # 控制按鈕
        control_group = QGroupBox("浮標控制")
        buttons_layout = QHBoxLayout()
        
        self.up_button = QPushButton("上升")
        self.up_button.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 10px;")
        self.up_button.clicked.connect(self.move_up)
        
        self.stop_button = QPushButton("停止")
        self.stop_button.setStyleSheet("background-color: #555555; color: white; font-weight: bold; padding: 10px;")
        self.stop_button.clicked.connect(self.stop_motor)
        
        self.down_button = QPushButton("下潛")
        self.down_button.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 10px;")
        self.down_button.clicked.connect(self.move_down)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.up_button)
        buttons_layout.addWidget(self.stop_button)
        buttons_layout.addWidget(self.down_button)
        buttons_layout.addStretch()
        control_group.setLayout(buttons_layout)
        
        # 信息顯示
        info_group = QGroupBox("即時數據")
        info_layout = QGridLayout()
        
        depth_label = QLabel("當前深度:")
        self.depth_value = QLabel("0.00 米")
        self.depth_value.setStyleSheet("font-size: 20px; font-weight: bold;")
        
        time_label = QLabel("時間:")
        self.time_value = QLabel("00:00:00")
        
        id_label = QLabel("設備ID:")
        self.id_value = QLabel("--")
        
        state_label = QLabel("馬達狀態:")
        self.state_value = QLabel("停止")
        
        info_layout.addWidget(depth_label, 0, 0)
        info_layout.addWidget(self.depth_value, 0, 1)
        info_layout.addWidget(time_label, 1, 0)
        info_layout.addWidget(self.time_value, 1, 1)
        info_layout.addWidget(id_label, 0, 2)
        info_layout.addWidget(self.id_value, 0, 3)
        info_layout.addWidget(state_label, 1, 2)
        info_layout.addWidget(self.state_value, 1, 3)
        
        info_group.setLayout(info_layout)
        
        # 添加到控制面板佈局
        control_layout.addWidget(connection_group)
        control_layout.addWidget(info_group)
        control_layout.addWidget(control_group)
        
        return control_layout
    
    def connect_esp32(self):
        """
        連接到ESP32
        """
        # 獲取用戶輸入的IP地址
        ip = self.ip_input.text().strip()
        if not ip:
            QMessageBox.warning(self, "錯誤", "請輸入有效的IP地址")
            return
        
        # 更新IP地址
        self.esp32_ip = ip
        
        # 重啟數據收集線程
        if hasattr(self, 'data_collector') and self.data_collector.isRunning():
            self.data_collector.stop()
        
        # 重置連接狀態
        self.is_connected = False
        self.connection_status.setStyleSheet("color: red; font-size: 20px;")
        self.connection_status.setToolTip("正在連接...")
        
        self.start_data_collection()
        self.statusBar().showMessage(f'正在嘗試連接到 {self.esp32_ip}...')
    
    def start_data_collection(self):
        """
        啟動數據收集線程
        """
        self.data_collector = DepthDataCollector(self.esp32_ip)
        self.data_collector.data_received.connect(self.update_data)
        self.data_collector.start()
    
    def update_data(self, data):
        """
        更新顯示的數據
        
        @param data: 從ESP32接收到的數據
        """
        # 更新連接狀態
        self.is_connected = True
        self.connection_status.setStyleSheet("color: green; font-size: 20px;")
        self.connection_status.setToolTip("已連接")
        
        # 更新數據顯示
        self.depth_value.setText(f"{data['depth']:.2f} 米")
        self.time_value.setText(data['time'])
        self.id_value.setText(data['id'])
        
        # 更新馬達狀態
        state_map = {0: "停止", 1: "上升", 2: "下潛"}
        state = state_map.get(data['state'], "未知")
        self.state_value.setText(state)
        
        # 更新圖表
        self.depth_plot.update_plot(data['timestamp'], data['depth'])
        
        # 記錄數據
        log_entry = f"{data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} | ID: {data['id']} | 深度: {data['depth']:.2f} 米 | 狀態: {state}"
        self.data_log.append(log_entry)
        self.log_text.append(log_entry)
        
        # 更新狀態欄
        self.statusBar().showMessage(f'已連接到 {self.esp32_ip} | 上次更新: {datetime.now().strftime("%H:%M:%S")}')
    
    def send_command(self, command):
        """
        發送命令到ESP32
        
        @param command: 命令路徑 (/up, /down, /stop)
        """
        if not self.is_connected:
            QMessageBox.warning(self, "錯誤", "未連接到ESP32")
            return
            
        try:
            response = requests.post(f"http://{self.esp32_ip}{command}", timeout=2)
            if response.status_code == 200:
                print(f"命令 {command} 發送成功")
                # 更新狀態欄顯示命令發送成功
                self.statusBar().showMessage(f'命令 {command} 發送成功', 2000)
            else:
                print(f"命令 {command} 發送失敗，狀態碼: {response.status_code}")
                QMessageBox.warning(self, "錯誤", f"命令發送失敗，狀態碼: {response.status_code}")
        except Exception as e:
            print(f"發送命令時出錯: {e}")
            QMessageBox.warning(self, "錯誤", f"無法連接到ESP32: {e}")
            # 更新連接狀態
            self.is_connected = False
            self.connection_status.setStyleSheet("color: red; font-size: 20px;")
            self.connection_status.setToolTip("連接斷開")
    
    def move_up(self):
        """
        控制浮標上升
        """
        self.send_command("/up")
    
    def move_down(self):
        """
        控制浮標下潛
        """
        self.send_command("/down")
    
    def stop_motor(self):
        """
        停止浮標馬達
        """
        self.send_command("/stop")
    
    def closeEvent(self, event):
        """
        關閉窗口時停止數據收集線程
        
        @param event: 關閉事件
        """
        if hasattr(self, 'data_collector') and self.data_collector.isRunning():
            self.data_collector.stop()
        event.accept()

if __name__ == '__main__':
    # 創建應用程序
    app = QApplication(sys.argv)
    
    # 設置應用程序樣式
    app.setStyle('Fusion')
    
    # 創建主窗口
    main_window = FloatControlGUI()
    main_window.show()
    
    # 運行應用程序
    sys.exit(app.exec_()) 