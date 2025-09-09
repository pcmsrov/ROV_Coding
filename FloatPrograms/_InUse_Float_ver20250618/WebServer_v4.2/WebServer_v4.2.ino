#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>  //add lib in arduino IDE
#include <Wire.h>
#include "MS5837.h" //add lib in arduino IDE, by Bluerobtoics v1.1.1


//---------- Maybe Change Here ----------
// 网络设置
//const char* ssid = "Float_Control";      // WiFi名称
//const char* password = "12345678";       // WiFi密码
const char* ssid = "A_MosaFloat";      // WiFi名称
const char* password = "pcmsrov22";       // WiFi密码
//---------- Maybe Change Here ----------

// 存储初始连接参数, 會從前端界面再發送，不用改
String companyID = "NotSetYet";
bool DEBUG_MODE = false;  // 设置为true时启用详细调试信息
unsigned long descendTime = 7300;
unsigned long waitTime = 10000;
unsigned long ascendTime = 7300;
bool useTimer = false;


float depthData = 0.0;  // Will be updated with real sensor data
float depthOffset = 0.0;  // 新增：深度偏移量

// 定义缓冲区大小 (5分钟 * 12次/分钟 = 36个数据点)
const int BUFFER_SIZE = 60;
String timeBuffer[BUFFER_SIZE];
float depthBuffer[BUFFER_SIZE];  // 新增深度数据缓冲区
int writeIndex = 0;        // 写入位置
int readIndex = 0;         // 读取位置
int dataCount = 0;         // 当前数据数量
unsigned long lastRecordTime = 0;
const unsigned long RECORD_INTERVAL = 5000; // 5秒 = 5000毫秒


String utcTime = "";
unsigned long utcStartMillis = 0;  // 存储UTC时间对应的millis值
bool isTimeInitialized = false;    // 时间是否已初始化

// Initialize pressure sensor
MS5837 sensor;


//Motor Control Parameters
// 定义马达控制引脚
const int IN1 = 25;  // 马达控制引脚1
const int IN2 = 26;  // 马达控制引脚2
const int TopLimitBtn = 19; // 下降时工作
const int DownLimitBtn = 18; // 上升时工作

// 定义阶段
enum Phase {
  IDLE,
  DESCENDING,
  WAITING,
  ASCENDING,
  COMPLETED
};

Phase currentPhase = IDLE;
unsigned long phaseStartTime = 0;
bool startProcess = false;
bool progress = false;
bool motorRunning = false;

bool testPull = false;
bool testPush = false;
bool testPullAll = false;  // 新增：测试完全拉出
bool testPushAll = false;  // 新增：测试完全推入
bool forceStop = false;

String inputString = "";      // 存储接收到的串口数据
bool stringComplete = false;  // 标记是否接收到完整字符串

// 创建WebServer对象
WebServer server(80);

/**
 * 设置WiFi接入点模式
 */
void setupWiFi() {
  WiFi.mode(WIFI_AP);
  WiFi.softAP(ssid, password);
  
  if (DEBUG_MODE) {
    Serial.print("接入点已创建, IP地址: ");
    Serial.println(WiFi.softAPIP());
  }
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
    response += String(depthBuffer[readIndex], 2) + " meters";
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
    ascendTime = doc["ascend_time"].as<unsigned long>();
    waitTime = doc["wait_time"].as<unsigned long>();
    DEBUG_MODE = doc["debug_mode"].as<bool>();
    useTimer = doc["use_timer"].as<bool>();  // 接收useTimer参数
    companyID = doc["company_id"].as<String>();
    
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
    // 新增：首次初始化時設置深度偏移
    depthOffset = depthData;
    
    // 打印接收到的参数
    if (DEBUG_MODE) {
      Serial.println("Received initial connection parameters:");
      Serial.print("Company ID: ");
      Serial.println(companyID);
      Serial.print("UTC Time: ");
      Serial.println(utcTime);
      Serial.print("Descend Time: ");
      Serial.println(descendTime);
      Serial.print("Ascend Time: ");
      Serial.println(ascendTime);
      Serial.print("Wait Time: ");
      Serial.println(waitTime);
      Serial.print("Debug Mode: ");
      Serial.println(DEBUG_MODE ? "Enabled" : "Disabled");
      Serial.print("Use Timer: ");
      Serial.println(useTimer ? "Enabled" : "Disabled");
      Serial.print("Total seconds: ");
      Serial.println(totalSeconds);
    }
    
    server.send(200, "text/plain", "Initial connection successful");
  } else {
    server.send(405, "text/plain", "Method Not Allowed");
  }
}

/**
 * 处理马达控制请求
 */
void handleMotorControl() {
  if (server.method() == HTTP_POST) {
    if (DEBUG_MODE) {
      Serial.println("Received motor control request");
      Serial.print("Current progress: ");
      Serial.println(progress ? "true" : "false");
      Serial.print("Current startProcess: ");
      Serial.println(startProcess ? "true" : "false");
    }
    
    if (!progress) {  // 只有在没有进行中的操作时才启动
      startProcess = true;
      currentPhase = DESCENDING;
      if (DEBUG_MODE) {
        Serial.println("Motor control started - Phase set to DESCENDING");
      }
      server.send(200, "text/plain", "Motor control started");
    } else {
      if (DEBUG_MODE) {
        Serial.println("Motor control rejected - Already in progress");
      }
      server.send(400, "text/plain", "Motor is already running");
    }
  } else {
    if (DEBUG_MODE) {
      Serial.println("Invalid method for motor control");
    }
    server.send(405, "text/plain", "Method Not Allowed");
  }
}

void handleTestPull() {
  if (server.method() == HTTP_POST) {
    testPull = true;
    server.send(200, "text/plain", "Test pull started");
  } else {
    server.send(405, "text/plain", "Method Not Allowed");
  }
}

void handleTestPush() {
  if (server.method() == HTTP_POST) {
    testPush = true;
    server.send(200, "text/plain", "Test push started");
  } else {
    server.send(405, "text/plain", "Method Not Allowed");
  }
}

void handleTestPullAll() {
  if (server.method() == HTTP_POST) {
    testPullAll = true;
    server.send(200, "text/plain", "Test pull all started");
  } else {
    server.send(405, "text/plain", "Method Not Allowed");
  }
}

void handleTestPushAll() {
  if (server.method() == HTTP_POST) {
    testPushAll = true;
    server.send(200, "text/plain", "Test push all started");
  } else {
    server.send(405, "text/plain", "Method Not Allowed");
  }
}

void handleForceStop() {
  if (server.method() == HTTP_POST) {
    forceStop = true;
    server.send(200, "text/plain", "Force stop command received");
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
  if (DEBUG_MODE) {
    Serial.println("\n启动时间数据服务器");
  }
  
  // Initialize I2C and pressure sensor
  Wire.begin();
  while (!sensor.init()) {
    if (DEBUG_MODE) {
      Serial.println("Init failed!");
      Serial.println("Are SDA/SCL connected correctly?");
      Serial.println("Blue Robotics Bar30: White=SDA, Green=SCL");
    }
    delay(5000);
  }
  sensor.setFluidDensity(997); // kg/m^3 (freshwater, 1029 for seawater)
  
  // 初始化马达控制引脚
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(TopLimitBtn, INPUT_PULLUP);
  pinMode(DownLimitBtn, INPUT_PULLUP);
  
  // 初始化缓冲区
  for(int i = 0; i < BUFFER_SIZE; i++) {
    timeBuffer[i] = "";
  }
  
  setupWiFi();
  
  // 设置Web服务器路由
  server.on("/", HTTP_GET, handleRoot);
  server.on("/data", HTTP_GET, handleData);
  server.on("/init", HTTP_POST, handleInit);
  server.on("/motor/start", HTTP_POST, handleMotorControl);
  server.on("/motor/test/pull", HTTP_POST, handleTestPull);
  server.on("/motor/test/push", HTTP_POST, handleTestPush);
  server.on("/motor/test/pullall", HTTP_POST, handleTestPullAll);  // 新增路由
  server.on("/motor/test/pushall", HTTP_POST, handleTestPushAll);  // 新增路由
  server.on("/motor/force/stop", HTTP_POST, handleForceStop);
  server.onNotFound(handleNotFound);
  
  // 启动服务器
  server.begin();
  if (DEBUG_MODE) {
    Serial.println("HTTP服务器已启动");
  }
  
  // 初始化马达状态
  stopMotor();
}

void loop() {
  server.handleClient();
  
  // Update sensor readings
  sensor.read();
  depthData = sensor.depth() - depthOffset;  // Update depth data with offset
  
  unsigned long currentTime = millis();

  // Test functionality
  if (testPull) {
    startMotorForward();
    delay(100);
    stopMotor();
    testPull = false;
  }
  
  if (testPush) {
    startMotorReverse();
    delay(100);
    stopMotor();
    testPush = false;
  }

  // 新增：测试完全拉出功能
  if (testPullAll) {
    if (forceStop) {
      stopMotor();
      testPullAll = false;
      forceStop = false;
      if (DEBUG_MODE) {
        Serial.println("Pull all test force stopped!");
      }
    } else {
      startMotorForward();
      if (digitalRead(TopLimitBtn) == LOW) {
        startMotorReverse();
        delay(250);
        stopMotor();
        testPullAll = false;
        if (DEBUG_MODE) {
          Serial.println("Pull all completed - Top limit reached");
        }
      }
    }
  }

  // 新增：测试完全推入功能
  if (testPushAll) {
    if (forceStop) {
      stopMotor();
      testPushAll = false;
      forceStop = false;
      if (DEBUG_MODE) {
        Serial.println("Push all test force stopped!");
      }
    } else {
      startMotorReverse();
      if (digitalRead(DownLimitBtn) == LOW) {
        startMotorForward();
        delay(250);
        stopMotor();
        testPushAll = false;
        if (DEBUG_MODE) {
          Serial.println("Push all completed - Down limit reached");
        }
      }
    }
  }
  
  // Check if process should start
  if (startProcess && !progress) {
    if (DEBUG_MODE) {
      Serial.println("Starting motor process");
      Serial.print("startProcess: ");
      Serial.println(startProcess);
      Serial.print("progress: ");
      Serial.println(progress);
    }
    progress = true;
    phaseStartTime = millis();  // 初始化阶段开始时间
    startMotorForward();
    if (DEBUG_MODE) {
      Serial.println("Starting descending phase");
    }
  }
  
  // Main process control
  if (progress) {
    // Check for force stop signal
    if (forceStop) {
      stopMotor();
      progress = false;
      startProcess = false;
      currentPhase = IDLE;
      if (DEBUG_MODE) {
        Serial.println("Process force stopped!");
      }
      forceStop = false;
      return;
    }

    // 每1秒打印状态
    if (millis() % 1000 < 500 && DEBUG_MODE) {
      Serial.print("Phase time elapsed: ");
      Serial.print((millis() - phaseStartTime) / 1000);
      Serial.print("s, Motor running: ");
      Serial.println(motorRunning ? "Yes" : "No");
    }
    
    switch (currentPhase) {
      case DESCENDING:
        if (digitalRead(TopLimitBtn) == LOW || (useTimer && millis() - phaseStartTime >= descendTime)) {
          startMotorReverse();  //move back a little
          delay(250);
          stopMotor();
          currentPhase = WAITING;
          phaseStartTime = millis();  // 更新为等待阶段开始时间
          if (DEBUG_MODE) {
            Serial.println("Descending phase completed");
          }
        }
        break;
        
      case WAITING:
        if (millis() - phaseStartTime >= waitTime) {  // 只使用等待时间
          startMotorReverse();
          currentPhase = ASCENDING;
          phaseStartTime = millis();  // 更新为上升阶段开始时间
          if (DEBUG_MODE) {
            Serial.println("Starting ascending phase");
          }
        }
        break;
        
      case ASCENDING:
        if (digitalRead(DownLimitBtn) == LOW || (useTimer && millis() - phaseStartTime >= ascendTime)) {  // 只使用上升时间
          startMotorForward(); //move back a little
          delay(250);
          stopMotor();
          currentPhase = COMPLETED;
          progress = false;
          startProcess = false;
          if (DEBUG_MODE) {
            Serial.println("Ascending phase completed");
          }
        }
        break;
        
      case COMPLETED:
        if (DEBUG_MODE) {
          Serial.println("Process completed");
        }
        delay(5000);
        
        break;
        
      default:
        break;
    }
  }
  
  // 只有在时间初始化后才记录数据
  if(isTimeInitialized && currentTime - lastRecordTime >= RECORD_INTERVAL) {
    // 获取当前时间
    String currentTimeStr = getTimeString();
    
    // 存储到缓冲区
    timeBuffer[writeIndex] = currentTimeStr;
    depthBuffer[writeIndex] = depthData;  // 存储深度数据
    
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
      //Serial.print("Buffer updated - Write Index: ");
      //Serial.print(writeIndex);
      //Serial.print(", Read Index: ");
      //Serial.println(readIndex);
      Serial.print("Depth at this record: ");
      Serial.print(depthData, 2);
      Serial.println(" meters");
    }
  }

  //delay(500);  // 增加延迟到0.5秒，减少CPU使用率
  delay(250);  // 增加延迟到0.25秒，减少CPU使用率
}

//linear actuator pull
void startMotorForward() {
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);
  motorRunning = true;
}

//linear actuator push
void startMotorReverse() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);
  motorRunning = true;
}

void stopMotor() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  motorRunning = false;
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
