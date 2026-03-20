"""Brain node: state machine controlling FireBot behavior."""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, Int32, String
from geometry_msgs.msg import Twist
from firebot_interfaces.msg import FireDetection


class State:
    IDLE = 'IDLE'
    WAITING_FOR_ALARM = 'WAITING_FOR_ALARM'
    SEARCHING = 'SEARCHING'
    WAITING_FOR_USER_CONFIRMATION = 'WAITING_FOR_USER_CONFIRMATION'
    APPROACHING = 'APPROACHING'
    WARNING = 'WARNING'
    EXTINGUISHING = 'EXTINGUISHING'
    COMPLETE = 'COMPLETE'


class BrainNode(Node):

    def __init__(self):
        super().__init__('brain_node')

        # Parameters
        self.declare_parameter('confidence_threshold', 0.6)
        self.declare_parameter('fire_label', 'Fire')
        self.declare_parameter('vision_trigger_confidence', 0.6)
        self.declare_parameter('vision_trigger_duration_sec', 10.0)
        self.declare_parameter('alarm_wait_timeout_sec', 30.0)
        self.declare_parameter('user_confirmation_timeout_sec', 30.0)
        self.declare_parameter('centering_tolerance', 0.05)
        self.declare_parameter('approach_distance_cm', 50.0)
        self.declare_parameter('rotation_speed', 0.5)
        self.declare_parameter('drive_speed', 80.0)
        self.declare_parameter('search_timeout_sec', 30.0)
        self.declare_parameter('warning_countdown_sec', 5)
        self.declare_parameter('discharge_duration_sec', 8.0)

        self.conf_threshold = self.get_parameter('confidence_threshold').value
        self.fire_label = str(self.get_parameter('fire_label').value)
        self.vision_trigger_conf = float(self.get_parameter('vision_trigger_confidence').value)
        self.vision_trigger_duration = float(self.get_parameter('vision_trigger_duration_sec').value)
        self.alarm_wait_timeout = float(self.get_parameter('alarm_wait_timeout_sec').value)
        self.user_confirm_timeout = float(self.get_parameter('user_confirmation_timeout_sec').value)
        self.center_tol = self.get_parameter('centering_tolerance').value
        self.approach_dist = self.get_parameter('approach_distance_cm').value
        self.rot_speed = self.get_parameter('rotation_speed').value
        self.drive_speed = self.get_parameter('drive_speed').value
        self.search_timeout = self.get_parameter('search_timeout_sec').value
        self.warning_secs = self.get_parameter('warning_countdown_sec').value
        self.discharge_duration = self.get_parameter('discharge_duration_sec').value

        # Publishers
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.ext_cmd_pub = self.create_publisher(Int32, '/extinguisher/cmd', 10)
        self.warn_cmd_pub = self.create_publisher(Int32, '/warning/cmd', 10)
        self.state_pub = self.create_publisher(String, '/firebot/state', 10)
        self.countdown_pub = self.create_publisher(Int32, '/firebot/warning_countdown', 10)

        # Subscribers
        self.create_subscription(FireDetection, '/detection', self._detection_cb, 10)
        self.create_subscription(Bool, '/alarm/trigger', self._alarm_cb, 10)
        self.create_subscription(Bool, '/user/fire_confirm', self._user_confirm_cb, 10)
        self.create_subscription(Int32, '/sensors/ultrasonic', self._ultrasonic_cb, 10)

        # State
        self.state = State.IDLE
        self.latest_detection = FireDetection()
        self.ultrasonic_cm = 999.0
        self.state_enter_time = self.get_clock().now()
        self.warning_remaining = 0

        # Confirmation variables (reset on denial/timeout/complete)
        self.vision_confirmed = False
        self.alarm_confirmed = False
        self.user_confirmed = False
        self.vision_hold_start = None  # rclpy.time.Time | None
        self._last_user_confirm = None  # bool | None

        # Main loop at 10 Hz
        self.timer = self.create_timer(0.1, self._loop)
        self.get_logger().info('Brain node started -- state: IDLE')

    def _set_state(self, new_state):
        if new_state != self.state:
            self.get_logger().info(f'State: {self.state} -> {new_state}')
            self.state = new_state
            self.state_enter_time = self.get_clock().now()

    def _time_in_state(self):
        return (self.get_clock().now() - self.state_enter_time).nanoseconds / 1e9

    def _detection_cb(self, msg):
        self.latest_detection = msg

    def _alarm_cb(self, msg):
        if msg.data:
            self.alarm_confirmed = True
            if self.state == State.IDLE:
                self.get_logger().warn('Alarm trigger received!')
                self._set_state(State.SEARCHING)
            elif self.state == State.WAITING_FOR_ALARM:
                self.get_logger().warn('Alarm received after vision confirmation')
                self._set_state(State.SEARCHING)

    def _user_confirm_cb(self, msg):
        # true => confirm, false => deny/reset
        self._last_user_confirm = bool(msg.data)
        if msg.data:
            self.user_confirmed = True
        else:
            self.user_confirmed = False

    def _ultrasonic_cb(self, msg):
        self.ultrasonic_cm = float(msg.data)

    def _publish_twist(self, linear_x=0.0, angular_z=0.0):
        twist = Twist()
        twist.linear.x = linear_x
        twist.angular.z = angular_z
        self.cmd_vel_pub.publish(twist)

    def _publish_extinguisher(self, action):
        msg = Int32()
        msg.data = action
        self.ext_cmd_pub.publish(msg)

    def _publish_warning(self, state):
        msg = Int32()
        msg.data = state
        self.warn_cmd_pub.publish(msg)

    def _stop_motors(self):
        self._publish_twist(0.0, 0.0)

    def _loop(self):
        # Publish current state
        state_msg = String()
        state_msg.data = self.state
        self.state_pub.publish(state_msg)

        if self.state == State.IDLE:
            self._handle_idle()
        elif self.state == State.WAITING_FOR_ALARM:
            self._handle_waiting_for_alarm()
        elif self.state == State.SEARCHING:
            self._handle_searching()
        elif self.state == State.WAITING_FOR_USER_CONFIRMATION:
            self._handle_waiting_for_user_confirmation()
        elif self.state == State.APPROACHING:
            self._handle_approaching()
        elif self.state == State.WARNING:
            self._handle_warning()
        elif self.state == State.EXTINGUISHING:
            self._handle_extinguishing()
        elif self.state == State.COMPLETE:
            self._handle_complete()

    def _reset_confirmations(self):
        self.vision_confirmed = False
        self.alarm_confirmed = False
        self.user_confirmed = False
        self.vision_hold_start = None
        self._last_user_confirm = None

    def _is_fire_detection(self, det: FireDetection) -> bool:
        if not det.detected:
            return False
        if det.confidence < self.vision_trigger_conf:
            return False
        return str(det.label).strip().lower() == self.fire_label.strip().lower()

    def _handle_idle(self):
        det = self.latest_detection
        # Alarm can immediately start searching.
        # Vision-only requires sustained detection, then we wait for alarm confirmation.
        if self._is_fire_detection(det):
            now = self.get_clock().now()
            if self.vision_hold_start is None:
                self.vision_hold_start = now
                self.get_logger().warn('Fire abnormality detected; checking fire alarm confirmation...')
                return
            held_for = (now - self.vision_hold_start).nanoseconds / 1e9
            if held_for >= self.vision_trigger_duration:
                self.vision_confirmed = True
                self.get_logger().warn(
                    f'Vision confirmed (held {held_for:.1f}s) — waiting for alarm trigger'
                )
                self._set_state(State.WAITING_FOR_ALARM)
        else:
            self.vision_hold_start = None

    def _handle_waiting_for_alarm(self):
        self._stop_motors()

        if self._last_user_confirm is False:
            self.get_logger().warn('User denied fire — resetting to IDLE')
            self._reset_confirmations()
            self._set_state(State.IDLE)
            return

        if self.alarm_confirmed:
            self.get_logger().info('Alarm confirmed — starting SEARCHING')
            self._set_state(State.SEARCHING)
            return

        if self._time_in_state() > self.alarm_wait_timeout:
            self.get_logger().info('Alarm wait timeout — resetting to IDLE')
            self._reset_confirmations()
            self._set_state(State.IDLE)

    def _handle_searching(self):
        det = self.latest_detection

        if self._time_in_state() > self.search_timeout:
            self.get_logger().info('Search timeout -- returning to IDLE')
            self._stop_motors()
            self._reset_confirmations()
            self._set_state(State.IDLE)
            return

        if det.detected and det.confidence >= self.conf_threshold:
            error = det.x_center - 0.5
            if abs(error) < self.center_tol:
                self.get_logger().info('Fire centered -- waiting for user confirmation')
                self._stop_motors()
                self._set_state(State.WAITING_FOR_USER_CONFIRMATION)
                return
            # Rotate toward fire: negative error = fire is left, rotate left (positive angular)
            direction = -1.0 if error > 0 else 1.0
            self._publish_twist(angular_z=direction * self.rot_speed)
        else:
            # No detection yet -- keep rotating to scan
            self._publish_twist(angular_z=self.rot_speed)

    def _handle_waiting_for_user_confirmation(self):
        self._stop_motors()

        if self._last_user_confirm is False:
            self.get_logger().warn('User denied fire — resetting to IDLE')
            self._reset_confirmations()
            self._set_state(State.IDLE)
            return

        if self.user_confirmed:
            self.get_logger().warn('User confirmed fire — proceeding to APPROACHING')
            self._set_state(State.APPROACHING)
            return

        if self._time_in_state() > self.user_confirm_timeout:
            self.get_logger().info('User confirmation timeout — resetting to IDLE')
            self._reset_confirmations()
            self._set_state(State.IDLE)

    def _handle_approaching(self):
        if self.ultrasonic_cm <= self.approach_dist:
            self.get_logger().info(
                f'Close enough ({self.ultrasonic_cm:.0f} cm) -- starting warning'
            )
            self._stop_motors()
            self.warning_remaining = self.warning_secs
            self._set_state(State.WARNING)
            return

        det = self.latest_detection
        if det.detected and det.confidence >= self.conf_threshold:
            error = det.x_center - 0.5
            correction = -error * self.rot_speed * 2.0
            self._publish_twist(linear_x=self.drive_speed, angular_z=correction)
        else:
            self._publish_twist(linear_x=self.drive_speed)

    def _handle_warning(self):
        self._stop_motors()
        self._publish_warning(1)

        elapsed = self._time_in_state()
        remaining = max(0, self.warning_secs - int(elapsed))

        countdown_msg = Int32()
        countdown_msg.data = remaining
        self.countdown_pub.publish(countdown_msg)

        if remaining != self.warning_remaining:
            self.warning_remaining = remaining
            self.get_logger().warn(
                f'WARNING: Fire extinguisher activating in {remaining} seconds!'
            )

        if elapsed >= self.warning_secs:
            self.get_logger().warn('Countdown complete -- activating extinguisher!')
            self._set_state(State.EXTINGUISHING)

    def _handle_extinguishing(self):
        self._publish_warning(2)

        elapsed = self._time_in_state()

        # Phase 1: pull pin (first 2 seconds)
        if elapsed < 2.0:
            self._publish_extinguisher(1)
        # Phase 2: discharge
        elif elapsed < self.discharge_duration:
            self._publish_extinguisher(2)
        else:
            self._publish_extinguisher(3)  # stop
            self.get_logger().info('Discharge complete')
            self._set_state(State.COMPLETE)

    def _handle_complete(self):
        self._stop_motors()
        self._publish_extinguisher(0)
        self._publish_warning(0)
        # Clear stale detection so we don't immediately re-trigger
        self.latest_detection = FireDetection()
        self._reset_confirmations()

        if self._time_in_state() > 3.0:
            self.get_logger().info('Returning to IDLE')
            self._set_state(State.IDLE)


def main(args=None):
    rclpy.init(args=args)
    node = BrainNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
