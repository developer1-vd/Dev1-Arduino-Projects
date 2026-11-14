/*
  ButtonBuzzerLevels - Arduino App Lab version (UNO Q)

  While held, each Modulino Button plays the Modulino Buzzer at a higher
  "loudness" level (A = quietest, C = loudest). The buzzer has no volume
  control, so each level uses a pitch closer to the piezo's ~4 kHz resonance,
  which sounds louder.

  Every time the held button changes, the sketch tells the Python side
  through the Bridge: Bridge.notify("level_changed", level)
    level = 0 -> released / silent
    level = 1..3 -> button A..C held
*/

#include <Arduino_Modulino.h>
#include <Arduino_RouterBridge.h>

ModulinoButtons buttons;
ModulinoBuzzer buzzer;

// Frequencies (Hz) from quietest to loudest.
const int levelFrequency[3] = { 400, 1500, 4000 };

// The buzzer only plays for a set time, so while a button is held we keep
// re-sending the tone before it runs out. This gives a continuous sound.
const unsigned long toneLengthMs = 1000;
const unsigned long refreshEveryMs = 500;

int activeLevel = -1;            // -1 = silent, otherwise 0..2
unsigned long lastToneSentMs = 0;

void setup() {
  Bridge.begin();

  // On the UNO Q the Qwiic connector is on Wire1
  Modulino.begin(Wire1);
  buttons.begin();
  buzzer.begin();

  buttons.setLeds(false, false, false);
}

void loop() {
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
    // Button pressed, released or changed
    activeLevel = heldLevel;
    buttons.setLeds(activeLevel == 0, activeLevel == 1, activeLevel == 2);

    if (activeLevel == -1) {
      buzzer.noTone();
    } else {
      buzzer.tone(levelFrequency[activeLevel], toneLengthMs);
      lastToneSentMs = now;
    }

    Bridge.notify("level_changed", activeLevel + 1);
  } else if (activeLevel != -1 && now - lastToneSentMs >= refreshEveryMs) {
    // Still held: keep the tone going
    buzzer.tone(levelFrequency[activeLevel], toneLengthMs);
    lastToneSentMs = now;
  }

  delay(10);
}
