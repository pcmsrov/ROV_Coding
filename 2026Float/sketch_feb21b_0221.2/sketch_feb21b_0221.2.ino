int Motor = 25;      // 电机速度控制的PWM引脚
int Direction = 26;  // 方向控制的数字引脚
boolean direction = true;

void setup() {
  //Serial.begin(115200);
  //Serial.println("DRV8871 测试");
  
  pinMode(Direction, OUTPUT);
  pinMode(Motor, OUTPUT);  // 将电机引脚设置为输出模式
  
  // 注意：analogWrite 使用默认的PWM频率（在大多数Arduino板上约为500Hz）
  // 如果需要特定频率，可能需要使用LEDC或直接设置预分频器
}

void loop() {
  digitalWrite(Direction, direction);
  
  // 速度从0逐渐增加到255
  for(int i = 0; i <= 255; i++) {
    analogWrite(Motor, i);  // 使用 analogWrite 替代 ledcWrite
    delay(15);
  }
  
  direction = !direction;  // 切换方向
}