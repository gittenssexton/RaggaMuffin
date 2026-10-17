"""Safe, read-only Furby Connect BLE connection probe for Windows.

Scans nearby BLE devices, lets you select one, connects temporarily and
lists GATT services. Does not write characteristics or change firmware.
"""
import asyncio
from bleak import BleakClient, BleakScanner


async def main():
    print("RaggaMuffin — Bluetooth connection probe")
    print("Power on Furby Connect and keep it near your computer.")
    print("Scanning for 15 seconds...")
    try:
        found = await BleakScanner.discover(timeout=15.0)
    except Exception as exc:
        print(f"Scanning failed: {exc}")
        print("Check Windows Bluetooth and permissions.")
        return

    if not found:
        print("No BLE devices detected. Check batteries and Bluetooth.")
        return

    for index, device in enumerate(found, 1):
        # Do not expose stable Bluetooth addresses in terminal output.
        print(f" {index:>2}. {device.name or '(unnamed BLE device)'}")
    print("Compare with a scan while Furby is off if you aren't sure which it is.")
    choice = input("Enter device number to try a read-only connection (or Enter to quit): ").strip()
    if not choice:
        return
    try:
        index = int(choice) - 1
        if not 0 <= index < len(found):
            raise ValueError("number out of range")
    except ValueError:
        print("Invalid selection.")
        return

    device = found[index]
    try:
        print(f"Connecting to {device.name or 'selected device'}...")
        async with BleakClient(device, timeout=15.0) as client:
            print(f"Connected: {client.is_connected}")
            print("Available GATT services (UUIDs are not private identifiers):")
            for service in client.services:
                print(f" - {service.uuid} ({service.description})")
                for characteristic in service.characteristics:
                    print(f"    {characteristic.uuid} [{', '.join(characteristic.properties)}]")
            print("No commands were sent to Furby.")
    except Exception as exc:
        print(f"Connection failed: {exc}")
        print("Try restarting Furby, moving closer, and closing apps using Bluetooth.")


if __name__ == "__main__":
    asyncio.run(main())
