# Arduino Uno Setup Guide

How to upload the FireBot firmware and connect the Arduino to the Raspberry Pi.

## 1. Install Arduino IDE

### Option A: On Windows (for initial development)
Download from https://www.arduino.cc/en/software and install.

### Option B: On Raspberry Pi (for deployment)
```bash
sudo apt install arduino-cli -y
# Or install the full IDE:
sudo apt install arduino -y
```

## 2. Upload the Sketch

### From Arduino IDE (Windows or Pi with desktop)

1. Open `arduino/firebot_controller/firebot_controller.ino`
2. Go to **Tools -> Board -> Arduino Uno**
3. Go to **Tools -> Port** and select the Arduino's COM port (Windows) or `/dev/ttyACM0` (Pi)
4. Click **Upload** (right arrow button)
5. Wait for "Done uploading" message

### From command line (Pi headless)

```bash
# Install arduino-cli if not already installed
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh
export PATH=$PATH:$HOME/bin

# Install Arduino Uno core
arduino-cli core install arduino:avr

# Compile
arduino-cli compile --fqbn arduino:avr:uno arduino/firebot_controller/

# Upload (adjust port if needed)
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:uno arduino/firebot_controller/
```

## 3. Test Serial Communication

After uploading, test that the Arduino responds to commands:

### From Pi terminal (without Docker)

```bash
# Set baud rate
stty -F /dev/ttyACM0 115200

# Send sensor request
echo "S" > /dev/ttyACM0

# Read response (should print D,999,XXX where XXX is audio reading)
cat /dev/ttyACM0 &
echo "S" > /dev/ttyACM0
# Press Ctrl+C after seeing the response
```

### From screen/minicom (interactive)

```bash
sudo apt install screen -y
screen /dev/ttyACM0 115200
# Type commands and see responses:
# S         -> D,999,512
# M,100,0,0 -> (motors run forward)
# M,0,0,0   -> (motors stop)
# W,1       -> (buzzer on)
# W,0       -> (buzzer off)
# Press Ctrl+A then K to quit screen
```

## 4. Pin Map Reference

The Arduino sketch uses these pin assignments:

```
Arduino Uno Pin Layout for FireBot
==================================

DIGITAL PINS:
  D0  - Hardware Serial RX (USB) -- reserved
  D1  - Hardware Serial TX (USB) -- reserved
  D2  - Buzzer (warning tone)
  D3  - Front-Left motor PWM    (L298N #1 ENA)  [PWM]
  D4  - Front-Left motor dir    (L298N #1 IN1)
  D5  - Front-Right motor PWM   (L298N #1 ENB)  [PWM]
  D6  - Rear-Left motor PWM     (L298N #2 ENA)  [PWM]
  D7  - Front-Left motor dir    (L298N #1 IN2)
  D8  - Front-Right motor dir   (L298N #1 IN3)
  D9  - Rear-Right motor PWM    (L298N #2 ENB)  [PWM]
  D10 - Extinguisher pin-pull relay
  D11 - Extinguisher lead-screw relay
  D12 - Warning LED
  D13 - Ultrasonic trigger

ANALOG PINS (used as digital unless noted):
  A0  - Front-Right motor dir   (L298N #1 IN4)
  A1  - Rear-Left motor dir     (L298N #2 IN1)
  A2  - Rear-Left motor dir     (L298N #2 IN2)
  A3  - Rear-Right motor dir    (L298N #2 IN3)
  A4  - Rear-Right motor dir    (L298N #2 IN4)
  A5  - Ultrasonic echo (digital input)
  A6  - Audio sensor (analog input only)
```

## 5. Serial Protocol Quick Reference

All commands are ASCII text terminated with newline (`\n`).

### Commands (Pi -> Arduino)

| Command | Format | Example | Action |
|---------|--------|---------|--------|
| Motor | `M,vx,vy,wz` | `M,100,0,0` | Drive forward at speed 100 |
| Motor | `M,0,0,50` | | Rotate right |
| Motor | `M,0,0,0` | | Stop all motors |
| Extinguisher | `E,0` | | Idle / stop |
| Extinguisher | `E,1` | | Pull pin |
| Extinguisher | `E,2` | | Push discharge lever |
| Extinguisher | `E,3` | | Stop |
| Warning | `W,0` | | Buzzer + LED off |
| Warning | `W,1` | | Warning beep (2kHz) + LED on |
| Warning | `W,2` | | Continuous tone (3kHz) + LED on |
| Sensors | `S` | | Request sensor readings |

### Responses (Arduino -> Pi)

| Response | Format | Example | Meaning |
|----------|--------|---------|---------|
| Sensors | `D,dist,audio` | `D,45,512` | 45cm distance, 512 audio ADC |

## 6. Troubleshooting

| Problem | Solution |
|---------|----------|
| Upload fails "port busy" | Close any serial monitor / screen sessions first |
| Upload fails "not in sync" | Press reset button on Arduino just before upload starts |
| No serial response | Check baud rate is 115200, check USB cable is data-capable (not charge-only) |
| Motors don't spin | Check L298N power supply, verify `ENA`/`ENB` jumpers are removed (PWM mode) |
| Wrong motor direction | Swap `IN1`/`IN2` wires for that motor, or swap in the sketch |
| Buzzer too quiet | Use a louder buzzer module or add an amplifier circuit |
| Ultrasonic reads 999 always | Check TRIG (D13) and ECHO (A5) wiring to HC-SR04 |
