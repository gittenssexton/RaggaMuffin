# RaggaMuffin 2D hardware map

The Windows application's **2D Furby Hardware Map** tab is an interactive conceptual schematic, not a literal circuit-board layout. Selecting a labeled subsystem shows its current test status.

## Verified on user's 2016 Furby Connect

- Bluetooth Low Energy connection to a device exposing the known Furby Connect custom service.
- Antenna RGB LED changed color using RaggaMuffin's command.

## Not yet verified by RaggaMuffin

- Individual touch and motion events over BLE.
- Eye animation control.
- Beak and body movement commands.
- Playing specific audio content or arbitrary speech.

These are proposed investigation targets; diagrams should not imply independent motors or sensor placement beyond what is documented.

## Safety

Keep firmware-update characteristics untouched. Avoid speculative writes and sustained movement commands. Validate each behavior on the physical device before labeling it as working. The 2D view is implemented directly in `app.py` with Tkinter canvas shapes, so it needs no external image assets.
