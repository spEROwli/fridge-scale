#!/usr/bin/env bash
# Idempotent dev-environment bootstrap for the Fridge Scale repo.
#
# What this repo actually runs:
#   - app/index.html  : static Web Bluetooth page, served over http.server.
#   - firmware/*.py    : MicroPython for a Pico 2 W. Not importable under
#                        CPython (uses `machine`, `aioble`, ...), but mpremote
#                        is the tool used to push/run it on attached hardware.
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

# --- Sanity: firmware files are syntactically valid Python (byte-compile
# --- only; hardware-only modules are not imported here). ---
echo "==> Byte-compiling firmware/*.py"
python -m py_compile firmware/*.py

echo "==> Setup complete."
echo "    Web app : http://localhost:8000/app/  (served by the 'web-app' terminal)"
echo "    Firmware: 'source .venv/bin/activate' then 'mpremote connect list'"
