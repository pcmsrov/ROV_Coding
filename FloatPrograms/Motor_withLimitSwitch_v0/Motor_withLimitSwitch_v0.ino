// Motor control using DVR8871 driver with NodeMCU-32
// IN1 connected to GPIO25
// IN2 connected to GPIO26

// Define motor control pins
const int IN1 = 25;  // Motor control pin 1
const int IN2 = 26;  // Motor control pin 2

const int TopLimitBtn = 19; //work while descending
const int DownLimitBtn = 18; //work while ascending

// Define phases
enum Phase {
  IDLE,
  DESCENDING,
  WAITING,
  ASCENDING,
  COMPLETED
};

Phase currentPhase = IDLE;

unsigned long startTime = 0;
//int descendTime = 7300;    // 7.3 seconds for descending
//int ascendTime = 7300;     // 7.3 seconds for ascending
//int executeAscend = 120000; // 2mins, ready to ascend

int descendTime = 5000;    // 7.3 seconds for descending
int ascendTime = 5000;     // 7.3 seconds for ascending
int executeAscendTime = 20000; // 2mins, ready to ascend

bool startProcess = false;
bool progress = false;
bool motorRunning = false;

String inputString = "";      // 存储接收到的串口数据
bool stringComplete = false;  // 标记是否接收到完整字符串

void setup() {
  // Initialize motor control pins as outputs
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(TopLimitBtn, INPUT_PULLUP);
  pinMode(DownLimitBtn, INPUT_PULLUP);

  // Initialize serial communication
  Serial.begin(115200);
  Serial.println("Motor control program started");
  Serial.println("Send 'Go' to start the process");
  
  // Initialize motor state
  stopMotor();
}

void loop() {
  // 检查串口数据
  serialEvent();
  
  // 如果收到完整字符串
  if (stringComplete) {
    inputString.trim();  // 移除首尾空白字符
    if (inputString == "Go") {
      startProcess = true;
      currentPhase = DESCENDING;
      Serial.println("Process started!");
    }
    // 清空接收缓冲区
    inputString = "";
    stringComplete = false;
  }

  // Check if process should start
  if (startProcess && !progress) {
    progress = true;
    startTime = millis();
    startMotorForward();
    Serial.println("Starting descending phase");
  }
  
  // Main process control
  if (progress) {
    // 每1秒打印状态
    if (millis() % 1000 < 500) {
      Serial.print("Time elapsed: ");
      Serial.print((millis() - startTime) / 1000);
      Serial.print("s, Motor running: ");
      Serial.println(motorRunning ? "Yes" : "No");
    }
    
    switch (currentPhase) {
      case DESCENDING:
        if (millis() - startTime >= descendTime) {
          stopMotor();
          currentPhase = WAITING;
          Serial.println("Descending phase completed");
        }
        break;
        
      case WAITING:
        if (millis() - startTime >= executeAscendTime) {
          startMotorReverse();
          currentPhase = ASCENDING;
          Serial.println("Starting ascending phase");
        }
        break;
        
      case ASCENDING:
        if (millis() - startTime >= ascendTime + executeAscendTime) {
          stopMotor();
          currentPhase = COMPLETED;
          progress = false;
          startProcess = false;
          Serial.println("Ascending phase completed");
        }
        break;
        
      case COMPLETED:
        Serial.println("Process completed");
        delay(5000);
        break;
        
      default:
        break;
    }
  }
  
  delay(500); // 添加500ms延时
}

void serialEvent() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    if (inChar == '\n') {
      stringComplete = true;
    } else {
      inputString += inChar;
    }
  }
}

void startMotorForward() {
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);
  motorRunning = true;
}

void startMotorReverse() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);
  motorRunning = true;
}

void stopMotor() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  motorRunning = false;
}