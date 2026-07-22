# HANDOFF — Smart-Fridge Scale (Pico 2 W + HX711 + load cell)

Instructions for the assistant (Opus 4.8) continuing this project. Read fully
before touching the board. Audience: Phillip (hardware side) + partner building
the app (likely Vercel-hosted). This folder is a SHARED Google Drive — never
put Wi-Fi passwords, API tokens, or any secrets in it.

## 1. Project goal

A "smart fridge intelligence" system: weigh fridge items one at a time on a
load-cell station; an app tracks how much of each item is left and what to buy.
Hardware emits ONE calibrated JSON weight event per item; the partner's app
consumes those events.

## 2. Environment quirks (do not re-derive)

- Board: Raspberry Pi Pico 2 W (RP2350), MicroPython v1.28.0.
- Serial: `/dev/cu.usbmodem14101` (2e8a:0005). If missing: `mpremote connect list`.
- mpremote only resolves in interactive zsh — ALWAYS wrap:
  `zsh -i -c 'mpremote ...'`
- macOS has no `timeout` command. For bounded reads use a Python loop with a
  fixed sample count via `mpremote exec`, or background the run and kill it.
- The serial port is EXCLUSIVE. If mpremote says "failed to access", find the
  holder with `lsof /dev/cu.usbmodem14101` and ask/kill (user has approved
  killing stale weigh runs before — still confirm if unclear).
- Long-running reads: launch in background redirecting to a scratchpad log,
  then poll the log file.
- On the board already: `lib/hx711_pio.py` (robert-hh PIO driver — works,
  don't replace) and `main_raw.py` (456 B raw reader — do not clobber
  main.py/main_raw.py without asking).

## 3. Hardware state (verified so far)

- Wiring per WIRING.md: HX711 VCC→3V3 pin 36 (NEVER 5 V), GND→GND,
  DT→GP16, SCK→GP17. Driver ctor order is (SCK, DATA):
  `HX711(Pin(17), Pin(16), state_machine=0)`.
- Load cell: 1 kg, 4-wire (red E+, black E−, green A+, white A−).
- VERIFIED: comms, stable baseline (~250-count noise), strong response to
  load (~44 k counts for wire strippers), tare works.
- NOT DONE: calibration. `calib.json` does NOT exist on the board. All
  readings so far are raw counts. Reference weight on hand: ½ oz tungsten
  = 14.17 g (avoirdupois; 15.55 g if troy — confirm with user).
- Fixture: UNRESOLVED. Hanging/binder-clip rig stopped transferring load
  (readings pinned at zero while item hung — mechanical, not electrical).
  DECISION MADE: switch to a PLATFORM (kitchen-scale sandwich) build —
  bottom plate → spacers → fixed end; free end → spacers → top plate.
  Beam must be free to bend; never clamp its middle.
- Capacity: 1 kg cell is dev-only. Real fridge items need a 5 kg cell
  (gallon milk ≈ 3.8 kg). Same HX711/wiring/code; recalibrate after swap.

## 4. Code state (host folder = this directory)

- `weigh.py` — continuous reader, loads calib.json, timeout-tolerant.
- `calibrate.py` — tare + two-point calibration via countdowns; writes
  calib.json to the BOARD. Set KNOWN_GRAMS before running.
- `weigh_events.py` — THE key deliverable. State machine
  (armed→weighing→done) emitting newline-delimited JSON on serial:
  ready/status/weight/error events. Features: startup auto-tare (cell must
  be EMPTY at boot), noise-floor-scaled thresholds, stability window
  (6 samples within tolerance), re-arm debounce (REARM_N=8 sustained
  near-zero samples — prevents double-fire from swing dips), 2 s heartbeat,
  safe_read retries on OSError timeouts.
- `clip_design.scad` — parametric OpenSCAD transfer clip (hanging concept;
  superseded by platform decision but kept for reference).
- Single-point-of-output rule: ALL emission goes through `emit(dict)` in
  weigh_events.py. Transport changes (serial→HTTP/MQTT) must only change
  emit(); the event schema is frozen so the app never breaks.

## 5. Remaining execution plan (in order)

1. **Platform fixture** — user builds the sandwich; verify with heartbeat
   run: stable zero, then sustained load reading when an item sits on it.
2. **Calibrate** — empty tare → place known weight → compute
   scale = (raw_loaded − offset)/grams → write calib.json to board →
   sanity-check readback (±5% of reference is fine at 14 g; re-cal with a
   heavier known mass when available). Persist a copy of the constants in
   this folder (constants only — fine for shared Drive).
3. **Re-test weigh_events.py calibrated** — one on/off/on cycle must yield
   exactly 2 weight events with plausible grams. Platform mode: consider
   dropping REARM_N to ~4 (no pendulum swing).
4. **Wi-Fi transport** — see §6. Add `secrets.py` ON THE BOARD ONLY
   (SSID, password, DEVICE_TOKEN). Never copy it into this folder.
5. **Auto-start** — once transport works, promote to `main.py` on the board
   (ASK USER FIRST — main_raw.py must survive) so it runs headless on a
   USB wall adapter.
6. **5 kg cell swap** when hardware arrives: rewire A±/E± to new cell,
   re-run calibration, nothing else changes.

## 6. Integration architecture (partner's app on Vercel)

Vercel is serverless: no persistent processes, no MQTT broker, no inbound
connection to the Pico. Correct topology is PUSH from the device:

    Pico 2 W ──HTTPS POST──▶ Vercel API route ──▶ DB ──▶ app UI
    (urequests,               /api/weigh-event     (Vercel Postgres,
     Wi-Fi, TLS)              validates token,      Supabase, etc.)
                              inserts event

- Device → cloud: `urequests.post(URL, json=event, headers={"Authorization":
  "Bearer " + DEVICE_TOKEN})` from inside emit(). Batch/retry on failure;
  buffer events in RAM (list) and flush when Wi-Fi returns.
- API route (partner's side): POST /api/weigh-event — verify bearer token,
  validate schema, insert row, return 200 fast. Idempotency: include a
  monotonically increasing `seq` from the Pico so retries dedupe.
- Realtime UI: DB with realtime (Supabase) or SWR polling — partner's call.
- Do NOT try WebSockets/MQTT from Pico to Vercel (serverless kills them).
  If realtime-from-device is ever required, use a hosted broker
  (HiveMQ Cloud free tier) + webhook bridge — but plain HTTPS POST is the
  right MVP.
- Time: Pico has no RTC battery. Send `ts` as ticks_ms AND let the server
  stamp authoritative received-at time. Optionally NTP-sync on boot.

### Event schema (frozen — the contract)

    {"event":"weight","grams":342.5,"stable":true,"calibrated":true,
     "n":6,"seq":17,"device":"fridge-scale-01","ts":123456}

    ready:  {"event":"ready","calibrated":bool,"noise_g":float,
             "load_threshold_g":float,...}
    status: {"event":"status","g":float,"state":"armed|weighing|done",...}
    error:  {"event":"error","reason":"sensor_timeout",...}

  Additive changes only; never rename/remove fields. `grams` is the settled
  average, one event per item placement.

### Item identity (app side, for context)

Weight alone can't identify items. MVP: user taps the item in the app before
(or after) weighing; event pairs with selection. v2: barcode scan on intake
pulls empty/full/serving weights; depletion tracking = (gross − empty)/net.
Hardware does NOT solve identity — don't try to fingerprint by weight.

## 7. Style / process notes that worked with this user

- Incremental hardware bring-up: prove one thing per step (comms → stable →
  responds → tare → calibrate), with explicit pass criteria stated before
  each test.
- User interacts physically on request ("hang it now", "press now") — give
  countdowns or wait for their "ready"/"done" before reading.
- Short, concrete instructions; tables for wiring; diagrams help.
- Never assume an item is on/off the scale — ask, then verify in data.
- Announce before killing their processes; they've said yes each time.
