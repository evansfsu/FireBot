"""Simulation publisher: generates fake fire detections and sensor data.

Run inside the Docker container alongside the real nodes to drive the
brain_node through its full state machine without any hardware.

Usage:
    ros2 run firebot sim_publisher
    # or directly:
    python3 sim_publisher.py
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, Int32
from firebot_interfaces.msg import FireDetection
import math
import time


class SimPublisher(Node):

    def __init__(self):
        super().__init__('sim_publisher')

        self.declare_parameter('scenario', 'full')  # 'full', 'alarm', 'detection'
        self.declare_parameter('vision_hold_sec', 10.5)

        self.det_pub = self.create_publisher(FireDetection, '/detection', 10)
        self.alarm_pub = self.create_publisher(Bool, '/alarm/trigger', 10)
        self.user_pub = self.create_publisher(Bool, '/user/fire_confirm', 10)
        self.ultra_pub = self.create_publisher(Int32, '/sensors/ultrasonic', 10)
        self.audio_pub = self.create_publisher(Int32, '/sensors/audio', 10)

        self.state_sub = self.create_subscription(
            rclpy.node.String if False else __import__('std_msgs.msg', fromlist=['String']).String,
            '/firebot/state', self._state_cb, 10
        )

        self.current_state = 'IDLE'
        self.start_time = time.time()
        self.scenario = self.get_parameter('scenario').value
        self.vision_hold_sec = float(self.get_parameter('vision_hold_sec').value)
        self.phase = 0

        self.timer = self.create_timer(0.5, self._tick)
        self.get_logger().info(f'Simulation publisher started (scenario: {self.scenario})')
        self.get_logger().info('Phase 0: Waiting 3 seconds before triggering...')

    def _state_cb(self, msg):
        if msg.data != self.current_state:
            self.get_logger().info(f'  [brain state changed] {self.current_state} -> {msg.data}')
            self.current_state = msg.data

    def _elapsed(self):
        return time.time() - self.start_time

    def _tick(self):
        elapsed = self._elapsed()

        # Phase 0: Wait 3 seconds, then start publishing sustained Fire detections
        if self.phase == 0:
            self._publish_sensors(200, 100)
            if elapsed > 3.0:
                self.phase = 1
                self.start_time = time.time()
                if self.scenario == 'alarm':
                    self.get_logger().info('Phase 1: Sending alarm trigger')
                    alarm = Bool()
                    alarm.data = True
                    self.alarm_pub.publish(alarm)
                else:
                    self.get_logger().info(
                        f'Phase 1: Publishing sustained Fire detection for {self.vision_hold_sec:.1f}s'
                    )

        # Phase 1: Sustained Fire detection (brain should transition IDLE -> WAITING_FOR_ALARM)
        elif self.phase == 1:
            self._publish_detection(True, 0.82, 0.8, 0.5, 'Fire')
            self._publish_sensors(200, 100)
            if self.current_state == 'WAITING_FOR_ALARM' or elapsed > self.vision_hold_sec:
                self.phase = 2
                self.start_time = time.time()
                self.get_logger().info('Phase 2: Sending alarm trigger (should start SEARCHING)')
                alarm = Bool()
                alarm.data = True
                self.alarm_pub.publish(alarm)

        # Phase 2: Searching; center fire and wait for user confirmation gate
        elif self.phase == 2:
            # Keep fire visible and centered so brain moves SEARCHING -> WAITING_FOR_USER_CONFIRMATION
            self._publish_detection(True, 0.90, 0.50, 0.5, 'Fire')
            self._publish_sensors(200, 300)
            if self.current_state == 'WAITING_FOR_USER_CONFIRMATION' or elapsed > 6.0:
                self.phase = 3
                self.start_time = time.time()
                self.get_logger().info('Phase 3: Publishing user confirmation true (should APPROACH)')
                u = Bool()
                u.data = True
                self.user_pub.publish(u)

        # Phase 3: Approaching; decrease ultrasonic until close enough
        elif self.phase == 3:
            self._publish_detection(True, 0.95, 0.50, 0.5, 'Fire')
            dist = max(40, int(200 - elapsed * 30))
            self._publish_sensors(dist, 500)
            if dist <= 50 or elapsed > 6.0:
                self.phase = 4
                self.start_time = time.time()
                self.get_logger().info(
                    f'Phase 4: Close enough ({dist}cm) -- brain should WARNING then EXTINGUISH'
                )

        # Phase 4: Let brain run WARNING countdown + EXTINGUISHING
        elif self.phase == 4:
            self._publish_detection(True, 0.95, 0.50, 0.5, 'Fire')
            self._publish_sensors(40, 500)
            if elapsed > 25.0 or self.current_state == 'COMPLETE':
                self.phase = 5
                self.start_time = time.time()
                self.get_logger().info('Phase 5: Scenario complete -- returning to idle publishing')

        # Phase 5: Done -- publish no-fire, normal sensors
        elif self.phase == 5:
            self._publish_detection(False, 0.0, 0.0, 0.0, '')
            self._publish_sensors(200, 100)
            if elapsed > 5.0:
                self.get_logger().info('Simulation finished. Shutting down.')
                raise SystemExit(0)

    def _publish_detection(self, detected, confidence, x_center, y_center, label):
        msg = FireDetection()
        msg.detected = detected
        msg.confidence = confidence
        msg.x_center = x_center
        msg.y_center = y_center
        msg.bbox_width = 0.15
        msg.bbox_height = 0.15
        msg.label = label
        self.det_pub.publish(msg)

    def _publish_sensors(self, distance_cm, audio_raw):
        d = Int32()
        d.data = distance_cm
        self.ultra_pub.publish(d)

        a = Int32()
        a.data = audio_raw
        self.audio_pub.publish(a)


def main(args=None):
    rclpy.init(args=args)
    node = SimPublisher()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
