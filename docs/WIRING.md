# Wiring — Pico 2 W + HX711 + 1 kg load cell

Board: Raspberry Pi Pico 2 W (RP2350), MicroPython v1.28.0.
Load cell: 1 kg, 4-wire standard.
HX711: green breakout, 2-wire interface (DT + SCK).

## Load cell (4-wire) → HX711

| Load cell wire | HX711 pad |
|----------------|-----------|
| red            | E+        |
| black          | E-        |
| green          | A+        |
| white          | A-        |

If readings go the "wrong way" (weight lowers the number), swap green/white
(A+/A-) — it just inverts the sign.

## HX711 → Pico 2 W

| HX711 pin | Pico signal   | Physical pin | Notes |
|-----------|---------------|--------------|-------|
| VCC       | 3V3(OUT)      | 36           | Power from 3V3, NOT VBUS/5V. 5V here would drive the DT line to 5V into a 3.3V-only GPIO. |
| GND       | GND           | 38           | Any GND pin works (e.g. pin 23 is next to GP16/GP17). |
| DT/DOUT   | GP16          | 21           | Data out from HX711. |
| SCK       | GP17          | 22           | Clock into HX711. |

## Driver / code convention

- Driver: robert-hh PIO HX711 at `lib/hx711_pio.py` (already on board).
- Constructor argument order is (SCK, DATA): `HX711(Pin(17), Pin(16), state_machine=0)`.
- DT = GP16, SCK = GP17.
