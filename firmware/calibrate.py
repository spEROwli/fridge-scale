# calibrate.py — tare + two-point calibration for HX711 + load cell on Pico 2 W.
#
# Runs ON the board via:  mpremote run calibrate.py
# Uses countdowns (not input()) so it works when driven over the serial link.
#
# Two calibration points:
#   point 1 = zero load  -> OFFSET (the "tare")
#   point 2 = KNOWN_GRAMS -> SCALE  = (raw_at_load - OFFSET) / KNOWN_GRAMS
# Result (OFFSET, SCALE) is written to calib.json on the board so readings are
# reproducible. weigh.py reads that file back.

from machine import Pin
from hx711_pio import HX711
import time, json

# Wiring convention (see README, 1 kg fixture): DT=GP16, SCK=GP17.
# NOTE constructor arg order for this driver is (SCK, DATA).
DT_PIN = 16
SCK_PIN = 17

# ---- SET THIS to the mass of your reference weight, in grams ----
KNOWN_GRAMS = 200.0   # set to the reference mass on the cell you are calibrating


def countdown(msg, secs):
    for s in range(secs, 0, -1):
        print("%s %d..." % (msg, s))
        time.sleep(1)


def main():
    hx = HX711(Pin(SCK_PIN), Pin(DT_PIN), state_machine=0)
    hx.set_offset(0)
    hx.set_scale(1)

    print("=== HX711 calibration (KNOWN_GRAMS = %.1f) ===" % KNOWN_GRAMS)

    # --- Point 1: zero / tare ---
    countdown("Remove ALL weight from the cell. Taring in", 8)
    hx.tare(times=20)              # OFFSET = average raw with no load
    offset = hx.OFFSET
    print("offset (zero point) =", offset)

    # --- Point 2: known weight ---
    countdown("Place the %.1f g weight on the cell. Reading in" % KNOWN_GRAMS, 12)
    raw = hx.read_average(times=20)
    print("raw at load =", raw)

    span = raw - offset
    if span == 0:
        print("ERROR: no change between zero and load — check wiring / weight.")
        return
    scale = span / KNOWN_GRAMS     # counts per gram
    print("scale (counts/gram) = %.6f" % scale)

    with open("calib.json", "w") as f:
        json.dump({"offset": offset, "scale": scale, "known_g": KNOWN_GRAMS}, f)
    print("Saved calib.json")

    # --- Sanity check: should read back ~KNOWN_GRAMS ---
    hx.set_scale(scale)
    print("Check: current reading = %.1f g (expect ~%.1f)" % (hx.get_units(), KNOWN_GRAMS))
    print("Done. Run weigh.py for live readings.")


main()
