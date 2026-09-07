# Fridge Scale — MVP

Calibrated load-cell scale: Pico 2 W + HX711 + 1 kg bar cell → live grams →
Bluetooth LE → web app. Working end-to-end as of 2026-07-21.

## Repo layout

    firmware/          MicroPython (runs on the Pico 2 W)
      weigh_ble.py       ← MAIN: broadcasts grams over BLE as "FridgeScale"
      weigh.py           live grams over USB serial (debug/bench)
      calibrate.py       tare + known-weight calibration → writes calib.json
      weigh_events.py    one-JSON-event-per-item state machine (serial; for
                         the future HTTPS/eventing path — see docs/HANDOFF.md)
    app/
      index.html         Web Bluetooth app (Chrome/Edge/Android). Static file —
                         deploys to Vercel as-is. Connect → live grams → Zero.
    docs/
      WIRING.md          pin map (HX711 VCC→3V3 pin 36, DT→GP16, SCK→GP17)
      HANDOFF.md         full tech state + environment quirks + architecture
      PRODUCT.md         product strategy, MVP scope, metrics
    hardware/
      clip_design.scad   parametric clip CAD (OpenSCAD)
    calib.json           calibration record (copy also lives on the board)

## Quick start (hardware attached)

    # live weight over Bluetooth (then open app/index.html in Chrome)
    zsh -i -c 'mpremote connect /dev/cu.usbmodem14101 run firmware/weigh_ble.py'

    # or over USB serial
    zsh -i -c 'mpremote connect /dev/cu.usbmodem14101 run firmware/weigh.py'

    # test the app locally (Web Bluetooth needs localhost or https)
    python3 -m http.server 8000    # then http://localhost:8000/app/

## Develop without the load cell

The web interface has a **Run demo** mode that generates a settling signal in
the browser. No Pico or sensor is required:

    python3 -m http.server 8000

Open `http://localhost:8000/app/` in Chrome or Edge and select **Run demo**.

To prove the Pico-to-computer path with no HX711 attached:

    mpremote connect auto run firmware/mock_serial.py

To send that simulated stream into the web interface over USB, temporarily
install the mock as the Pico startup program, then select **Connect USB**:

    mpremote connect auto fs cp firmware/mock_serial.py :main.py
    mpremote connect auto reset

Remove the temporary startup program after testing:

    mpremote connect auto fs rm :main.py

## Current calibration

offset −7259, scale 603.44 counts/gram (50.0 g = 10 US nickels; verified
reading 49.4 g). **Fixture-specific** — recalibrate after any mounting change:
edit KNOWN_GRAMS in firmware/calibrate.py, run it, follow the countdowns.

## BLE contract (for the app)

- Device name: `FridgeScale`
- Service UUID: `5f6d0001-1e2d-4b3a-9c8f-0a1b2c3d4e5f`
- Characteristic (read/notify): `5f6d0002-1e2d-4b3a-9c8f-0a1b2c3d4e5f`
  — ASCII grams, e.g. `"49.4"`, ~3 Hz
- iOS Safari has no Web Bluetooth: use Chrome on Android/desktop for MVP;
  native wrapper (Capacitor) later if iOS is needed.

## Known gotchas

- `mpremote` needs an interactive shell on this Mac: wrap every call in
  `zsh -i -c '...'`.
- Only ONE process can hold the serial port. "failed to access" →
  `lsof /dev/cu.usbmodem*`, stop the holder (Ctrl+C in its terminal).
- The port NAME can change after a USB hiccup/replug (14101 ↔ 14201 …).
  If access fails with nothing holding it: `mpremote connect list` and use
  whatever `usbmodem` it shows.
- The board also has `main_raw.py` + `lib/hx711_pio.py` (driver) — keep both.
- SHARED folder: no secrets here, ever (Wi-Fi creds etc. go on the board only).
