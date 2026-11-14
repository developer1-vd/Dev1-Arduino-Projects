/*
  FarthestDistance

  Uses a Modulino Distance (time-of-flight sensor) to tell you how far away
  the farthest object is, and a Modulino Buzzer as a proximity alarm: it
  beeps when something comes closer than 40 cm, faster as it gets closer,
  and continuously below 10 cm (like a parking sensor). The buzzer is
  optional. The sensor measures a single distance in its
  narrow field of view, so to find the farthest object, slowly sweep the
  sensor across the scene: the sketch keeps the farthest reading from the
  last few seconds.

  Serial Monitor (9600 baud) shows, 4 times a second:
    now: 412 mm   farthest: 1187 mm

  Objects beyond the sensor's range (roughly 1.2 m or more, depending on the
  target and light) give no reading and show as "out of range".

  Works on any board with a Qwiic connector, including the UNO Q and
  VENTUNO Q in the Arduino IDE.

  Requires the "Arduino_Modulino" library (Library Manager).
*/

#include <Modulino.h>

ModulinoDistance distance;
ModulinoBuzzer buzzer;

// Farthest distance seen in the last few seconds. Sweep the sensor across
// the scene and this reports the farthest thing it pointed at.
const unsigned long windowMs = 5000;      // how long a "farthest" reading is kept
const unsigned long reportEveryMs = 250;  // how often to print
const unsigned long noTargetAfterMs = 500;

float currentMm = NAN;            // latest valid reading
float windowMaxMm = 0;            // farthest in the current window
float previousWindowMaxMm = 0;    // farthest in the previous window
unsigned long windowStartMs = 0;
unsigned long lastValidMs = 0;
unsigned long lastReportMs = 0;

// Read the sensor and update the farthest values
void updateDistance() {
  unsigned long now = millis();

  if (distance.available()) {
    currentMm = distance.get();
    lastValidMs = now;
    if (currentMm > windowMaxMm) {
      windowMaxMm = currentMm;
    }
  } else if (now - lastValidMs > noTargetAfterMs) {
    currentMm = NAN;  // nothing in range for a while
  }

  // Start a new window, keeping the previous one so the value doesn't drop
  // suddenly to zero right at the switch
  if (now - windowStartMs >= windowMs) {
    previousWindowMaxMm = windowMaxMm;
    windowMaxMm = 0;
    windowStartMs = now;
  }
}

float farthestMm() {
  return max(windowMaxMm, previousWindowMaxMm);
}

// ---- Proximity alarm (Modulino Buzzer) ----
// Like a parking sensor: starts beeping when something is closer than
// alertMm, beeps faster as it gets closer, and sounds continuously below
// solidMm. 4000 Hz is the buzzer's loudest pitch.
const float alertMm = 400;        // start beeping (40 cm)
const float solidMm = 100;        // continuous tone (10 cm)
const int alarmFrequency = 4000;
const unsigned long beepLengthMs = 60;
const unsigned long fastestBeepEveryMs = 120;  // just outside solidMm
const unsigned long slowestBeepEveryMs = 800;  // just inside alertMm

bool buzzerFound = false;
bool alarmOn = false;
unsigned long lastBeepMs = 0;

// Returns true while something is close enough to sound the alarm
bool updateAlarm() {
  unsigned long now = millis();
  bool close = !isnan(currentMm) && currentMm < alertMm;

  if (!buzzerFound) {
    return close;
  }

  if (!close) {
    if (alarmOn) {
      buzzer.noTone();
    }
    return false;
  }

  if (currentMm <= solidMm) {
    // Very close: keep a continuous tone going
    if (now - lastBeepMs >= 150) {
      buzzer.tone(alarmFrequency, 250);
      lastBeepMs = now;
    }
  } else {
    // Closer = shorter gap between beeps
    unsigned long beepEveryMs = map((long)currentMm, (long)solidMm, (long)alertMm,
                                    (long)fastestBeepEveryMs, (long)slowestBeepEveryMs);
    if (now - lastBeepMs >= beepEveryMs) {
      buzzer.tone(alarmFrequency, beepLengthMs);
      lastBeepMs = now;
    }
  }
  return true;
}

void setup() {
  Serial.begin(9600);
#if defined(ARDUINO_UNO_Q) || defined(ARDUINO_VENTUNO_Q)
  // On the UNO Q and VENTUNO Q the Qwiic connector is on the second I2C bus
  Modulino.begin(Wire1);
#else
  Modulino.begin();
#endif

  while (!distance.begin()) {
    Serial.println("Modulino Distance NOT found - check the Qwiic cable. Retrying...");
    delay(1000);
  }
  Serial.println("Modulino Distance found. Sweep it slowly across the scene.");

  // The buzzer is optional: without it you still get the distances
  buzzerFound = buzzer.begin();
  Serial.println(buzzerFound ? "Modulino Buzzer found: proximity alarm on."
                             : "Modulino Buzzer NOT found: no proximity alarm.");
}

void loop() {
  updateDistance();

  bool close = updateAlarm();
  if (close != alarmOn) {
    alarmOn = close;
    if (alarmOn) {
      Serial.print("!!! Something is close: ");
      Serial.print((int)currentMm);
      Serial.println(" mm");
    } else {
      Serial.println("All clear.");
    }
  }

  unsigned long now = millis();
  if (now - lastReportMs >= reportEveryMs) {
    lastReportMs = now;

    Serial.print("now: ");
    if (isnan(currentMm)) {
      Serial.print("out of range");
    } else {
      Serial.print((int)currentMm);
      Serial.print(" mm");
    }

    Serial.print("   farthest: ");
    if (farthestMm() > 0) {
      Serial.print((int)farthestMm());
      Serial.println(" mm");
    } else {
      Serial.println("-");
    }
  }
}
