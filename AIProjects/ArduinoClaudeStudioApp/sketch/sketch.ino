// Claude Studio playground sketch.
//
// This is the code Claude writes for you. After it changes this file, press
// Stop and then Run in App Lab to compile and flash it to the
// microcontroller (Claude Studio comes back with your chat).
//
// studioLog("...") sends a line to the "Sketch output" panel in Claude
// Studio. Keep it: it's how you and Claude see what the sketch is doing.

#include <Arduino_RouterBridge.h>

void studioLog(String line) {
  Bridge.notify("studio_log", line);
}

void setup() {
  Bridge.begin();
  pinMode(LED_BUILTIN, OUTPUT);
  studioLog("Playground sketch started");
}

void loop() {
  digitalWrite(LED_BUILTIN, HIGH);
  studioLog("LED on");
  delay(1000);
  digitalWrite(LED_BUILTIN, LOW);
  studioLog("LED off");
  delay(1000);
}
