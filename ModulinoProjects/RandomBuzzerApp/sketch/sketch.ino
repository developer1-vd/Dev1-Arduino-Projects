/*
  RandomBuzzer - Arduino App Lab version (UNO Q and VENTUNO Q)

  Uses only a Modulino Buzzer. It plays continuously and randomly jumps
  between three levels (low 400 Hz, mid 1500 Hz, high 4000 Hz), holding each
  for a random time. Higher pitches are closer to the piezo's ~4 kHz
  resonance, so they also sound louder.

  Each change is sent to Python through the Bridge:
    Bridge.notify("level_changed", level, holdMs)   level = 1..3
*/

#include <Arduino_Modulino.h>
#include <Arduino_RouterBridge.h>

ModulinoBuzzer buzzer;

const int levelFrequency[3] = { 400, 1500, 4000 };

// Random hold time for each level (ms)
const unsigned long minHoldMs = 200;
const unsigned long maxHoldMs = 1500;

void setup() {
  Bridge.begin();

  // On the UNO Q and VENTUNO Q the Qwiic connector is on Wire1
  Modulino.begin(Wire1);
  buzzer.begin();

  randomSeed(analogRead(A0));
}

void loop() {
  int level = random(3);                                  // 0, 1 or 2
  unsigned long holdMs = random(minHoldMs, maxHoldMs + 1);

  // Slightly longer than the hold, so there is no gap before the next tone
  buzzer.tone(levelFrequency[level], holdMs + 100);

  Bridge.notify("level_changed", level + 1, (int)holdMs);

  delay(holdMs);
}
