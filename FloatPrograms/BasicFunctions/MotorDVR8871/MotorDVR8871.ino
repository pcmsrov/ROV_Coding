// Motor control using DVR8871 driver with NodeMCU-32
// IN1 connected to GPIO25
// IN2 connected to GPIO26

// Define motor control pins
const int IN1 = 25;  // Motor control pin 1
const int IN2 = 26;  // Motor control pin 2
const int BtnPin = 18;
int stop = false;

void setup() {
  // Initialize motor control pins as outputs
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(BtnPin, INPUT_PULLUP);

  // Initialize serial communication
  Serial.begin(115200);
  Serial.println("Motor control program started");
}

void loop() {
  // Rotate motor clockwise
  if(!stop)
  {
    Serial.println("Motor rotating clockwise");
    digitalWrite(IN1, HIGH);
    digitalWrite(IN2, LOW);
    delay(2000);  // Run for 1 second
    
    // Stop motor
    Serial.println("Motor stopped");
    digitalWrite(IN1, LOW);
    digitalWrite(IN2, LOW);
    delay(2000);  // Stop for 1 second
  }

  int BtnState = digitalRead(BtnPin);
  if(BtnState == LOW)
  {
    stop = true;
    Serial.println("Button Pressed, Motor Stopped");
  }
}