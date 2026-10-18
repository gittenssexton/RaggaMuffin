"""RaggaMuffin Windows Bluetooth explorer (read-only)."""
import asyncio
import threading
import tkinter as tk
from tkinter import ttk
from bleak import BleakScanner, BleakClient


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
        self.status = tk.StringVar(value="Ready. No connection or commands sent.")
        ttk.Label(main, textvariable=self.status).pack(anchor="w", pady=8)
        self.listbox = tk.Listbox(main, height=7, exportselection=False)
        self.listbox.pack(fill="x")
        self.listbox.bind("<<ListboxSelect>>", lambda _event: self.update_buttons())
        ttk.Label(main, text="Results / service details:").pack(anchor="w", pady=(10, 3))
        self.log = tk.Text(main, height=10, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True)
        ttk.Label(main, text="Read-only: discovers devices and enumerates GATT services. No pairing PIN, firmware changes, or motor commands.", wraplength=660).pack(anchor="w", pady=(7, 0))

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


if __name__ == "__main__":
    root = tk.Tk()
    RaggaMuffinApp(root)
    root.mainloop()
