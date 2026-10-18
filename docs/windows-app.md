# Windows app

RaggaMuffin includes a graphical, read-only Bluetooth discovery and connection inspector.

## Download an EXE from GitHub Actions

1. Open **Actions** in the RaggaMuffin repository.
2. Select **Build Windows EXE** and choose **Run workflow** (or open a completed run).
3. When the build succeeds, download the **RaggaMuffin-Windows** artifact from the run summary.
4. Extract the ZIP and double-click **RaggaMuffin.exe**.

The file is not signed; Windows SmartScreen may warn about unfamiliar downloads. Verify the artifact came from this repository before running.

## Development

On Windows, run:

```powershell
py -m pip install -r requirements.txt
py app.py
```

This application **does not pair via Windows Settings**, send Furby control commands, install firmware, or run an AI model. It uses Bluetooth Low Energy discovery, connects only after you select a device, lists available GATT services/characteristics, and disconnects. Furby Connect may appear unnamed. Compare scans when it is awake and asleep.
