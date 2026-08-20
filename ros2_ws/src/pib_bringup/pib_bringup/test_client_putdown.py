#!/usr/bin/env python3
"""
test_client_putdown.py — Kehrt die Pickup-Demo exakt um (Dose absetzen und loslassen).

Identische 4 Keyframes wie test_client.py → _make_pickup_trajectory(), nur in
umgekehrter Reihenfolge durchlaufen:

  Step 1 lift     → t=0.0s  Startzustand: Dose gehoben, Hand geschlossen
  Step 2 grasp    → t=2.0s  Ellbogen senkt ab (elbow_right 55.4° → 17.7°) — Dose auf dem Tisch
  Step 3 approach → t=4.0s  Finger öffnen (33.3° → 0°) — Dose losgelassen
  Step 4 neutral  → t=6.0s  Arm zurück in T-Pose

Voraussetzung: Roboter steht im Endzustand von test_client_pickup.py (Dose bereits gehoben).
Reihenfolge: zuerst `ros2 run pib_bringup test_client_pickup`, danach dieses Skript.

Start:
  ros2 run pib_bringup test_client_putdown
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


# ── Identisch zu test_client.py — gleiche 25 von 44 DOFs ─────────────────────
PICKUP_JOINTS = [
    "dof_shoulder_vertical_left", "dof_shoulder_horizontal_left",
    "dof_upper_arm_left", "dof_elbow_left", "dof_forearm_left",
    "dof_shoulder_vertical_right", "dof_shoulder_horizontal_right",
    "dof_elbow_right", "dof_forearm_right", "dof_wrist_right",
    "dof_thumb_right_rotator", "dof_thumb_right_proximal", "dof_thumb_right_distal",
    "dof_index_right_proximal",  "dof_index_right_distal",  "dof_index_right_tip",
    "dof_middle_right_proximal", "dof_middle_right_distal", "dof_middle_right_tip",
    "dof_ring_right_proximal",   "dof_ring_right_distal",   "dof_ring_right_tip",
    "dof_pinky_right_proximal",  "dof_pinky_right_distal",  "dof_pinky_right_tip",
]

_G = 33.3
_OPEN = 0.0
_THUMB_OPP = 90.0


def _make_putdown_trajectory():
    def pt(positions_deg, sec):
        return JointTrajectoryPoint(
            positions=[_r(d) for d in positions_deg],
            time_from_start=Duration(sec=sec, nanosec=0),
        )

    # Step 1 — Lift (= Endzustand von test_client.py)
    lift = [
        90.0, 90.0, 0.1, -45.0, -0.2,
        62.5, 90.0, 55.4, 1.4, 4.0,
        _THUMB_OPP, _G, _G,
        _G, _G, _G,
        _G, _G, _G,
        _G, _G, _G,
        _G, _G, _G,
    ]

    # Step 2 — Grasp: Ellbogen senkt ab, Finger bleiben geschlossen
    grasp = [
        90.0, 90.0, 0.1, -45.0, -0.2,
        62.5, 90.0, 17.7, 1.4, 4.0,
        _THUMB_OPP, _G, _G,
        _G, _G, _G,
        _G, _G, _G,
        _G, _G, _G,
        _G, _G, _G,
    ]

    # Step 3 — Approach: Finger öffnen, Dose losgelassen
    approach = [
        90.0, 90.0, 0.1, -45.0, -0.2,
        62.5, 90.0, 17.7, 1.4, 4.0,
        _THUMB_OPP, _OPEN, _OPEN,
        _OPEN, _OPEN, _OPEN,
        _OPEN, _OPEN, _OPEN,
        _OPEN, _OPEN, _OPEN,
        _OPEN, _OPEN, _OPEN,
    ]

    # Step 4 — Neutral: T-Pose
    neutral = [0.0] * len(PICKUP_JOINTS)

    return [
        pt(lift,     sec=0),
        pt(grasp,    sec=2),
        pt(approach, sec=4),
        pt(neutral,  sec=6),
    ]


class PibPutdownClient(Node):

    def __init__(self):
        super().__init__("pib_putdown_client")
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

    def send_putdown(self):
        self.get_logger().info("Warte auf Action-Server...")
        self._action_client.wait_for_server()
        self.get_logger().info(
            "Action-Server bereit. Starte Putdown-Demo (Dose absetzen und loslassen)."
        )

        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = PICKUP_JOINTS
        goal.trajectory.points = _make_putdown_trajectory()

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
            "elbow_right":         7,
            "thumb_right_rotator": 10,
            "index_right_proximal":13,
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
    client = PibPutdownClient()
    client.send_putdown()

    while rclpy.ok() and not client._done:
        rclpy.spin_once(client, timeout_sec=0.1)

    client.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
