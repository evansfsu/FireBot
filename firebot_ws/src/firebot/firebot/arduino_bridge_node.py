"""Arduino bridge node: serial communication between ROS2 and Arduino Uno."""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32
from geometry_msgs.msg import Twist

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


class ArduinoBridgeNode(Node):

    def __init__(self):
        super().__init__('arduino_bridge_node')

        self.declare_parameter('serial_port', '/dev/ttyACM0')
        self.declare_parameter('baud_rate', 115200)
        self.declare_parameter('sensor_poll_hz', 10.0)

        port = self.get_parameter('serial_port').value
        baud = self.get_parameter('baud_rate').value
        poll_hz = self.get_parameter('sensor_poll_hz').value

        # Publishers for sensor data
        self.ultra_pub = self.create_publisher(Int32, '/sensors/ultrasonic', 10)
        self.audio_pub = self.create_publisher(Int32, '/sensors/audio', 10)

        # Subscribers for commands
        self.create_subscription(Twist, '/cmd_vel', self._cmd_vel_cb, 10)
        self.create_subscription(Int32, '/extinguisher/cmd', self._ext_cb, 10)
        self.create_subscription(Int32, '/warning/cmd', self._warn_cb, 10)

        # Serial connection
        self.ser = None
        if SERIAL_AVAILABLE:
            try:
                self.ser = serial.Serial(port, baud, timeout=0.05)
                self.get_logger().info(f'Serial opened: {port} @ {baud}')
            except serial.SerialException as e:
                self.get_logger().warn(f'Serial open failed: {e}')
        else:
            self.get_logger().warn('pyserial not installed -- running without Arduino')

        # Poll sensors
        period = 1.0 / max(poll_hz, 0.1)
        self.poll_timer = self.create_timer(period, self._poll_sensors)
        self.get_logger().info('Arduino bridge node started')

    def _send(self, cmd: str):
        if self.ser and self.ser.is_open:
            try:
                self.ser.write((cmd + '\n').encode('ascii'))
            except Exception as e:
                self.get_logger().error(f'Serial write error: {e}')

    def _cmd_vel_cb(self, msg: Twist):
        vx = int(msg.linear.x)
        vy = 0
        wz = int(msg.angular.z * 100)
        self._send(f'M,{vx},{vy},{wz}')

    def _ext_cb(self, msg: Int32):
        self._send(f'E,{msg.data}')

    def _warn_cb(self, msg: Int32):
        self._send(f'W,{msg.data}')

    def _poll_sensors(self):
        self._send('S')
        if self.ser is None or not self.ser.is_open:
            return

        try:
            line = self.ser.readline().decode('ascii', errors='ignore').strip()
        except Exception:
            return

        if not line.startswith('D,'):
            return

        parts = line.split(',')
        if len(parts) < 3:
            return

        try:
            dist = int(parts[1])
            audio = int(parts[2])
        except ValueError:
            return

        dist_msg = Int32()
        dist_msg.data = dist
        self.ultra_pub.publish(dist_msg)

        audio_msg = Int32()
        audio_msg.data = audio
        self.audio_pub.publish(audio_msg)

    def destroy_node(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ArduinoBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
