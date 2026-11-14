/*
  FarthestDistance - Arduino App Lab version (UNO Q and VENTUNO Q)

  Uses a Modulino Distance (time-of-flight sensor). It measures one distance
  in its narrow field of view, so slowly sweep it across the scene; the
  sketch keeps the farthest reading from the last few seconds.

  Sent to Python through the Bridge 4 times a second:
    Bridge.notify("distance", nowMm, farthestMm)   -1 = no reading
  At startup:
    Bridge.notify("sensor_status", found)
*/

#include <Arduino_Modulino.h>
#include <Arduino_RouterBridge.h>

ModulinoDistance distance;

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

void setup() {
  Bridge.begin();

  // On the UNO Q and VENTUNO Q the Qwiic connector is on Wire1
  Modulino.begin(Wire1);

  while (!distance.begin()) {
    Bridge.notify("sensor_status", false);
    delay(1000);
  }
  Bridge.notify("sensor_status", true);
}

void loop() {
  updateDistance();

  unsigned long now = millis();
  if (now - lastReportMs >= reportEveryMs) {
    lastReportMs = now;
    int nowMm = isnan(currentMm) ? -1 : (int)currentMm;
    int farMm = farthestMm() > 0 ? (int)farthestMm() : -1;
    Bridge.notify("distance", nowMm, farMm);
  }
}
