# weigh_ble.py — Pico 2 W broadcasts live calibrated grams over Bluetooth LE.
#
# Advertises as "FridgeScale" with a custom GATT service; notifies weight
# (grams, as an ASCII string like "49.4") ~3x/sec to any connected central.
# Consume it from the Web Bluetooth page (app/index.html).
#
# Run:   mpremote connect /dev/cu.usbmodem14101 run weigh_ble.py
# Deploy headless: copy to the board as main.py (ASK first — keep main_raw.py).
#
# Needs on the board: lib/hx711_pio.py and calib.json (from calibrate).

import asyncio, aioble, bluetooth, json, time
from machine import Pin
from hx711_pio import HX711

# Custom 128-bit UUIDs — the web page / app must use these exact strings.
_SVC_UUID = bluetooth.UUID("5f6d0001-1e2d-4b3a-9c8f-0a1b2c3d4e5f")
_CHR_UUID = bluetooth.UUID("5f6d0002-1e2d-4b3a-9c8f-0a1b2c3d4e5f")
_ADV_US   = 250_000          # advertising interval (microseconds)
_NAME     = "FridgeScale"

DT_PIN, SCK_PIN = 16, 17     # GP16 data, GP17 clock (ctor order is SCK, DATA)


def init_hx():
    for _ in range(6):
        try:
            return HX711(Pin(SCK_PIN), Pin(DT_PIN), state_machine=0)
        except OSError:
            time.sleep_ms(200)
    raise OSError("HX711 init failed — check DT/SCK wiring")


hx = init_hx()
try:
    c = json.load(open("calib.json"))
    hx.set_offset(c["offset"]); hx.set_scale(c["scale"])
    print("calib loaded: offset=%d scale=%.3f" % (c["offset"], c["scale"]))
except Exception as e:
    print("WARNING no calib.json (%s) — sending raw-ish counts" % e)

_svc = aioble.Service(_SVC_UUID)
_weight = aioble.Characteristic(_svc, _CHR_UUID, read=True, notify=True)
aioble.register_services(_svc)


def read_grams():
    for _ in range(4):
        try:
            return hx.get_units()      # (lowpass - offset) / scale
        except OSError:
            time.sleep_ms(50)
    return None


async def sensor_task():
    while True:
        g = read_grams()
        if g is not None:
            _weight.write(("%.1f" % g).encode(), send_update=True)
        await asyncio.sleep_ms(300)


async def peripheral_task():
    while True:
        print("advertising as '%s' ..." % _NAME)
        try:
            async with await aioble.advertise(
                _ADV_US, name=_NAME, services=[_SVC_UUID]
            ) as conn:
                print("connected:", conn.device)
                await conn.disconnected()
                print("disconnected — re-advertising")
        except Exception as e:
            print("advertise error:", e)
            await asyncio.sleep_ms(500)


async def main():
    print("BLE scale starting")
    await asyncio.gather(sensor_task(), peripheral_task())


asyncio.run(main())
