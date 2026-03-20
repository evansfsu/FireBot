# FireBot

Fire detection and suppression robot using ROS2, YOLOv8 computer vision, mecanum drive, and automated fire extinguisher discharge.

## Hardware

- **Compute**: Raspberry Pi 5 (16GB RAM)
- **Microcontroller**: Arduino Uno (motor/sensor I/O)
- **Camera**: Arducam 12.3MP IMX477 HQ Camera (CSI) with 6mm CS lens
- **Drive**: 4x mecanum wheels via 2x L298N motor drivers
- **Extinguisher**: DC motor (pin pull) + lead screw (discharge lever)
- **Sensors**: HC-SR04 ultrasonic, analog audio/sound sensor
- **Warning**: Piezo buzzer + LED
- **YOLO Model**: [sayedgamal99/Real-Time-Smoke-Fire-Detection-YOLO11](https://github.com/sayedgamal99/Real-Time-Smoke-Fire-Detection-YOLO11) (Fire/Smoke)

## Architecture

Three ROS2 nodes running in a Docker container on the Pi:

| Node | Role |
|------|------|
| `fire_detector_node` | Camera capture + YOLOv8 fire/smoke detection |
| `brain_node` | State machine (IDLE -> SEARCHING -> APPROACHING -> WARNING -> EXTINGUISHING -> COMPLETE) |
| `arduino_bridge_node` | Serial bridge to Arduino for motors, extinguisher, and sensors |

The Arduino runs a single sketch that parses serial commands and drives all hardware. Nodes degrade gracefully when hardware is missing -- you can run with just a camera, or no hardware at all.

## Safety confirmation (3-stage)

FireBot requires **three confirmations** before it will approach and discharge an extinguisher:

1. **Vision confirmation**: sustained `Fire` detection for `vision_trigger_duration_sec`
2. **Alarm confirmation**: `/alarm/trigger` must be `true`
3. **User confirmation**: publish `/user/fire_confirm` as `true`

To deny/reset at any time, publish `/user/fire_confirm` as `false`.

## Quick Start (Raspberry Pi)

### 1. Install Docker on the Pi

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in
```

### 2. Clone and Build

```bash
git clone https://github.com/evansfsu/FireBot.git
cd FireBot
docker compose -f docker/docker-compose.yml up --build
```

The YOLO fire model is baked into the Docker image -- no separate download needed. First build takes 15-20 minutes on Pi 5.

### 3. Verify

In a second terminal:

```bash
# Enter the running container
docker exec -it $(docker ps -q) bash
source /opt/ros/humble/setup.bash && source /firebot_ws/install/setup.bash

# Check all nodes are running
ros2 node list

# Check state (should be IDLE)
ros2 topic echo /firebot/state --once

# Check if camera is detecting (with camera connected)
ros2 topic echo /detection --once

# Trigger alarm manually to test state machine
ros2 topic pub --once /alarm/trigger std_msgs/msg/Bool "data: true"
```

### 4. Raspberry Pi CLI demo (state + signals)

For a live command-line demo on the Pi, watch these topics:

```bash
ros2 topic echo /firebot/state
ros2 topic echo /firebot/status_message
```

Send manual confirmation signals:

```bash
# Fire alarm input
ros2 topic pub --once /alarm/trigger std_msgs/msg/Bool "data: true"

# User confirms fire
ros2 topic pub --once /user/fire_confirm std_msgs/msg/Bool "data: true"

# User denies fire (forces reset path)
ros2 topic pub --once /user/fire_confirm std_msgs/msg/Bool "data: false"
```

You can also run the helper demo script from inside the container:

```bash
bash /scripts/rpi_signal_demo.sh
```

Full copy/paste setup + demo flow:

```bash
# 1) Pull and run on Raspberry Pi
git pull
docker compose -f docker/docker-compose.yml down
docker compose -f docker/docker-compose.yml up --build -d

# 2) Open shell in running container
docker exec -it $(docker ps -q) bash
source /opt/ros/humble/setup.bash
source /firebot_ws/install/setup.bash

# 3) In separate terminals, observe state + messages
ros2 topic echo /firebot/state
ros2 topic echo /firebot/status_message

# 4) Send signals (or run helper script)
ros2 topic pub --once /alarm/trigger std_msgs/msg/Bool "data: true"
ros2 topic pub --once /user/fire_confirm std_msgs/msg/Bool "data: true"
ros2 topic pub --once /user/fire_confirm std_msgs/msg/Bool "data: false"
# OR:
bash /scripts/rpi_signal_demo.sh
```

### Camera-Only Mode

With just the camera connected (no Arduino), all three nodes start. The `arduino_bridge_node` logs a warning about the missing serial port but keeps running. The `fire_detector_node` and `brain_node` work fully -- you can test fire detection and watch the state machine respond.

When using a CSI camera in Docker, `fire_detector_node` should log `Pi Camera initialized`. If you see `picamera2 not available`, rebuild the Docker image so the required camera packages are installed.

### Windows Development

```bash
docker compose -f docker/docker-compose.yml --profile dev up --build
```

No hardware required. Use `scripts/test_state_machine_standalone.py` or the Docker simulation scripts to test.

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
├── scripts/                        # Test and simulation scripts
├── docs/                           # Setup guides
└── models/                         # YOLO .pt weights (baked into Docker image, git-ignored)
```

## Documentation

| Guide | Description |
|-------|-------------|
| [Raspberry Pi Setup](docs/RASPBERRY_PI_SETUP.md) | OS, Docker, camera, deployment, step-by-step |
| [Arduino Setup](docs/ARDUINO_SETUP.md) | Firmware upload, serial testing, pin map, protocol reference |
| [YOLO Fire Model](docs/YOLO_FIRE_MODEL.md) | Model source, classes, performance, fine-tuning |
| [Wiring Guide](docs/WIRING_GUIDE.md) | Complete pin-by-pin wiring for all components |

## Testing (No Hardware Required)

```bash
# Standalone state machine test (just Python, no Docker)
python scripts/test_state_machine_standalone.py

# Full ROS2 integration test in Docker
docker compose -f docker/docker-compose.yml --profile dev build
docker run --rm -v ./scripts:/scripts -v ./firebot_ws/src:/firebot_ws/src docker-firebot-dev \
  bash -c "sed -i 's/\r$//' /scripts/run_full_test.sh && bash /scripts/run_full_test.sh"
```
