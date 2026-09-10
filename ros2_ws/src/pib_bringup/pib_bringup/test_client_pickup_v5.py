#!/usr/bin/env python3
"""
test_client_pickup_v5.py — Pickup-Demo für pib ros2_control-Stack (v5-Hand).

Analog zu test_client_pickup.py (v4), aber mit v5-Joint-Namen (kein dof_-Präfix, Daumen-
Mittelgelenk heißt "tip") und der über isaac_sim/tools/dump_pose.py aus der laufenden
v5-Stage aufgenommenen Sequenz (isaac_sim/tools/_pose_dump.json, gitignored):
  1. neutral  — T-Pose
  2. approach — rechter Arm über die Dose, Daumen opponiert
  3. grasp    — alle rechten Finger schließen (41.4°)
  4. lift     — Schulter hebt die Dose an (shoulder_vertical_right 54.3° → 23.1°)

Sendet alle 44 DOFs (nicht nur eine Teilmenge wie bei v4) — 1:1 wie aufgenommen, kein
Handverlesen nötig, da dump_pose.py ohnehin den vollen Gelenkzustand dumpt.

Voraussetzung:
  1. Isaac Sim läuft (pib_upperbody_v5.usd mit Action Graph geladen, start.py ausgeführt,
     Play gedrückt)
  2. ros2 launch pib_bringup pib_sim_v5.launch.py

Start:
  ros2 run pib_bringup test_client_pickup_v5
"""
import math
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint
from builtin_interfaces.msg import Duration
from sensor_msgs.msg import JointState


def _r(deg: float) -> float:
    """Grad → Radiant (ros2_control-Konvention)."""
    return math.radians(deg)


# ── Alle 44 v5-DOFs, Reihenfolge wie in _pose_dump.json aufgenommen ──────────
POSE_JOINTS = [
    "head_horizontal", "head_vertical", "shoulder_vertical_left",
    "shoulder_horizontal_left", "upper_arm_left", "elbow_left", "forearm_left",
    "wrist_left", "index_left_proximal", "index_left_distal", "index_left_tip",
    "middle_left_proximal", "middle_left_distal", "middle_left_tip",
    "pinky_left_proximal", "pinky_left_distal", "pinky_left_tip", "ring_left_proximal",
    "ring_left_distal", "ring_left_tip", "thumb_left_rotator", "thumb_left_proximal",
    "thumb_left_tip", "shoulder_vertical_right", "shoulder_horizontal_right",
    "upper_arm_right", "elbow_right", "forearm_right", "wrist_right",
    "index_right_proximal", "index_right_distal", "index_right_tip",
    "middle_right_proximal", "middle_right_distal", "middle_right_tip",
    "pinky_right_proximal", "pinky_right_distal", "pinky_right_tip",
    "ring_right_proximal", "ring_right_distal", "ring_right_tip", "thumb_right_rotator",
    "thumb_right_proximal", "thumb_right_tip",
]

# ── Waypoints, direkt aus isaac_sim/tools/_pose_dump.json übernommen (Grad) ──
_NEUTRAL = [
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
]

_APPROACH = [
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 54.3, 85.4, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 90.0, 0.0, 0.0,
]

_GRASP = [
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 54.3, 85.4, 0.0, 0.0, 0.0, 0.0, 41.4, 41.4, 41.4, 41.4,
    41.4, 41.4, 41.4, 41.4, 41.4, 41.4, 41.4, 41.4, 90.0, 41.4, 41.4,
]

_LIFT = [
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 23.1, 85.4, 0.0, 0.0, 0.0, 0.0, 41.4, 41.4, 41.4, 41.4,
    41.4, 41.4, 41.4, 41.4, 41.4, 41.4, 41.4, 41.4, 90.0, 41.4, 41.4,
]

# Feedback-Indizes in POSE_JOINTS (für die Fortschritts-Ausgabe pro Sekunde)
_IDX_ELBOW_RIGHT = 26
_IDX_THUMB_RIGHT_ROTATOR = 41
_IDX_INDEX_RIGHT_PROXIMAL = 29


def _make_pickup_trajectory():
    """
    4 Waypoints, je 2s Abstand (wie in _pose_dump.json aufgenommen, "t": 2.0 pro Waypoint).

    Step 1 neutral  → t=0.0s  T-Pose, alle 0°
    Step 2 approach → t=2.0s  Arm positioniert, Hand offen, Daumen opponiert
    Step 3 grasp    → t=4.0s  Finger schließen auf 41.4°
    Step 4 lift     → t=6.0s  Schulter hebt (54.3° → 23.1°), Dose angehoben
    """
    def pt(positions_deg, sec):
        return JointTrajectoryPoint(
            positions=[_r(d) for d in positions_deg],
            time_from_start=Duration(sec=sec, nanosec=0),
        )

    return [
        pt(_NEUTRAL,  sec=0),
        pt(_APPROACH, sec=2),
        pt(_GRASP,    sec=4),
        pt(_LIFT,     sec=6),
    ]


class PibPickupClientV5(Node):

    def __init__(self):
        super().__init__("pib_pickup_client_v5")
        self._action_client = ActionClient(
            self,
            FollowJointTrajectory,
            "/joint_trajectory_controller/follow_joint_trajectory",
        )
        self._joint_states_sub = self.create_subscription(
            JointState,
            "/joint_states",
            self._on_joint_states,
            10,
        )
        self._last_joint_states = None
        self._done = False

    def _on_joint_states(self, msg: JointState):
        self._last_joint_states = msg

    def send_pickup(self):
        self.get_logger().info("Warte auf Action-Server...")
        self._action_client.wait_for_server()
        self.get_logger().info(
            "Action-Server bereit. Starte Pickup-Demo v5 (Dose greifen und heben)."
        )

        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = POSE_JOINTS
        goal.trajectory.points = _make_pickup_trajectory()

        future = self._action_client.send_goal_async(
            goal,
            feedback_callback=self._on_feedback,
        )
        future.add_done_callback(self._on_goal_response)

    def _on_goal_response(self, future):
        handle = future.result()
        if not handle.accepted:
            self.get_logger().error("Goal abgelehnt!")
            self._done = True
            return
        self.get_logger().info("Goal akzeptiert — Ausführung läuft (6s)...")
        handle.get_result_async().add_done_callback(self._on_result)

    def _on_feedback(self, feedback_msg):
        """Zeigt Ist- vs. Soll-Position der wichtigsten Gelenke pro Sekunde."""
        fb = feedback_msg.feedback
        if not fb.actual.positions or not fb.desired.positions:
            return

        t = fb.actual.time_from_start.sec + fb.actual.time_from_start.nanosec * 1e-9
        if not hasattr(self, "_last_fb_t"):
            self._last_fb_t = -1.0
        if t - self._last_fb_t < 0.9:
            return
        self._last_fb_t = t

        tracked = {
            "elbow_right":         _IDX_ELBOW_RIGHT,
            "thumb_right_rotator": _IDX_THUMB_RIGHT_ROTATOR,
            "index_right_proximal": _IDX_INDEX_RIGHT_PROXIMAL,
        }
        parts = []
        for label, idx in tracked.items():
            if idx < len(fb.actual.positions):
                ist  = math.degrees(fb.actual.positions[idx])
                soll = math.degrees(fb.desired.positions[idx])
                err  = ist - soll
                parts.append(f"{label}: {ist:.1f}° (Δ{err:+.1f}°)")
        self.get_logger().info(f"  t={t:.1f}s | " + " | ".join(parts))

    def _on_result(self, future):
        result = future.result().result
        self.get_logger().info(f"Fertig! Error-Code: {result.error_code}")

        if self._last_joint_states:
            self.get_logger().info("Endzustand rechte Hand + Arm:")
            for name, pos in zip(
                self._last_joint_states.name,
                self._last_joint_states.position,
            ):
                if "right" in name:
                    self.get_logger().info(f"  {name}: {math.degrees(pos):.1f}°")

        self._done = True


def main(args=None):
    rclpy.init(args=args)
    client = PibPickupClientV5()
    client.send_pickup()

    while rclpy.ok() and not client._done:
        rclpy.spin_once(client, timeout_sec=0.1)

    client.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
