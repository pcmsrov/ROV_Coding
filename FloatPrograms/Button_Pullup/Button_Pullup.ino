// 定义按钮引脚
//const int buttonPin = 4;  // 使用GPIO2作为按钮输入引脚
const int buttonPin = 18;  // 使用GPIO2作为按钮输入引脚

void setup() {
  // 初始化串口通信
  Serial.begin(115200);
  
  // 配置按钮引脚为上拉输入
  pinMode(buttonPin, INPUT_PULLUP);
}

void loop() {
  // 读取按钮状态
  int buttonState = digitalRead(buttonPin);
  
  // 打印按钮状态
  if (buttonState == LOW) {
    Serial.println("Pressed");
  } else {
    Serial.println("Not Pressed");
  }
  
  // 短暂延时以避免过于频繁的读取
  delay(100);
}
