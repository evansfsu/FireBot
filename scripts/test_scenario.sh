#!/bin/bash
# Full scenario test -- watches all FireBot topics while the sim_publisher
# drives the brain_node through every state.
# Run inside the Docker container.

set -e

source /opt/ros/humble/setup.bash
source /firebot_ws/install/setup.bash 2>/dev/null || true

echo "========================================="
echo "  FireBot Full Scenario Test"
echo "========================================="
echo ""
echo "This script monitors key topics while"
echo "the simulation publisher runs a full"
echo "fire detection scenario."
echo ""
echo "Starting topic monitors in background..."
echo ""

# Monitor key topics in background
ros2 topic echo /firebot/state --no-arr &
PID_STATE=$!

ros2 topic echo /cmd_vel --no-arr &
PID_VEL=$!

ros2 topic echo /extinguisher/cmd --no-arr &
PID_EXT=$!

ros2 topic echo /firebot/warning_countdown --no-arr &
PID_WARN=$!

cleanup() {
    echo ""
    echo "Stopping monitors..."
    kill $PID_STATE $PID_VEL $PID_EXT $PID_WARN 2>/dev/null || true
}
trap cleanup EXIT

echo "Starting simulation publisher..."
echo "-----------------------------------------"
python3 /scripts/sim_publisher.py

echo ""
echo "========================================="
echo "  Scenario test complete!"
echo "========================================="
