"""RaggaMuffin Windows Bluetooth explorer with a limited antenna LED test."""
import asyncio
import threading
import tkinter as tk
from tkinter import ttk
from bleak import BleakScanner, BleakClient

FURBY_SERVICE = 'dab91435-b5a1-e29c-b041-bcd562613bde'
FURBY_WRITE = 'dab91383-b5a1-e29c-b041-bcd562613bde'
# Documented Bluefluff GeneralPlus command 0x14 followed by RGB.
ANTENNA_COLORS = {'Red': (255, 0, 0), 'Green': (0, 255, 0), 'Blue': (0, 0, 255), 'Off': (0, 0, 0)}


class RaggaMuffinApp:
    def __init__(self, root):
        self.root = root
        root.title("RaggaMuffin — Furby Connect")
        root.geometry("700x470")
        root.minsize(600, 380)
        self.devices = []
        self.busy = False
        main = ttk.Frame(root, padding=16)
        main.pack(fill="both", expand=True)
        ttk.Label(main, text="RaggaMuffin — Furby Connect", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(main, text="Wake Furby and keep it nearby. Scan first, then select its Bluetooth entry.").pack(anchor="w", pady=(4, 10))
        bar = ttk.Frame(main)
        bar.pack(fill="x")
        self.scan_btn = ttk.Button(bar, text="Scan Bluetooth (15s)", command=self.scan)
        self.scan_btn.pack(side="left")
        self.connect_btn = ttk.Button(bar, text="Connect & inspect", command=self.connect, state="disabled")
        self.connect_btn.pack(side="left", padx=8)
        self.color = tk.StringVar(value="Blue")
        self.color_choice = ttk.Combobox(bar, textvariable=self.color, values=list(ANTENNA_COLORS), state="readonly", width=8)
        self.color_choice.pack(side="left", padx=(8, 2))
        self.led_btn = ttk.Button(bar, text="Test antenna light", command=self.antenna_test, state="disabled")
        self.led_btn.pack(side="left", padx=4)
        self.status = tk.StringVar(value="Ready. No connection or commands sent.")
        ttk.Label(main, textvariable=self.status).pack(anchor="w", pady=8)
        self.listbox = tk.Listbox(main, height=7, exportselection=False)
        self.listbox.pack(fill="x")
        self.listbox.bind("<<ListboxSelect>>", lambda _event: self.update_buttons())
        ttk.Label(main, text="Results / service details:").pack(anchor="w", pady=(10, 3))
        self.log = tk.Text(main, height=10, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True)
        ttk.Label(main, text="Antenna light test sends one documented RGB command only after you click. No firmware, audio, or motor commands.", wraplength=660).pack(anchor="w", pady=(7, 0))

    def write(self, message):
        self.log.configure(state="normal")
        self.log.insert("end", message + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def set_busy(self, busy, message):
        self.busy = busy
        self.status.set(message)
        self.update_buttons()

    def update_buttons(self):
        self.scan_btn.configure(state="disabled" if self.busy else "normal")
        has_choice = len(self.listbox.curselection()) == 1
        self.connect_btn.configure(state="normal" if has_choice and not self.busy else "disabled")
        self.led_btn.configure(state="normal" if has_choice and not self.busy else "disabled")

    def launch(self, coroutine, finish):
        def worker():
            try:
                result = asyncio.run(coroutine())
                self.root.after(0, lambda: finish(result, None))
            except Exception as exc:
                message = f"{type(exc).__name__}: {exc}"
                self.root.after(0, lambda: finish(None, message))
        threading.Thread(target=worker, daemon=True).start()

    def scan(self):
        self.listbox.delete(0, "end")
        self.devices.clear()
        self.set_busy(True, "Scanning Bluetooth Low Energy devices for 15 seconds...")
        self.write("Scanning. Compare Furby awake versus asleep if no obvious Furby entry appears.")
        async def work():
            return await BleakScanner.discover(timeout=15.0)
        def done(result, error):
            if error:
                self.write("Scan failed: " + error)
                self.set_busy(False, "Scan failed. Check Windows Bluetooth and try again.")
                return
            self.devices = result or []
            for device in self.devices:
                # Do not display stable device IDs / MAC addresses.
                self.listbox.insert("end", device.name or "(unnamed BLE device)")
            self.write(f"Found {len(self.devices)} devices.")
            self.set_busy(False, "Choose a device, then select Connect & inspect.")
        self.launch(work, done)

    def connect(self):
        selection = self.listbox.curselection()
        if not selection:
            return
        device = self.devices[selection[0]]
        self.set_busy(True, "Connecting and reading GATT service metadata...")
        async def work():
            lines = []
            async with BleakClient(device, timeout=15.0) as client:
                lines.append("Connected: " + str(client.is_connected))
                for service in client.services:
                    lines.append(f"Service: {service.uuid} ({service.description})")
                    for characteristic in service.characteristics:
                        lines.append(f"  Characteristic: {characteristic.uuid} [{', '.join(characteristic.properties)}]")
            lines.append("Disconnected safely. No characteristic values were read or written.")
            return "\n".join(lines)
        def done(result, error):
            self.write("Connection failed: " + error if error else result)
            self.set_busy(False, "Connection complete." if not error else "Could not connect; wake Furby and retry.")
        self.launch(work, done)


    def antenna_test(self):
        selection = self.listbox.curselection()
        if not selection:
            return
        device = self.devices[selection[0]]
        color_name = self.color.get()
        rgb = ANTENNA_COLORS[color_name]
        self.set_busy(True, "Connecting for a single antenna-light command...")
        async def work():
            async with BleakClient(device, timeout=15.0) as client:
                service_uuids = {str(service.uuid).lower() for service in client.services}
                if FURBY_SERVICE not in service_uuids:
                    raise RuntimeError("Selected device does not expose the known Furby Connect service. No command sent.")
                char_uuids = {str(char.uuid).lower() for service in client.services for char in service.characteristics}
                if FURBY_WRITE not in char_uuids:
                    raise RuntimeError("Expected Furby control characteristic was not found. No command sent.")
                await client.write_gatt_char(FURBY_WRITE, bytes((0x14, *rgb)), response=False)
            return f"Sent documented antenna RGB command: {color_name} {rgb}. Disconnected."
        def done(result, error):
            self.write("Antenna test failed: " + error if error else result)
            self.set_busy(False, "Antenna test finished." if not error else "Antenna test did not finish.")
        self.launch(work, done)


if __name__ == "__main__":
    root = tk.Tk()
    RaggaMuffinApp(root)
    root.mainloop()
