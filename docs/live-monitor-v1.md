# RaggaMuffin live monitoring v1

## What's new

- Scan Bluetooth and select the Furby Connect device.
- **Connect & monitor** opens one persistent BLE connection and subscribes to notifications on `dab91382-b5a1-e29c-b041-bcd562613bde`.
- **Bluetooth Details** shows incoming messages as hexadecimal bytes. Packet prefix `0x21` is labeled **Sensor status**, `0x20` is labeled **Furby message**; other packets remain unclassified.
- **2D Furby Hardware Map** shows the BLE connection state and counts sensor frames received.
- **Test antenna light** uses the already open connection for the previously verified RGB command (`0x14 R G B`).
- **Disconnect** ends the BLE session.

## How to test

1. Close any older RaggaMuffin window before replacing its EXE.
2. Download the successful new Windows build from **Actions → Build Windows EXE**.
3. Wake Furby and select it after scanning.
4. Click **Connect & monitor**. Once connected, open **Bluetooth Details**.
5. Pet, tilt, gently move, or touch Furby. Watch for new notification packets. Some event types may require a documented command to enable a stream; this v1 implementation does not send those commands.
6. Try an antenna color while still connected, then click **Disconnect**.

## Scientific honesty and safety

Receiving a `0x21` packet does not by itself establish which sensor was triggered. We do **not** map individual bytes to petting/tilt/antenna until tested or independently documented. No motor, audio, firmware-update, or DLC commands are used. The app has not been physically regression-tested with this Furby after these changes.

Protocol source: https://github.com/Jeija/bluefluff/blob/master/doc/generalplus.md
