# weigh_events.py — one calibrated JSON weight event per item (transfer-clip flow)
#
# Workflow this implements:
#   hang item on clip -> weight rises -> holds steady -> ONE event emitted
#   -> remove item (return to zero) -> re-armed for the next item.
#
# Output is newline-delimited JSON on the serial port — the transport-agnostic
# INTERFACE the partner app consumes. Example events:
#   {"event": "ready",  "calibrated": false, "noise_g": 250.0, "ts": 812}
#   {"event": "weight", "grams": 342.5, "stable": true, "calibrated": true, "ts": 9021}
#   {"event": "error",  "reason": "sensor_timeout", "ts": 9500}
#
# To move to Wi-Fi/MQTT or BLE later, change ONLY emit() (publish the same dict).
# Nothing else — and the app's data contract stays identical.
#
# Run:  mpremote run weigh_events.py

from machine import Pin
from hx711_pio import HX711
import time, json

DT_PIN = 16       # GP16 (see WIRING.md); HX711 constructor order is (SCK, DATA)
SCK_PIN = 17      # GP17

# --- tuning, in grams. When the board is UNCALIBRATED (scale=1) these auto-
# --- raise to the measured noise floor so raw counts don't false-trigger. ---
LOAD_THRESHOLD = 10.0   # min load to treat as "an item is on the clip"
RETURN_BAND    = 5.0    # within +/- this of zero = "empty again" -> re-arm
STABLE_TOL     = 2.0    # settled when the reading window spans less than this
STABLE_N       = 6      # in-band samples in a row needed to call it settled
SAMPLE_DT      = 0.10   # seconds between samples
REARM_N        = 8      # consecutive near-zero samples to re-arm (~0.8s).
                        # Debounce: a swinging item can dip below threshold for a
                        # moment — that must NOT re-arm and double-fire an event.
HEARTBEAT_S    = 2.0    # emit a status event this often (0 to disable) — shows
                        # live grams + state so the host can see what's happening


def load_calib(path="calib.json"):
    try:
        with open(path) as f:
            c = json.load(f)
        return c.get("offset", 0), c.get("scale", 1), True
    except (OSError, ValueError):
        return 0, 1, False


def safe_read(hx, retries=4):
    # One transient sensor timeout (loose jumper / power blip) shouldn't kill us.
    for _ in range(retries):
        try:
            return hx.read()
        except OSError:
            time.sleep_ms(50)
    return None


def emit(evt):
    # SINGLE output point. Swap this for an MQTT publish or BLE notify later;
    # keep the dict shape identical so the app never has to change.
    print(json.dumps(evt))


def main():
    hx = HX711(Pin(SCK_PIN), Pin(DT_PIN), state_machine=0)
    offset, scale, calibrated = load_calib()
    hx.set_offset(offset)
    hx.set_scale(scale)

    # --- auto-zero + noise estimate at startup (cell must be EMPTY here) ---
    samples = []
    while len(samples) < 25:
        r = safe_read(hx)
        if r is not None:
            samples.append(r)
        time.sleep(SAMPLE_DT)
    zero = sum(samples) / len(samples)
    hx.set_offset(zero)                       # fresh tare over the real rest value
    noise = (max(samples) - min(samples)) / (scale if scale else 1)   # grams

    # thresholds, floored to the noise so an uncalibrated board behaves
    load_th = max(LOAD_THRESHOLD, noise * 5)
    ret_th  = max(RETURN_BAND, noise * 3)
    stab_tol = max(STABLE_TOL, noise * 2)

    emit({"event": "ready", "calibrated": calibrated,
          "noise_g": round(noise, 3), "load_threshold_g": round(load_th, 3),
          "ts": time.ticks_ms()})

    ARMED, WEIGHING, DONE = 0, 1, 2
    state = ARMED
    window = []
    zero_run = 0            # consecutive near-zero samples (for re-arm debounce)
    names = ("armed", "weighing", "done")
    last_hb = time.ticks_ms()

    while True:
        r = safe_read(hx)
        if r is None:
            emit({"event": "error", "reason": "sensor_timeout", "ts": time.ticks_ms()})
            time.sleep(0.2)
            continue
        g = (r - hx.OFFSET) / (scale if scale else 1)   # grams vs current zero

        if HEARTBEAT_S and time.ticks_diff(time.ticks_ms(), last_hb) >= HEARTBEAT_S * 1000:
            emit({"event": "status", "g": round(g, 1), "state": names[state],
                  "ts": time.ticks_ms()})
            last_hb = time.ticks_ms()

        if state == ARMED:
            if g > load_th:
                state = WEIGHING
                window = [g]
            elif abs(g) < ret_th:
                # slow auto-zero to fight baseline drift while idle
                hx.set_offset(hx.OFFSET + 0.05 * (r - hx.OFFSET))

        elif state == WEIGHING:
            window.append(g)
            if len(window) > STABLE_N:
                window.pop(0)
            if len(window) == STABLE_N and (max(window) - min(window)) < stab_tol:
                grams = sum(window) / len(window)
                emit({"event": "weight", "grams": round(grams, 1),
                      "stable": True, "calibrated": calibrated,
                      "n": STABLE_N, "ts": time.ticks_ms()})
                state = DONE
            elif g < ret_th:
                zero_run += 1
                if zero_run >= REARM_N:  # sustained zero = truly removed
                    state = ARMED
                    zero_run = 0
            else:
                zero_run = 0

        elif state == DONE:
            if g < ret_th:
                zero_run += 1
                if zero_run >= REARM_N:  # debounced: a swing-dip won't re-arm
                    state = ARMED
                    zero_run = 0
            else:
                zero_run = 0

        time.sleep(SAMPLE_DT)


main()
