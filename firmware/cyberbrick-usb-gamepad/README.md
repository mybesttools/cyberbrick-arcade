# CyberBrick Controller Firmware

This project targets **ESP32-C3 BLE gamepad mode** by default.

The board advertises as `CyberBrick Arcade` and pairs directly with RetroPie over Bluetooth.

It also includes an optional tiny OLED status display (SSD1306 I2C) showing:

- boot status
- advertising / connected state
- live axis and button activity

## BLE and USB support

Yes, both are supported from the same codebase:

- BLE gamepad mode on ESP32-C3 (`cyberbrick_esp32c3_ble`)
- USB serial bridge mode on ESP32-C3 (`cyberbrick_esp32c3_usbserial`)

Note: ESP32-C3 does not expose native USB HID gamepad device mode in this project.
USB mode here is CDC serial output for a Pi-side bridge.

## Project layout

- `src/main.cpp`: controller firmware (BLE + USB HID + serial bridge modes)
- `include/pinmap.h`: joystick/button mapping and calibration
- `platformio.ini`: PlatformIO build config
- `tools/flash_our_firmware.sh`: upload helper for default ESP32-C3 BLE env

## Wiring

Joystick:

- `JOY_X_PIN` = `A0`
- `JOY_Y_PIN` = `A1`

Buttons (active LOW, wire each button between GPIO pin and GND):

- A = `2`
- B = `3`
- X = `4`
- Y = `5`
- L = `6`
- R = `7`
- START = `9`
- SELECT = `10`
- HOTKEY = `20`
- COIN = `21`

## Optional tiny OLED display

The BLE environment enables SSD1306 status output (`CYBERBRICK_STATUS_OLED`).

Default config is in `include/pinmap.h`:

- `STATUS_DISPLAY_ENABLED = false`
- `STATUS_OLED_I2C_ADDR = 0x3C`
- `STATUS_OLED_WIDTH = 128`
- `STATUS_OLED_HEIGHT = 64`

Note: on tiny ESP32-C3 display boards, GPIO8/GPIO9 are commonly tied to I2C.
The default button map avoids GPIO8 and keeps the OLED disabled unless you
intentionally enable it.

If your display has different dimensions or address, change those constants.

## Setup — step by step

### 1. Build and upload to ESP32-C3

```bash
cd firmware/cyberbrick-usb-gamepad
pio run -e cyberbrick_esp32c3_ble
pio run -e cyberbrick_esp32c3_ble -t upload

# USB serial bridge firmware
pio run -e cyberbrick_esp32c3_usbserial
pio run -e cyberbrick_esp32c3_usbserial -t upload
```

If needed, upload with explicit port:

```bash
pio run -e cyberbrick_esp32c3_ble -t upload --upload-port /dev/tty.usbmodemXXXX
```

Or use the helper script:

```bash
./tools/flash_our_firmware.sh
```

### 2. Pair with RetroPie

In RetroPie Bluetooth settings:

1. Register and connect new Bluetooth device
2. Select `CyberBrick Arcade`

### 3. Configure in EmulationStation

In RetroPie/EmulationStation:

1. Hold any button to start controller setup.
2. Map joystick directions and action buttons.
3. Map Start / Select / Hotkey.
4. Skip unused controls by holding a button.

## Verify on Pi (optional)

Install joystick tools to inspect Linux input events:

```bash
sudo apt install joystick
```

Test:

```bash
jstest /dev/input/js0
```

## Tuning

Edit `include/pinmap.h` and adjust:

- `JOY_CENTER_X`, `JOY_CENTER_Y`
- `JOY_DEADZONE`
- `JOY_MIN`, `JOY_MAX`
- `BUTTON_PINS[]` order if you want a different button layout

## Alternate environments

- `cyberbrick_esp32c3_ble` (default)
- `cyberbrick_esp32c3_usbserial` (USB CDC serial bridge mode on ESP32-C3)
- `cyberbrick_rp2040_usbhid` (wired USB HID on Pico)
- `cyberbrick_d1_dongle` (ESP8266 ESP-NOW dongle utility)
