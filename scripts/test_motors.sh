#!/bin/bash
# Motor test script -- sends individual motor commands via ROS2 topics.
# Run inside the Docker container with ROS2 sourced.
# Tests each direction and rotation one at a time.

set -e

source /opt/ros/humble/setup.bash
source /firebot_ws/install/setup.bash 2>/dev/null || true

SPEED=80
DURATION=2

echo "========================================="
echo "  FireBot Motor Test"
echo "========================================="
echo ""
echo "This will test each movement direction."
echo "Make sure arduino_bridge_node is running"
echo "and Arduino is connected."
echo ""
echo "Press Ctrl+C at any time to abort."
echo ""

stop_motors() {
    ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
        "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
}

trap stop_motors EXIT

echo "[1/5] Forward (${DURATION}s)..."
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
    "{linear: {x: ${SPEED}.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
sleep $DURATION
stop_motors
sleep 1

echo "[2/5] Backward (${DURATION}s)..."
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
    "{linear: {x: -${SPEED}.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
sleep $DURATION
stop_motors
sleep 1

echo "[3/5] Rotate left (${DURATION}s)..."
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
    "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.5}}"
sleep $DURATION
stop_motors
sleep 1

echo "[4/5] Rotate right (${DURATION}s)..."
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
    "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: -0.5}}"
sleep $DURATION
stop_motors
sleep 1

echo "[5/5] Warning buzzer test (2s)..."
ros2 topic pub --once /warning/cmd std_msgs/msg/Int32 "data: 1"
sleep 2
ros2 topic pub --once /warning/cmd std_msgs/msg/Int32 "data: 0"

echo ""
echo "========================================="
echo "  Motor test complete!"
echo "========================================="
