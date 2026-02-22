// 引脚定义
#define FAN_IN1_PIN 25   // DRV8871 IN1（正转控制）
#define FAN_IN2_PIN 26   // DRV8871 IN2（反转控制）
#define POT_PIN 34       // 电位器信号脚

// PWM 设置
#define PWM_CHANNEL1 0   // IN1 对应 PWM 通道
#define PWM_CHANNEL2 1   // IN2 对应 PWM 通道
#define PWM_FREQ 25000   // 25kHz 适配风扇/马达
#define PWM_RESOLUTION 8 // 0-255 调速范围

// 电位器参数
#define POT_MID 2048     // 电位器中点值
#define DEAD_ZONE 50     // 中点死区（±50）
#define POT_MIN 0        // 电位器最小值
#define POT_MAX 4095     // 电位器最大值

void setup() {
  // 初始化 PWM 通道（ESP32 标准写法）
  ledcSetup(PWM_CHANNEL1, PWM_FREQ, PWM_RESOLUTION);
  ledcSetup(PWM_CHANNEL2, PWM_FREQ, PWM_RESOLUTION);
  
  // 绑定 PWM 到引脚（ESP32 专用，注意函数名是 ledcAttachPin）
  ledcAttachPin(FAN_IN1_PIN, PWM_CHANNEL1);
  ledcAttachPin(FAN_IN2_PIN, PWM_CHANNEL2);
  
  // 初始状态：两个引脚都输出 0（马达停止）
  ledcWrite(PWM_CHANNEL1, 0);
  ledcWrite(PWM_CHANNEL2, 0);
  
  // 电位器设为输入
  pinMode(POT_PIN, INPUT);
}

void loop() {
  // 1. 读取电位器当前值
  int potValue = analogRead(POT_PIN);
  
  // 2. 判断电位器位置并控制马达
  if (potValue < POT_MID - DEAD_ZONE) {
    // 左侧：正转，转速 = 偏离中点的幅度
    int speed = map(potValue, POT_MIN, POT_MID - DEAD_ZONE, 255, 0);
    ledcWrite(PWM_CHANNEL1, speed);  // IN1 输出 PWM
    ledcWrite(PWM_CHANNEL2, 0);      // IN2 低电平
  } 
  else if (potValue > POT_MID + DEAD_ZONE) {
    // 右侧：反转，转速 = 偏离中点的幅度
    int speed = map(potValue, POT_MID + DEAD_ZONE, POT_MAX, 0, 255);
    ledcWrite(PWM_CHANNEL1, 0);      // IN1 低电平
    ledcWrite(PWM_CHANNEL2, speed);  // IN2 输出 PWM
  } 
  else {
    // 中点死区：马达停止
    ledcWrite(PWM_CHANNEL1, 0);
    ledcWrite(PWM_CHANNEL2, 0);
  }
  
  // 平滑延迟，减少抖动
  delay(20);
}