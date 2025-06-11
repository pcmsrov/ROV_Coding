#include <Arduino.h>

void setup() {
  Serial.begin(115200); // 初始化串口
}

void loop() {
  static unsigned long lastPrint = 0;
  unsigned long now = millis();
  if (now - lastPrint >= 2000) { // 每2秒
    lastPrint = now;
    // 使用ESP32內建RTC計時（millis為軟件RTC，硬件RTC需用deep sleep等）
    Serial.print("Millis: ");
    Serial.println(now);
  }
}
