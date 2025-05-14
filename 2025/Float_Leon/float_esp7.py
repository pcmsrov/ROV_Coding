#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// Updated UUIDs for the BLE service and characteristic
#define SERVICE_UUID        "12345678-1234-5678-1234-56789abcdef0"
#define CHARACTERISTIC_UUID "abcdef01-1234-5678-1234-56789abcdef0"

// Updated device name
#define DEVICE_NAME "My_ESP32_Device"

// Motor control pins for DRV8833
#define MOTOR_IN1 19 // Motor IN1 pin
#define MOTOR_IN2 23 // Motor IN2 pin

// Global variables for BLE
BLECharacteristic *pCharacteristic;
bool deviceConnected = false;
std::string receivedValue = "";
bool startMotorSequence = false; // Flag to start motor sequence

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

      // Check if the received message is "2"
      if (receivedValue == "2") {
        startMotorSequence = true; // Set the flag to start motor sequence
      }

      // Example: Respond to the client
      std::string response =  receivedValue;
      pCharacteristic->setValue(response);
      pCharacteristic->notify(); // Send notification
    }
  }
};

// Function to control the motor
void motorControl(int in1, int in2) {
  digitalWrite(MOTOR_IN1, in1);
  digitalWrite(MOTOR_IN2, in2);
}

void motorSequence() {
  // Sequence: Forward -> Stop -> Backward -> Stop -> Forward -> Stop -> Backward -> Stop
  Serial.println("Motor sequence started...");

  // Forward 10 seconds
  Serial.println("Motor forward...");
  motorControl(LOW, HIGH);
  delay(10000);

  // Stop 10 seconds
  Serial.println("Motor stop...");
  motorControl(LOW, LOW);
  delay(10000);

  // Backward 10 seconds
  Serial.println("Motor backward...");
  motorControl(LOW, HIGH);
  delay(10000);

  // Stop 10 seconds
  Serial.println("Motor stop...");
  motorControl(LOW, LOW);
  delay(10000);

  // Forward 10 seconds
  Serial.println("Motor forward...");
  motorControl(HIGH, LOW);
  delay(10000);

  // Stop 10 seconds
  Serial.println("Motor stop...");
  motorControl(LOW, LOW);
  delay(10000);

  // Backward 10 seconds
  Serial.println("Motor backward...");
  motorControl(LOW, HIGH);
  delay(10000);

  // Stop 10 seconds
  Serial.println("Motor stop...");
  motorControl(LOW, LOW);
  delay(10000);

  Serial.println("Motor sequence completed!");
}

void setup() {
  Serial.begin(115200);
  Serial.println("Starting BLE...");

  // Initialize motor control pins
  pinMode(MOTOR_IN1, OUTPUT);
  pinMode(MOTOR_IN2, OUTPUT);
  motorControl(LOW, LOW); // Ensure motor is stopped initially

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
}

void loop() {
  // Check if the motor sequence should start
  if (startMotorSequence) {
    startMotorSequence = false; // Reset the flag
    motorSequence(); // Execute the motor sequence
  }
}