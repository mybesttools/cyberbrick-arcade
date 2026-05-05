#!/usr/bin/env python3
"""
ESP32-C3 USB Serial -> Linux uinput gamepad bridge for RetroPie.

Reads lines from firmware in format:
  R,<x>,<y>,<buttons_hex>

Where:
  x,y = signed int16 in range -32767..32767
  buttons_hex = hex bitmask (bit 0 = A, bit 1 = B, ...)

Usage:
  sudo python3 tools/pi_usb_serial_to_uinput.py --port /dev/ttyACM0
  sudo python3 tools/pi_usb_serial_to_uinput.py --port auto
"""

import argparse
import glob
import serial
from evdev import UInput, AbsInfo, ecodes as e

# Bitmask layout from firmware MCP_BUTTON_BITS[]:
#  0:A  1:B  2:X  3:Y  4:L  5:R  6:Start  7:Select  8:Hotkey  9:Coin
#  10:L3  11:R3  12:DUp  13:DDown  14:DLeft  15:DRight
BUTTON_MAP = [
    e.BTN_A,       # 0  - A / Cross
    e.BTN_B,       # 1  - B / Circle
    e.BTN_X,       # 2  - X / Square
    e.BTN_Y,       # 3  - Y / Triangle
    e.BTN_TL,      # 4  - L shoulder
    e.BTN_TR,      # 5  - R shoulder
    e.BTN_START,   # 6  - Start
    e.BTN_SELECT,  # 7  - Select
    e.BTN_MODE,    # 8  - Hotkey
    e.BTN_C,       # 9  - Coin
    e.BTN_THUMBL,  # 10 - L3
    e.BTN_THUMBR,  # 11 - R3
    # bits 12-15 are D-pad directions → ABS_HAT0X/Y, not buttons
]

# Bitmask positions for D-pad directions (must match MCP_BUTTON_BITS order)
DPAD_UP_BIT    = 12
DPAD_DOWN_BIT  = 13
DPAD_LEFT_BIT  = 14
DPAD_RIGHT_BIT = 15


def auto_port():
    for pattern in ("/dev/ttyACM*", "/dev/ttyUSB*", "/dev/tty.usbmodem*"):
        ports = sorted(glob.glob(pattern))
        if ports:
            return ports[0]
    raise RuntimeError("No serial device found. Use --port explicitly.")


def make_device():
    return UInput(
        {
            e.EV_ABS: [
                (e.ABS_X,     AbsInfo(0, -32767, 32767, 0, 0, 0)),
                (e.ABS_Y,     AbsInfo(0, -32767, 32767, 0, 0, 0)),
                (e.ABS_RX,    AbsInfo(0, -32767, 32767, 0, 0, 0)),
                (e.ABS_RY,    AbsInfo(0, -32767, 32767, 0, 0, 0)),
                (e.ABS_HAT0X, AbsInfo(0, -1, 1, 0, 0, 0)),
                (e.ABS_HAT0Y, AbsInfo(0, -1, 1, 0, 0, 0)),
            ],
            e.EV_KEY: BUTTON_MAP,
        },
        name="BLE Everywhere USB Bridge",
        version=0x1,
    )


def parse_line(line):
    if not line.startswith("R,"):
        return None

    parts = line.strip().split(",")
    if len(parts) < 4:
        return None

    try:
        x = int(parts[1])
        y = int(parts[2])
        buttons = int(parts[3], 16)
        rx = int(parts[4]) if len(parts) > 4 else 0
        ry = int(parts[5]) if len(parts) > 5 else 0
    except ValueError:
        return None

    x  = max(-32767, min(32767, x))
    y  = max(-32767, min(32767, y))
    rx = max(-32767, min(32767, rx))
    ry = max(-32767, min(32767, ry))
    return x, y, buttons, rx, ry


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="auto")
    parser.add_argument("--baud", type=int, default=115200)
    args = parser.parse_args()

    port = auto_port() if args.port == "auto" else args.port
    print(f"Using serial port: {port}")

    ui = make_device()
    print("uinput gamepad created: BLE Everywhere USB Bridge")

    last_buttons = 0

    with serial.Serial(port, args.baud, timeout=0.2) as ser:
        while True:
            raw = ser.readline()
            if not raw:
                continue

            line = raw.decode("utf-8", errors="ignore")
            parsed = parse_line(line)
            if parsed is None:
                continue

            x, y, buttons, rx, ry = parsed

            ui.write(e.EV_ABS, e.ABS_X,  x)
            ui.write(e.EV_ABS, e.ABS_Y,  y)
            ui.write(e.EV_ABS, e.ABS_RX, rx)
            ui.write(e.EV_ABS, e.ABS_RY, ry)

            # D-pad → hat switch
            hat_x = (1 if buttons & (1 << DPAD_RIGHT_BIT) else 0) \
                  - (1 if buttons & (1 << DPAD_LEFT_BIT)  else 0)
            hat_y = (1 if buttons & (1 << DPAD_DOWN_BIT)  else 0) \
                  - (1 if buttons & (1 << DPAD_UP_BIT)    else 0)
            ui.write(e.EV_ABS, e.ABS_HAT0X, hat_x)
            ui.write(e.EV_ABS, e.ABS_HAT0Y, hat_y)

            # Face / shoulder / thumb buttons (bits 0-11)
            changed = buttons ^ last_buttons
            for bit, key in enumerate(BUTTON_MAP):
                if changed & (1 << bit):
                    pressed = 1 if (buttons & (1 << bit)) else 0
                    ui.write(e.EV_KEY, key, pressed)

            ui.syn()
            last_buttons = buttons


if __name__ == "__main__":
    main()
