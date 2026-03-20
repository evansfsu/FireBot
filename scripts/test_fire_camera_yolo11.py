"""Manual camera + YOLO11 smoke/fire detection test (Pi host script).

This is intended to run on the Raspberry Pi host (not necessarily inside Docker),
because it uses a display window via OpenCV. It mirrors the script described in
`changes.md` and is useful for verifying:
- Picamera2 works with your CSI camera (e.g., OV5647)
- The YOLO11 model loads and produces detections
- Basic performance (display FPS and inference FPS)

Usage (on Raspberry Pi):
  python3 scripts/test_fire_camera_yolo11.py --model models/best_small.pt
  # Press 'q' to quit
"""

import argparse
import time

import cv2

try:
    from picamera2 import Picamera2
except ImportError as e:  # pragma: no cover
    raise SystemExit(
        "Picamera2 is not installed. On Raspberry Pi OS, install it with:\n"
        "  sudo apt update && sudo apt install -y python3-picamera2\n"
        "Then re-run this script."
    ) from e

try:
    from ultralytics import YOLO
except ImportError as e:  # pragma: no cover
    raise SystemExit(
        "ultralytics is not installed. Install it with:\n"
        "  pip install ultralytics\n"
        "Then re-run this script."
    ) from e


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="models/best_small.pt", help="Path to YOLO11 .pt weights")
    p.add_argument("--conf", type=float, default=0.20, help="Confidence threshold")
    p.add_argument("--imgsz", type=int, default=512, help="Inference image size")
    p.add_argument("--max-det", type=int, default=3, help="Max detections per frame")
    p.add_argument("--infer-every", type=int, default=3, help="Run inference every N frames")
    p.add_argument("--display-fps", type=float, default=10.0, help="Target display FPS")
    p.add_argument("--width", type=int, default=1920, help="Camera capture width")
    p.add_argument("--height", type=int, default=1080, help="Camera capture height")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    model = YOLO(args.model)

    picam2 = Picamera2()
    config = picam2.create_video_configuration(
        main={"size": (args.width, args.height), "format": "RGB888"}
    )
    picam2.configure(config)
    picam2.start()
    time.sleep(2)

    frame_count = 0
    last_result = None
    last_annotated = None
    last_infer_fps = 0.0

    display_frames = 0
    display_fps = 0.0
    last_display_time = time.time()
    frame_interval = 1.0 / max(args.display_fps, 1.0)

    try:
        while True:
            loop_start = time.time()

            frame = picam2.capture_array()
            frame_count += 1

            if frame_count % args.infer_every == 0 or last_result is None:
                t0 = time.time()
                results = model.predict(
                    source=frame,
                    imgsz=args.imgsz,
                    conf=args.conf,
                    max_det=args.max_det,
                    verbose=False,
                    device="cpu",
                )
                infer_dt = time.time() - t0
                last_infer_fps = 1.0 / infer_dt if infer_dt > 0 else 0.0
                last_result = results[0]
                last_annotated = last_result.plot()

            shown = last_annotated.copy() if last_annotated is not None else frame.copy()
            n = 0 if last_result is None or last_result.boxes is None else len(last_result.boxes)

            cv2.putText(
                shown,
                f"Display FPS: {display_fps:.1f}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (255, 0, 0),
                2,
            )
            cv2.putText(
                shown,
                f"Infer FPS: {last_infer_fps:.1f}",
                (20, 80),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (255, 0, 0),
                2,
            )
            cv2.putText(
                shown,
                f"Detections: {n}",
                (20, 120),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (255, 0, 0),
                2,
            )

            cv2.imshow("YOLO11 Fire/Smoke Detection", shown)
            if (cv2.waitKey(1) & 0xFF) == ord("q"):
                break

            display_frames += 1
            now = time.time()
            if now - last_display_time >= 1.0:
                display_fps = display_frames / (now - last_display_time)
                display_frames = 0
                last_display_time = now

            elapsed = time.time() - loop_start
            if frame_interval > elapsed:
                time.sleep(frame_interval - elapsed)
    finally:
        picam2.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

