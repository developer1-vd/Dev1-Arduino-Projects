/*
  VibroButtonLevels

  Uses a Modulino Buttons and a Modulino Vibro (connected via Qwiic).
  While held, each button makes the vibration motor run at a stronger level:

    Button A -> barely vibrating
    Button B -> medium
    Button C -> super vibrating

  Release the button to stop. The LED above the held button lights up.

  Works on any board with a Qwiic connector, including the UNO Q and
  VENTUNO Q in the Arduino IDE.

  Requires the "Arduino_Modulino" library (Library Manager).
*/

#include <Modulino.h>

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
  Serial.begin(9600);
#if defined(ARDUINO_UNO_Q) || defined(ARDUINO_VENTUNO_Q)
  // On the UNO Q and VENTUNO Q the Qwiic connector is on the second I2C bus
  Modulino.begin(Wire1);
#else
  Modulino.begin();
#endif

  if (!buttons.begin()) {
    Serial.println("Modulino Buttons NOT found - check the Qwiic cable.");
  }
  if (!vibro.begin()) {
    Serial.println("Modulino Vibro NOT found - check the Qwiic cable.");
  }

  buttons.setLeds(false, false, false);
}

void loop() {
  if (updateVibro()) {
    if (activeLevel == -1) {
      Serial.println("Released -> off");
    } else {
      Serial.print("Button ");
      Serial.print((char)('A' + activeLevel));
      Serial.print(" -> ");
      Serial.print(levelName[activeLevel]);
      Serial.print(" (power ");
      Serial.print(levelPower[activeLevel]);
      Serial.println(")");
    }
  }
  delay(10);
}
