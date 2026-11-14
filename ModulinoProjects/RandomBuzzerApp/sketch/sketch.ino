/*
  RandomBuzzer - Arduino App Lab version (UNO Q and VENTUNO Q)

  Uses only a Modulino Buzzer. It plays continuously and randomly jumps
  between three levels (low 2500 Hz, mid 3300 Hz, high 4000 Hz), holding each
  for a random time. Higher pitches are closer to the piezo's ~4 kHz
  resonance, so they also sound louder.

  Each change is sent to Python through the Bridge:
    Bridge.notify("level_changed", level, holdMs)   level = 1..3
  At startup it also reports whether the buzzer was found:
    Bridge.notify("buzzer_status", found)
  and plays a short test beep.
*/

#include <Arduino_Modulino.h>
#include <Arduino_RouterBridge.h>

ModulinoBuzzer buzzer;

// All levels are kept near the piezo's ~4 kHz resonance, where it is
// loudest. Lower pitches (e.g. 400 Hz) are much quieter on this buzzer.
const int levelFrequency[3] = { 2500, 3300, 4000 };

// Random hold time for each level (ms)
const unsigned long minHoldMs = 200;
const unsigned long maxHoldMs = 1500;

bool buzzerFound = false;

// Try to find the Modulino Buzzer on the Qwiic bus and report the result
// to Python, so a wiring/detection problem shows up in the App Lab console.
bool connectBuzzer() {
  buzzerFound = buzzer.begin();
  Bridge.notify("buzzer_status", buzzerFound);
  Monitor.println(buzzerFound ? "Modulino Buzzer found" : "Modulino Buzzer NOT found");
  return buzzerFound;
}

void setup() {
  Bridge.begin();
  Monitor.begin();

  // On the UNO Q and VENTUNO Q the Qwiic connector is on Wire1
  Modulino.begin(Wire1);

  // The Modulino can take a moment to start after power-up, so retry a few times
  for (int attempt = 0; attempt < 10 && !connectBuzzer(); attempt++) {
    delay(300);
  }

  // Short test beep so you know the buzzer works before the random part starts
  if (buzzerFound) {
    buzzer.tone(1000, 500);
    delay(700);
  }

  randomSeed(micros());
}

void loop() {
  if (!buzzerFound) {
    // Keep trying, so plugging the buzzer in later also works
    connectBuzzer();
    delay(2000);
    return;
  }

  int level = random(3);                                  // 0, 1 or 2
  unsigned long holdMs = random(minHoldMs, maxHoldMs + 1);

  // Slightly longer than the hold, so there is no gap before the next tone
  buzzer.tone(levelFrequency[level], holdMs + 100);

  Bridge.notify("level_changed", level + 1, (int)holdMs);

  delay(holdMs);
}
