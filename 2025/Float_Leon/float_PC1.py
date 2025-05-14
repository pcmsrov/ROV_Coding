import asyncio
from bleak import BleakClient, BleakScanner

# UUIDs for the BLE service and characteristic (must match ESP32 code)
SERVICE_UUID = "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
CHARACTERISTIC_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"

# ESP32 Bluetooth name
DEVICE_NAME = "ESP32_Bluetooth"

# Callback function to handle notifications from ESP32
def callback(sender, data):
    print(f"Received from ESP32: {data.decode()}")

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
            while True:
                # Send data to ESP32
                message = input("Enter a message to send to ESP32: ")
                await client.write_gatt_char(CHARACTERISTIC_UUID, message.encode())
                print("Message sent!")

                # Wait for responses (notifications are handled in the callback)
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("Exiting program...")

        # Stop notifications when done
        await client.stop_notify(CHARACTERISTIC_UUID)

# Run the program
asyncio.run(main())
