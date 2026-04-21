#include <Wire.h>

// ===================== 完全按照你的接线，已修复编译错误 =====================
const float TARGET_DEPTH = 0.24;        // 目标深度 0.24米
const float DEPTH_TOLERANCE = 0.01;    // 误差1厘米内停止
const int READ_INTERVAL = 100;         // 读取间隔

// 限位开关
const int TOP_LIMIT_PIN = 19;
const int BOTTOM_LIMIT_PIN = 18;

// L298N 电机驱动
const int IN1 = 25;  // 上升
const int IN2 = 26;  // 下沉

// JY-8871 常用I2C地址
#define SENSOR_ADDR 0x76

void setup() {
  Serial.begin(115200);
  Wire.begin();  // ESP32默认SDA=21 SCL=22，无需重复定义
  
  pinMode(TOP_LIMIT_PIN, INPUT_PULLUP);
  pinMode(BOTTOM_LIMIT_PIN, INPUT_PULLUP);
  
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  
  stopMotor();
  Serial.println("===== 浮球深度控制系统已启动 =====");
  Serial.println("目标深度：0.24 m");
  delay(2000);
}

// 停止推杆
void stopMotor() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
}

// 上升（浮球升高）
void up() {
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);
}

// 下沉（浮球降低）
void down() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);
}

// 读取 JY-8871 深度（单位：米）
float getDepth() {
  float depth = 0.0;
  Wire.beginTransmission(SENSOR_ADDR);
  Wire.write(0x01);
  Wire.endTransmission(false);
  Wire.requestFrom(SENSOR_ADDR, 4);
  
  if (Wire.available() >= 4) {
    byte d1 = Wire.read();
    byte d2 = Wire.read();
    byte d3 = Wire.read();
    byte d4 = Wire.read();
    uint16_t val = (d2 << 8) | d1;
    depth = val / 1000.0f;
  }
  return depth;
}

// 检查限位开关
int checkLimit() {
  int top = digitalRead(TOP_LIMIT_PIN);
  int bot = digitalRead(BOTTOM_LIMIT_PIN);

  if (top == LOW) return 1;    // 上限触发
  if (bot == LOW) return 2;    // 下限触发
  return 0;                    // 正常
}

void loop() {
  // 1. 限位开关最高优先
  int limit = checkLimit();
  if (limit == 1) {
    stopMotor();
    Serial.println("⚠️  上限开关触发 —— 停止上升");
    delay(100);
    return;
  }
  if (limit == 2) {
    stopMotor();
    Serial.println("⚠️  下限开关触发 —— 停止下沉");
    delay(100);
    return;
  }

  // 2. 读取当前深度
  float now = getDepth();

  // 3. 自动控制逻辑
  if (now > TARGET_DEPTH + DEPTH_TOLERANCE) {
    down();
    Serial.printf("📉 深度过高：%.3f m → 下沉\n", now);
  }
  else if (now < TARGET_DEPTH - DEPTH_TOLERANCE) {
    up();
    Serial.printf("📈 深度过低：%.3f m → 上升\n", now);
  }
  else {
    stopMotor();
    Serial.printf("✅ 深度稳定：%.3f m → 停止\n", now);
  }

  delay(READ_INTERVAL);
}