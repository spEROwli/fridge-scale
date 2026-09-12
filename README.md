# Fridge Scale

## Purpose

A load-cell scale for fridge inventory: Pico 2 W + HX711 → live grams over
Bluetooth LE → a static web page (`Connect` → grams → `Zero`).

## Current status

**Works** (bench, 2026-07-21) — 1 kg fixture, firmware `weigh_ble.py`, web app:

- Pico 2 W broadcasts ASCII grams over BLE as `FridgeScale`
- `app/index.html` in Chrome/Edge/Android (Web Bluetooth) shows live grams and a software zero
- USB serial debug: `firmware/weigh.py`
- Driver `lib/hx711_pio.py` (robert-hh PIO) lives **on the board**, not in this repo

**Untested**

- Planned **10 kg** assembly (new cell / fixture) — not built, not calibrated
- JSON one-event-per-item path, Wi-Fi, HTTPS ingest
- Native / iOS client (no Web Bluetooth on Safari)
- Headless auto-start as `main.py`

## Architecture

Pico 2 W reads the HX711 and BLE-notifies ASCII grams; `app/index.html` is the client.

## Why this revision

The working path is BLE grams on the 1 kg fixture. Newer eventing notes, product
handoffs, and a hardware-free simulator were easy to mistake for that path.
README is now the only front door: what works, what is untested, how to reproduce.

## Wiring

### Working — 1 kg fixture

Pico 2 W (RP2350, MicroPython v1.28.0) + HX711 + **1 kg** 4-wire bar cell.
Verified on this fixture only.

Load cell → HX711: red E+, black E−, green A+, white A− (swap A+/A− if the sign is inverted).

| HX711 | Pico | Physical pin | Notes |
|-------|------|--------------|--------|
| VCC | 3V3(OUT) | 36 | 3.3 V only — never 5 V / VBUS |
| GND | GND | 38 | any GND |
| DT/DOUT | GP16 | 21 | |
| SCK | GP17 | 22 | ctor order is `(SCK, DATA)`: `HX711(Pin(17), Pin(16), state_machine=0)` |

### Planned — 10 kg assembly

Not built. Same Pico + HX711 pin map is the intent; different cell and fixture.
Recalibrate after the swap. Do **not** reuse 1 kg calibration numbers. Untested.

## Results

One historical measurement on the **prior 1 kg fixture** (cantilever in vise,
U-channel as hook): known **50.0 g** (10 US nickels) read back **49.4 g**.

That is not an accuracy spec and is not evidence for a 10 kg (or any new) sensor.

## Reproduce

Board must already have `lib/hx711_pio.py`. Copy a real `calib.json` onto the
board (from `firmware/calibrate.py`); `calib.example.json` in git is the
historical 1 kg record only.

    bash .cursor/install.sh
    source .venv/bin/activate
    mpremote connect list                          # port name can change after replug
    mpremote run firmware/weigh_ble.py             # then http://localhost:8000/app/
    # serial debug:  mpremote run firmware/weigh.py
    python3 -m http.server 8000                    # Web Bluetooth needs localhost or https

On the original Mac, `mpremote` needed an interactive shell:
`zsh -i -c 'mpremote connect /dev/cu.usbmodem14101 run firmware/weigh_ble.py'`.
Only one process may hold the serial port (`lsof /dev/cu.usbmodem*` if "failed to access").

### Demo data (secondary)

`tools/scale_sim.py` and `http://localhost:8000/app/?demo` are **synthetic demo
data**, not sensor readings. They do not prove the board, the 1 kg fixture, or
the 10 kg assembly.

## BLE contract

- Device name: `FridgeScale`
- Service: `5f6d0001-1e2d-4b3a-9c8f-0a1b2c3d4e5f`
- Characteristic (read/notify): `5f6d0002-1e2d-4b3a-9c8f-0a1b2c3d4e5f` — ASCII grams, e.g. `"49.4"`, ~3 Hz

## Deferred

- 10 kg cell + fixture, then a new calibration
- Wi-Fi / HTTPS ingest; `secrets.py` on the board only (never in git)
- Native iOS/Android client
- Promote `weigh_ble.py` to `main.py` (do not clobber `main_raw.py` on the board)
