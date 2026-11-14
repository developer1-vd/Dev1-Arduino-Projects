/*
  RandomBuzzer

  Uses only a Modulino Buzzer (connected via Qwiic). No buttons.
  The buzzer plays continuously and randomly jumps between three levels:

    level 1 -> low  (2500 Hz)
    level 2 -> mid  (3300 Hz)
    level 3 -> high (loudest, 4000 Hz = buzzer resonance)

  Each level is held for a random time before the next random jump.

  Note: the Modulino Buzzer has no volume control - only frequency and
  duration. Its piezo is loudest near its ~4 kHz resonance, so higher levels
  also sound louder.

  Works on any board with a Qwiic connector, including the UNO Q and
  VENTUNO Q in the Arduino IDE (select the board after installing the
  "Arduino UNO Q Zephyr Core" in the Boards Manager).

  Requires the "Modulino" (Arduino_Modulino) library (Library Manager).
*/

#include <Modulino.h>

ModulinoBuzzer buzzer;

// All levels are kept near the piezo's ~4 kHz resonance, where it is
// loudest. Lower pitches (e.g. 400 Hz) are much quieter on this buzzer.
const int levelFrequency[3] = { 2500, 3300, 4000 };
const char* levelName[3] = { "low", "mid", "high" };

// Random hold time for each level (ms)
const unsigned long minHoldMs = 200;
const unsigned long maxHoldMs = 1500;

void setup() {
  Serial.begin(9600);
#if defined(ARDUINO_UNO_Q) || defined(ARDUINO_VENTUNO_Q)
  // On the UNO Q and VENTUNO Q the Qwiic connector is on the second I2C bus
  Modulino.begin(Wire1);
#else
  Modulino.begin();
#endif
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
