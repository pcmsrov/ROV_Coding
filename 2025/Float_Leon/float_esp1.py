#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// UUIDs for the BLE service and characteristic
#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

BLECharacteristic *pCharacteristic;
bool deviceConnected = false;

// Callback class for BLE Server events
class ServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer* pServer) {
    deviceConnected = true;
    Serial.println("Device connected!");
  }

  void onDisconnect(BLEServer* pServer) {
    deviceConnected = false;
    Serial.println("Device disconnected!");
    BLEDevice::startAdvertising(); // Restart advertising when disconnected
  }
};

void setup() {
  Serial.begin(115200);
  Serial.println("Starting BLE work...");

  // Configure pin 2 as output for LED control
  pinMode(23, OUTPUT);
  digitalWrite(23, LOW); // Ensure LED is off initially

  // Initialize BLE device
  BLEDevice::init("ESP32_Bluetooth");

  // Create BLE server and set callbacks
  BLEServer *pServer = BLEDevice::createServer();
  pServer->setCallbacks(new ServerCallbacks());

  // Create BLE service
  BLEService *pService = pServer->createService(SERVICE_UUID);

  // Create BLE characteristic with required properties
  pCharacteristic = pService->createCharacteristic(
                      CHARACTERISTIC_UUID,
                      BLECharacteristic::PROPERTY_READ   |
                      BLECharacteristic::PROPERTY_WRITE  |
                      BLECharacteristic::PROPERTY_NOTIFY |
                      BLECharacteristic::PROPERTY_INDICATE
                    );

  // Add a descriptor to enable notifications
  pCharacteristic->addDescriptor(new BLE2902());

  // Start the BLE service
  pService->start();

  // Start advertising
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->start();
  Serial.println("Waiting for a client connection...");
}

void loop() {
  // If a device is connected, check for received data
  if (deviceConnected) {
    if (pCharacteristic->getValue().length() > 0) {
      // Read the received data
      String receivedData = pCharacteristic->getValue().c_str();
      Serial.println("Received: " + receivedData);

      // Clear the characteristic value after reading
      pCharacteristic->setValue("");

      // Check if the received data is "2"
      if (receivedData == "2") {
        digitalWrite(23, LOW); // Turn on the LED
        Serial.println("LED turned ON");
        delay(3000);
      } else {
        digitalWrite(23, HIGH); // Turn off the LED for any other input
        Serial.println("LED turned OFF");
      }

      // Send a response back
      String response = "ESP32 received: " + receivedData;
      pCharacteristic->setValue(response.c_str());
      pCharacteristic->notify(); // Notify the client
    }
    delay(100); // Small delay for stability
  }
}