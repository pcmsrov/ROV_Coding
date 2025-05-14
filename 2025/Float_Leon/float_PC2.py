import asyncio
from bleak import BleakClient, BleakScanner

# UUIDs for the BLE service and characteristic (must match ESP32 code)
SERVICE_UUID = "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
CHARACTERISTIC_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"

# ESP32 Bluetooth name
DEVICE_NAME = "ESP32_Bluetooth"

# Callback function to handle notifications from ESP32
def callback(sender, data):
    received_data = data.decode()
    print(f"Raw data received: {received_data}")

    # Split the CSV string into a list of integers
    try:
        array = [int(x) for x in received_data.split(",")]
        print(f"Parsed array: {array}")
    except ValueError:
        print("Failed to parse array.")

async def main():
    # Scan for BLE devices
    print("Scanning for devices...")
    devices = await BleakScanner.discover()
    esp32_address = None

    # Find the ESP32 by its name
    for device in devices:
        print(f"Found device: {device.name}, {device.address}")
        if device.name == DEVICE_NAME:
            esp32_address = device.address
            break

    if not esp32_address:
        print("ESP32 not found. Exiting...")
        return

    print(f"Connecting to ESP32 at address {esp32_address}...")

    # Connect to ESP32
    async with BleakClient(esp32_address) as client:
        print("Connected to ESP32!")

        # Start notifications
        await client.start_notify(CHARACTERISTIC_UUID, callback)

        try:
            print("Receiving data... Press Ctrl+C to exit.")
            while True:
                # Keep receiving notifications
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("Exiting program...")

        # Stop notifications when done
        await client.stop_notify(CHARACTERISTIC_UUID)

# Run the program
asyncio.run(main())