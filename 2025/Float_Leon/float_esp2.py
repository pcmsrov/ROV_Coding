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
  // Simulate an array of sensor values
  static int sensorValues[5] = {0};
  static int counter = 0;

  // If a device is connected, send the array
  if (deviceConnected) {
    // Update simulated sensor values
    for (int i = 0; i < 5; i++) {
      sensorValues[i] = counter + i; // Simulate incremental values
    }
    counter++; // Increment counter for simulation

    // Convert the array to a CSV string
    String dataToSend = "";
    for (int i = 0; i < 5; i++) {
      dataToSend += String(sensorValues[i]);
      if (i < 4) dataToSend += ","; // Add comma between values
    }

    // Log the array to the serial monitor
    Serial.println("Sending array: " + dataToSend);

    // Send the array as a notification
    pCharacteristic->setValue(dataToSend.c_str());
    pCharacteristic->notify();

    // Wait for 1 second before sending the next array
    delay(1000);
  } else {
    delay(100); // Small delay when no device is connected
  }
}