# Raspberry Pi 5 Setup Guide

Step-by-step setup for deploying FireBot on a Raspberry Pi 5 (16GB RAM). Start with just the camera -- Arduino and other hardware can be added later.

## 1. Flash the OS

1. Download **Raspberry Pi Imager** from https://www.raspberrypi.com/software/
2. Insert a microSD card (32GB+ recommended)
3. In Imager, choose:
   - **Device**: Raspberry Pi 5
   - **OS**: Raspberry Pi OS (64-bit) -- based on Debian Bookworm
   - **Storage**: Your microSD card
4. Click the gear icon to pre-configure:
   - Set hostname: `firebot`
   - Enable SSH (use password or SSH key)
   - Set username/password
   - Configure WiFi (if not using Ethernet)
5. Flash the card and boot the Pi

## 2. Initial Pi Configuration

SSH into the Pi or connect a monitor:

```bash
ssh your_username@firebot.local
```

Update the system:

```bash
sudo apt update && sudo apt upgrade -y
```

## 3. Connect the Camera

**Camera**: Arducam 12.3MP IMX477 HQ Camera with 6mm CS lens (CSI interface).

**Important**: This camera was originally packaged for Jetson Nano. If the CSI ribbon cable doesn't fit the Pi 5's mini CSI connector, you'll need a 22-pin to 15-pin adapter cable, or an Arducam Pi-compatible ribbon cable.

Connect the CSI ribbon cable:
1. Locate the CSI camera port on the Pi 5 (labeled CAM/DISP 0 or 1)
2. Lift the latch
3. Slide the ribbon cable in with contacts facing the board
4. Press the latch down

Verify the camera is detected:

```bash
# Quick camera test (shows preview if display connected)
rpicam-hello

# Or capture a test image (works headless)
rpicam-still -o test.jpg
ls -la test.jpg
# Should show a file of several MB

# Check video device exists
ls /dev/video*
```

If the camera isn't detected, check:
- Ribbon cable orientation and seating
- `sudo dmesg | grep -i cam` for errors
- The IMX477 sensor should be auto-detected by libcamera

## 4. Install Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

**Log out and back in** for the group change to take effect, then verify:

```bash
docker --version
docker run hello-world
```

Install Docker Compose plugin if not already included:

```bash
sudo apt install docker-compose-plugin -y
docker compose version
```

## 5. Clone and Build

```bash
cd ~
git clone https://github.com/evansfsu/FireBot.git
cd FireBot
```

Build and start (the YOLO model is baked into the Docker image):

```bash
docker compose -f docker/docker-compose.yml up --build
```

First build takes **15-20 minutes** on Pi 5 (pulling ROS2 Humble base image + installing PyTorch/Ultralytics). Subsequent starts are fast (~5 seconds).

You'll see output like:

```
[fire_detector_node] [INFO] Pi Camera initialized
[fire_detector_node] [INFO] YOLO model loaded: /models/best_small.pt
[fire_detector_node] [INFO] Fire detector node started
[brain_node]         [INFO] Brain node started -- state: IDLE
[arduino_bridge_node] [WARN] Serial open failed: /dev/ttyACM0   <-- expected without Arduino
[arduino_bridge_node] [INFO] Arduino bridge node started
```

The serial warning for `arduino_bridge_node` is expected when Arduino isn't connected. All nodes continue running.

## 6. Test Camera + Detection (Camera-Only)

Open a second SSH terminal and enter the running container:

```bash
docker exec -it $(docker ps -q) bash
source /opt/ros/humble/setup.bash
source /firebot_ws/install/setup.bash
```

### Check all nodes are alive

```bash
ros2 node list
# Expected: /fire_detector_node  /brain_node  /arduino_bridge_node
```

### Check fire detection is running

```bash
ros2 topic echo /detection --once
```

If no fire is visible, you should see:

```
detected: false
confidence: 0.0
...
```

### Test with a fire image on your phone

1. Search for "fire" on your phone and display a clear fire image
2. Hold it in front of the camera
3. Watch detections:

```bash
ros2 topic echo /detection
```

You should see:

```
detected: true
confidence: 0.85
x_center: 0.52
label: Fire
...
```

### Watch the state machine react

```bash
# In one terminal, watch the state:
ros2 topic echo /firebot/state

# In another terminal, trigger an alarm:
ros2 topic pub --once /alarm/trigger std_msgs/msg/Bool "data: true"
```

The brain will go `IDLE -> SEARCHING` and if it sees fire, it will proceed through the full state machine. Without motors it won't physically move, but you can see the `/cmd_vel` commands it would send:

```bash
ros2 topic echo /cmd_vel
```

## 7. Run in Background

Once everything is working:

```bash
# Stop the foreground session (Ctrl+C), then:
docker compose -f docker/docker-compose.yml up -d

# View logs anytime:
docker compose -f docker/docker-compose.yml logs -f

# Stop:
docker compose -f docker/docker-compose.yml down
```

## 8. Adding Arduino Later

When you're ready to connect the Arduino Uno:

1. Upload the sketch (see [Arduino Setup](ARDUINO_SETUP.md))
2. Connect Arduino to Pi via USB
3. Verify the serial port:

```bash
ls /dev/ttyACM* /dev/ttyUSB*
```

4. If the port is `/dev/ttyUSB0` instead of `/dev/ttyACM0`, update `firebot_ws/src/firebot/config/firebot_params.yaml`
5. Add your user to the dialout group:

```bash
sudo usermod -aG dialout $USER
# Log out and back in
```

6. Restart the container:

```bash
docker compose -f docker/docker-compose.yml down
docker compose -f docker/docker-compose.yml up -d
```

## 9. Auto-Start on Boot (Optional)

The `restart: unless-stopped` policy in `docker-compose.yml` handles restarts after the first manual start. For fully automatic startup on power-on:

```bash
sudo tee /etc/systemd/system/firebot.service > /dev/null << 'EOF'
[Unit]
Description=FireBot Docker Service
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/your_username/FireBot
ExecStart=/usr/bin/docker compose -f docker/docker-compose.yml up -d
ExecStop=/usr/bin/docker compose -f docker/docker-compose.yml down

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable firebot.service
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Camera not detected in Docker (CSI camera) | 1) Confirm Picamera2 can be imported inside the container: `docker exec -it <container> python3 -c "from picamera2 import Picamera2; print('ok')"` 2) Confirm media nodes exist on the Pi: `ls /dev/media* /dev/v4l-subdev*` 3) If your Pi uses different numbering, update `docker/docker-compose.yml` device mappings to match, then rebuild and restart. |
| IMX477 not recognized | Should be auto-detected by libcamera. Try `libcamera-hello --list-cameras` |
| Docker build fails on ARM | Ensure you're using 64-bit Raspberry Pi OS |
| Out of disk space | Use a larger SD card (32GB+) or clean Docker: `docker system prune` |
| YOLO model not found | Model is baked into the image. If missing, rebuild: `docker compose build --no-cache` |
| `/dev/ttyACM0` missing | Arduino not connected -- expected for camera-only testing |
| Serial permission denied | `sudo usermod -aG dialout $USER` then log out/in |
| Pi overheating during YOLO | Add a heatsink/fan. The Pi 5 active cooler is strongly recommended |
| Slow inference | YOLOv8s runs ~3-5 FPS on Pi 5 CPU. This is normal and sufficient for fire detection |
