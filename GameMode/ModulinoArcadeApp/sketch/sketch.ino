/*
  Modulino Arcade - App Lab app for the Arduino UNO Q / VENTUNO Q

  Two games played with a Modulino Buttons and a Modulino Buzzer, shown on the
  board's 8x13 LED matrix:

    Button A -> Reaction: wait for a button's LED to light, press that button
                as fast as you can. 5 rounds; score = average reaction in ms
                (lower is better). Pressing too early or the wrong button
                costs 1000 ms.
    Button B -> Simon: watch the sequence of LEDs and tones, repeat it. It
                grows by one each round; score = longest sequence repeated.

  The browser page (Python + Web UI) can also start games, and keeps the
  high scores. Events go to Python through the Bridge:
    Bridge.notify("arcade_status", text)          what's happening
    Bridge.notify("arcade_over", game, score)     game 1 = Reaction, 2 = Simon
  Python starts games with Bridge.call("start_game", game).
*/

#include <Arduino_LED_Matrix.h>
#include <Arduino_Modulino.h>
#include <Arduino_RouterBridge.h>

ModulinoButtons buttons;
ModulinoBuzzer buzzer;
Arduino_LED_Matrix matrix;

const int GAME_NONE = 0;
const int GAME_REACTION = 1;
const int GAME_SIMON = 2;

const int buttonTone[3] = { 2637, 3136, 3520 };  // E7, G7, A7: near the buzzer's loud range

volatile int requestedGame = GAME_NONE;  // set by Python, read in loop()
bool buttonsFound = false;
bool buzzerFound = false;

// ---------------- LED matrix (8 rows x 13 columns) ----------------
uint8_t frame[104];

// 3x5 digits, each row is 3 bits (MSB = left column)
const uint8_t DIGITS[10][5] = {
  {7, 5, 5, 5, 7}, {2, 6, 2, 2, 7}, {7, 1, 7, 4, 7}, {7, 1, 7, 1, 7}, {5, 5, 7, 1, 1},
  {7, 4, 7, 1, 7}, {7, 4, 7, 5, 7}, {7, 1, 1, 1, 1}, {7, 5, 7, 5, 7}, {7, 5, 7, 1, 7},
};

void clearFrame() {
  memset(frame, 0, sizeof(frame));
}

void setPixel(int x, int y) {
  if (x >= 0 && x < 13 && y >= 0 && y < 8) frame[y * 13 + x] = 1;
}

void drawDigit(int d, int x, int y) {
  for (int row = 0; row < 5; row++)
    for (int col = 0; col < 3; col++)
      if (DIGITS[d][row] & (4 >> col)) setPixel(x + col, y + row);
}

// Show a number 0-999 centred on the matrix
void showNumber(int n) {
  n = constrain(n, 0, 999);
  clearFrame();
  int digits = n >= 100 ? 3 : (n >= 10 ? 2 : 1);
  int width = digits * 4 - 1;
  int x = (13 - width) / 2;
  int divisor = digits == 3 ? 100 : (digits == 2 ? 10 : 1);
  for (int i = 0; i < digits; i++) {
    drawDigit((n / divisor) % 10, x, 1);
    x += 4;
    divisor /= 10;
  }
  matrix.draw(frame);
}

// Light one third of the matrix for button 0, 1 or 2 (-1 = blank)
void showSection(int section) {
  clearFrame();
  if (section >= 0) {
    for (int x = section * 4 + section / 2; x < section * 4 + section / 2 + 4; x++)
      for (int y = 1; y < 7; y++) setPixel(x, y);
  }
  matrix.draw(frame);
}

void showSmiley() {
  clearFrame();
  setPixel(4, 2); setPixel(8, 2);
  setPixel(3, 4); setPixel(9, 4);
  for (int x = 4; x <= 8; x++) setPixel(x, 5);
  matrix.draw(frame);
}

void showCross() {
  clearFrame();
  for (int i = 0; i < 6; i++) { setPixel(4 + i, 1 + i); setPixel(9 - i, 1 + i); }
  matrix.draw(frame);
}

// ---------------- helpers ----------------
void status(const char* text) {
  Bridge.notify("arcade_status", String(text));
}

void beep(int freq, int ms) {
  if (buzzerFound) buzzer.tone(freq, ms);
}

void leds(int which) {  // -1 = all off, 3 = all on
  if (!buttonsFound) return;
  buttons.setLeds(which == 0 || which == 3, which == 1 || which == 3, which == 2 || which == 3);
}

// Returns the pressed button (0-2) or -1. Only reports new presses.
bool wasDown[3] = { false, false, false };
int pressedButton() {
  if (!buttonsFound) return -1;
  buttons.update();
  int result = -1;
  for (int i = 0; i < 3; i++) {
    bool down = buttons.isPressed(i);
    if (down && !wasDown[i] && result == -1) result = i;
    wasDown[i] = down;
  }
  return result;
}

// Wait for a press for up to timeoutMs; -1 on timeout
int waitForPress(unsigned long timeoutMs) {
  unsigned long start = millis();
  while (millis() - start < timeoutMs) {
    int b = pressedButton();
    if (b >= 0) return b;
    delay(5);
  }
  return -1;
}

void waitForRelease() {
  while (buttonsFound) {
    buttons.update();
    if (!buttons.isPressed(0) && !buttons.isPressed(1) && !buttons.isPressed(2)) break;
    delay(5);
  }
  for (int i = 0; i < 3; i++) wasDown[i] = false;
}

void countdown() {
  for (int n = 3; n >= 1; n--) {
    showNumber(n);
    beep(1760, 120);
    delay(700);
  }
}

void gameOverSound() {
  beep(880, 200); delay(220);
  beep(660, 200); delay(220);
  beep(440, 400); delay(450);
}

// ---------------- Reaction ----------------
void playReaction() {
  status("Reaction: press the lit button as fast as you can!");
  countdown();
  const int rounds = 5;
  unsigned long total = 0;

  for (int round = 1; round <= rounds; round++) {
    showSection(-1);
    leds(-1);
    waitForRelease();

    // Random wait; pressing during it is a false start
    unsigned long waitMs = random(1000, 3000);
    int early = waitForPress(waitMs);
    unsigned long reaction;
    if (early >= 0) {
      showCross();
      beep(220, 300);
      reaction = 1000;
      status("Too early! +1000 ms");
      delay(800);
    } else {
      int target = random(3);
      leds(target);
      showSection(target);
      beep(buttonTone[target], 80);
      unsigned long start = millis();
      int pressed = waitForPress(2000);
      reaction = millis() - start;
      if (pressed != target) {
        showCross();
        beep(220, 300);
        reaction = 1000;
        status(pressed < 0 ? "Too slow! +1000 ms" : "Wrong button! +1000 ms");
        delay(800);
      } else {
        showNumber(min((int)reaction, 999));
        beep(3520, 60);
        delay(700);
      }
    }
    total += reaction;
    Bridge.notify("arcade_round", GAME_REACTION, round, (int)reaction);
  }

  int average = total / rounds;
  leds(-1);
  showNumber(min(average, 999));
  gameOverSound();
  Bridge.notify("arcade_over", GAME_REACTION, average);
  delay(1500);
}

// ---------------- Simon ----------------
void playSimon() {
  status("Simon: watch the sequence, then repeat it.");
  countdown();
  const int maxLength = 50;
  int sequence[maxLength];
  int length = 0;

  while (length < maxLength) {
    sequence[length++] = random(3);

    // Play the sequence; faster as it grows
    int stepMs = max(180, 500 - length * 15);
    showNumber(length);
    delay(600);
    for (int i = 0; i < length; i++) {
      leds(sequence[i]);
      showSection(sequence[i]);
      beep(buttonTone[sequence[i]], stepMs);
      delay(stepMs);
      leds(-1);
      showSection(-1);
      delay(stepMs / 2);
    }

    // Player repeats it
    waitForRelease();
    for (int i = 0; i < length; i++) {
      int pressed = waitForPress(4000);
      if (pressed != sequence[i]) {
        showCross();
        leds(3);
        gameOverSound();
        leds(-1);
        int score = length - 1;
        showNumber(score);
        Bridge.notify("arcade_over", GAME_SIMON, score);
        delay(1500);
        return;
      }
      leds(pressed);
      showSection(pressed);
      beep(buttonTone[pressed], 150);
      delay(170);
      leds(-1);
      showSection(-1);
    }
    Bridge.notify("arcade_round", GAME_SIMON, length, 0);
    showSmiley();
    delay(500);
  }
  Bridge.notify("arcade_over", GAME_SIMON, length);
}

// ---------------- menu ----------------
void startGameFromPython(int game) {
  requestedGame = game;  // handled in loop(), not inside the Bridge callback
}

void showMenu() {
  showSmiley();
  leds(3);
  status("Press A for Reaction or B for Simon (or start one from this page).");
}

void setup() {
  Bridge.begin();
  Bridge.provide("start_game", startGameFromPython);

  matrix.begin();
  matrix.setGrayscaleBits(1);

  // On the UNO Q and VENTUNO Q the Qwiic connector is Wire1
  Modulino.begin(Wire1);
  for (int i = 0; i < 10 && !buttonsFound; i++) {
    buttonsFound = buttons.begin();
    if (!buttonsFound) delay(300);
  }
  buzzerFound = buzzer.begin();
  Bridge.notify("arcade_modules", buttonsFound, buzzerFound);

  randomSeed(micros());
  showMenu();
}

void loop() {
  int game = requestedGame;
  if (game == GAME_NONE) {
    int b = pressedButton();
    if (b == 0) game = GAME_REACTION;
    else if (b == 1) game = GAME_SIMON;
  }

  if (game == GAME_REACTION || game == GAME_SIMON) {
    requestedGame = GAME_NONE;
    leds(-1);
    if (game == GAME_REACTION) playReaction();
    else playSimon();
    waitForRelease();
    showMenu();
  }

  if (!buttonsFound) {
    // keep trying, so plugging the buttons in later works
    static unsigned long lastTry = 0;
    if (millis() - lastTry > 2000) {
      lastTry = millis();
      buttonsFound = buttons.begin();
      if (buttonsFound) {
        Bridge.notify("arcade_modules", buttonsFound, buzzerFound);
        showMenu();
      }
    }
  }
  delay(10);
}
