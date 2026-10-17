"""Read-only BLE device discovery for Furby Connect experiments.

Does not connect to devices or transmit custom commands.
"""
import asyncio
from bleak import BleakScanner


async def main() -> None:
    print("Scanning for nearby Bluetooth Low Energy devices for 15 seconds...")
    print("This is discovery only; no device connection or control commands.")
    devices = await BleakScanner.discover(timeout=15.0, return_adv=True)
    if not devices:
        print("No devices found. Check Bluetooth, batteries and proximity.")
        return
    for _identifier, (device, advertisement) in sorted(
        devices.items(), key=lambda item: (item[1][0].name or "").lower()
    ):
        # Do not print or store MAC addresses or Windows BLE identifiers.
        name = device.name or advertisement.local_name or "(unnamed)"
        print(f"Name: {name!r}; RSSI: {advertisement.rssi} dBm")
    print("Compare scan results with Furby powered on vs. off to identify it.")


if __name__ == "__main__":
    asyncio.run(main())
