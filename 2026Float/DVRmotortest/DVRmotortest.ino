int MotorIN1 = 25;  // 第一個PWM引脚 (原本的Motor)
int MotorIN2 = 26;  // 第二個PWM引脚 (原本的Direction)
int pwmValue = 0;   // PWM值

void setup() {
  //Serial.begin(115200);
  //Serial.println("DRV8871 双PWM测试");
  
  // 兩個腳位都設為輸出
  pinMode(MotorIN1, OUTPUT);
  pinMode(MotorIN2, OUTPUT);
  
  // 初始化兩個PWM腳位為0
  analogWrite(MotorIN1, 0);
  analogWrite(MotorIN2, 0);
}

void loop() {
  // 正轉：IN1 = PWM, IN2 = 0
  Serial.println("正轉");
  for(int i = 0; i <= 255; i++) {
    analogWrite(MotorIN1, i);  // IN1 PWM逐漸增加
    analogWrite(MotorIN2, 0);   // IN2保持0
    delay(15);
  }
  
  delay(1000);  // 暫停1秒
  
  // 反轉：IN1 = 0, IN2 = PWM
  Serial.println("反轉");
  for(int i = 0; i <= 255; i++) {
    analogWrite(MotorIN1, 0);   // IN1保持0
    analogWrite(MotorIN2, i);  // IN2 PWM逐漸增加
    delay(15);
  }
  
  delay(1000);  // 暫停1秒
}