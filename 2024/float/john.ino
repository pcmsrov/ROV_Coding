#include <BluetoothSerial.h>
#include <WiFi.h>
#include "time.h"
#include "Timer.h"
#include <Arduino.h>
#include "FS.h"
#include <LittleFS.h>
#include <AsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <Wire.h>
#include "MS5837.h"

#define FORMAT_LITTLEFS_IF_FAILED true

AsyncWebServer server(80);

MS5837 sensor;
const char* path = "/data.txt";
const char* ssid     = "HUAWEI_B316_4B30"; // WiFi名稱
const char* password = "12345677";       // WiFi密   碼
const int pin1 = 16; // 紅色板IN1 pin所接的ESP32 pin
const int pin2 = 17; // 紅色板IN2 pin所接的ESP32 pin

float a;
float depth;
String d;
String dataMessage;

// 獲取時間設定(不用改)
const char* ntpServer = "pool.ntp.org";
const long  gmtOffset_sec = 0;
const int   daylightOffset_sec = 3600;

BluetoothSerial BT;    // 建立藍牙串口物件
struct tm timeinfoTmp; // 建立時間結構
Timer timer;           // 建立計時物件

void writeFile(fs::FS &fs, const char * path, const char * message) {
  File file = fs.open(path, FILE_WRITE)
  if (!file) {
    Serial.println("failed to open file for writing");
    return;
  }
  if (file.print(message)) {
    Serial.println("file written");
  } else {
    Serial.println("write failed");
  }
  file.close();
}


void appendFile(fs::FS &fs, const char * path, const char * message) {
  if (!file) {
    Serial.println("failed to open file");
    return;
  }
  if (file.print(message)) {
    Serial.println("message appended");
  } else {
    Serial.println("append failed");
  }
  file.close();
}

void readFile(fs::FS &fs, const char * path) {
  File file = fs.open(path);
  if (!file || file.isDirectory()) {
    Serial.println("failed to open filed");
  }
  while (file.avilable()) {
    Serial.write(file.read());
  }
  file.close();
}

void setup() {
  // 串口初始化(Debug用)
  Serial.begin(115200);
  if (!LittleFS.begin(FORMAT_LITTLEFS_IF_FAILED)) {
    Serial.println("mount failed");
    return;
  }
  else {
    Serial.println("mounted successfully");
  }
  if (!file) {
    writeFile(LittleFS, "/data.txt", "Time, Depth, Pressure \r\n");
  }
  Wire.begin();

  server.on("/", HTTP_GET, [](AsyncWebServerRequest *request){
    request->send(SD, "/index.html", "text/html");
  });

  // Handle the download button
  server.on("/download", HTTP_GET, [](AsyncWebServerRequest *request){
    request->send(SD, "/data.txt", String(), true);
  });

  // Handle the View Data button
  server.on("/view-data", HTTP_GET, [](AsyncWebServerRequest *request){
    request->send(SD, "/data.txt", "text/plain", false);
  });

  // Handle the delete button
  server.on("/delete", HTTP_GET, [](AsyncWebServerRequest *request){
    deleteFile(SD, dataPath);
    request->send(200, "text/plain", "data.txt was deleted.");
  });
  server.begin();

  // 針腳初始化
  pinMode(pin1, OUTPUT);
  pinMode(pin2, OUTPUT);

  // 藍牙初始化
  BT.begin("PCMSROV.float");
  Serial.println("Setup complete.");

  // WiFi初始化
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);

  // 使計時器每秒執行一次getTime()
  timer.every(1000, getTime);

  sensor.setFluidDensity(997);
}

void getTime() {
  // 如果WiFi已連線則獲取時間
  if (WiFi.status() == WL_CONNECTED) {
    // 獲取時間的設定(不用改)
    configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
    struct tm timeinfo;
    getLocalTime(&timeinfo);
    BT.println(WiFi.localIP());
    delay(5000);
    a = sensor.pressure() * 20.0;
    depth = sensor.depth()+10;

    // 將結果通過藍牙串口傳送到電腦(記得加返team number)
    BT.println(&timeinfo, "%H:%M:%S UTC RN31");

    BT.print(a);
    BT.print("mbar");
    BT.print("      ");
    BT.print(depth);
    BT.print("m");

  } else {
    // 否則傳送空字串表示無改變
    BT.println("");
  }
}

void loop() {
  timer.update(); // 每次Loop更新計時器(會自動平衡刷新率，使getTime()保持在一秒一次)
  String inputFromPC; // 每次Loop重置接收指令用的空字串

  sensor.read();

  Serial.print("Pressure: ");
  Serial.print(sensor.pressure()*20);
  Serial.println(" mbar");

  Serial.print("Temperature: ");
  Serial.print(sensor.temperature());
  Serial.println(" deg C");

  Serial.print("Depth: ");
  Serial.print(sensor.depth()+10);
  Serial.println(" m");
  delay(1000);

  dataMessage = String(getTime()) + "," + String(sensor.depth() + 10) + "," + String(sensor.pressure() * 20) + "\r\n";
  appendFile(LittleFS, "/data.txt", dataMessage.c_str());

  if (BT.available()) {
    // 當藍牙串口收到訊息時運行以下程式
    inputFromPC = BT.readString(); // 讀取文字訊息
    Serial.println(inputFromPC);   // 打印文字訊息(Debug用)
    // 以下指令對照電腦端，不作解釋
    if (inputFromPC == "push") {
      BT.println("Float is pushing!");
      digitalWrite(pin1, HIGH); // 將pin1改成高電位
      digitalWrite(pin2, LOW);  // 將pin2改成低電位
      delay(1000*10.5);  // 因為放Switch感應推杆好麻煩，所以直接計時
      digitalWrite(pin1, LOW);  // 使兩pin都是低電位，推杆
    } else if (inputFromPC == "pull") {
      BT.println("Float is pulling!");
      digitalWrite(pin1, LOW);
      digitalWrite(pin2, HIGH);
      delay(1000*12);  // 其實用timer會更好，但delay可以模擬藍牙斷線，所以無改到
      digitalWrite(pin1, LOW);
    } else if (inputFromPC == "dive") {
      BT.println("Float is diving!");
      digitalWrite(pin1, LOW);
      digitalWrite(pin2, HIGH);
      delay(1000*20);
      digitalWrite(pin1, HIGH);
      digitalWrite(pin2, LOW);
      delay(1000*10.5);
      digitalWrite(pin1, LOW);
    } else if (inputFromPC.indexOf("wifi") > -1) {
      // 以下為遠程控制連接WiFi的程式
      String tmp[3];
      // 將"wifi^HUAWEI P40 Pro^12345678以"^"分割成字串列表
      for (int i=0;i<3;i++) {
        int index = inputFromPC.lastIndexOf("^");
        int length = inputFromPC.length();
        tmp[i] = inputFromPC.substring(index+1, length);
        inputFromPC.remove(index, length);
      }
      BT.println("Float Connnecting to: " + tmp[1]);
      char new_ssid[20];     // 初始化長度為20字元的字符new_ssid
      char new_password[20]; // 初始化長度為20字元的字符new_password
      tmp[1].toCharArray(new_ssid, 20);     // 將字串轉換為字符
      tmp[0].toCharArray(new_password, 20); // 將字串轉換為字符
      Serial.println(new_ssid);     // Debug用，可Delete
      Serial.println(new_password); // Debug用，可Delete
      WiFi.disconnect();   // 重置WiFi連線
      WiFi.begin(new_ssid, new_password);  // 使用新SSID及密碼連接WiFi
      // 等待WiFi成功連接（20秒）
      for (int i=0;i<20;i++) {
        Serial.print(".");
        if (WiFi.status() == WL_CONNECTED) {
          BT.println("WiFi connected.");
          return;  // 成功時直接進入下一Loop
        }
        delay(1000);
      }
      // 成功時直接進入下一Loop，不會運行以下程式
      BT.println("Fail to connect WiFi.");
    } else if (inputFromPC != "") {
      BT.println("Invalid Action!");
    }
  }
}

