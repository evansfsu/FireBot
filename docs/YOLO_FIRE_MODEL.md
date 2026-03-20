# YOLO Fire Detection Model Guide

How to obtain and use a YOLO model for fire and smoke detection with FireBot.

## Selected Model (YOLO11 / YOLOv11)

FireBot uses the pre-trained YOLO11 model from
[sayedgamal99/Real-Time-Smoke-Fire-Detection-YOLO11](https://github.com/sayedgamal99/Real-Time-Smoke-Fire-Detection-YOLO11).

| Property | Value |
|----------|-------|
| Base architecture | YOLOv11 (Ultralytics) |
| Classes | `Fire`, `Smoke` |
| Recommended weights filename | `best_small.pt` |
| Dataset | Roboflow fire-smoke-detection-yolov11 |
| Task | Object detection |

FireBot is configured to **trigger only on `Fire`** detections (smoke alone will not arm the extinguisher flow).

## Download the Model

Place the weights file at `models/best_small.pt`.

### Option A: Direct download (recommended)

```bash
# From the FireBot project root:
curl -L -o models/best_small.pt \
  https://raw.githubusercontent.com/sayedgamal99/Real-Time-Smoke-Fire-Detection-YOLO11/main/models/kaggle%20developed%20models/best_small.pt
```

On Windows (PowerShell):

```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/sayedgamal99/Real-Time-Smoke-Fire-Detection-YOLO11/main/models/kaggle%20developed%20models/best_small.pt" -OutFile "models/best_small.pt"
```

### Option B: Clone the full repo

```bash
git clone https://github.com/sayedgamal99/Real-Time-Smoke-Fire-Detection-YOLO11.git
cp Real-Time-Smoke-Fire-Detection-YOLO11/models/kaggle\ developed\ models/best_small.pt models/best_small.pt
```

## Verify the Model

Test that the model loads correctly (inside Docker):

```bash
docker run --rm -v ./models:/models docker-firebot-dev \
  python3 -c "from ultralytics import YOLO; m = YOLO('/models/best_small.pt'); print('Classes:', m.names)"
```

Expected output:

```
Classes: {0: 'Fire', 1: 'Smoke'}
```

## How It Integrates with FireBot

1. The `fire_detector_node` loads the model at startup from the path specified in `firebot_params.yaml`
2. Each camera frame is passed through the model
3. The detector publishes `/detection` as a `FireDetection` message
4. FireBot is configured with `fire_only: true` so `/detection.detected == true` only when the model predicts the `Fire` class
5. The `brain_node` requires **three confirmations** before approaching/extinguishing:
   - sustained vision confirmation (`Fire`)
   - alarm confirmation (`/alarm/trigger`)
   - user confirmation (`/user/fire_confirm`)

## Configuration

In `firebot_ws/src/firebot/config/firebot_params.yaml`:

```yaml
fire_detector_node:
  ros__parameters:
    model_path: "/models/best_small.pt"
    confidence_threshold: 0.2
    inference_imgsz: 512
    fire_only: true
    fire_class_name: "Fire"
    detection_fps: 2.0
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
yolo detect train model=models/best_small.pt data=your_data.yaml epochs=25 imgsz=640
cp runs/detect/train/weights/best.pt models/best_small.pt
```

This starts from the existing fire-trained weights so it converges faster than training from scratch.

## Model Performance on Raspberry Pi 5

Expected inference speeds on Pi 5 (no GPU, CPU-only):

| Model | Size | Speed (Pi 5) | Use case |
|-------|------|-------------|----------|
| YOLOv8n (nano) | 6 MB | ~80-120ms (~8-12 FPS) | Fastest, good accuracy |
| **YOLOv11 nano** | **small** | **~5-12 FPS (varies)** | **Recommended for Pi** |
| YOLOv8m (medium) | 50 MB | ~500-800ms (~1-2 FPS) | Best accuracy, too slow |

Performance depends heavily on the model variant and whether you export to ONNX/TensorRT.
Start with the provided nano weights, then tune `imgsz` and `detection_fps` in `firebot_params.yaml`.

## Alternative Fire Detection Models

If the YOLO11 model doesn't meet your needs:

| Repository | Model | Notes |
|-----------|-------|-------|
| [gaiasd/DFireDataset](https://github.com/gaiasd/DFireDataset) | YOLOv5/v8 | D-Fire dataset (21,000+ images) |
| [spacewalk01/yolov8-fire-detection](https://github.com/spacewalk01/yolov8-fire-detection) | YOLOv8 | Ready weights |
| [Roboflow Universe](https://universe.roboflow.com/search?q=fire+smoke) | Various | Many datasets with pre-trained models |
