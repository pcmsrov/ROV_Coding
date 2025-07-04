/**
 * ESP32 浮標控制系統
 * 
 * @description 使用ESP32和DRV8871控制馬達浮力裝置
 * @author Thomas Team
 * @version 1.0.0
 */

#include <WiFi.h>
#include <WebServer.h>
#include <Wire.h>

// 網絡設置
const char* ssid = "Float_Control";      // WiFi名稱
const char* password = "12345678";       // WiFi密碼

// DRV8871馬達驅動引腳
#define MOTOR_IN1 25                     // 馬達控制IN1引腳
#define MOTOR_IN2 26                     // 馬達控制IN2引腳

// 深度感測器相關設置
// 注意：這裡只是模擬數據，如果有實際感測器需要引入對應庫
float currentDepth = 0.0;                // 當前深度(米)
unsigned long lastDepthUpdate = 0;       // 上次深度更新時間
bool isSimulation = true;                // 是否使用模擬數據

// 浮標控制狀態
enum MotorState {
  MOTOR_STOP = 0,
  MOTOR_UP = 1,
  MOTOR_DOWN = 2
};

MotorState currentState = MOTOR_STOP;    // 當前馬達狀態
String deviceId = "RN01";                // 設備ID

// 創建WebServer對象
WebServer server(80);

/**
 * 設置硬件引腳和初始狀態
 */
void setupHardware() {
  // 設置馬達控制引腳為輸出模式
  pinMode(MOTOR_IN1, OUTPUT);
  pinMode(MOTOR_IN2, OUTPUT);
  
  // 初始化馬達為停止狀態
  digitalWrite(MOTOR_IN1, LOW);
  digitalWrite(MOTOR_IN2, LOW);
  
  // 初始化I2C通信（如果有實際感測器）
  Wire.begin();
  
  Serial.println("硬件初始化完成");
}

/**
 * 設置WiFi接入點模式
 */
void setupWiFi() {
  WiFi.mode(WIFI_AP);
  WiFi.softAP(ssid, password);
  
  Serial.print("接入點已創建, IP地址: ");
  Serial.println(WiFi.softAPIP());
}

/**
 * 設置Web服務器和API端點
 */
void setupWebServer() {
  // API端點
  server.on("/", HTTP_GET, handleRoot);
  server.on("/status", HTTP_GET, handleStatus);
  server.on("/up", HTTP_POST, handleMoveUp);
  server.on("/down", HTTP_POST, handleMoveDown);
  server.on("/stop", HTTP_POST, handleStop);
  
  // 404處理
  server.onNotFound(handleNotFound);
  
  // 啟動服務器
  server.begin();
  Serial.println("HTTP服務器已啟動");
}

/**
 * 控制馬達上升
 */
void motorUp() {
  digitalWrite(MOTOR_IN1, LOW);
  digitalWrite(MOTOR_IN2, HIGH);
  currentState = MOTOR_UP;
  Serial.println("馬達運轉: 上升");
}

/**
 * 控制馬達下潛
 */
void motorDown() {
  Serial.println("開始下潛操作...");
  Serial.println("設置 IN1=HIGH, IN2=LOW");
  
  digitalWrite(MOTOR_IN1, HIGH);
  digitalWrite(MOTOR_IN2, LOW);
  currentState = MOTOR_DOWN;
  
  Serial.println("馬達運轉: 下潛");
  Serial.print("當前深度: ");
  Serial.println(currentDepth);
}

/**
 * 停止馬達
 */
void motorStop() {
  digitalWrite(MOTOR_IN1, LOW);
  digitalWrite(MOTOR_IN2, LOW);
  currentState = MOTOR_STOP;
  Serial.println("馬達停止");
}

/**
 * 更新深度數據
 * 如果使用模擬數據，則根據當前馬達狀態改變深度
 * 如果連接實際感測器，應從感測器讀取數據
 */
void updateDepth() {
  if (isSimulation) {
    // 根據馬達狀態更新模擬深度
    if (currentState == MOTOR_DOWN) {
      currentDepth += 0.05;  // 下潛時增加深度
    } else if (currentState == MOTOR_UP && currentDepth > 0) {
      currentDepth -= 0.05;  // 上升時減少深度，但不低於0
      if (currentDepth < 0) currentDepth = 0;
    }
  } else {
    // 從實際感測器讀取深度數據
    // 例如: currentDepth = readDepthSensor();
  }
}

/**
 * 獲取格式化的當前時間字符串
 * @return 格式為 "HH:MM:SS" 的時間字符串
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

/**
 * 處理根路徑請求，返回簡單HTML控制界面
 */
void handleRoot() {
  String html = "<html><head><title>浮標控制系統</title>";
  html += "<meta name='viewport' content='width=device-width, initial-scale=1'>";
  html += "<style>";
  html += "body { font-family: Arial; text-align: center; margin: 0; padding: 20px; }";
  html += "h1 { color: #0066cc; }";
  html += ".btn { background-color: #4CAF50; border: none; color: white; padding: 15px 32px; ";
  html += "text-align: center; text-decoration: none; display: inline-block; font-size: 16px; ";
  html += "margin: 4px 2px; cursor: pointer; border-radius: 8px; }";
  html += ".btn-up { background-color: #2196F3; }";
  html += ".btn-down { background-color: #f44336; }";
  html += ".btn-stop { background-color: #555555; }";
  html += ".status { margin-top: 20px; padding: 10px; background-color: #f1f1f1; border-radius: 5px; }";
  html += "</style></head><body>";
  html += "<h1>浮標控制系統</h1>";
  html += "<div><button class='btn btn-up' onclick='sendCommand(\"/up\")'>上升</button></div>";
  html += "<div><button class='btn btn-stop' onclick='sendCommand(\"/stop\")'>停止</button></div>";
  html += "<div><button class='btn btn-down' onclick='sendCommand(\"/down\")'>下潛</button></div>";
  html += "<div class='status' id='status'>深度: " + String(currentDepth, 2) + " 米</div>";
  html += "<script>";
  html += "function sendCommand(command) {";
  html += "  fetch(command, { method: 'POST' })";
  html += "    .then(response => response.text())";
  html += "    .then(data => { updateStatus(); })";
  html += "    .catch(error => console.error('Error:', error));";
  html += "}";
  html += "function updateStatus() {";
  html += "  fetch('/status')";
  html += "    .then(response => response.json())";
  html += "    .then(data => {";
  html += "      document.getElementById('status').innerHTML = '深度: ' + data.depth + ' 米<br>時間: ' + data.time + '<br>ID: ' + data.id;";
  html += "    });";
  html += "}";
  html += "setInterval(updateStatus, 1000);";  // 每秒更新一次狀態
  html += "</script></body></html>";
  
  server.send(200, "text/html", html);
}

/**
 * 處理狀態請求，返回JSON格式的當前狀態
 */
void handleStatus() {
  String jsonResponse = "{";
  jsonResponse += "\"depth\":" + String(currentDepth) + ",";
  jsonResponse += "\"time\":\"" + getTimeString() + "\",";
  jsonResponse += "\"id\":\"" + deviceId + "\",";
  jsonResponse += "\"state\":" + String((int)currentState);
  jsonResponse += "}";
  
  server.send(200, "application/json", jsonResponse);
}

/**
 * 處理上升請求
 */
void handleMoveUp() {
  motorUp();
  server.send(200, "text/plain", "Moving up");
}

/**
 * 處理下潛請求
 */
void handleMoveDown() {
  Serial.println("收到下潛請求");
  motorDown();
  server.send(200, "text/plain", "Moving down");
  Serial.println("下潛命令已發送");
}

/**
 * 處理停止請求
 */
void handleStop() {
  motorStop();
  server.send(200, "text/plain", "Stopped");
}

/**
 * 處理未找到的路徑
 */
void handleNotFound() {
  server.send(404, "text/plain", "Not found");
}

/**
 * 初始化設置
 */
void setup() {
  Serial.begin(115200);
  Serial.println("\n啟動浮標控制系統");
  
  setupHardware();
  setupWiFi();
  setupWebServer();
  
  Serial.println("系統初始化完成");
}

/**
 * 主循環
 */
void loop() {
  server.handleClient();
  
  // 每秒更新一次深度數據
  unsigned long currentMillis = millis();
  if (currentMillis - lastDepthUpdate >= 1000) {
    updateDepth();
    lastDepthUpdate = currentMillis;
  }
} 