#!/usr/bin/env bash
# Idempotent dev-environment bootstrap for the Fridge Scale repo.
#
# What this repo actually runs:
#   - firmware/weigh_ble.py : documented working entrypoint (Pico 2 W, BLE grams)
#   - app/index.html        : Web Bluetooth client
#   - tools/scale_sim.py    : demo data only (secondary)
set -euo pipefail

cd "$(dirname "$0")/.."

# --- System package needed to create Python virtualenvs on Ubuntu 24.04 ---
if ! python3 -c "import ensurepip" >/dev/null 2>&1; then
  echo "==> Installing python3-venv (needed for virtualenv creation)"
  sudo apt-get update -qq
  sudo apt-get install -y -qq python3-venv
fi

# --- Repo-local venv holding the firmware tooling (mpremote) ---
if [ ! -x .venv/bin/python ]; then
  echo "==> Creating .venv"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
. .venv/bin/activate

echo "==> Installing firmware tooling (mpremote)"
python -m pip install --upgrade pip >/dev/null
python -m pip install mpremote

# --- Sanity: firmware + tools are syntactically valid Python (byte-compile
# --- only; hardware-only modules are not imported here). ---
echo "==> Byte-compiling firmware (documented path) and tools (demo, secondary)"
python -m py_compile firmware/*.py tools/*.py

echo "==> Setup complete."
echo "    Path     : source .venv/bin/activate && mpremote run firmware/weigh_ble.py"
echo "    Web app  : http://localhost:8000/app/"
echo "    Demo data: tools/scale_sim.py and /app/?demo (synthetic, not sensor)"
