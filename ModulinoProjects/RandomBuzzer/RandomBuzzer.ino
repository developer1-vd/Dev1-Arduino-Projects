/*
  RandomBuzzer

  Uses only a Modulino Buzzer (connected via Qwiic). No buttons.
  The buzzer plays continuously and randomly jumps between three levels:

    level 1 -> low  (quietest, 400 Hz)
    level 2 -> mid  (1500 Hz)
    level 3 -> high (loudest, 4000 Hz)

  Each level is held for a random time before the next random jump.

  Note: the Modulino Buzzer has no volume control - only frequency and
  duration. Its piezo is loudest near its ~4 kHz resonance, so higher levels
  also sound louder.

  Requires the "Modulino" (Arduino_Modulino) library (Library Manager).
*/

#include <Modulino.h>

ModulinoBuzzer buzzer;

const int levelFrequency[3] = { 400, 1500, 4000 };
const char* levelName[3] = { "low", "mid", "high" };

// Random hold time for each level (ms)
const unsigned long minHoldMs = 200;
const unsigned long maxHoldMs = 1500;

void setup() {
  Serial.begin(9600);
  Modulino.begin();
  buzzer.begin();

  // Seed the random generator from an unconnected analog pin
  randomSeed(analogRead(A0));
}

void loop() {
  int level = random(3);                                  // 0, 1 or 2
  unsigned long holdMs = random(minHoldMs, maxHoldMs + 1);

  // Ask for a tone slightly longer than the hold time, so there is no gap
  // before the next tone replaces it.
  buzzer.tone(levelFrequency[level], holdMs + 100);

  Serial.print("Level ");
  Serial.print(level + 1);
  Serial.print(" (");
  Serial.print(levelName[level]);
  Serial.print(") for ");
  Serial.print(holdMs);
  Serial.println(" ms");

  delay(holdMs);
}
