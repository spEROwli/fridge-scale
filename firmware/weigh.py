# weigh.py — live weight readings using saved calibration.
#
# Run from this folder:  mpremote run weigh.py
# Requires on the board:  lib/hx711_pio.py  and  calib.json (from calibrate.py).
# If calib.json is missing it falls back to offset=0 scale=1 (raw-ish counts).

from machine import Pin
from hx711_pio import HX711
import time, json

DT_PIN = 16       # GP16 (see WIRING.md); constructor order is (SCK, DATA)
SCK_PIN = 17      # GP17


def safe_units(hx, retries=3):
    # A transient "sensor timeout" (loose jumper, power blip) shouldn't kill
    # the loop — retry a few times, then report the glitch and keep going.
    for _ in range(retries):
        try:
            return hx.get_units()
        except OSError:
            time.sleep_ms(50)
    return None


def load_calib(path="calib.json"):
    try:
        with open(path) as f:
            c = json.load(f)
        return c["offset"], c["scale"]
    except (OSError, ValueError, KeyError):
        print("WARNING: no calib.json — showing uncalibrated counts.")
        return 0, 1


def main():
    hx = HX711(Pin(SCK_PIN), Pin(DT_PIN), state_machine=0)
    offset, scale = load_calib()
    hx.set_offset(offset)
    hx.set_scale(scale)
    print("offset=%d scale=%.6f" % (offset, scale))
    while True:
        grams = safe_units(hx)        # (lowpass_raw - offset) / scale
        if grams is None:
            print("-- sensor timeout (check wiring) --")
        else:
            print("%.1f g" % grams)
        time.sleep(0.3)


main()
