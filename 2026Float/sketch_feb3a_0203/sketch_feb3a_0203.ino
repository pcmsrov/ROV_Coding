#include <ESP32Servo.h>

// 定义引脚
#define SERVO_PIN 25
#define POT_PIN 34

Servo myServo;

void setup() {
  // 为避免定时器冲突，建议在 attach 前设置定时器
  myServo.setPeriodHertz(50); // 标准伺服电机使用50Hz
  myServo.attach(SERVO_PIN, 500, 2500); // 设置脉宽范围
  pinMode(POT_PIN, INPUT);
}

void loop() {
  int potValue = analogRead(POT_PIN);
  int angle = map(potValue, 0, 4095, 0, 180);
  myServo.write(angle);
  delay(50);
}