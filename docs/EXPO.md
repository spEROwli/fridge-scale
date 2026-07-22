# Expo app ↔ scale integration

How the Expo (React Native) app talks to the FridgeScale BLE peripheral.
Verified against react-native-ble-plx docs, July 2026.

## The one hard constraint

**Expo Go cannot do Bluetooth.** BLE is native code, so the app needs a
**development build** (custom dev client). After that one-time setup, the dev
workflow is normal Expo (hot reload etc.) — just launched from the dev client
instead of Expo Go.

## Setup (partner's app repo)

    npx expo install react-native-ble-plx

`app.json`:

    {
      "expo": {
        "plugins": [
          ["react-native-ble-plx", {
            "isBackgroundEnabled": false,
            "modes": ["central"],
            "bluetoothAlwaysPermission":
              "Allow $(PRODUCT_NAME) to connect to the fridge scale"
          }]
        ]
      }
    }

Build a dev client (either):

    npx expo prebuild && npx expo run:android   # or run:ios (needs macOS/Xcode)
    eas build --profile development             # cloud build, no Mac needed

Android 12+ also needs runtime permission requests for BLUETOOTH_SCAN /
BLUETOOTH_CONNECT before scanning (the plugin adds manifest entries only).

## BLE contract (must match firmware/weigh_ble.py)

| Field | Value |
|---|---|
| Device name | `FridgeScale` |
| Service UUID | `5f6d0001-1e2d-4b3a-9c8f-0a1b2c3d4e5f` |
| Weight characteristic | `5f6d0002-1e2d-4b3a-9c8f-0a1b2c3d4e5f` (read + notify) |
| Value format | ASCII grams, e.g. `"49.4"`, ~3 Hz. ble-plx delivers it base64-encoded. |

## Minimal client

    import { BleManager } from 'react-native-ble-plx';
    import { Buffer } from 'buffer';

    const SVC = '5f6d0001-1e2d-4b3a-9c8f-0a1b2c3d4e5f';
    const CHR = '5f6d0002-1e2d-4b3a-9c8f-0a1b2c3d4e5f';
    const manager = new BleManager();

    export function watchScale(onGrams) {
      manager.startDeviceScan([SVC], null, async (err, device) => {
        if (err || device?.name !== 'FridgeScale') return;
        manager.stopDeviceScan();
        const d = await device.connect();
        await d.discoverAllServicesAndCharacteristics();
        d.monitorCharacteristicForService(SVC, CHR, (e, ch) => {
          if (ch?.value) onGrams(parseFloat(Buffer.from(ch.value, 'base64').toString()));
        });
      });
    }

## Test without the app

`app/index.html` (Web Bluetooth, Chrome/Edge desktop or Android) is the
zero-install harness — use it to confirm the scale is advertising before
debugging the Expo side. iOS Safari has no Web Bluetooth; the Expo dev build
is the iOS path.

## Additive changes only

Firmware may add characteristics (e.g. a stable-event flag or battery level)
but existing UUIDs and the grams format never change — the app can depend on
this contract.
