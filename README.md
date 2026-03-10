# FireBot

Fire detection and suppression robot using ROS2, YOLOv8 computer vision, mecanum drive, and automated fire extinguisher discharge.

## Hardware

- **Compute**: Raspberry Pi 5 (16GB RAM)
- **Microcontroller**: Arduino Uno (motor/sensor I/O)
- **Camera**: Raspberry Pi Camera Module (CSI)
- **Drive**: 4x mecanum wheels via 2x L298N motor drivers
- **Extinguisher**: DC motor (pin pull) + lead screw (discharge lever)
- **Sensors**: HC-SR04 ultrasonic, analog audio/sound sensor
- **Warning**: Piezo buzzer + LED

## Architecture

Three ROS2 nodes running in a Docker container on the Pi:

| Node | Role |
|------|------|
| `fire_detector_node` | Pi Camera capture + YOLOv8 fire/smoke detection |
| `brain_node` | State machine (IDLE → SEARCHING → APPROACHING → WARNING → EXTINGUISHING → COMPLETE) |
| `arduino_bridge_node` | Serial bridge to Arduino for motors, extinguisher, and sensors |

The Arduino runs a single sketch that parses serial commands and drives all hardware.

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Arduino IDE or `arduino-cli` for uploading the sketch
- A trained YOLO model (`.pt` file) placed in `models/`

### 1. Upload Arduino Sketch

Open `arduino/firebot_controller/firebot_controller.ino` in Arduino IDE, select Arduino Uno, and upload.

### 2. Build and Run (Raspberry Pi)

```bash
docker compose -f docker/docker-compose.yml up --build
```

### 3. Build and Run (Windows Development)

```bash
docker compose -f docker/docker-compose.yml --profile dev up --build
```

No hardware is required for development -- nodes will log warnings and use mock data when devices are unavailable.

### 4. Test Alarm Trigger

```bash
# Inside the container or with ROS2 sourced:
ros2 topic pub --once /alarm/trigger std_msgs/msg/Bool "data: true"
```

## Configuration

All tunable parameters are in `firebot_ws/src/firebot/config/firebot_params.yaml`.

## Project Structure

```
FireBot/
├── docker/                         # Dockerfile + docker-compose
├── firebot_ws/src/
│   ├── firebot_interfaces/         # FireDetection.msg custom message
│   └── firebot/                    # All ROS2 Python nodes
│       ├── firebot/                # Node source code
│       ├── launch/                 # Launch file
│       └── config/                 # Parameter YAML
├── arduino/firebot_controller/     # Arduino sketch
└── models/                         # YOLO .pt weights (git-ignored)
```
