# RaggaMuffin

An experimental, open-source AI companion project for the **2016 Furby Connect**.

## Goal

Explore the Furby Connect's Bluetooth Low Energy (BLE) interface, document reproducible findings, and gradually build a computer-hosted AI controller that can use the toy's original expressions, sensors, sounds and movement.

**Status:** Early research. No hardware communication has been verified on the owner's Furby yet.

## Guiding principles

- **Non-destructive first:** keep the original firmware and hardware intact.
- **Observe before control:** start with BLE discovery and read-only inspection; verify all commands against trustworthy sources before transmitting them.
- **Safe experiments:** avoid unsupported firmware updates, prolonged motor activation, and irreversible writes.
- **Separate intelligence from hardware:** future personality, speech, and memory components should communicate through a small Furby adapter so they can be adapted to other robots.
- **Document evidence:** distinguish verified hardware results from proposed features.

## Getting started (Windows)

1. Install Python 3.11 or later and enable Bluetooth on the computer.
2. Power up the Furby Connect with working batteries.
3. In a terminal, run:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python experiments/01_discover.py
```

The scanner lists visible BLE devices for 15 seconds and **does not connect or send commands**. Furby advertisements may appear under an unfamiliar name or without a name. Bluetooth behavior varies by firmware, proximity and connection state.

## Research references

- [Jeija / bluefluff](https://github.com/Jeija/bluefluff) — Furby Connect BLE reverse engineering.
- [martinwoodward / PyFluff](https://github.com/martinwoodward/PyFluff) — Python-oriented BLE experiments.

These are external reference projects, not vendored code. Review their licenses before reusing implementation.

## Roadmap

1. Detect the Furby using BLE advertisements.
2. Test a read-only connection and enumerate services where supported.
3. Verify and implement a narrowly scoped command adapter.
4. Demonstrate expressions and sensor-triggered reactions.
5. Add an optional external AI brain with explicit user controls and a safe shutdown.

See [research log](docs/research-log.md) for findings and open questions.
