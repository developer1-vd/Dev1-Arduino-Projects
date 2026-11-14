/*
  ButtonBuzzerLevels

  Uses a Modulino Buttons and a Modulino Buzzer (connected via Qwiic).
  Each of the 3 buttons plays the buzzer at a higher "loudness" level:

    Button A -> level 1 (quietest)
    Button B -> level 2
    Button C -> level 3 (loudest)

  Note: the Modulino Buzzer has no volume control - it only accepts a
  frequency and a duration. Its piezo element is loudest near its resonant
  frequency (~4 kHz), so each level uses a frequency closer to resonance,
  which sounds noticeably louder. The LED above the pressed button lights up.

  Requires the "Modulino" library (Library Manager).
*/

#include <Modulino.h>

ModulinoButtons buttons;
ModulinoBuzzer buzzer;

// Frequencies (Hz) from quietest to loudest.
const int levelFrequency[3] = { 400, 1500, 4000 };
const int beepDurationMs = 300;

void setup() {
  Serial.begin(9600);
  Modulino.begin();
  buttons.begin();
  buzzer.begin();

  buttons.setLeds(false, false, false);
}

void loop() {
  // update() returns true only when a button state changed
  if (!buttons.update()) {
    return;
  }

  for (int i = 0; i < 3; i++) {
    if (buttons.isPressed(i)) {
      buttons.setLeds(i == 0, i == 1, i == 2);
      buzzer.tone(levelFrequency[i], beepDurationMs);

      Serial.print("Button ");
      Serial.print((char)('A' + i));
      Serial.print(" -> level ");
      Serial.println(i + 1);
      return;  // handle one button at a time
    }
  }

  // No button held: turn the LEDs off
  buttons.setLeds(false, false, false);
}
