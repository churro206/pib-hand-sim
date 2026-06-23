"""
tools/send_test_trajectory.py — Testskript für den pib ROS2-Server.

Läuft AUSSERHALB von Isaac Sim (normales Terminal mit Jazzy-Setup).

Usage:
    source /opt/ros/jazzy/setup.bash
    python3 tools/send_test_trajectory.py

Sendet: rechte Hand öffnen (0°) → schließen (90°) → öffnen (0°) über 4 Sekunden.
Liest danach /pib/joint_states und zeigt die empfangene Antwort.

Voraussetzung: ros2_server.py läuft in Isaac Sim.
"""
import rclpy
from rclpy.node import Node
from builtin_interfaces.msg import Duration
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from sensor_msgs.msg import JointState


# ── Konfiguration ─────────────────────────────────────────────────────────────
ANGLE_UNIT = "deg"   # muss mit config/server_config.py übereinstimmen

TOPIC_SEND   = "/pib/joint_trajectory"
TOPIC_STATES = "/pib/joint_states"

# Rechte Handfinger (DirectMode — DOF-Namen, Onshape-Konvention)
JOINTS = [
    "dof_index_right_proximal",
    "dof_index_right_distal",
    "dof_index_right_tip",
    "dof_middle_right_proximal",
    "dof_middle_right_distal",
    "dof_middle_right_tip",
    "dof_ring_right_proximal",
    "dof_ring_right_distal",
    "dof_ring_right_tip",
    "dof_pinky_right_proximal",
    "dof_pinky_right_distal",
    "dof_pinky_right_tip",
    "dof_thumb_right_rotator",
    "dof_thumb_right_proximal",
    "dof_thumb_right_distal",
]

OPEN   = [0.0]  * len(JOINTS)
CLOSED = [90.0] * len(JOINTS)


def _make_duration(sec: float) -> Duration:
    d = Duration()
    d.sec     = int(sec)
    d.nanosec = int((sec - int(sec)) * 1e9)
    return d


def _make_trajectory() -> JointTrajectory:
    msg = JointTrajectory()
    msg.joint_names = JOINTS

    # Punkt 0: t=0s — offen (Startpose, optional aber sauber)
    p0 = JointTrajectoryPoint()
    p0.positions       = OPEN
    p0.time_from_start = _make_duration(0.0)

    # Punkt 1: t=2s — geschlossen
    p1 = JointTrajectoryPoint()
    p1.positions       = CLOSED
    p1.time_from_start = _make_duration(2.0)

    # Punkt 2: t=4s — offen
    p2 = JointTrajectoryPoint()
    p2.positions       = OPEN
    p2.time_from_start = _make_duration(4.0)

    msg.points = [p0, p1, p2]
    return msg


class TestSender(Node):
    def __init__(self):
        super().__init__("pib_test_sender")
        self._pub    = self.create_publisher(JointTrajectory, TOPIC_SEND,   10)
        self._sub    = self.create_subscription(JointState, TOPIC_STATES, self._on_states, 10)
        self._states = None

    def send(self):
        msg = _make_trajectory()
        self._pub.publish(msg)
        self.get_logger().info(
            f"Trajectory gesendet: {len(msg.points)} Punkte über "
            f"{msg.points[-1].time_from_start.sec}s → {TOPIC_SEND}"
        )

    def _on_states(self, msg):
        self._states = msg

    def print_states(self):
        if self._states is None:
            print("[test] Keine /pib/joint_states empfangen — läuft ros2_server.py?")
            return
        print(f"\n── /pib/joint_states ({len(self._states.name)} DOFs) ──────────────")
        for name, pos in zip(self._states.name, self._states.position):
            unit = "°" if ANGLE_UNIT == "deg" else "rad"
            print(f"  {name:<36s} {pos:7.2f}{unit}")
        print()


def main():
    rclpy.init()
    node = TestSender()

    # Kurz warten damit Subscriber im Server Zeit hat sich zu registrieren
    import time
    print("[test] Warte 1s auf Verbindung...")
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)

    node.send()

    # Auf joint_states warten (max 2s)
    print("[test] Warte auf /pib/joint_states...")
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline and node._states is None:
        rclpy.spin_once(node, timeout_sec=0.1)

    node.print_states()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
