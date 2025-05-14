import asyncio
from bleak import BleakClient, BleakScanner, BleakError
import matplotlib.pyplot as plt

SERVICE_UUID = "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
CHARACTERISTIC_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"
DEVICE_NAME = "ESP32_Bluetooth"

received_depth_data = None

def notification_handler(sender, data):
    global received_depth_data
    text = data.decode()
    print(f"Received from ESP32: {text}")
    if "," in text:
        received_depth_data = text

async def scan_and_connect():
    print("Scanning for devices...")
    esp32_address = None
    for _ in range(5):  # Scan up to 5 times
        devices = await BleakScanner.discover(timeout=3.0)
        for device in devices:
            if device.name == DEVICE_NAME:
                esp32_address = device.address
                print(f"Found ESP32 at {esp32_address}")
                break
        if esp32_address:
            break
        print("ESP32 not found, retrying...")
    return esp32_address

async def plot_depth_data(depth_str):
    depth_list = [float(x) for x in depth_str.strip().split(",") if x.strip()]
    plt.figure(figsize=(8,4))
    plt.plot(range(1, len(depth_list) + 1), depth_list, marker='o')
    plt.xlabel("Seconds")
    plt.ylabel("Depth (m)")
    plt.title("Depth Data from ESP32")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

async def main():
    global received_depth_data

    esp32_address = await scan_and_connect()
    if not esp32_address:
        print("ESP32 not found. Exiting...")
        return

    while True:
        try:
            print(f"Connecting to ESP32 at {esp32_address}...")
            async with BleakClient(esp32_address) as client:
                print("Connected to ESP32!")
                await client.start_notify(CHARACTERISTIC_UUID, notification_handler)

                while True:
                    # Prompt for user input
                    message = input("Enter a message to send to ESP32 (type '2' to start depth collection, or 'quit' to exit): ")
                    if message.lower() == "quit":
                        await client.stop_notify(CHARACTERISTIC_UUID)
                        print("Exiting program...")
                        return

                    await client.write_gatt_char(CHARACTERISTIC_UUID, message.encode())
                    print("Message sent! Waiting for depth data if applicable...")

                    # Only expect depth data if "2" is sent
                    if message.strip() == "2":
                        received_depth_data = None
                        while received_depth_data is None:
                            await asyncio.sleep(1)
                            if not client.is_connected:
                                print("Bluetooth disconnected, waiting for ESP32 to finish, will try to reconnect...")
                                break
                        else:
                            print("Received depth data! Plotting...")
                            await plot_depth_data(received_depth_data)
                            # Ready for next command
                            continue

                        # If disconnected, try to reconnect and resume notifications
                        while True:
                            print("Looking for ESP32 to reconnect...")
                            await asyncio.sleep(3)
                            new_address = await scan_and_connect()
                            if new_address:
                                esp32_address = new_address
                                break
                            print("ESP32 still not available...")

                        # After reconnect, break inner loop to restart connection
                        break

        except BleakError as e:
            print(f"BLE error: {e}")
            print("Retrying connection...")
            await asyncio.sleep(2)
        except Exception as e:
            print(f"Unexpected error: {e}")
            break

if __name__ == "__main__":
    asyncio.run(main())