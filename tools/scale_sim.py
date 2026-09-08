#!/usr/bin/env python3
"""scale_sim.py — simulate the Fridge Scale board with NO hardware attached.

A Cloud Agent VM (and CI) has no USB, no BLE, and no load cell, so the real
firmware in ``firmware/`` cannot run here. This simulator stands in for the
board: it drives a synthetic weight trace through the SAME state-machine logic
as ``firmware/weigh_events.py`` and emits the identical, frozen event contract
(see docs/HANDOFF.md §"Event schema"). It lets the event pipeline / app be
exercised end-to-end without the physical Pico 2 W.

Two output modes:

  events  (default)  newline-delimited JSON, exactly like weigh_events.py:
                       {"event":"ready", ...}
                       {"event":"status","g":...,"state":"armed", ...}
                       {"event":"weight","grams":342.5,"stable":true, ...}
  grams              plain "%.1f" grams per line, like the BLE characteristic
                     payload broadcast by weigh_ble.py / the serial stream in
                     weigh.py — handy for piping into a bridge.

Examples
--------
  # simulate placing a 342.5 g item then a 1015 g item, JSON events:
  python tools/scale_sim.py --items 342.5 1015

  # fast, deterministic run for tests:
  python tools/scale_sim.py --items 342.5 --speed 20 --seed 1

  # raw grams stream (like the BLE payload):
  python tools/scale_sim.py --mode grams --items 500
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time

# --- Tuning mirrors firmware/weigh_events.py (grams). ---
LOAD_THRESHOLD = 10.0   # min load to treat as "an item is on the scale"
RETURN_BAND = 5.0       # within +/- this of zero = "empty again" -> re-arm
STABLE_TOL = 2.0        # settled when the reading window spans less than this
STABLE_N = 6            # in-band samples in a row needed to call it settled
SAMPLE_DT = 0.10        # seconds between samples (scaled by --speed)
REARM_N = 8             # consecutive near-zero samples to re-arm
HEARTBEAT_S = 2.0       # emit a status event this often (0 disables)


def load_calib(path: str = "calib.json") -> tuple[float, float, bool]:
    """Return (offset, scale, calibrated) — same shape weigh_events.py uses."""
    try:
        with open(path) as f:
            c = json.load(f)
        return float(c.get("offset", 0)), float(c.get("scale", 1)), True
    except (OSError, ValueError):
        return 0.0, 1.0, False


class FakeCell:
    """Synthetic HX711 + load cell: turns a target mass (grams) into raw counts.

    raw = offset + grams * scale + gaussian_noise, so the simulator produces
    exactly the kind of samples weigh_events.py consumes from real hardware.
    """

    def __init__(self, offset: float, scale: float, noise_counts: float, rng: random.Random):
        self.offset = offset
        self.scale = scale if scale else 1.0
        self.noise = noise_counts
        self.rng = rng
        self.target_g = 0.0
        self.offset_tare = offset  # software zero (set fresh at startup auto-tare)

    def set_target_grams(self, grams: float) -> None:
        self.target_g = grams

    def read(self) -> int:
        return round(self.offset + self.target_g * self.scale + self.rng.gauss(0, self.noise))


def build_trace(items: list[float]) -> list[tuple[float, float]]:
    """Synthetic weight program: list of (duration_s, grams) segments.

    empty rest -> place item -> hold -> remove -> (repeat) -> final rest.
    """
    trace: list[tuple[float, float]] = [(3.0, 0.0)]  # empty at boot (auto-tare)
    for g in items:
        trace.append((1.0, 0.0))    # settle at zero / re-armed
        trace.append((4.0, g))      # item placed and held
        trace.append((1.5, 0.0))    # item removed
    trace.append((1.5, 0.0))        # final rest
    return trace


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Simulate the Fridge Scale board (no hardware).")
    ap.add_argument("--mode", choices=["events", "grams"], default="events",
                    help="events = weigh_events.py JSON (default); grams = plain grams stream")
    ap.add_argument("--items", type=float, nargs="*", default=[342.5],
                    help="masses in grams to place, one after another")
    ap.add_argument("--device", default="fridge-scale-sim", help="device id in events")
    ap.add_argument("--speed", type=float, default=5.0,
                    help="time acceleration (1 = real time, 20 = 20x faster)")
    ap.add_argument("--noise-counts", type=float, default=250.0,
                    help="raw-count noise stddev (~250 matches the real bench baseline)")
    ap.add_argument("--seed", type=int, default=None, help="RNG seed for reproducible runs")
    ap.add_argument("--calib", default="calib.json", help="path to calibration record")
    args = ap.parse_args(argv)

    rng = random.Random(args.seed)
    offset, scale, calibrated = load_calib(args.calib)
    cell = FakeCell(offset, scale, args.noise_counts, rng)
    dt = SAMPLE_DT / args.speed if args.speed > 0 else 0.0

    def emit_event(evt: dict) -> None:
        # SINGLE output point, mirroring weigh_events.py's emit().
        print(json.dumps(evt), flush=True)

    # Simulated device clock (like the Pico's ticks_ms): advances by SAMPLE_DT
    # per sample regardless of --speed, so timestamps/heartbeats stay realistic.
    sim_ms = 0

    def now_ms() -> int:
        return sim_ms

    trace = build_trace(list(args.items))

    # --- Startup auto-tare + noise estimate (cell EMPTY here), as in firmware ---
    cell.set_target_grams(0.0)
    samples = [cell.read() for _ in range(25)]
    zero = sum(samples) / len(samples)
    cell.offset_tare = zero
    noise_g = (max(samples) - min(samples)) / (scale if scale else 1)
    sim_ms += round(25 * SAMPLE_DT * 1000)

    load_th = max(LOAD_THRESHOLD, noise_g * 5)
    ret_th = max(RETURN_BAND, noise_g * 3)
    stab_tol = max(STABLE_TOL, noise_g * 2)

    if args.mode == "events":
        emit_event({"event": "ready", "calibrated": calibrated,
                    "noise_g": round(noise_g, 3), "load_threshold_g": round(load_th, 3),
                    "device": args.device, "ts": now_ms()})

    ARMED, WEIGHING, DONE = 0, 1, 2
    state = ARMED
    names = ("armed", "weighing", "done")
    window: list[float] = []
    zero_run = 0
    seq = 0
    last_hb = now_ms()

    for seg_dt, seg_g in trace:
        n_samples = max(1, round(seg_dt / SAMPLE_DT))
        for _ in range(n_samples):
            sim_ms += round(SAMPLE_DT * 1000)
            cell.set_target_grams(seg_g)
            r = cell.read()
            g = (r - cell.offset_tare) / (scale if scale else 1)

            if args.mode == "grams":
                print("%.1f" % g, flush=True)
                time.sleep(dt)
                continue

            if HEARTBEAT_S and sim_ms - last_hb >= HEARTBEAT_S * 1000:
                emit_event({"event": "status", "g": round(g, 1), "state": names[state],
                            "ts": now_ms()})
                last_hb = now_ms()

            if state == ARMED:
                if g > load_th:
                    state = WEIGHING
                    window = [g]
                elif abs(g) < ret_th:
                    cell.offset_tare += 0.05 * (r - cell.offset_tare)
            elif state == WEIGHING:
                window.append(g)
                if len(window) > STABLE_N:
                    window.pop(0)
                if len(window) == STABLE_N and (max(window) - min(window)) < stab_tol:
                    grams = sum(window) / len(window)
                    seq += 1
                    emit_event({"event": "weight", "grams": round(grams, 1),
                                "stable": True, "calibrated": calibrated, "n": STABLE_N,
                                "seq": seq, "device": args.device, "ts": now_ms()})
                    state = DONE
                elif g < ret_th:
                    zero_run += 1
                    if zero_run >= REARM_N:
                        state, zero_run = ARMED, 0
                else:
                    zero_run = 0
            elif state == DONE:
                if g < ret_th:
                    zero_run += 1
                    if zero_run >= REARM_N:
                        state, zero_run = ARMED, 0
                else:
                    zero_run = 0

            time.sleep(dt)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        # Downstream consumer (e.g. `| head`) closed the pipe — exit quietly.
        try:
            sys.stdout.close()
        except Exception:
            pass
        sys.exit(0)
