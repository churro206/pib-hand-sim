#!/usr/bin/env bash
# scripts/start_ros2.sh — ros2_control-Stack starten.
#
# Startet JointTrajectoryController + JointStateBroadcaster via pib_sim.launch.py.
# Isaac Sim muss bereits laufen (start_isaac.sh) und der Action Graph aktiv sein
# (im Isaac-Log nach Play sichtbar).
#
# Verwendung:
#   ./scripts/start_ros2.sh
#
# Optional: Pickup-Demo danach in einem dritten Terminal:
#   ./scripts/test_pickup.sh

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

source /opt/ros/jazzy/setup.bash
source "${REPO_ROOT}/ros2_ws/install/setup.bash"
export ROS_DOMAIN_ID=0

echo "[start_ros2] Starte ros2_control-Stack..."
echo "[start_ros2] ROS_DOMAIN_ID=${ROS_DOMAIN_ID}"

ros2 launch pib_bringup pib_sim.launch.py
