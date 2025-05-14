#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// Updated UUIDs for the BLE service and characteristic
#define SERVICE_UUID        "12345678-1234-5678-1234-56789abcdef0"
#define CHARACTERISTIC_UUID "abcdef01-1234-5678-1234-56789abcdef0"

// Updated device name
#define DEVICE_NAME "My_ESP32_Device"

// Motor control pins (DRV8833)
#define MOTOR_A_IN1  25  // Motor A input 1
#define MOTOR_A_IN2  26  // Motor A input 2

// Global variables for BLE
BLECharacteristic *pCharacteristic;
bool deviceConnected = false;
std::string receivedValue = "";

// Motor control sequence timing
unsigned long lastActionTime = 0; // Tracks the time of the last action
int motorState = 0; // State of the motor in the sequence

// Callback for BLE server events (connection/disconnection)
class MyServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer* pServer) {
    deviceConnected = true;
    Serial.println("Device connected!");
  }

  void onDisconnect(BLEServer* pServer) {
    deviceConnected = false;
    Serial.println("Device disconnected!");
    // Start advertising again
    pServer->getAdvertising()->start();
  }
};

// Callback for BLE characteristic events (read/write)
class MyCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *pCharacteristic) {
    // Get the value written by the client
    receivedValue = pCharacteristic->getValue();
    if (receivedValue.length() > 0) {
      Serial.println("Received from client: " + String(receivedValue.c_str()));

      // Example: Respond to the client
      std::string response = receivedValue;
      pCharacteristic->setValue(response);
      pCharacteristic->notify(); // Send notification
    }
  }
};

void setup() {
  Serial.begin(115200);
  Serial.println("Starting BLE...");

  // Initialize BLE and create a server
  BLEDevice::init(DEVICE_NAME);
  BLEServer *pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  // Create a BLE service
  BLEService *pService = pServer->createService(SERVICE_UUID);

  // Create a BLE characteristic
  pCharacteristic = pService->createCharacteristic(
                      CHARACTERISTIC_UUID,
                      BLECharacteristic::PROPERTY_READ |
                      BLECharacteristic::PROPERTY_WRITE |
                      BLECharacteristic::PROPERTY_NOTIFY
                    );

  // Set initial value for the characteristic
  pCharacteristic->setValue("Hello from ESP32");
  pCharacteristic->setCallbacks(new MyCallbacks());

  // Add a descriptor for notifications
  pCharacteristic->addDescriptor(new BLE2902());

  // Start the service
  pService->start();

  // Start advertising
  pServer->getAdvertising()->start();
  Serial.println("BLE service and characteristic created. Waiting for connections...");

  // Initialize motor control pins
  pinMode(MOTOR_A_IN1, OUTPUT);
  pinMode(MOTOR_A_IN2, OUTPUT);

  // Initialize motor in stopped state
  digitalWrite(MOTOR_A_IN1, LOW);
  digitalWrite(MOTOR_A_IN2, LOW);

  // Initialize timing
  lastActionTime = millis();
}

void loop() {
  // Motor control sequence
  unsigned long currentTime = millis();

  if (currentTime - lastActionTime >= 10000) { // 10-second intervals
    lastActionTime = currentTime; // Update the last action time

    switch (motorState) {
      case 0: // Forward
        Serial.println("Motor: Forward");
        digitalWrite(MOTOR_A_IN1, HIGH);
        digitalWrite(MOTOR_A_IN2, LOW);
        motorState = 1;
        break;

      case 1: // Stop
        Serial.println("Motor: Stop");
        digitalWrite(MOTOR_A_IN1, LOW);
        digitalWrite(MOTOR_A_IN2, LOW);
        motorState = 2;
        break;

      case 2: // Backward
        Serial.println("Motor: Backward");
        digitalWrite(MOTOR_A_IN1, LOW);
        digitalWrite(MOTOR_A_IN2, HIGH);
        motorState = 3;
        break;

      case 3: // Stop
        Serial.println("Motor: Stop");
        digitalWrite(MOTOR_A_IN1, LOW);
        digitalWrite(MOTOR_A_IN2, LOW);
        motorState = 4;
        break;

      case 4: // Forward
        Serial.println("Motor: Forward");
        digitalWrite(MOTOR_A_IN1, HIGH);
        digitalWrite(MOTOR_A_IN2, LOW);
        motorState = 5;
        break;

      case 5: // Stop
        Serial.println("Motor: Stop");
        digitalWrite(MOTOR_A_IN1, LOW);
        digitalWrite(MOTOR_A_IN2, LOW);
        motorState = 6;
        break;

      case 6: // Backward
        Serial.println("Motor: Backward");
        digitalWrite(MOTOR_A_IN1, LOW);
        digitalWrite(MOTOR_A_IN2, HIGH);
        motorState = 7;
        break;

      case 7: // Stop
        Serial.println("Motor: Stop");
        digitalWrite(MOTOR_A_IN1, LOW);
        digitalWrite(MOTOR_A_IN2, LOW);
        motorState = 0; // Reset to the beginning of the sequence
        break;
    }
  }
}