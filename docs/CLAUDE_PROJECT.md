# Claude project instructions — Fridge Scale app (paste this into her Claude project)

You are helping build the app side of the Fridge Scale MVP: a smart-fridge
inventory system. The hardware side is DONE and working — a calibrated load
cell (Pico 2 W + HX711) broadcasts live weight in grams over Bluetooth LE.
Your job is the Expo (React Native) app that consumes it.

## Source of truth

Repo: https://github.com/spEROwli/fridge-scale (private; ask Phillip for access)

- `README.md` — quick start, BLE contract, hardware gotchas
- `docs/EXPO.md` — **read first**: verified Expo/BLE setup + working client code
- `docs/PRODUCT.md` — product strategy: JTBD, Milk-Bay MVP scope, metrics,
  kill criteria. Build THIS scope, resist feature creep.
- `docs/HANDOFF.md` — hardware/firmware state + future HTTPS/Vercel eventing path
- `app/index.html` — Web Bluetooth test harness (Chrome): proves the scale
  works before debugging app code
- `firmware/` — MicroPython on the Pico. Do not modify from the app project.

## Hard constraints (verified, don't relearn them)

1. **Expo Go cannot do BLE.** Use a development build:
   `react-native-ble-plx` + its config plugin in app.json, then
   `npx expo prebuild && npx expo run:android`, or
   `eas build --profile development` (iOS without a Mac).
2. **BLE contract is frozen** (additive changes only):
   - Device name `FridgeScale`
   - Service `5f6d0001-1e2d-4b3a-9c8f-0a1b2c3d4e5f`
   - Characteristic `5f6d0002-1e2d-4b3a-9c8f-0a1b2c3d4e5f`, notify,
     ASCII grams like "49.4" at ~3 Hz, base64-encoded by ble-plx.
   Working client snippet is in docs/EXPO.md — start from it.
3. **Android 12+** needs runtime BLUETOOTH_SCAN / BLUETOOTH_CONNECT requests.
4. iOS Safari / web has no Web Bluetooth — the Expo dev build IS the iOS path.
5. The scale reports **grams only**. Item identity, empty/full weights,
   servings, and "days left" math live in the app.

## MVP scope (from docs/PRODUCT.md — hold this line)

One item class (milk first), one screen: current weight → % remaining →
estimated days left (slope of weight history) → "running low" alert.
Tap-to-select item identity. No barcode scanning, no multi-user, no
auto-ordering in v1. Weight-history storage can be local (AsyncStorage/SQLite)
for the MVP; the Vercel/HTTPS ingest path in HANDOFF.md §6 is v2.

## Working style

- Test against `app/index.html` in Chrome first when BLE seems broken — it
  isolates hardware vs app issues in seconds.
- The scale must be powered and running `firmware/weigh_ble.py` to be
  discoverable (Phillip's side).
- Keep secrets out of the repo; it may be shared.
