# YOLO Fire Detection Model Guide

How to obtain and use a YOLO model for fire and smoke detection with FireBot.

## Selected Model

FireBot uses the pre-trained YOLOv8 fire and smoke detection model from
[Abonia1/YOLOv8-Fire-and-Smoke-Detection](https://github.com/Abonia1/YOLOv8-Fire-and-Smoke-Detection).

| Property | Value |
|----------|-------|
| Base architecture | YOLOv8s (small) |
| File size | ~21 MB |
| Classes | `Fire` (0), `default` (1), `smoke` (2) |
| Dataset | Roboflow fire-wrpgm v8 (CC BY 4.0) |
| Task | Object detection |

The model was trained on a Roboflow-annotated dataset of fire and smoke images and detects both fire and smoke in real-time video frames.

## Download the Model

The trained weights file should be placed at `models/fire_model.pt`.

### Option A: Direct download (recommended)

```bash
# From the FireBot project root:
curl -L -o models/fire_model.pt \
  https://github.com/Abonia1/YOLOv8-Fire-and-Smoke-Detection/raw/main/runs/detect/train/weights/best.pt
```

On Windows (PowerShell):

```powershell
Invoke-WebRequest -Uri "https://github.com/Abonia1/YOLOv8-Fire-and-Smoke-Detection/raw/main/runs/detect/train/weights/best.pt" -OutFile "models/fire_model.pt"
```

### Option B: Clone the full repo

```bash
git clone https://github.com/Abonia1/YOLOv8-Fire-and-Smoke-Detection.git
cp YOLOv8-Fire-and-Smoke-Detection/runs/detect/train/weights/best.pt models/fire_model.pt
```

## Verify the Model

Test that the model loads correctly (inside Docker):

```bash
docker run --rm -v ./models:/models docker-firebot-dev \
  python3 -c "from ultralytics import YOLO; m = YOLO('/models/fire_model.pt'); print('Classes:', m.names)"
```

Expected output:

```
Classes: {0: 'Fire', 1: 'default', 2: 'smoke'}
```

## How It Integrates with FireBot

1. The `fire_detector_node` loads the model at startup from the path specified in `firebot_params.yaml`
2. Each camera frame is passed through the model
3. The highest-confidence detection is published on the `/detection` topic as a `FireDetection` message
4. The `brain_node` reacts to any detection where `detected == True` and `confidence >= threshold`
5. The class label (`Fire`, `default`, or `smoke`) is included in the message but the brain treats all classes equally -- any detection above the confidence threshold triggers the response

## Configuration

In `firebot_ws/src/firebot/config/firebot_params.yaml`:

```yaml
fire_detector_node:
  ros__parameters:
    model_path: "/models/fire_model.pt"
    confidence_threshold: 0.6    # Lower = more sensitive, higher = fewer false positives
    detection_fps: 2.0           # Frames per second (IDLE state)
```

## Testing Without a Fire

To test the full detection pipeline without an actual fire:

1. Display a fire image or video on a phone/monitor
2. Point the camera at the screen
3. The detector should pick up the fire with high confidence

Or use the simulation publisher to inject fake detections:

```bash
ros2 run firebot sim_publisher
```

## Retraining or Fine-tuning (Optional)

If you want to improve detection for your specific environment:

1. Collect images of your room/garage (with and without fire)
2. Annotate with [Roboflow](https://roboflow.com/) (free tier available)
3. Export in YOLOv8 format
4. Fine-tune:

```bash
pip install ultralytics
yolo detect train model=models/fire_model.pt data=your_data.yaml epochs=25 imgsz=640
cp runs/detect/train/weights/best.pt models/fire_model.pt
```

This starts from the existing fire-trained weights so it converges faster than training from scratch.

## Model Performance on Raspberry Pi 5

Expected inference speeds on Pi 5 (no GPU, CPU-only):

| Model | Size | Speed (Pi 5) | Use case |
|-------|------|-------------|----------|
| YOLOv8n (nano) | 6 MB | ~80-120ms (~8-12 FPS) | Fastest, good accuracy |
| **YOLOv8s (small)** | **21 MB** | **~200-300ms (~3-5 FPS)** | **Current model -- good balance** |
| YOLOv8m (medium) | 50 MB | ~500-800ms (~1-2 FPS) | Best accuracy, too slow |

The current model (YOLOv8s) runs at approximately 3-5 FPS on the Pi 5, which is adequate for fire detection since fires don't appear and disappear rapidly. If you need faster inference, retrain using YOLOv8n as the base:

```bash
yolo detect train model=yolov8n.pt data=datasets/fire-8/data.yaml epochs=50 imgsz=640
```

## Alternative Fire Detection Models

If the Abonia1 model doesn't meet your needs:

| Repository | Model | Notes |
|-----------|-------|-------|
| [gaiasd/DFireDataset](https://github.com/gaiasd/DFireDataset) | YOLOv5/v8 | D-Fire dataset (21,000+ images) |
| [spacewalk01/yolov8-fire-detection](https://github.com/spacewalk01/yolov8-fire-detection) | YOLOv8 | Ready weights |
| [Roboflow Universe](https://universe.roboflow.com/search?q=fire+smoke) | Various | Many datasets with pre-trained models |
