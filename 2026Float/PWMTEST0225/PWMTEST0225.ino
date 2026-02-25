int MotorIN1 = 25;  // 正轉PWM引脚
int MotorIN2 = 26;  // 反轉PWM引脚
int potPin = 34;    // 可變電阻接在 GPIO34 (ADC輸入)

int potValue = 0;      // 讀取到的可變電阻值 (0-4095)
int motorSpeed = 0;    // 計算後的馬達速度 (0-255)
int lastMotorSpeed = 0; // 上次的速度，用於顯示變化
int lastDirection = 0;  // 上次的方向，用於顯示變化
String currentDirection = "停止"; // 當前方向

// 定義中間值的範圍（避免抖動）
const int CENTER_MIN = 2028;  // 中間值下限 (約 2048 - 20)
const int CENTER_MAX = 2068;  // 中間值上限 (約 2048 + 20)

void setup() {
  Serial.begin(115200);
  Serial.println("可變電阻控制風扇正反轉與轉速");
  Serial.println("=================================");
  Serial.println("控制說明：");
  Serial.println("  最左邊 → 正轉 速度 255 (最快)");
  Serial.println("  向左中間 → 正轉 速度遞減");
  Serial.println("  正中央 → 停止");
  Serial.println("  向右中間 → 反轉 速度遞減");
  Serial.println("  最右邊 → 反轉 速度 255 (最快)");
  Serial.println("=================================");
  
  pinMode(MotorIN1, OUTPUT);
  pinMode(MotorIN2, OUTPUT);
  
  // 初始化
  analogWrite(MotorIN1, 0);
  analogWrite(MotorIN2, 0);
}

void loop() {
  // 讀取可變電阻值 (0-4095)
  potValue = analogRead(potPin);
  
  // 判斷可變電阻位置並計算速度
  if (potValue < CENTER_MIN) {
    // 左半邊 (0 到 CENTER_MIN-1) -> 正轉
    // 將 0 到 CENTER_MIN 映射到 255 到 0
    // 最左邊 (0) → 速度 255
    // 接近中間 (CENTER_MIN) → 速度 0
    motorSpeed = map(potValue, 0, CENTER_MIN, 255, 0);
    
    // 限制速度在 0-255 範圍內
    motorSpeed = constrain(motorSpeed, 0, 255);
    
    // 設定PWM輸出
    analogWrite(MotorIN1, motorSpeed);
    analogWrite(MotorIN2, 0);
    
    currentDirection = "正轉";
    
  } else if (potValue > CENTER_MAX) {
    // 右半邊 (CENTER_MAX+1 到 4095) -> 反轉
    // 將 CENTER_MAX 到 4095 映射到 0 到 255
    // 接近中間 (CENTER_MAX) → 速度 0
    // 最右邊 (4095) → 速度 255
    motorSpeed = map(potValue, CENTER_MAX, 4095, 0, 255);
    
    // 限制速度在 0-255 範圍內
    motorSpeed = constrain(motorSpeed, 0, 255);
    
    // 設定PWM輸出
    analogWrite(MotorIN1, 0);
    analogWrite(MotorIN2, motorSpeed);
    
    currentDirection = "反轉";
    
  } else {
    // 中間區域 (CENTER_MIN 到 CENTER_MAX) -> 停止
    motorSpeed = 0;
    
    analogWrite(MotorIN1, 0);
    analogWrite(MotorIN2, 0);
    
    currentDirection = "停止";
  }
  
  // 只有在速度或方向有變化時才顯示（避免一直刷屏）
  if (motorSpeed != lastMotorSpeed || 
      (currentDirection != "停止" && lastDirection == 0) ||
      (currentDirection == "停止" && lastDirection != 0)) {
    
    // 顯示當前狀態
    Serial.print("電阻值: ");
    Serial.print(potValue);
    Serial.print(" (");
    
    // 顯示位置百分比
    if (potValue < CENTER_MIN) {
      int percent = map(potValue, 0, CENTER_MIN, 100, 0);
      Serial.print("左邊 ");
      Serial.print(percent);
      Serial.print("%");
    } else if (potValue > CENTER_MAX) {
      int percent = map(potValue, CENTER_MAX, 4095, 0, 100);
      Serial.print("右邊 ");
      Serial.print(percent);
      Serial.print("%");
    } else {
      Serial.print("中央");
    }
    Serial.print(") | ");
    
    Serial.print("方向: ");
    Serial.print(currentDirection);
    Serial.print(" | 速度: ");
    Serial.println(motorSpeed);
    
    lastMotorSpeed = motorSpeed;
    
    // 記錄方向狀態
    if (currentDirection == "正轉") lastDirection = 1;
    else if (currentDirection == "反轉") lastDirection = -1;
    else lastDirection = 0;
  }
  
  delay(50);  // 小延時，避免過度頻繁讀取
}