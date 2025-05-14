#include <BluetoothSerial.h>
#include <Arduino.h>
#include <ESP_Google_Sheet_Client.h>
#include <GS_SDHelper.h>
#include <iostream>
#include <list>
#include <WiFi.h>
#include "time.h"
#include "Timer.h"
#include <NTPClient.h>
#include <WiFiUdp.h>
#include <Wire.h>
#include <iostream>
#include <chrono>
#include <thread>
#include "MS5837.h"

using namespace std;

MS5837 sensor;
const char* ssid = "pcmsrov";       
const char* password = "12345678"; 
const int pin1 = 16;                
const int pin2 = 17;                

list<int> timeList;
list<float> depthList;

#define PROJECT_ID "float-info"

#define CLIENT_EMAIL "floattransmitter@float-info.iam.gserviceaccount.com"

const char PRIVATE_KEY[] PROGMEM = "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC642yaOO24f20Z\nkyQby2UOoNV3AsbVEjuPVDdLw/VRS3GpWtTcp4+SWWuPALIdNUaW8UCQESDiLnyL\n6E8M0Dm/nQyDyYgix8mJ8sG3CeatkzNmVbEdCeLHqsX5hSQjtOyTJN3snl/+jmbx\nmiT9r6VwZfwED4k536XmlPTOd7mU/yjK9bAE5ntmbpKBHQj/WrHUpykZgTYZe8M0\n1SY+f6cRLyxB9KJyB4UZCRsdmGvbABUbFmf+PK1tVN9QhweZK488Nt6nQHXVlp12\nlIiGKBp5QCW/F91LCVXxIx5uDCA/Jib0fAVxvAY1s8HvBgquVF0AtBfNXgZiN/qC\n6do+s9BfAgMBAAECggEACCYJYrIPv2ci8SYGwYV9SwV9OTqwQ7MPUMEJxi5toFVL\nR+iTdmmB644lj+8mVPqxMLylJYLxrZr8SDdhVvwvQGkPFiHv4yBV68NfaeUvHytX\nZuNenRcEwdLy3d3NxRbK5+GIIZyIL/eyil8/tKX3by6rLdwljhXvzF17TRNQTqw8\nO0EZVsM5H6OdOOiwBwF/yg/OjY5ISfy9n8Uq4ri/7003LcXgoiyFlEjg1qYdkW9e\nADf5mbxd77xFjqPs7nDc5NrLf9ZZ8QqbNCTkNAfmpQTIRFyOxoSZGMxCGI0+yZkG\nQUPku5h4XmRuoN3TFUveV9rBI8PXLvU67lWkq+woxQKBgQD2rSX26TM8jqq2vSZs\ng8Y3NxB2yfC1JEHqZOyvdHD2mbNrgxpqiMOSOdu2yIJIvekshzNIHLI7po4pB8rq\nWKcYw3YLBh8SsQmlSGZONl4VSrs4rUjk+tKMIJgnWeq5mKE+tG/FJgH0hTtrWffk\nnWqMGXtRTVbIbjrL5IvH7jhUywKBgQDB88PBLwBB2zzcTQrRudeCfnKr6uGj6w4S\npAc5S+d67s1evISf60/i2kxsZJbm0NrvPo5YTZZ6jAg4VIRtq4FAm/1P7Ao/levG\n+UUWK2gg9iEwKJ/g9/r6Pyc3sG6vi4ZmDTzaby+RaRXsTZzHUKj8bGMEXAPujPg4\nSdVytL9UPQKBgQCjuhtHvlMmr575uaRGRFSNE3xXDAQ7hvxFQoWik0vjMfNXueYP\nrgT5CnQd5woqk/qvdnGAPKPEWfFjpGt3ji4ijqHMAV0gf+diECLvaMCbq0WHAeUv\nLpgPMBctj03vsDHeN88z8N09Wi0tPML/t8gfg05JkWa3lApsiJ6KrkAvbwKBgE0w\nGD3v2Khc+jGqr52b2nrim/xzc+1qhKVChmV1IeC43R7Q4+9JFPfxbOzOc4fUou0H\n9lqKNlL7G+JfMHz8/mmaKwv9om5/2d/MIIScLcrAaaDi6g38YvPo4lC1dLeETa6b\nohZEnae/LKxojvZ70WT0NcvsWtw7WiX8rGgEKwj5AoGBAKH1RwEOEOCH+NryGzbK\n7pk5tJP30usAt4BFNGbhPPYIruNZl0O1mYtNH5oT7srPC54XOpDkXlAq6gOHPXiJ\nsnGJSdNw2InLZCOp4OWSgM1PVdkRwgJ0kA4tygyx/a4b4/m5CbfYIh7AptUIUZsd\nNpxeGT1dwYvH7wyJFhYNabyA\n-----END PRIVATE KEY-----\n";

const char spreadsheetId[] = "1l9fQ2_P42tdo-NMY-iV2iqaUs8bRqyZpD1TH2Bab2fw";

unsigned long timerDelay = 3;

void tokenStatusCallback(TokenInfo info);

float a;
float depth;
String d;

// 獲取時間設定(不用改)
const char* ntpServer = "pool.ntp.org";
const long gmtOffset_sec = 0;
const int daylightOffset_sec = 3600;

int lastTime;
int startTime;
unsigned long epochTime;

WiFiUDP ntpUDP;
NTPClient timeClient(ntpUDP, ntpServer, gmtOffset_sec, daylightOffset_sec);

BluetoothSerial BT;     // 建立藍牙串口物件
struct tm timeinfoTmp;  // 建立時間結構
Timer timer;            // 建立計時物件


void getTime() {
  // 如果WiFi已連線則獲取時間
  if (WiFi.status() == WL_CONNECTED) {
    // 獲取時間的設定(不用改)
    configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
    struct tm timeinfo;
    getLocalTime(&timeinfo);

    // a = sensor.pressure() * 20.0;
    // depth = sensor.depth() + 10;

    // 將結果通過藍牙串口傳送到電腦(記得加返team number)
    BT.println(&timeinfo, "%H:%M:%S UTC R4"); 

  } else {
    // 否則傳送空字串表示無改變
    BT.println("");
  }
}

void setup() {
  // 串口初始化(Debug用)
  Serial.begin(115200);
  Wire.begin();

  // 針腳初始化
  pinMode(pin1, OUTPUT);
  pinMode(pin2, OUTPUT);

  // 藍牙初始化
  BT.begin("PCMSROV.m1");
  Serial.println("Setup complete.");

  // WiFi初始化
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);

  // 使計時器每秒執行一次getTime()
  timer.every(1000, getTime);
  GSheet.setTokenCallback(tokenStatusCallback);
  GSheet.setPrerefreshSeconds(3540);
  GSheet.begin(CLIENT_EMAIL, PROJECT_ID, PRIVATE_KEY);

  sensor.setFluidDensity(997);
  timeClient.begin();
  timeClient.update();
}

void loop() {
  timeClient.update();
  timer.update();      // 每次Loop更新計時器(會自動平衡刷新率，使getTime()保持在一秒一次)
  String inputFromPC;  // 每次Loop重置接收指令用的空字串
  if (BT.available()) {
    // 當藍牙串口收到訊息時運行以下程式
    inputFromPC = BT.readString();  // 讀取文字訊息
    Serial.println(inputFromPC);    // 打印文字訊息(Debug用)
    // 以下指令對照電腦端，不作解釋
    if (inputFromPC == "push") {
      BT.println("Float is pushing!");
      digitalWrite(pin1, HIGH);  // 將pin1改成高電位
      digitalWrite(pin2, LOW);   // 將pin2改成低電位
      delay(1000 * 10.5);        // 因為放Switch感應推杆好麻煩，所以直接計時
      digitalWrite(pin1, LOW);   // 使兩pin都是低電位，推杆
    } else if (inputFromPC == "pull") {
      BT.println("Float is pulling!");
      digitalWrite(pin1, LOW);
      digitalWrite(pin2, HIGH);
      delay(1000 * 12);  // 其實用timer會更好，但delay可以模擬藍牙斷線，所以無改到
      digitalWrite(pin1, LOW);
    } else if (inputFromPC == "dive") {
      BT.println("Float is diving!");
      lastTime = 0;
      int time = timeClient.getEpochTime();
      startTime = time;
      digitalWrite(pin1, LOW);
      digitalWrite(pin2, HIGH);
      while (time < startTime + 120) {
        time = timeClient.getEpochTime();
        if (time - lastTime > timerDelay) {
          lastTime = time;
          sensor.read();
          depth = sensor.depth() + 10;
          timeList.push_back(time);
          depthList.push_back(depth);
        }
        if (time == startTime + 60) {
          digitalWrite(pin1, LOW);
          digitalWrite(pin2, LOW);
          digitalWrite(pin1, HIGH);
          digitalWrite(pin2, LOW);
        }
      }
      digitalWrite(pin1, LOW);
      do {
        bool ready = GSheet.ready();
        if (ready) {
          FirebaseJson response;
          FirebaseJson valueRange;
          for (int i = 0; i < timeList.size(); i++) {
            valueRange.add("majorDimension", "COLUMNS");
            valueRange.set("values/[0]/[0]", *next(timeList.begin(), i));
            valueRange.set("values/[1]/[0]", *next(depthList.begin(), i));

            bool success = GSheet.values.append(&response, spreadsheetId, "Sheet1!A1", &valueRange);
            if (success) {
              response.toString(Serial, true);
              valueRange.clear();
            }
            else {
              Serial.println(GSheet.errorReason());
            }
          }
        }
      } while (WiFi.status() != WL_CONNECTED);
      BT.println("Uploaded depth data!");
      delay(1000 * 10);
      timeList.clear();
      depthList.clear();  
    } else if (inputFromPC.indexOf("wifi") > -1) {
      String tmp[3];
      for (int i = 0; i < 3; i++) {
        int index = inputFromPC.lastIndexOf("^");
        int length = inputFromPC.length();
        tmp[i] = inputFromPC.substring(index + 1, length);
        inputFromPC.remove(index, length);
      }
      BT.println("Float Connnecting to: " + tmp[1]);
      char new_ssid[20];                     // 初始化長度為20字元的字符new_ssid
      char new_password[20];                 // 初始化長度為20字元的字符new_password
      tmp[1].toCharArray(new_ssid, 20);      // 將字串轉換為字符
      tmp[0].toCharArray(new_password, 20);  // 將字串轉換為字符
      Serial.println(new_ssid);              // Debug用，可Delete
      Serial.println(new_password);          // Debug用，可Delete
      WiFi.disconnect();                     // 重置WiFi連線
      WiFi.begin(new_ssid, new_password);    // 使用新SSID及密碼連接WiFi
      for (int i = 0; i < 20; i++) {
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
void tokenStatusCallback(TokenInfo info){
    if (info.status == token_status_error){
        GSheet.printf("Token info: type = %s, status = %s\n", GSheet.getTokenType(info).c_str(), GSheet.getTokenStatus(info).c_str());
        GSheet.printf("Token error: %s\n", GSheet.getTokenError(info).c_str());
    }
    else{
        GSheet.printf("Token info: type = %s, status = %s\n", GSheet.getTokenType(info).c_str(), GSheet.getTokenStatus(info).c_str());
    }
}
