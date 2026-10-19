"""RaggaMuffin Windows Bluetooth explorer with a limited antenna LED test."""
import asyncio
import threading
import concurrent.futures
import time
from datetime import datetime
import tkinter as tk
from tkinter import ttk
from bleak import BleakScanner, BleakClient

FURBY_SERVICE = 'dab91435-b5a1-e29c-b041-bcd562613bde'
FURBY_NOTIFY = 'dab91382-b5a1-e29c-b041-bcd562613bde'
FURBY_WRITE = 'dab91383-b5a1-e29c-b041-bcd562613bde'
# Documented Bluefluff GeneralPlus command 0x14 followed by RGB.
# Fixed action IDs from Jeija/bluefluff doc/actionlist.md.
SAFE_ACTIONS = {"Friendly phrase": (1, 0, 0, 0), "Friendly purr": (1, 2, 1, 1), "Short giggle": (2, 0, 0, 1)}
ANTENNA_COLORS = {'Red': (255, 0, 0), 'Green': (0, 255, 0), 'Blue': (0, 0, 255), 'Off': (0, 0, 0)}


class RaggaMuffinApp:
    def __init__(self, root):
        self.root = root
        root.title("RaggaMuffin — Furby Connect")
        root.geometry("940x700")
        root.minsize(760, 560)
        self.devices = []
        self.busy = False
        self.client = None
        self.connected = False
        self.manual_disconnect = False
        self.reconnect_enabled = tk.BooleanVar(value=True)
        self.reconnect_job = None
        self.reconnect_attempt = 0
        self.selected_device = None
        self.connection_generation = 0
        self.connected_at = None
        self.disconnect_count = 0
        self.last_packet_at = None
        self.loop = asyncio.new_event_loop()
        self.ble_thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.ble_thread.start()
        self.notification_count = 0
        self.sensor_count = 0
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)
        main = ttk.Frame(root, padding=16)
        main.pack(fill="both", expand=True)
        ttk.Label(main, text="RaggaMuffin — Furby Connect", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(main, text="Wake Furby and keep it nearby. Scan first, then select its Bluetooth entry.").pack(anchor="w", pady=(4, 10))
        bar = ttk.Frame(main)
        bar.pack(fill="x")
        self.scan_btn = ttk.Button(bar, text="Scan Bluetooth (15s)", command=self.scan)
        self.scan_btn.pack(side="left")
        self.connect_btn = ttk.Button(bar, text="Connect & monitor", command=self.connect, state="disabled")
        self.connect_btn.pack(side="left", padx=8)
        self.disconnect_btn = ttk.Button(bar, text="Disconnect", command=self.disconnect, state="disabled")
        self.disconnect_btn.pack(side="left", padx=(0, 8))
        ttk.Checkbutton(main, text="Auto-reconnect after unexpected disconnect", variable=self.reconnect_enabled).pack(anchor="w", pady=(6, 0))
        self.color = tk.StringVar(value="Blue")
        self.color_choice = ttk.Combobox(bar, textvariable=self.color, values=list(ANTENNA_COLORS), state="readonly", width=8)
        self.color_choice.pack(side="left", padx=(8, 2))
        self.led_btn = ttk.Button(bar, text="Test antenna light", command=self.antenna_test, state="disabled")
        self.led_btn.pack(side="left", padx=4)
        actions_bar = ttk.Frame(main)
        actions_bar.pack(fill="x", pady=(7, 0))
        ttk.Label(actions_bar, text="Real Furby actions:").pack(side="left")
        self.action_name = tk.StringVar(value="Friendly phrase")
        ttk.Combobox(actions_bar, textvariable=self.action_name, values=list(SAFE_ACTIONS), state="readonly", width=19).pack(side="left", padx=6)
        self.action_btn = ttk.Button(actions_bar, text="Play action on Furby", command=self.play_action, state="disabled")
        self.action_btn.pack(side="left")
        self.monitor_var = tk.StringVar(value="Events: 0 | Sensor packets: 0 | Disconnects: 0")
        ttk.Label(main, textvariable=self.monitor_var).pack(anchor="w", pady=(4, 0))
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
        self.map_note = tk.StringVar(value="Antenna LED and three documented built-in actions are available. Other labeled parts remain informational.")
        ttk.Label(map_tab, textvariable=self.map_note, wraplength=850).pack(anchor="w", pady=4)
        self.log = tk.Text(log_tab, height=10, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True)
        ttk.Label(main, text="HOW TO USE: Scan -> select Furby -> Connect & monitor -> test antenna light or Play action on Furby. Start with Friendly phrase.", wraplength=900).pack(anchor="w", pady=(7, 0))


    def write(self, message):
        self.log.configure(state="normal")
        self.log.insert("end", datetime.now().strftime("[%H:%M:%S] ") + message + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def set_busy(self, busy, message):
        self.busy = busy
        self.status.set(message)
        self.update_buttons()

    def update_buttons(self):
        self.scan_btn.configure(state="disabled" if self.busy or self.connected else "normal")
        has_choice = len(self.listbox.curselection()) == 1
        self.connect_btn.configure(state="normal" if has_choice and not self.busy and not self.connected else "disabled")
        self.disconnect_btn.configure(state="normal" if not self.busy and self.connected else "disabled")
        self.led_btn.configure(state="normal" if has_choice and not self.busy and self.connected else "disabled")
        self.action_btn.configure(state="normal" if has_choice and not self.busy and self.connected else "disabled")

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
        if self.connected:
            self.write("Disconnect before scanning; scanning while connected may interrupt BLE on some adapters.")
            return
        self.cancel_reconnect()
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

    def ui(self, action, *args):
        try:
            self.root.after(0, lambda: action(*args))
        except (RuntimeError, tk.TclError):
            pass

    def submit(self, coroutine, on_done):
        future = asyncio.run_coroutine_threadsafe(coroutine, self.loop)
        def completed(f):
            try:
                value = f.result()
                self.ui(on_done, value, None)
            except Exception as exc:
                self.ui(on_done, None, str(exc))
        future.add_done_callback(completed)

    def receive(self, _sender, data):
        payload = bytes(data)
        self.notification_count += 1
        self.last_packet_at = time.monotonic()
        if payload and payload[0] == 0x21:
            self.sensor_count += 1
            event_type = "Sensor status (0x21)"
        elif payload and payload[0] == 0x20:
            event_type = "Furby message (0x20)"
        else:
            event_type = "GeneralPlus response"
        # No unsupported bit-to-sensor decoding: display only documented packet types.
        self.ui(self.show_event, event_type, payload.hex(" ").upper(),
                self.notification_count, self.sensor_count)

    def show_event(self, kind, hex_data, total, sensors):
        self.monitor_var.set(f"Events: {total} | Sensor packets: {sensors} | Disconnects: {self.disconnect_count}")
        self.write(f"{kind}: {hex_data}")
        if sensors and kind.startswith("Sensor"):
            self.map_note.set("Sensor activity received! Check the raw bytes under Bluetooth Details.")
        self.draw_map()

    async def open_connection(self, device):
        if self.client is not None and self.client.is_connected:
            return "Already connected."
        client = BleakClient(device, timeout=20.0, disconnected_callback=self.lost_connection)
        try:
            await client.connect()
            uuidset = {str(s.uuid).lower() for s in client.services}
            charmap = {str(ch.uuid).lower(): ch for s in client.services for ch in s.characteristics}
            if FURBY_SERVICE not in uuidset or FURBY_WRITE not in charmap or FURBY_NOTIFY not in charmap:
                raise RuntimeError("Device does not expose the expected Furby Connect control and notification interface.")
            await client.start_notify(FURBY_NOTIFY, self.receive)
            self.client = client
            return "Connected and subscribed to Furby GeneralPlus notifications."
        except Exception:
            if client.is_connected:
                await client.disconnect()
            raise

    def lost_connection(self, client):
        self.ui(self.connection_lost, client)

    def connection_lost(self, client):
        # Ignore stale callbacks from an earlier BLE session.
        if self.client is not client:
            return
        duration = time.monotonic() - self.connected_at if self.connected_at else None
        self.disconnect_count += 1
        if duration is not None and duration >= 60:
            self.reconnect_attempt = 0
        self.connected = False
        self.client = None
        elapsed = f" after {duration:.1f}s" if duration is not None else ""
        self.status.set("Bluetooth connection lost.")
        self.write(f"Bluetooth connection lost unexpectedly{elapsed}. Drop #{self.disconnect_count}.")
        self.connected_at = None
        self.update_buttons()
        self.draw_map()
        if not self.manual_disconnect and self.reconnect_enabled.get():
            self.schedule_reconnect()

    def cancel_reconnect(self):
        if self.reconnect_job is not None:
            self.root.after_cancel(self.reconnect_job)
            self.reconnect_job = None

    def schedule_reconnect(self):
        if self.manual_disconnect or self.connected or self.busy or self.reconnect_job is not None:
            return
        self.reconnect_attempt += 1
        if self.reconnect_attempt > 5:
            self.status.set("Reconnect paused after 5 attempts; use Connect & monitor.")
            self.write("Reconnect paused. Check batteries, distance, or competing apps.")
            return
        delay = min(30000, 1000 * (2 ** (self.reconnect_attempt - 1)))
        self.status.set(f"Retrying Bluetooth in {delay // 1000}s (attempt {self.reconnect_attempt}/5)...")
        self.reconnect_job = self.root.after(delay, self.retry_connect)

    def retry_connect(self):
        self.reconnect_job = None
        if self.manual_disconnect or self.connected or self.busy or self.selected_device is None:
            return
        self.start_connection(self.selected_device, automatic=True)

    def connect(self):
        choice = self.listbox.curselection()
        if not choice:
            return
        self.manual_disconnect = False
        self.reconnect_attempt = 0
        self.cancel_reconnect()
        self.selected_device = self.devices[choice[0]]
        self.start_connection(self.selected_device)

    def start_connection(self, device, automatic=False):
        self.connection_generation += 1
        generation = self.connection_generation
        self.set_busy(True, "Reconnecting..." if automatic else "Connecting and subscribing to sensor events...")
        def done(message, error):
            if generation != self.connection_generation:
                return
            if error:
                self.write("Bluetooth connection failed: " + error)
                self.set_busy(False, "Connection failed.")
                if self.reconnect_enabled.get() and not self.manual_disconnect:
                    self.schedule_reconnect()
            else:
                self.connected = bool(self.client and self.client.is_connected)
                if self.connected:
                    # A fleeting connection should not reset the retry budget.
                    # Only a stable connection lasting >=60s resets it upon loss.
                    self.connected_at = time.monotonic()
                    self.write(message)
                    self.set_busy(False, "Connected: monitoring incoming events.")
                else:
                    self.set_busy(False, "Connection closed during setup.")
                    if self.reconnect_enabled.get() and not self.manual_disconnect:
                        self.schedule_reconnect()
                self.draw_map()
        self.submit(self.open_connection(device), done)

    async def close_connection(self):
        client = self.client
        self.client = None
        if client and client.is_connected:
            try:
                await client.stop_notify(FURBY_NOTIFY)
            finally:
                await client.disconnect()
        return "Disconnected safely."

    def disconnect(self):
        self.manual_disconnect = True
        self.cancel_reconnect()
        self.connection_generation += 1
        self.set_busy(True, "Disconnecting...")
        def done(message, error):
            self.connected = False
            self.write(error or message)
            self.set_busy(False, "Disconnected.")
            self.draw_map()
        self.submit(self.close_connection(), done)

    def antenna_test(self):
        if not self.connected:
            self.write("Connect to Furby first.")
            return
        color_name = self.color.get()
        rgb = ANTENNA_COLORS[color_name]
        self.set_busy(True, "Sending antenna color...")
        async def work():
            client = self.client
            if not client or not client.is_connected:
                raise RuntimeError("Furby is disconnected.")
            await client.write_gatt_char(FURBY_WRITE, bytes((0x14, *rgb)), response=False)
            return f"Antenna command: {color_name} {rgb}"
        def done(message, error):
            self.write(error or message)
            self.set_busy(False, "Connected: monitoring incoming events." if not error else "Antenna command failed.")
        self.submit(work(), done)

    def play_action(self):
        if not self.connected:
            self.write("Connect to Furby first.")
            return
        name = self.action_name.get()
        action = SAFE_ACTIONS.get(name)
        if action is None:
            return
        self.set_busy(True, "Sending built-in Furby action...")
        async def work():
            client = self.client
            if not client or not client.is_connected:
                raise RuntimeError("Furby disconnected.")
            # 0x13: specific action; 00, Input, Index, Subindex, Specific.
            await client.write_gatt_char(FURBY_WRITE, bytes((0x13, 0x00, *action)), response=False)
            return f"Sent built-in action '{name}' (input/index/subindex/specific={action})."
        def done(message, error):
            self.write(error or message)
            self.set_busy(False, "Connected: action requested." if not error else "Action failed.")
        self.submit(work(), done)

    def on_close(self):
        self.manual_disconnect = True
        self.cancel_reconnect()
        # Request disconnect before shutting down the BLE event loop.
        try:
            future = asyncio.run_coroutine_threadsafe(self.close_connection(), self.loop)
            future.add_done_callback(lambda _f: self.loop.call_soon_threadsafe(self.loop.stop))
        except RuntimeError:
            pass
        self.root.destroy()

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
        c.create_text(center, h-48, text=f"BLE: {'CONNECTED' if self.connected else 'DISCONNECTED'}  |  Sensor frames: {self.sensor_count}", fill="#166086", font=("Segoe UI", 10, "bold"))
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
