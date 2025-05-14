#define MOTOR_AIN1 19
#define MOTOR_AIN2 23

void setup() {
  pinMode(MOTOR_AIN1, OUTPUT);
  pinMode(MOTOR_AIN2, OUTPUT);

    // Start motor forward
  digitalWrite(MOTOR_AIN1, HIGH);
  digitalWrite(MOTOR_AIN2, LOW);

  delay(100); // Run for 5 seconds (5000 milliseconds)


  // Stop motor
  digitalWrite(MOTOR_AIN1, LOW);
  digitalWrite(MOTOR_AIN2, LOW);

  
}

void loop() {
  // Do nothing
}