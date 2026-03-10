# FireBot Complete Wiring Guide

Full wiring reference for connecting all hardware to the Arduino Uno.

## Component List

| Component | Qty | Purpose |
|-----------|-----|---------|
| Arduino Uno | 1 | Microcontroller |
| L298N Motor Driver | 2 | Drive 4 mecanum wheels |
| Mecanum wheel DC motor | 4 | Movement |
| DC motor (small) | 1 | Pull fire extinguisher pin (via relay/MOSFET) |
| DC motor or linear actuator | 1 | Push extinguisher discharge lever (via relay/MOSFET) |
| Relay module (or MOSFET) | 2 | Switch extinguisher motors |
| HC-SR04 Ultrasonic Sensor | 1 | Distance measurement |
| Sound/Audio sensor module | 1 | Audio detection |
| Piezo buzzer (active) | 1 | Warning alert |
| LED (red, 5mm) + 220 ohm resistor | 1 | Warning indicator |
| Raspberry Pi 5 | 1 | Main compute (not wired to Arduino directly -- USB only) |
| Pi Camera Module v2/v3 | 1 | Connected to Pi via CSI ribbon |
| USB A-B cable | 1 | Pi to Arduino serial |
| 12V battery / power supply | 1 | Powers L298N boards and motors |
| Jumper wires | Many | Connections |

## Power Architecture

```
12V Battery ──┬── L298N #1 (12V input) ── Front motors
              ├── L298N #2 (12V input) ── Rear motors
              └── Relay modules ── Extinguisher motors

L298N #1 (5V output) ── Arduino Uno (Vin)
                        (L298N's onboard regulator provides 5V)

Raspberry Pi 5 ── USB-C power supply (5V/5A) or battery with regulator
```

**Important**: Do NOT power the Pi from the Arduino. The Pi 5 needs its own 5V/5A supply.

## Wiring Diagram (Pin-by-Pin)

### L298N Motor Driver #1 (Front Wheels)

```
L298N #1          Arduino Uno
────────          ───────────
ENA ────────────── D3  (PWM - front-left speed)
IN1 ────────────── D4  (front-left direction A)
IN2 ────────────── D7  (front-left direction B)
ENB ────────────── D5  (PWM - front-right speed)
IN3 ────────────── D8  (front-right direction A)
IN4 ────────────── A0  (front-right direction B)

12V ────────────── 12V battery (+)
GND ────────────── Battery GND + Arduino GND (common ground!)
5V  ────────────── Arduino Vin (powers the Arduino)

OUT1 ───────────── Front-Left motor wire A
OUT2 ───────────── Front-Left motor wire B
OUT3 ───────────── Front-Right motor wire A
OUT4 ───────────── Front-Right motor wire B
```

**Remove the ENA and ENB jumpers** on the L298N board to enable PWM speed control.

### L298N Motor Driver #2 (Rear Wheels)

```
L298N #2          Arduino Uno
────────          ───────────
ENA ────────────── D6  (PWM - rear-left speed)
IN1 ────────────── A1  (rear-left direction A)
IN2 ────────────── A2  (rear-left direction B)
ENB ────────────── D9  (PWM - rear-right speed)
IN3 ────────────── A3  (rear-right direction A)
IN4 ────────────── A4  (rear-right direction B)

12V ────────────── 12V battery (+)
GND ────────────── Battery GND + Arduino GND (common ground!)
5V  ────────────── (leave disconnected -- Arduino already powered by L298N #1)

OUT1 ───────────── Rear-Left motor wire A
OUT2 ───────────── Rear-Left motor wire B
OUT3 ───────────── Rear-Right motor wire A
OUT4 ───────────── Rear-Right motor wire B
```

### Extinguisher Motors (via Relay Modules)

```
Relay #1 (Pin Pull)        Arduino Uno
───────────────────        ───────────
Signal (IN) ────────────── D10
VCC ────────────────────── 5V
GND ────────────────────── GND
COM ────────────────────── 12V battery (+)
NO  ────────────────────── Pin-pull motor (+)
Pin-pull motor (-) ──────── Battery GND

Relay #2 (Lead Screw)     Arduino Uno
─────────────────────     ───────────
Signal (IN) ────────────── D11
VCC ────────────────────── 5V
GND ────────────────────── GND
COM ────────────────────── 12V battery (+)
NO  ────────────────────── Lead-screw motor (+)
Lead-screw motor (-) ────── Battery GND
```

### HC-SR04 Ultrasonic Sensor

```
HC-SR04           Arduino Uno
───────           ───────────
VCC ────────────── 5V
TRIG ───────────── D13
ECHO ───────────── A5
GND ────────────── GND
```

Note: The ECHO pin outputs 5V which is fine for the Arduino. If using a 3.3V board, add a voltage divider.

### Sound/Audio Sensor Module

```
Audio Sensor      Arduino Uno
────────────      ───────────
VCC ────────────── 5V (or 3.3V depending on module)
OUT (analog) ───── A6
GND ────────────── GND
```

A6 is an analog-input-only pin on the Uno, which is perfect for reading the audio sensor's analog output.

### Buzzer and Warning LED

```
Buzzer (active)   Arduino Uno
───────────────   ───────────
(+) ────────────── D2
(-) ────────────── GND

LED               Arduino Uno
───                ───────────
Anode (+) ──[220Ω]── D12
Cathode (-) ──────── GND
```

## Common Ground

**Critical**: All GND connections must be tied together:
- Arduino GND
- L298N #1 GND
- L298N #2 GND
- Relay module GND(s)
- Sensor GNDs
- Battery GND
- Buzzer/LED GND

Without a common ground, serial communication and motor control will be unreliable.

## Mecanum Wheel Motor Orientation

When looking at the robot from above, the rollers on each mecanum wheel should form an **X pattern**:

```
  Front
  ╱  ╲       ← roller angles viewed from above
 FL  FR
 ╲  ╱
 RL  RR
  Back
```

If a wheel spins the wrong direction, swap the two motor wires for that wheel (or swap IN1/IN2 in the code).

### Motor Direction Test

After wiring, send these serial commands to verify each motor:

```
M,100,0,0    -> All wheels forward (robot moves forward)
M,-100,0,0   -> All wheels backward
M,0,0,50     -> Spin clockwise (rotate right)
M,0,0,-50    -> Spin counter-clockwise (rotate left)
```

If the robot moves in an unexpected direction, swap wires on the offending motor(s).

## Complete Pin Summary

| Arduino Pin | Connected To | Type |
|------------|-------------|------|
| D0 | USB Serial RX (reserved) | Serial |
| D1 | USB Serial TX (reserved) | Serial |
| D2 | Buzzer (+) | Digital Out |
| D3 | L298N #1 ENA (front-left PWM) | PWM Out |
| D4 | L298N #1 IN1 (front-left dir) | Digital Out |
| D5 | L298N #1 ENB (front-right PWM) | PWM Out |
| D6 | L298N #2 ENA (rear-left PWM) | PWM Out |
| D7 | L298N #1 IN2 (front-left dir) | Digital Out |
| D8 | L298N #1 IN3 (front-right dir) | Digital Out |
| D9 | L298N #2 ENB (rear-right PWM) | PWM Out |
| D10 | Relay #1 signal (pin-pull) | Digital Out |
| D11 | Relay #2 signal (lead-screw) | Digital Out |
| D12 | Warning LED anode (via 220 ohm) | Digital Out |
| D13 | HC-SR04 TRIG | Digital Out |
| A0 | L298N #1 IN4 (front-right dir) | Digital Out |
| A1 | L298N #2 IN1 (rear-left dir) | Digital Out |
| A2 | L298N #2 IN2 (rear-left dir) | Digital Out |
| A3 | L298N #2 IN3 (rear-right dir) | Digital Out |
| A4 | L298N #2 IN4 (rear-right dir) | Digital Out |
| A5 | HC-SR04 ECHO | Digital In |
| A6 | Audio sensor (analog out) | Analog In |

**18 of 20 usable pins used** (D0/D1 reserved for serial, A7 free).
