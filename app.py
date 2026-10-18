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
        root.geometry("940x700")
        root.minsize(760, 560)
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
        notebook = ttk.Notebook(main)
        notebook.pack(fill="both", expand=True, pady=(10, 0))
        map_tab = ttk.Frame(notebook)
        log_tab = ttk.Frame(notebook)
        notebook.add(map_tab, text="2D Furby Hardware Map")
        notebook.add(log_tab, text="Bluetooth Details")
        self.map_canvas = tk.Canvas(map_tab, width=875, height=420, background="#f5f8fc", highlightthickness=0)
        self.map_canvas.pack(fill="both", expand=True)
        self.map_canvas.bind("<Configure>", lambda _e: self.draw_map())
        self.map_canvas.bind("<Button-1>", self.map_clicked)
        self.map_note = tk.StringVar(value="Select a part on the map. Green = tested; blue = Bluetooth detected; amber = next experiment.")
        ttk.Label(map_tab, textvariable=self.map_note, wraplength=850).pack(anchor="w", pady=4)
        self.log = tk.Text(log_tab, height=10, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True)
        ttk.Label(main, text="Antenna LED control is tested. Other features are shown as investigation targets, not enabled hardware controls.", wraplength=900).pack(anchor="w", pady=(7, 0))


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


    def draw_map(self):
        c = self.map_canvas
        c.delete("all")
        w = max(c.winfo_width(), 760)
        h = max(c.winfo_height(), 360)
        center = w / 2
        # Flat two-dimensional schematic rather than an unsupported 3-D or physical cutaway.
        c.create_oval(center-130, 97, center+130, h-22, fill="#46c1d7", outline="#16758e", width=4)
        c.create_polygon(center-100, 175, center-164, 42, center-34, 105, fill="#5cbed6", outline="#16758e", width=3)
        c.create_polygon(center+100, 175, center+164, 42, center+34, 105, fill="#5cbed6", outline="#16758e", width=3)
        c.create_oval(center-90, 122, center+90, 258, fill="#ecf4f8", outline="#b9d1d9", width=3)
        for dx in (-43, 43):
            c.create_oval(center+dx-34, 151, center+dx+34, 217, fill="#242557", outline="#707dde", width=3)
            c.create_oval(center+dx-15, 167, center+dx+15, 199, fill="#9ec6ff", outline="")
        c.create_oval(center-30, 206, center+30, 247, fill="#ffc04f", outline="#b77724", width=3)
        c.create_line(center, 97, center, 43, fill="#578795", width=8)
        c.create_oval(center-17, 20, center+17, 54, fill="#a5f2dd", outline="#087b55", width=3, tags="antenna")
        c.create_text(center, 10, text="ANTENNA LED • VERIFIED", fill="#087b55", font=("Segoe UI", 10, "bold"))
        c.create_text(center, h-15, text="FURBY CONNECT 2016 • schematic, not a wiring diagram", fill="#56677c", font=("Segoe UI", 9))
        specs = [
            ("Bluetooth / BLE", "DETECTED", "#276ec1", 18, 45, center-125, 120),
            ("Touch / petting", "UNTESTED", "#bd6d15", 18, 116, center-106, 180),
            ("Tilt / movement", "UNTESTED", "#bd6d15", 18, 187, center-95, 286),
            ("Sound input", "UNTESTED", "#bd6d15", 18, 258, center-85, 328),
            ("Internal events", "UNTESTED", "#bd6d15", 18, 329, center-60, 330),
            ("Antenna light", "VERIFIED", "#168452", w-219, 45, center+16, 37),
            ("Eye animation", "UNTESTED", "#bd6d15", w-219, 116, center+45, 181),
            ("Beak / mouth", "UNTESTED", "#bd6d15", w-219, 187, center+26, 230),
            ("Body movement", "UNTESTED", "#bd6d15", w-219, 258, center+99, 299),
            ("Speaker / audio", "UNTESTED", "#bd6d15", w-219, 329, center+55, 332),
        ]
        self.map_regions = []
        for name, status, color, x, y, targetx, targety in specs:
            c.create_line(x + (194 if x < center else 0), y+20, targetx, targety, fill=color, width=2)
            c.create_rectangle(x, y, x+194, y+41, fill="#ffffff", outline=color, width=2)
            c.create_text(x+8, y+10, anchor="w", text=name, fill="#273c50", font=("Segoe UI", 10, "bold"))
            c.create_text(x+8, y+29, anchor="w", text=status, fill=color, font=("Segoe UI", 9))
            self.map_regions.append((x, y, x+194, y+41, name))

    def map_clicked(self, event):
        for x1, y1, x2, y2, name in getattr(self, "map_regions", []):
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                if name == "Antenna light":
                    self.map_note.set("LED is confirmed. Choose a color above and click Test antenna light.")
                elif name == "Bluetooth / BLE":
                    self.map_note.set("BLE connection and custom Furby services have been confirmed. Use Connect & inspect.")
                else:
                    self.map_note.set(name + ": hardware capability to investigate; no tested command is enabled yet.")
                return


if __name__ == "__main__":
    root = tk.Tk()
    RaggaMuffinApp(root)
    root.mainloop()
