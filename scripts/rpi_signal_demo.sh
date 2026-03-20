#!/bin/bash
# Raspberry Pi CLI demo for FireBot confirmation/state transitions.
# Run this INSIDE the running FireBot container:
#   docker exec -it <container_name> bash
#   source /opt/ros/humble/setup.bash && source /firebot_ws/install/setup.bash
#   bash /firebot_ws/src/../../scripts/rpi_signal_demo.sh

set -e

echo "========================================="
echo " FireBot RPi CLI Signal Demo"
echo "========================================="
echo ""
echo "Open 2 extra terminals and run:"
echo "  1) ros2 topic echo /firebot/state"
echo "  2) ros2 topic echo /firebot/status_message"
echo ""
echo "This demo publishes alarm + user confirm/deny topics."
echo ""

echo "[1/5] Trigger alarm -> should enter SEARCHING"
ros2 topic pub --once /alarm/trigger std_msgs/msg/Bool "data: true"
sleep 2

echo "[2/5] User DENY -> should reset to IDLE when waiting for confirmation"
ros2 topic pub --once /user/fire_confirm std_msgs/msg/Bool "data: false"
sleep 2

echo "[3/5] Trigger alarm again"
ros2 topic pub --once /alarm/trigger std_msgs/msg/Bool "data: true"
sleep 2

echo "[4/5] User CONFIRM -> allows APPROACHING when centered"
ros2 topic pub --once /user/fire_confirm std_msgs/msg/Bool "data: true"
sleep 2

echo "[5/5] User DENY (manual reset path)"
ros2 topic pub --once /user/fire_confirm std_msgs/msg/Bool "data: false"
sleep 1

echo ""
echo "Demo signals sent."
echo "If sim_publisher or real detection is active, you should see state transitions."
echo ""
