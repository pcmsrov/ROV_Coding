#include <WiFi.h>
#include <WiFiClient.h>
#include <WiFiServer.h>
#include <Wire.h>
#include <BluetoothSerial.h>
#include <Wifi.h>
#include "time.h"
#include "Timer.h"
#include "MS5837.h"

// WiFi 參數
MS5837 sensor;
const char* ssid = "HUAWEI_B316_4B30";
const char* password = "12345677";
const int pin1 = 16;
const int pin2 = 17;

float a;
float depth;
String d;
const char* ntpServer = "pool.ntp.org";
const long offset = 0;
const int dayoffset = 3600;

BluetoothSerial BT;
struct tm timeinfoTmp;
Timer timer;


// 設定 WiFi 伺服器端口
WiFiServer server(80);

void setup() {
  Serial.begin(115200);
  Wire.begin();

  pinMode(pin1, OUTPUT);
  pinMode(pin2, OUTPUT);

  BT.begin("PCMSROV.float")
  Serial.println("Setup complete");

  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("正在連接WiFi...");
  }

  Serial.println("WiFi 連接成功");
  Serial.print("IP 地址: ");
  BT.println(WiFi.localIP());

  server.begin();

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

    a = sensor.pressure() * 20.0;
    depth = sensor.depth()+10;

    // 將結果通過藍牙串口傳送到電腦(記得加返team number)
    BT.println(&timeinfo, "%H:%M:%S UTC RN31");

    BT.print(a);
    BT.print("mbar");
    BT.print("      ");
    BT.print(depth);
    BT.print("m");
    if (client.available()) {
      String request = client.readStringUntil('\r');
      Serial.println(request);
      client.flush();

        // 讀取深度傳感器資料
      float depth = depthSensor.readDepth(); // 替換為實際的讀取方法

        // 建立 CSV 字符串
      String csvData = "深度\n";
      csvData += String(depth) + "\n";

        // 傳送 CSV 資料到客戶端
      client.print(csvData);

      break;
    }
  } else {
    // 否則傳送空字串表示無改變
    BT.println("");
  }
}

void loop() {
  timer.update()
  String inputFromPc;

  WiFiClient client = server.available();
  BT.println(WiFi.localIP());
  delay(5000);

  sensor.read();


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
