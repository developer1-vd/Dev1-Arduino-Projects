/*
  FarthestDistance - Arduino App Lab version (UNO Q and VENTUNO Q)

  Uses a Modulino Distance (time-of-flight sensor). It measures one distance
  in its narrow field of view, so slowly sweep it across the scene; the
  sketch keeps the farthest reading from the last few seconds.

  A Modulino Buzzer (optional) works as a proximity alarm: it beeps when
  something comes closer than 40 cm, faster as it gets closer, and
  continuously below 10 cm, like a parking sensor.

  Sent to Python through the Bridge 4 times a second:
    Bridge.notify("distance", nowMm, farthestMm)   -1 = no reading
  When the alarm starts or stops:
    Bridge.notify("alarm", on, nowMm)
  At startup:
    Bridge.notify("sensor_status", found)
    Bridge.notify("buzzer_status", found)
*/

#include <Arduino_Modulino.h>
#include <Arduino_RouterBridge.h>

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
  Bridge.begin();

  // On the UNO Q and VENTUNO Q the Qwiic connector is on Wire1
  Modulino.begin(Wire1);

  while (!distance.begin()) {
    Bridge.notify("sensor_status", false);
    delay(1000);
  }
  Bridge.notify("sensor_status", true);

  // The buzzer is optional: without it you still get the distances
  buzzerFound = buzzer.begin();
  Bridge.notify("buzzer_status", buzzerFound);
}

void loop() {
  updateDistance();

  bool close = updateAlarm();
  if (close != alarmOn) {
    alarmOn = close;
    Bridge.notify("alarm", alarmOn, alarmOn ? (int)currentMm : -1);
  }

  unsigned long now = millis();
  if (now - lastReportMs >= reportEveryMs) {
    lastReportMs = now;
    int nowMm = isnan(currentMm) ? -1 : (int)currentMm;
    int farMm = farthestMm() > 0 ? (int)farthestMm() : -1;
    Bridge.notify("distance", nowMm, farMm);
  }
}
