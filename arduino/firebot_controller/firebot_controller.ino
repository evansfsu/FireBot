// FireBot Arduino Controller
// Drives 4 mecanum wheels (2x L298N), fire extinguisher (relay/MOSFET),
// buzzer/LED warning, HC-SR04 ultrasonic, and audio sensor.
// Communicates with Raspberry Pi over USB serial.
//
// Pin budget (Arduino Uno: D0-D13, A0-A5 as digital, A6-A7 analog-only):
//   D0, D1    = Hardware serial (USB) -- reserved
//   D2        = Buzzer (tone output)
//   D3        = FL motor enable (PWM)
//   D4        = FL direction IN1
//   D5        = FR motor enable (PWM)
//   D6        = RL motor enable (PWM)
//   D7        = FL direction IN2
//   D8        = FR direction IN1
//   D9        = RR motor enable (PWM)
//   D10       = Extinguisher pin-pull relay
//   D11       = Extinguisher lead-screw relay
//   D12       = Warning LED
//   D13       = Ultrasonic trigger
//   A0        = FR direction IN2
//   A1        = RL direction IN1
//   A2        = RL direction IN2
//   A3        = RR direction IN1
//   A4        = RR direction IN2
//   A5        = Ultrasonic echo (digital input)
//   A6        = Audio sensor (analog input only)

// ── L298N #1: Front wheels ──
#define FL_EN   3
#define FL_IN1  4
#define FL_IN2  7
#define FR_EN   5
#define FR_IN1  8
#define FR_IN2  A0

// ── L298N #2: Rear wheels ──
#define RL_EN   6
#define RL_IN1  A1
#define RL_IN2  A2
#define RR_EN   9
#define RR_IN1  A3
#define RR_IN2  A4

// ── Extinguisher (relay or MOSFET -- single pin per actuator) ──
#define PIN_PULL_RELAY    10
#define LEADSCREW_RELAY   11

// ── Warning ──
#define BUZZER_PIN  2
#define LED_PIN     12

// ── Ultrasonic HC-SR04 ──
#define TRIG_PIN  13
#define ECHO_PIN  A5

// ── Audio sensor ──
#define AUDIO_PIN A6

// Serial command buffer
char cmdBuffer[64];
int cmdIdx = 0;

void setup() {
  Serial.begin(115200);

  // Motor outputs
  const int motorPins[] = {
    FL_EN, FL_IN1, FL_IN2,
    FR_EN, FR_IN1, FR_IN2,
    RL_EN, RL_IN1, RL_IN2,
    RR_EN, RR_IN1, RR_IN2
  };
  for (int i = 0; i < 12; i++) {
    pinMode(motorPins[i], OUTPUT);
    digitalWrite(motorPins[i], LOW);
  }

  // Extinguisher relays
  pinMode(PIN_PULL_RELAY, OUTPUT);
  pinMode(LEADSCREW_RELAY, OUTPUT);
  digitalWrite(PIN_PULL_RELAY, LOW);
  digitalWrite(LEADSCREW_RELAY, LOW);

  // Warning outputs
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);

  // Ultrasonic
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
}

void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (cmdIdx > 0) {
        cmdBuffer[cmdIdx] = '\0';
        processCommand(cmdBuffer);
        cmdIdx = 0;
      }
    } else if (cmdIdx < (int)sizeof(cmdBuffer) - 1) {
      cmdBuffer[cmdIdx++] = c;
    }
  }
}

// ─── Command dispatch ───

void processCommand(const char* cmd) {
  switch (cmd[0]) {
    case 'M': handleMotor(cmd);        break;
    case 'E': handleExtinguisher(cmd); break;
    case 'W': handleWarning(cmd);      break;
    case 'S': handleSensors();         break;
  }
}

// ─── M,vx,vy,wz — Mecanum motor command ───

void handleMotor(const char* cmd) {
  int vx = 0, vy = 0, wz = 0;
  sscanf(cmd, "M,%d,%d,%d", &vx, &vy, &wz);

  int fl = vx + vy + wz;
  int fr = vx - vy - wz;
  int rl = vx - vy + wz;
  int rr = vx + vy - wz;

  setMotor(FL_EN, FL_IN1, FL_IN2, fl);
  setMotor(FR_EN, FR_IN1, FR_IN2, fr);
  setMotor(RL_EN, RL_IN1, RL_IN2, rl);
  setMotor(RR_EN, RR_IN1, RR_IN2, rr);
}

void setMotor(int enPin, int in1, int in2, int speed) {
  int pwm = constrain(abs(speed), 0, 255);
  if (speed > 0) {
    digitalWrite(in1, HIGH);
    digitalWrite(in2, LOW);
  } else if (speed < 0) {
    digitalWrite(in1, LOW);
    digitalWrite(in2, HIGH);
  } else {
    digitalWrite(in1, LOW);
    digitalWrite(in2, LOW);
  }
  analogWrite(enPin, pwm);
}

// ─── E,action — Extinguisher command ───
// 0 = idle, 1 = pull pin, 2 = discharge, 3 = stop

void handleExtinguisher(const char* cmd) {
  int action = 0;
  sscanf(cmd, "E,%d", &action);

  switch (action) {
    case 1:
      digitalWrite(PIN_PULL_RELAY, HIGH);
      digitalWrite(LEADSCREW_RELAY, LOW);
      break;
    case 2:
      digitalWrite(PIN_PULL_RELAY, LOW);
      digitalWrite(LEADSCREW_RELAY, HIGH);
      break;
    default: // 0 and 3: everything off
      digitalWrite(PIN_PULL_RELAY, LOW);
      digitalWrite(LEADSCREW_RELAY, LOW);
      break;
  }
}

// ─── W,state — Warning buzzer + LED ───
// 0 = off, 1 = warning beep (countdown), 2 = continuous (discharge)

void handleWarning(const char* cmd) {
  int state = 0;
  sscanf(cmd, "W,%d", &state);

  switch (state) {
    case 0:
      noTone(BUZZER_PIN);
      digitalWrite(LED_PIN, LOW);
      break;
    case 1:
      tone(BUZZER_PIN, 2000);
      digitalWrite(LED_PIN, HIGH);
      break;
    case 2:
      tone(BUZZER_PIN, 3000);
      digitalWrite(LED_PIN, HIGH);
      break;
  }
}

// ─── S — Read sensors and reply ───
// Response format: D,distance_cm,audio_raw

void handleSensors() {
  long dist = readUltrasonic();
  int audio = analogRead(AUDIO_PIN);

  Serial.print("D,");
  Serial.print(dist);
  Serial.print(",");
  Serial.println(audio);
}

long readUltrasonic() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 30000);
  if (duration == 0) return 999;
  return duration / 58;
}
