#include <WiFi.h>
#include <WebServer.h>

// 定义缓冲区大小 (3分钟 * 12次/分钟 = 36个数据点)
const int BUFFER_SIZE = 36;
String timeBuffer[BUFFER_SIZE];
int writeIndex = 0;        // 写入位置
int readIndex = 0;         // 读取位置
int dataCount = 0;         // 当前数据数量
unsigned long lastRecordTime = 0;
const unsigned long RECORD_INTERVAL = 5000; // 5秒 = 5000毫秒

// 网络设置
const char* ssid = "Float_Control";      // WiFi名称
const char* password = "12345678";       // WiFi密码

// 创建WebServer对象
WebServer server(80);

/**
 * 设置WiFi接入点模式
 */
void setupWiFi() {
  WiFi.mode(WIFI_AP);
  WiFi.softAP(ssid, password);
  
  Serial.print("接入点已创建, IP地址: ");
  Serial.println(WiFi.softAPIP());
}

/**
 * 处理根路径请求
 */
void handleRoot() {
  String html = "<html><head><title>时间数据服务器</title>";
  html += "<meta name='viewport' content='width=device-width, initial-scale=1'>";
  html += "<style>";
  html += "body { font-family: Arial; text-align: center; margin: 0; padding: 20px; }";
  html += "h1 { color: #0066cc; }";
  html += ".btn { background-color: #4CAF50; border: none; color: white; padding: 15px 32px; ";
  html += "text-align: center; text-decoration: none; display: inline-block; font-size: 16px; ";
  html += "margin: 4px 2px; cursor: pointer; border-radius: 8px; }";
  html += "</style></head><body>";
  html += "<h1>时间数据服务器</h1>";
  html += "<div><button class='btn' onclick='getData()'>获取数据</button></div>";
  html += "<div id='data' style='margin-top: 20px;'></div>";
  html += "<script>";
  html += "function getData() {";
  html += "  fetch('/data')";
  html += "    .then(response => response.json())";
  html += "    .then(data => {";
  html += "      let html = '<h2>时间数据列表</h2><ul>';";
  html += "      data.forEach(time => {";
  html += "        html += '<li>' + time + '</li>';";
  html += "      });";
  html += "      html += '</ul>';";
  html += "      document.getElementById('data').innerHTML = html;";
  html += "    });";
  html += "}";
  html += "</script></body></html>";
  
  server.send(200, "text/html", html);
}

/**
 * 处理数据请求
 */
void handleData() {
  String response = "[";
  bool firstData = true;
  
  // 从上次读取位置开始，发送新数据
  while (readIndex != writeIndex) {
    if (!firstData) {
      response += ",";
    }
    response += "\"" + timeBuffer[readIndex] + "\"";
    readIndex = (readIndex + 1) % BUFFER_SIZE;
    firstData = false;
  }
  
  response += "]";
  server.send(200, "application/json", response);
  
  // 打印调试信息
  Serial.print("发送数据，当前读取位置: ");
  Serial.print(readIndex);
  Serial.print(", 写入位置: ");
  Serial.println(writeIndex);
}

/**
 * 处理未找到的路径
 */
void handleNotFound() {
  server.send(404, "text/plain", "Not found");
}

void setup() {
  Serial.begin(115200);
  Serial.println("\n启动时间数据服务器");
  
  // 初始化缓冲区
  for(int i = 0; i < BUFFER_SIZE; i++) {
    timeBuffer[i] = "";
  }
  
  setupWiFi();
  
  // 设置Web服务器路由
  server.on("/", HTTP_GET, handleRoot);
  server.on("/data", HTTP_GET, handleData);
  server.onNotFound(handleNotFound);
  
  // 启动服务器
  server.begin();
  Serial.println("HTTP服务器已启动");
}

void loop() {
  server.handleClient();
  
  unsigned long currentTime = millis();
  
  // 检查是否到达记录时间
  if(currentTime - lastRecordTime >= RECORD_INTERVAL) {
    // 获取当前时间
    String currentTimeStr = getTimeString();
    
    // 存储到缓冲区
    timeBuffer[writeIndex] = currentTimeStr;
    
    // 更新写入索引
    writeIndex = (writeIndex + 1) % BUFFER_SIZE;
    
    // 如果缓冲区已满，移动读取索引
    if (writeIndex == readIndex) {
      readIndex = (readIndex + 1) % BUFFER_SIZE;
    }
    
    // 更新最后记录时间
    lastRecordTime = currentTime;
    
    // 打印当前缓冲区状态（用于调试）
    Serial.print("Buffer updated - Write Index: ");
    Serial.print(writeIndex);
    Serial.print(", Read Index: ");
    Serial.println(readIndex);
  }
}

/**
 * 获取格式化的当前时间字符串
 * @return 格式为 "HH:MM:SS" 的时间字符串
 */
String getTimeString() {
  unsigned long currentMillis = millis();
  unsigned long seconds = currentMillis / 1000;
  int hours = (seconds / 3600) % 24;
  int minutes = (seconds / 60) % 60;
  int secs = seconds % 60;
  
  char timeStr[9];
  sprintf(timeStr, "%02d:%02d:%02d", hours, minutes, secs);
  return String(timeStr);
}
