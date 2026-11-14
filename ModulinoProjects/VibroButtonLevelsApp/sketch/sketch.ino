/*
  VibroButtonLevels - Arduino App Lab version (UNO Q and VENTUNO Q)

  While held, each Modulino Button runs the Modulino Vibro at a stronger
  level: A = barely vibrating, B = medium, C = super vibrating. Release to
  stop. The LED above the held button lights up.

  Sent to Python through the Bridge:
    Bridge.notify("level_changed", level)   0 = off, 1..3 = button A..C
  At startup:
    Bridge.notify("module_status", buttonsFound, vibroFound)
*/

#include <Arduino_Modulino.h>
#include <Arduino_RouterBridge.h>

ModulinoButtons buttons;
ModulinoVibro vibro;

// Vibration strength for buttons A, B, C: barely -> super.
// The library's range is GENTLE (25) to MAXIMUM (50); below GENTLE the
// motor may not spin at all.
const int levelPower[3] = { GENTLE, MEDIUM, MAXIMUM };
const char* levelName[3] = { "barely", "medium", "super" };

// The motor only runs for a set time, so while a button is held we keep
// re-sending the command before it runs out. This gives a continuous buzz.
const unsigned long vibrateLengthMs = 1000;
const unsigned long refreshEveryMs = 500;

int activeLevel = -1;            // -1 = off, otherwise 0..2
unsigned long lastSentMs = 0;

// Checks the buttons and drives the motor. Returns true if the held button
// changed (pressed, released or switched).
bool updateVibro() {
  buttons.update();

  // Find the held button (lowest index wins if several are held)
  int heldLevel = -1;
  for (int i = 0; i < 3; i++) {
    if (buttons.isPressed(i)) {
      heldLevel = i;
      break;
    }
  }

  unsigned long now = millis();

  if (heldLevel != activeLevel) {
    activeLevel = heldLevel;
    buttons.setLeds(activeLevel == 0, activeLevel == 1, activeLevel == 2);

    if (activeLevel == -1) {
      vibro.off();
    } else {
      vibro.on(vibrateLengthMs, false, levelPower[activeLevel]);
      lastSentMs = now;
    }
    return true;
  }

  if (activeLevel != -1 && now - lastSentMs >= refreshEveryMs) {
    // Still held: keep it vibrating
    vibro.on(vibrateLengthMs, false, levelPower[activeLevel]);
    lastSentMs = now;
  }
  return false;
}

void setup() {
  Bridge.begin();

  // On the UNO Q and VENTUNO Q the Qwiic connector is on Wire1
  Modulino.begin(Wire1);

  bool buttonsFound = buttons.begin();
  bool vibroFound = vibro.begin();
  Bridge.notify("module_status", buttonsFound, vibroFound);

  buttons.setLeds(false, false, false);
}

void loop() {
  if (updateVibro()) {
    Bridge.notify("level_changed", activeLevel + 1);
  }
  delay(10);
}
