#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>  //add lib in arduino IDE

String companyID = "RN99";
float depthData = 7.7;  //meters
const bool DEBUG_MODE = false;  // 设置为true时启用详细调试信息



// 定义缓冲区大小 (3分钟 * 12次/分钟 = 36个数据点)
const int BUFFER_SIZE = 36;
String timeBuffer[BUFFER_SIZE];
int writeIndex = 0;        // 写入位置
int readIndex = 0;         // 读取位置
int dataCount = 0;         // 当前数据数量
unsigned long lastRecordTime = 0;
const unsigned long RECORD_INTERVAL = 5000; // 5秒 = 5000毫秒

// 存储初始连接参数
unsigned long descendTime = 7300;
unsigned long accendTime = 7300;
String utcTime = "";
unsigned long utcStartMillis = 0;  // 存储UTC时间对应的millis值
bool isTimeInitialized = false;    // 时间是否已初始化

// 网络设置
const char* ssid = "Float_Control";      // WiFi名称
const char* password = "12345678";       // WiFi密码

// 创建WebServer对象
WebServer server(80);

// 调试标志

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
  // 如果时间未初始化，返回空数组
  if (!isTimeInitialized) {
    server.send(200, "application/json", "[]");
    return;
  }

  String response = "[";
  bool firstData = true;
  
  // 从上次读取位置开始，发送新数据
  while (readIndex != writeIndex) {
    if (!firstData) {
      response += ",";
    }
    response += "\"";
    response += companyID + ", ";
    response += timeBuffer[readIndex] + " UTC, ";
    response += String(depthData, 2) + " meters";
    response += "\"";
    
    readIndex = (readIndex + 1) % BUFFER_SIZE;
    firstData = false;
  }
  
  response += "]";
  server.send(200, "application/json", response);
  
  // 只在调试模式下打印信息
  if (DEBUG_MODE) {
    Serial.print("发送数据，当前读取位置: ");
    Serial.print(readIndex);
    Serial.print(", 写入位置: ");
    Serial.println(writeIndex);
  }
}

/**
 * 处理初始连接请求
 */
void handleInit() {
  if (server.method() == HTTP_POST) {
    String postBody = server.arg("plain");
    StaticJsonDocument<200> doc;
    DeserializationError error = deserializeJson(doc, postBody);
    
    if (error) {
      server.send(400, "text/plain", "Invalid JSON");
      return;
    }
    
    // 获取参数
    utcTime = doc["utc_time"].as<String>();
    descendTime = doc["descend_time"].as<unsigned long>();
    accendTime = doc["accend_time"].as<unsigned long>();
    
    // 解析UTC时间字符串
    int hours = utcTime.substring(0, 2).toInt();
    int minutes = utcTime.substring(3, 5).toInt();
    int seconds = utcTime.substring(6, 8).toInt();
    
    // 计算总秒数
    unsigned long totalSeconds = hours * 3600 + minutes * 60 + seconds;
    
    // 记录当前millis值
    utcStartMillis = millis();
    
    // 标记时间已初始化
    isTimeInitialized = true;
    
    // 打印接收到的参数
    Serial.println("Received initial connection parameters:");
    Serial.print("UTC Time: ");
    Serial.println(utcTime);
    Serial.print("Descend Time: ");
    Serial.println(descendTime);
    Serial.print("Accend Time: ");
    Serial.println(accendTime);
    Serial.print("Total seconds: ");
    Serial.println(totalSeconds);
    
    server.send(200, "text/plain", "Initial connection successful");
  } else {
    server.send(405, "text/plain", "Method Not Allowed");
  }
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
  server.on("/init", HTTP_POST, handleInit);  // 添加初始连接路由
  server.onNotFound(handleNotFound);
  
  // 启动服务器
  server.begin();
  Serial.println("HTTP服务器已启动");

}

void loop() {
  server.handleClient();
  
  unsigned long currentTime = millis();
  
  // 只有在时间初始化后才记录数据
  if(isTimeInitialized && currentTime - lastRecordTime >= RECORD_INTERVAL) {
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
    
    // 只在调试模式下打印信息
    if (DEBUG_MODE) {
      Serial.print("Buffer updated - Write Index: ");
      Serial.print(writeIndex);
      Serial.print(", Read Index: ");
      Serial.println(readIndex);
    }
  }

  delay(1000);  // 增加延迟到1秒，减少CPU使用率
}

/**
 * 获取格式化的当前时间字符串
 * @return 格式为 "HH:MM:SS" 的时间字符串
 */
String getTimeString() {
  if (!isTimeInitialized) {
    return "00:00:00";
  }
  
  // 计算从初始化到现在经过的毫秒数
  unsigned long elapsedMillis = millis() - utcStartMillis;
  
  // 解析初始UTC时间
  int hours = utcTime.substring(0, 2).toInt();
  int minutes = utcTime.substring(3, 5).toInt();
  int seconds = utcTime.substring(6, 8).toInt();
  
  // 计算总秒数
  unsigned long totalSeconds = hours * 3600 + minutes * 60 + seconds;
  
  // 加上经过的秒数
  totalSeconds += elapsedMillis / 1000;
  
  // 计算新的时间
  hours = (totalSeconds / 3600) % 24;
  minutes = (totalSeconds / 60) % 60;
  seconds = totalSeconds % 60;
  
  char timeStr[9];
  sprintf(timeStr, "%02d:%02d:%02d", hours, minutes, seconds);
  return String(timeStr);
}
