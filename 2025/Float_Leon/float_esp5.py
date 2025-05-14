#include <Wire.h>
#include "MS5837.h"

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// BLE Definitions
#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"
#define MOTOR_AIN1 19
#define MOTOR_AIN2 23

BLECharacteristic *pCharacteristic;
bool deviceConnected = false;

// MS5837 pressure sensor
MS5837 sensor;

// Motor timing (in milliseconds)
const unsigned long motor1_time = 7100;
const unsigned long delay1_time = 15000;
const unsigned long motor2_time = 6200;
const unsigned long delay2_time = 15000;
const unsigned long motor3_time = 7100;
const unsigned long delay3_time = 15000;
const unsigned long motor4_time = 6200;

// Compute total data array size (one sample per second, rounded up)
const int total_time_ms = motor1_time + delay1_time + motor2_time + delay2_time + motor3_time + delay3_time + motor4_time;
#define DEPTH_ARRAY_SIZE ((total_time_ms / 1000) + 2)  // +2 for rounding and safety

float depthData[DEPTH_ARRAY_SIZE];
int depthDataCount = 0;

// Callback class for BLE Server events
class ServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer* pServer) {
    deviceConnected = true;
    Serial.println("Device connected!");
  }

  void onDisconnect(BLEServer* pServer) {
    deviceConnected = false;
    Serial.println("Device disconnected!");
    BLEDevice::startAdvertising();
  }
};

void setup() {
  // Motor pins
  pinMode(MOTOR_AIN1, OUTPUT);
  pinMode(MOTOR_AIN2, OUTPUT);
  digitalWrite(MOTOR_AIN1, LOW);
  digitalWrite(MOTOR_AIN2, LOW);

  Serial.begin(115200);
  Serial.println("Starting BLE and MS5837...");

  // MS5837 Sensor init
  Wire.begin();
  while (!sensor.init()) {
    Serial.println("MS5837 Init failed!");
    delay(5000);
  }
  sensor.setModel(MS5837::MS5837_30BA);
  sensor.setFluidDensity(997); // kg/m^3

  // BLE Initialization
  BLEDevice::init("ESP32_Bluetooth");
  BLEServer *pServer = BLEDevice::createServer();
  pServer->setCallbacks(new ServerCallbacks());
  BLEService *pService = pServer->createService(SERVICE_UUID);

  pCharacteristic = pService->createCharacteristic(
                      CHARACTERISTIC_UUID,
                      BLECharacteristic::PROPERTY_READ   |
                      BLECharacteristic::PROPERTY_WRITE  |
                      BLECharacteristic::PROPERTY_NOTIFY |
                      BLECharacteristic::PROPERTY_INDICATE
                    );
  pCharacteristic->addDescriptor(new BLE2902());
  pService->start();
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->start();
  Serial.println("Waiting for a client connection...");
}

void collectDepthSample() {
  sensor.read();
  float d = sensor.depth();
  if (depthDataCount < DEPTH_ARRAY_SIZE) {
    depthData[depthDataCount++] = d;
    Serial.print("Depth sample ");
    Serial.print(depthDataCount);
    Serial.print(": ");
    Serial.print(d, 3);
    Serial.println(" m");
  }
}

// Helper: Run motor for a set time, collecting depth every second
void runMotorAndCollect(int ain1, int ain2, unsigned long runTimeMs) {
  digitalWrite(MOTOR_AIN1, ain1);
  digitalWrite(MOTOR_AIN2, ain2);

  unsigned long startTime = millis();
  unsigned long lastSample = millis();

  while (millis() - startTime < runTimeMs) {
    // Collect one value each second
    if (millis() - lastSample >= 1000) {
      collectDepthSample();
      lastSample += 1000;
    }
    delay(10); // Small delay to keep loop responsive
  }
}

// Helper: Pause for a set time, collecting depth every second
void pauseAndCollect(unsigned long pauseMs) {
  unsigned long startTime = millis();
  unsigned long lastSample = millis();

  digitalWrite(MOTOR_AIN1, LOW);
  digitalWrite(MOTOR_AIN2, LOW);

  while (millis() - startTime < pauseMs) {
    // Collect one value each second
    if (millis() - lastSample >= 1000) {
      collectDepthSample();
      lastSample += 1000;
    }
    delay(10);
  }
}

void printDepthData() {
  Serial.println("\nCollected depth data:");
  for (int i = 0; i < depthDataCount; i++) {
    Serial.print("Depth [s ");
    Serial.print(i + 1);
    Serial.print("]: ");
    Serial.print(depthData[i], 3);
    Serial.println(" m");
  }
}

// BLE: Send collected depth data as comma-separated string
void sendDepthDataBLE() {
  String dataStr = "";
  for (int i = 0; i < depthDataCount; i++) {
    dataStr += String(depthData[i], 3);
    if (i < depthDataCount - 1) dataStr += ",";
  }
  pCharacteristic->setValue(dataStr.c_str());
  pCharacteristic->notify();
  Serial.println("Depth data sent over BLE:");
  Serial.println(dataStr);
}

// Motor off
void stopMotor() {
  digitalWrite(MOTOR_AIN1, LOW);
  digitalWrite(MOTOR_AIN2, LOW);
}

void loop() {
  if (deviceConnected) {
    if (pCharacteristic->getValue().length() > 0) {
      String receivedData = pCharacteristic->getValue().c_str();
      Serial.println("Received: " + receivedData);
      pCharacteristic->setValue(""); // Clear characteristic

      if (receivedData == "2") {
        depthDataCount = 0; // Reset data index

        Serial.println("\n=== Starting Motor Sequence and Depth Collection ===");

        // 1. Motor move (AIN1 LOW, AIN2 HIGH) and collect depth
        Serial.println("Motor1: LOW, HIGH");
        runMotorAndCollect(LOW, HIGH, motor1_time);

        // 2. Pause, collect depth
        Serial.println("Pause after Motor1");
        pauseAndCollect(delay1_time);

        // 3. Motor move (AIN1 HIGH, AIN2 LOW), collect depth
        Serial.println("Motor2: HIGH, LOW");
        runMotorAndCollect(HIGH, LOW, motor2_time);

        // 4. Pause, collect depth
        Serial.println("Pause after Motor2");
        pauseAndCollect(delay2_time);

        // 5. Motor move (AIN1 LOW, AIN2 HIGH), collect depth
        Serial.println("Motor3: LOW, HIGH");
        runMotorAndCollect(LOW, HIGH, motor3_time);

        // 6. Pause, collect depth
        Serial.println("Pause after Motor3");
        pauseAndCollect(delay3_time);

        // 7. Motor move (AIN1 HIGH, AIN2 LOW), collect depth
        Serial.println("Motor4: HIGH, LOW");
        runMotorAndCollect(HIGH, LOW, motor4_time);

        stopMotor();

        Serial.println("=== End of Sequence ===");
        printDepthData();
        sendDepthDataBLE();

      } else {
        stopMotor();
        String response =  receivedData;
        pCharacteristic->setValue(response.c_str());
        pCharacteristic->notify();
      }
      delay(100);
    }
  }
}