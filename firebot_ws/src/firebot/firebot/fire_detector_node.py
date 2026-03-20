"""Fire detection node: captures Pi Camera frames and runs YOLOv8 inference."""

import rclpy
from rclpy.node import Node
from firebot_interfaces.msg import FireDetection

try:
    from picamera2 import Picamera2
    PICAMERA_AVAILABLE = True
except ImportError:
    PICAMERA_AVAILABLE = False

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

import cv2
import numpy as np


class FireDetectorNode(Node):

    def __init__(self):
        super().__init__('fire_detector_node')

        self.declare_parameter('model_path', '/models/best_small.pt')
        self.declare_parameter('confidence_threshold', 0.6)
        self.declare_parameter('inference_imgsz', 512)
        self.declare_parameter('max_det', 3)
        self.declare_parameter('fire_only', True)
        self.declare_parameter('fire_class_name', 'Fire')
        self.declare_parameter('camera_width', 640)
        self.declare_parameter('camera_height', 480)
        self.declare_parameter('detection_fps', 2.0)

        self.model_path = self.get_parameter('model_path').value
        self.conf_threshold = self.get_parameter('confidence_threshold').value
        self.infer_imgsz = int(self.get_parameter('inference_imgsz').value)
        self.max_det = int(self.get_parameter('max_det').value)
        self.fire_only = bool(self.get_parameter('fire_only').value)
        self.fire_class_name = str(self.get_parameter('fire_class_name').value)
        self.cam_w = self.get_parameter('camera_width').value
        self.cam_h = self.get_parameter('camera_height').value
        self.det_fps = self.get_parameter('detection_fps').value

        self.publisher = self.create_publisher(FireDetection, '/detection', 10)

        self._init_camera()
        self._init_model()

        period = 1.0 / max(self.det_fps, 0.1)
        self.timer = self.create_timer(period, self._detect_callback)
        self.get_logger().info('Fire detector node started')

    def _init_camera(self):
        self.camera = None
        if PICAMERA_AVAILABLE:
            try:
                self.camera = Picamera2()
                config = self.camera.create_still_configuration(
                    main={'size': (self.cam_w, self.cam_h), 'format': 'RGB888'}
                )
                self.camera.configure(config)
                self.camera.start()
                self.get_logger().info('Pi Camera initialized')
            except Exception as e:
                self.get_logger().warn(f'Pi Camera init failed: {e}')
                self.camera = None
        else:
            self.get_logger().warn(
                'picamera2 not available -- attempting USB camera fallback'
            )
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                self.camera = cap
                self.get_logger().info('USB camera opened as fallback')
            else:
                cap.release()
                self.get_logger().warn('No camera available -- running without vision')

    def _init_model(self):
        self.model = None
        if YOLO_AVAILABLE:
            try:
                self.model = YOLO(self.model_path)
                self.get_logger().info(f'YOLO model loaded: {self.model_path}')
            except Exception as e:
                self.get_logger().warn(f'YOLO model load failed: {e}')
        else:
            self.get_logger().warn('ultralytics not installed -- detection disabled')

    def _capture_frame(self):
        if self.camera is None:
            return None
        if PICAMERA_AVAILABLE and isinstance(self.camera, Picamera2):
            return self.camera.capture_array()
        if isinstance(self.camera, cv2.VideoCapture):
            ret, frame = self.camera.read()
            return frame if ret else None
        return None

    def _detect_callback(self):
        frame = self._capture_frame()
        if frame is None or self.model is None:
            msg = FireDetection()
            msg.detected = False
            self.publisher.publish(msg)
            return

        results = self.model.predict(
            source=frame,
            imgsz=self.infer_imgsz,
            conf=self.conf_threshold,
            max_det=self.max_det,
            verbose=False,
            device='cpu',
        )

        best = None
        best_conf = 0.0

        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                label = self.model.names.get(cls_id, 'unknown')

                if self.fire_only and label.strip().lower() != self.fire_class_name.strip().lower():
                    continue

                if conf > best_conf:
                    best_conf = conf
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    best = {
                        'conf': conf,
                        'label': label,
                        'x1': x1, 'y1': y1,
                        'x2': x2, 'y2': y2,
                    }

        msg = FireDetection()
        if best is not None:
            h, w = frame.shape[:2]
            msg.detected = True
            msg.confidence = best['conf']
            msg.x_center = ((best['x1'] + best['x2']) / 2.0) / w
            msg.y_center = ((best['y1'] + best['y2']) / 2.0) / h
            msg.bbox_width = (best['x2'] - best['x1']) / w
            msg.bbox_height = (best['y2'] - best['y1']) / h
            msg.label = best['label']
        else:
            msg.detected = False

        self.publisher.publish(msg)

    def destroy_node(self):
        if self.camera is not None:
            if PICAMERA_AVAILABLE and isinstance(self.camera, Picamera2):
                self.camera.stop()
            elif isinstance(self.camera, cv2.VideoCapture):
                self.camera.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = FireDetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
