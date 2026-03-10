#!/bin/bash
# Comprehensive FireBot Docker test -- exercises every node and topic
# without any hardware connected.
exec 2>&1
set -o pipefail

source /opt/ros/humble/setup.bash
source /firebot_ws/install/setup.bash

echo "============================================="
echo "  FireBot Comprehensive Docker Test"
echo "============================================="
echo ""

# ── Test 1: Launch all 3 nodes ──
echo "[TEST 1] Launching all nodes..."
ros2 launch firebot firebot.launch.py &
LAUNCH_PID=$!
sleep 8
echo "  Launch PID: $LAUNCH_PID"
echo ""

# ── Test 2: Verify all nodes are running ──
echo "[TEST 2] Active ROS2 Nodes:"
ros2 node list
echo ""

# ── Test 3: Verify all topics are advertised ──
echo "[TEST 3] Active ROS2 Topics:"
ros2 topic list
echo ""

# ── Test 4: Check topic types ──
echo "[TEST 4] Topic Details:"
TOPICS="/detection /cmd_vel /extinguisher/cmd /warning/cmd /firebot/state /firebot/warning_countdown /sensors/ultrasonic /sensors/audio /alarm/trigger"
for t in $TOPICS; do
    info=$(ros2 topic info $t 2>/dev/null)
    if [ -n "$info" ]; then
        type=$(echo "$info" | head -1)
        pubs=$(echo "$info" | grep "Publisher" | head -1)
        subs=$(echo "$info" | grep "Subscriber" | head -1)
        echo "  $t -- $type | $pubs | $subs"
    else
        echo "  $t -- NOT FOUND (expected if no publisher yet)"
    fi
done
echo ""

# ── Test 5: Check parameters loaded from YAML ──
echo "[TEST 5] Parameters Loaded:"
echo "  brain_node:"
ros2 param get /brain_node confidence_threshold 2>/dev/null && \
ros2 param get /brain_node warning_countdown_sec 2>/dev/null && \
ros2 param get /brain_node approach_distance_cm 2>/dev/null
echo ""
echo "  fire_detector_node:"
ros2 param get /fire_detector_node model_path 2>/dev/null && \
ros2 param get /fire_detector_node confidence_threshold 2>/dev/null && \
ros2 param get /fire_detector_node detection_fps 2>/dev/null
echo ""
echo "  arduino_bridge_node:"
ros2 param get /arduino_bridge_node serial_port 2>/dev/null && \
ros2 param get /arduino_bridge_node baud_rate 2>/dev/null
echo ""

# ── Test 6: Verify brain starts in IDLE ──
echo "[TEST 6] Brain State (should be IDLE):"
timeout 3 ros2 topic echo /firebot/state --once 2>/dev/null || echo "  (no message received)"
echo ""

# ── Test 7: Verify fire_detector publishes even without camera ──
echo "[TEST 7] Fire Detector (no camera -- should publish detected=false):"
timeout 5 ros2 topic echo /detection --once 2>/dev/null || echo "  (no detection message)"
echo ""

# ── Test 8: Manual alarm trigger ──
echo "[TEST 8] Manual Alarm Trigger:"
echo "  Sending alarm..."
ros2 topic pub --once /alarm/trigger std_msgs/msg/Bool "data: true"
sleep 2
echo "  State after alarm:"
timeout 3 ros2 topic echo /firebot/state --once 2>/dev/null || echo "  (no state message)"
# Reset: let search timeout (override to 2s for speed -- not possible via topic, just wait)
echo "  Waiting for search timeout..."
sleep 5
echo ""

# ── Test 9: Manual motor/warning commands ──
echo "[TEST 9] Manual Commands:"
echo "  Forward drive..."
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 80.0}, angular: {z: 0.0}}"
sleep 1
echo "  Rotate..."
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0}, angular: {z: 0.5}}"
sleep 1
echo "  Stop..."
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0}, angular: {z: 0.0}}"
echo "  Warning buzzer on..."
ros2 topic pub --once /warning/cmd std_msgs/msg/Int32 "data: 1"
sleep 1
echo "  Warning buzzer off..."
ros2 topic pub --once /warning/cmd std_msgs/msg/Int32 "data: 0"
echo "  Extinguisher pin-pull test..."
ros2 topic pub --once /extinguisher/cmd std_msgs/msg/Int32 "data: 1"
sleep 1
echo "  Extinguisher stop..."
ros2 topic pub --once /extinguisher/cmd std_msgs/msg/Int32 "data: 0"
echo ""

# ── Test 10: Full simulation scenario ──
echo "[TEST 10] Full Simulation Scenario:"
echo "  Running sim_publisher through entire state machine..."
echo ""
ros2 run firebot sim_publisher
echo ""

echo "============================================="
echo "  ALL TESTS COMPLETE"
echo "============================================="

kill $LAUNCH_PID 2>/dev/null
wait $LAUNCH_PID 2>/dev/null
exit 0
