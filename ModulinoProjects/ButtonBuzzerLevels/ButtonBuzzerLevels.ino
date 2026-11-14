/*
  ButtonBuzzerLevels

  Uses a Modulino Buttons and a Modulino Buzzer (connected via Qwiic).
  While held, each of the 3 buttons plays the buzzer at a higher "loudness" level:

    Button A -> level 1 (quietest)
    Button B -> level 2
    Button C -> level 3 (loudest)

  Note: the Modulino Buzzer has no volume control - it only accepts a
  frequency and a duration. Its piezo element is loudest near its resonant
  frequency (~4 kHz), so each level uses a frequency closer to resonance,
  which sounds noticeably louder. The sound stops when the button is released,
  and the LED above the held button lights up.

  Requires the "Modulino" library (Library Manager).
*/

#include <Modulino.h>

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
  Serial.begin(9600);
  Modulino.begin();
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
      Serial.println("Released -> silent");
    } else {
      buzzer.tone(levelFrequency[activeLevel], toneLengthMs);
      lastToneSentMs = now;
      Serial.print("Button ");
      Serial.print((char)('A' + activeLevel));
      Serial.print(" -> level ");
      Serial.println(activeLevel + 1);
    }
  } else if (activeLevel != -1 && now - lastToneSentMs >= refreshEveryMs) {
    // Still held: keep the tone going
    buzzer.tone(levelFrequency[activeLevel], toneLengthMs);
    lastToneSentMs = now;
  }

  delay(10);
}
