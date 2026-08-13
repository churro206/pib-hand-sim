#!/usr/bin/env bash
# scripts/launch.sh — Startet die komplette pib-Simulation per Knopfdruck.
#
# Öffnet zwei Terminals:
#   Tab 1: Isaac Sim (USD laden + start.py + Play + pib_bridge)
#   Tab 2: ros2_control-Stack (JTC + JointStateBroadcaster)
#
# Erster manueller Schritt danach:
#   ros2 run pib_bringup test_client     (Pickup-Demo)
#   ros2 run pib_bringup test_client     (oder eigene Action senden)
#
# Verwendung:
#   ./scripts/launch.sh

set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

ISAAC_CMD="source /opt/ros/jazzy/setup.bash \
  && source ${REPO_ROOT}/ros2_ws/install/setup.bash \
  && export ROS_DOMAIN_ID=0 \
  && export PIB_HAND_SIM_ROOT=${REPO_ROOT} \
  && ${HOME}/isaacsim/isaac-sim.sh --exec ${REPO_ROOT}/isaac_sim/autostart.py"

# ros2_control erst starten wenn pib_bridge bereit (30s Puffer für Isaac-Start)
ROS2_CMD="echo '[launch] Warte 30s auf Isaac Sim...' \
  && sleep 30 \
  && source /opt/ros/jazzy/setup.bash \
  && source ${REPO_ROOT}/ros2_ws/install/setup.bash \
  && export ROS_DOMAIN_ID=0 \
  && ros2 launch pib_bringup pib_sim.launch.py"

echo "[launch] Öffne Terminal-Tabs für Isaac Sim und ros2_control..."

# LD_LIBRARY_PATH leeren: verhindert snap/glibc-Konflikt bei gnome-terminal
# (tritt auf wenn .venv aktiv ist)
LD_LIBRARY_PATH="" gnome-terminal \
  --tab --title="Isaac Sim" -- bash -c "${ISAAC_CMD}; exec bash" \
  --tab --title="ros2_control" -- bash -c "${ROS2_CMD}; exec bash"

echo "[launch] Terminals geöffnet."
echo ""
echo "  Erster manueller Schritt (wenn alles läuft):"
echo "    source ${REPO_ROOT}/ros2_ws/install/setup.bash"
echo "    ros2 run pib_bringup test_client"
