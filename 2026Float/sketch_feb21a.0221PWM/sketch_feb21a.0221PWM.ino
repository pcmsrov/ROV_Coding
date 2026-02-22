int Motor = 25;      // 电机速度控制的PWM引脚
int Direction = 26;  // 方向控制的数字引脚
boolean direction = true;  // true 表示正轉，false 表示反轉
int pwmValue = 0;    // 存储用户输入的PWM值
int motorOutput = 0; // 實際輸出到馬達的PWM值
bool newInput = false;  // 标记是否有新输入

void setup() {
  Serial.begin(115200);
  Serial.println("DRV8871 手动PWM控制模式");
  Serial.println("请输入PWM值 (0-255):");
  
  pinMode(Direction, OUTPUT);
  pinMode(Motor, OUTPUT);  // 将电机引脚设置为输出模式
  
  // 初始方向設定
  digitalWrite(Direction, direction);
}

void loop() {
  // 检查是否有串口数据输入
  if (Serial.available() > 0) {
    int inputValue = Serial.parseInt();  // 读取输入的整数值
    
    // 验证输入值是否在有效范围内
    if (inputValue >= 0 && inputValue <= 255) {
      pwmValue = inputValue;
      newInput = true;
      
      Serial.print("已设置PWM值为: ");
      Serial.println(pwmValue);
      Serial.println("请输入新的PWM值 (0-255):");
    } else {
      Serial.println("输入无效！请输入0-255之间的数值");
    }
    
    // 清除串口缓冲区
    while (Serial.available() > 0) {
      Serial.read();
    }
  }
  
  // 如果接收到新输入，更新PWM输出
  if (newInput) {
    
    // 根據方向計算實際輸出到馬達的PWM值
    if (direction == true) {
      // 正向：套用公式 (x-255)*(-1)
      // 當x=0時，(0-255)*(-1)=255 (最快)
      // 當x=255時，(255-255)*(-1)=0 (最慢)
      motorOutput = (pwmValue - 255) * (-1);
      Serial.print("正向模式 - 輸入PWM: ");
      Serial.print(pwmValue);
      Serial.print("，實際輸出: ");
      Serial.println(motorOutput);
    } else {
      // 反向：直接使用輸入值
      // 當x=0時，輸出=0 (最慢)
      // 當x=255時，輸出=255 (最快)
      motorOutput = pwmValue;
      Serial.print("反向模式 - 輸入PWM: ");
      Serial.print(pwmValue);
      Serial.print("，實際輸出: ");
      Serial.println(motorOutput);
    }
    
    // 更新PWM輸出（使用計算後的motorOutput）
    analogWrite(Motor, motorOutput);
    
    // 根據PWM值顯示電機狀態
    if (pwmValue == 0) {
      Serial.println("电机停止");
    } else {
      digitalWrite(Direction, direction);
      Serial.print("电机运行，方向: ");
      Serial.println(direction ? "正向" : "反向");
    }
    
    newInput = false;  // 重置标记
  }
  
  // 可以添加一个小的延时，避免过度占用CPU
  delay(100);
}