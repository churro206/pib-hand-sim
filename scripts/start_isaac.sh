#!/usr/bin/env bash
# scripts/start_isaac.sh — Isaac Sim mit automatischem Startup starten.
#
# Lädt die USD, führt start.py aus, drückt Play und startet pib_bridge —
# alles ohne Script Editor oder manuelle Schritte.
#
# Verwendung:
#   ./scripts/start_isaac.sh
#
# Voraussetzung: start_ros2.sh in einem anderen Terminal starten (nach Isaac bereit).

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AUTOSTART="${REPO_ROOT}/isaac_sim/autostart.py"
ISAAC="${HOME}/isaacsim/isaac-sim.sh"

if [ ! -f "${ISAAC}" ]; then
    echo "FEHLER: Isaac Sim nicht gefunden unter ${ISAAC}"
    echo "PIB_HAND_SIM_ROOT setzen oder Pfad in diesem Skript anpassen."
    exit 1
fi

# ROS2 + ros2_ws sourcing (damit pib_bridge.py rclpy findet)
source /opt/ros/jazzy/setup.bash
source "${REPO_ROOT}/ros2_ws/install/setup.bash"
export ROS_DOMAIN_ID=0
export PIB_HAND_SIM_ROOT="${REPO_ROOT}"

echo "[start_isaac] Starte Isaac Sim mit autostart.py..."
echo "[start_isaac] Repo: ${REPO_ROOT}"
echo "[start_isaac] ROS_DOMAIN_ID=${ROS_DOMAIN_ID}"

"${ISAAC}" --exec "${AUTOSTART}"
