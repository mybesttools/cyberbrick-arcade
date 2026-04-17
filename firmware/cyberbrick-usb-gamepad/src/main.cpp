#include <Arduino.h>
#include "pinmap.h"

#if defined(CYBERBRICK_STATUS_OLED)
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#endif

static constexpr uint32_t USB_SERIAL_FRAME_INTERVAL_MS = 10;

int16_t mapAxis(int raw, int minV, int centerV, int maxV, int deadzone);
uint32_t readButtons();

#if defined(CYBERBRICK_STATUS_OLED)
static Adafruit_SSD1306 statusDisplay(STATUS_OLED_WIDTH, STATUS_OLED_HEIGHT, &Wire, -1);
static bool statusDisplayReady = false;
static uint32_t statusLastMs = 0;
static bool statusWasConnected = false;

static void statusDrawLines(const char *l1, const char *l2, const char *l3)
{
  if (!statusDisplayReady)
  {
    return;
  }

  statusDisplay.clearDisplay();
  statusDisplay.setTextColor(SSD1306_WHITE);
  statusDisplay.setTextSize(1);
  statusDisplay.setCursor(0, 0);
  statusDisplay.println(l1);
  statusDisplay.println(l2);
  statusDisplay.println(l3);
  statusDisplay.display();
}

static void statusInit()
{
  if (!STATUS_DISPLAY_ENABLED)
  {
    return;
  }

  Wire.begin();
  if (statusDisplay.begin(SSD1306_SWITCHCAPVCC, STATUS_OLED_I2C_ADDR))
  {
    statusDisplayReady = true;
    statusDrawLines("CyberBrick", "Booting...", "BLE init");
  }
}

static void statusUpdate(bool connected, int16_t x, int16_t y, uint32_t buttons)
{
  if (!statusDisplayReady)
  {
    return;
  }

  uint32_t now = millis();
  if ((now - statusLastMs) < 100 && connected == statusWasConnected)
  {
    return;
  }
  statusLastMs = now;
  statusWasConnected = connected;

  if (!connected)
  {
    statusDrawLines("CyberBrick", "BLE: advertising", "waiting host");
    return;
  }

  char line2[32];
  char line3[32];
  snprintf(line2, sizeof(line2), "X:%6d Y:%6d", x, y);
  snprintf(line3, sizeof(line3), "BTN:0x%03lX", (unsigned long)(buttons & 0x3FF));
  statusDrawLines("BLE: connected", line2, line3);
}
#endif

#if defined(CYBERBRICK_DIAGNOSTIC_INPUTS)
static void readControllerState(int16_t &x, int16_t &y, uint32_t &buttons)
{
  uint32_t phase = (millis() / 20) % 400;
  int32_t wave = (phase < 200) ? phase : (399 - phase);
  x = (int16_t)((wave * 32767 / 199) - 16384);
  y = (int16_t)(-x);
  buttons = ((millis() / 1000) % 2 == 0) ? 0x1 : 0x0;
}
#else
static void readControllerState(int16_t &x, int16_t &y, uint32_t &buttons)
{
  int rawX = analogRead(JOY_X_PIN);
  int rawY = analogRead(JOY_Y_PIN);
  x = mapAxis(rawX, JOY_MIN, JOY_CENTER_X, JOY_MAX, JOY_DEADZONE);
  y = mapAxis(rawY, JOY_MIN, JOY_CENTER_Y, JOY_MAX, JOY_DEADZONE);
  buttons = readButtons();
}
#endif

#if defined(CONTROLLER_MODE_BLE)
#include <BleGamepad.h>
BleGamepadConfiguration bleGamepadConfig;
BleGamepad bleGamepad("CyberBrick Arcade", "CyberBrick", 100);

// Convert signed joystick axes to an 8-way hat direction.
static uint8_t axesToHat(int16_t x, int16_t y)
{
  bool up    = (y >  HAT_THRESHOLD);
  bool down  = (y < -HAT_THRESHOLD);
  bool right = (x >  HAT_THRESHOLD);
  bool left  = (x < -HAT_THRESHOLD);

  if (up   && right) return HAT_UP_RIGHT;
  if (up   && left)  return HAT_UP_LEFT;
  if (down && right) return HAT_DOWN_RIGHT;
  if (down && left)  return HAT_DOWN_LEFT;
  if (up)            return HAT_UP;
  if (down)          return HAT_DOWN;
  if (right)         return HAT_RIGHT;
  if (left)          return HAT_LEFT;
  return HAT_CENTERED;
}
#elif defined(CONTROLLER_MODE_USB_HID)
#include <Adafruit_TinyUSB.h>

// HID report descriptor for a simple gamepad with 2 axes and 16 buttons
#define TUD_HID_REPORT_DESC_SIMPLE_GAMEPAD(...) \
  HID_USAGE_PAGE ( HID_USAGE_PAGE_DESKTOP      )                 , \
  HID_USAGE      ( HID_USAGE_DESKTOP_GAMEPAD   )                 , \
  HID_COLLECTION ( HID_COLLECTION_APPLICATION  )                 , \
    __VA_ARGS__ \
    /* 2 axes (x, y) */ \
    HID_USAGE_PAGE ( HID_USAGE_PAGE_DESKTOP      )                 , \
    HID_USAGE      ( HID_USAGE_DESKTOP_X         )                 , \
    HID_USAGE      ( HID_USAGE_DESKTOP_Y         )                 , \
    HID_LOGICAL_MIN  ( -127                                      ) , \
    HID_LOGICAL_MAX  ( 127                                       ) , \
    HID_REPORT_SIZE  ( 8                                         ) , \
    HID_REPORT_COUNT ( 2                                         ) , \
    HID_INPUT        ( HID_DATA | HID_VARIABLE | HID_ABSOLUTE    ) , \
    /* 16 buttons */ \
    HID_USAGE_PAGE ( HID_USAGE_PAGE_BUTTON       )                 , \
    HID_USAGE_MIN    ( 1                                         ) , \
    HID_USAGE_MAX    ( 16                                        ) , \
    HID_LOGICAL_MIN  ( 0                                         ) , \
    HID_LOGICAL_MAX  ( 1                                         ) , \
    HID_REPORT_SIZE  ( 1                                         ) , \
    HID_REPORT_COUNT ( 16                                        ) , \
    HID_INPUT        ( HID_DATA | HID_VARIABLE | HID_ABSOLUTE    ) , \
  HID_COLLECTION_END

uint8_t const desc_hid_report[] = { TUD_HID_REPORT_DESC_SIMPLE_GAMEPAD(HID_REPORT_ID(1)) };
Adafruit_USBD_HID usb_hid;
#endif

// Convert analog joystick reading to signed 16-bit range with center deadzone.
int16_t mapAxis(int raw, int minV, int centerV, int maxV, int deadzone)
{
  if (raw < centerV - deadzone)
  {
    long v = map(raw, minV, centerV - deadzone, -32767, 0);
    return (int16_t)constrain(v, -32767, 0);
  }

  if (raw > centerV + deadzone)
  {
    long v = map(raw, centerV + deadzone, maxV, 0, 32767);
    return (int16_t)constrain(v, 0, 32767);
  }

  return 0;
}

uint32_t readButtons()
{
  uint32_t bits = 0;

  for (size_t i = 0; i < BUTTON_COUNT; i++)
  {
    bool pressed = (digitalRead(BUTTON_PINS[i]) == LOW);
    if (pressed)
    {
      bits |= (1UL << i);
    }
  }

  return bits;
}

void setup()
{
#if !defined(CYBERBRICK_DIAGNOSTIC_INPUTS)
  analogReadResolution(12);

  for (size_t i = 0; i < BUTTON_COUNT; i++)
  {
    pinMode(BUTTON_PINS[i], INPUT_PULLUP);
  }

  pinMode(JOY_X_PIN, INPUT);
  pinMode(JOY_Y_PIN, INPUT);
#endif

#if defined(CONTROLLER_MODE_BLE)
  bleGamepadConfig.setButtonCount(BUTTON_COUNT);
  bleGamepadConfig.setHatSwitchCount(1);
  bleGamepadConfig.setWhichAxes(false, false, false, false, false, false, false, false);
  bleGamepad.begin(&bleGamepadConfig);
  statusInit();
#elif defined(CONTROLLER_MODE_USB_HID)
  usb_hid.setPollInterval(2);
  usb_hid.setReportDescriptor(desc_hid_report, sizeof(desc_hid_report));
  usb_hid.begin();
  // For debug printing
  Serial.begin(SERIAL_BAUD_RATE);
#else
  Serial.begin(SERIAL_BAUD_RATE);
  delay(100);
  Serial.println("CYBERBRICK_SERIAL_GAMEPAD_V1");
#endif
}

void loop()
{
#if defined(CONTROLLER_MODE_BLE)
  if (!bleGamepad.isConnected())
  {
    statusUpdate(false, 0, 0, 0);
    delay(10);
    return;
  }

  int16_t x = 0;
  int16_t y = 0;
  uint32_t buttons = 0;
  readControllerState(x, y, buttons);
  for (size_t i = 0; i < BUTTON_COUNT; i++)
  {
    uint8_t buttonIndex = (uint8_t)(i + 1);
    bool pressed = ((buttons & (1UL << i)) != 0);

    if (pressed)
    {
      bleGamepad.press(buttonIndex);
    }
    else
    {
      bleGamepad.release(buttonIndex);
    }
  }

  bleGamepad.setHat1(axesToHat(x, JOY_INVERT_Y ? -y : y));
  statusUpdate(true, x, y, buttons);
#elif defined(CONTROLLER_MODE_USB_HID)
  // Wait for host to be ready
  if ( !usb_hid.ready() ) {
    delay(10);
    return;
  }

  int16_t x = 0;
  int16_t y = 0;
  uint32_t buttons = 0;
  readControllerState(x, y, buttons);

  struct {
    int8_t x;
    int8_t y;
    uint16_t buttons;
  } report = { 0 };

  report.x = map(x, -32767, 32767, -127, 127);
  report.y = map(y, -32767, 32767, -127, 127);
  report.buttons = buttons;

  usb_hid.sendReport(1, &report, sizeof(report));
#else
  static uint32_t lastSerialFrameMs = 0;
  uint32_t now = millis();
  if ((now - lastSerialFrameMs) < USB_SERIAL_FRAME_INTERVAL_MS)
  {
    delay(1);
    return;
  }
  lastSerialFrameMs = now;

  int16_t x = 0;
  int16_t y = 0;
  uint32_t buttons = 0;
  readControllerState(x, y, buttons);

  // CSV frame for Pi bridge: R,<x>,<y>,<buttons_hex>
  Serial.print("R,");
  Serial.print(x);
  Serial.print(',');
  Serial.print(y);
  Serial.print(',');
  Serial.println(buttons, HEX);
#endif

  delay(1);
}
