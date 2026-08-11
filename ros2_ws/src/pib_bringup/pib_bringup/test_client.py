#!/usr/bin/env python3
"""
test_client.py — Pickup-Demo für pib ros2_control-Stack.

Führt die physikalisch verifizierte Dose-Greif-Sequenz aus:
  1. T-Pose (neutral)
  2. Approach — rechter Arm über die Dose, Daumen opponiert
  3. Grasp   — alle Finger schließen (33.3°)
  4. Lift    — Ellbogen hebt die Dose an

Sequenz entspricht config/sequences.py → PICKUP (DirectMode, Onshape-Konvention).
Winkel werden hier nach Radiant konvertiert; robot_io wendet JOINT_SIGN intern an.

Voraussetzung:
  1. Isaac Sim läuft (start.py + pib_bridge.py im Script Editor)
  2. ros2 launch pib_bringup pib_sim.launch.py

Start:
  ros2 run pib_bringup test_client
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


# ── Gelenke die sich in der Pickup-Sequenz bewegen (25 von 44 DOFs) ──────────
PICKUP_JOINTS = [
    # Linker Arm — Haltepose
    "dof_shoulder_vertical_left", "dof_shoulder_horizontal_left",
    "dof_upper_arm_left", "dof_elbow_left", "dof_forearm_left",
    # Rechter Arm — über Dose
    "dof_shoulder_vertical_right", "dof_shoulder_horizontal_right",
    "dof_elbow_right", "dof_forearm_right", "dof_wrist_right",
    # Rechte Hand
    "dof_thumb_right_rotator", "dof_thumb_right_proximal", "dof_thumb_right_distal",
    "dof_index_right_proximal",  "dof_index_right_distal",  "dof_index_right_tip",
    "dof_middle_right_proximal", "dof_middle_right_distal", "dof_middle_right_tip",
    "dof_ring_right_proximal",   "dof_ring_right_distal",   "dof_ring_right_tip",
    "dof_pinky_right_proximal",  "dof_pinky_right_distal",  "dof_pinky_right_tip",
]

_G = 33.3   # Greifwinkel (Onshape-Konvention, physikalisch verifiziert)
_OPEN = 0.0
_THUMB_OPP = 90.0  # Daumen opponiert für Zylindergriff


def _make_pickup_trajectory():
    """
    4 Waypoints aus config/sequences.py → PICKUP (kumulativer State, Onshape → rad).

    Step 1 neutral  → t=0.0s  T-Pose, alle 0°
    Step 2 approach → t=2.0s  Arm positioniert, Hand offen, Daumen opponiert
    Step 3 grasp    → t=3.5s  Finger schließen auf 33.3°
    Step 4 lift     → t=5.5s  Ellbogen hebt, Dose angehoben
    """
    def pt(positions_deg, sec):
        return JointTrajectoryPoint(
            positions=[_r(d) for d in positions_deg],
            time_from_start=Duration(sec=sec, nanosec=0),
        )

    # Step 1 — T-Pose
    neutral = [0.0] * len(PICKUP_JOINTS)

    # Step 2 — Approach (aus _PICKUP_APPROACH nach _isaac()-Negation)
    approach = [
        90.0, 90.0, 0.1, -45.0, -0.2,          # linker Arm
        62.5, 90.0, 17.7, 1.4, 4.0,             # rechter Arm
        _THUMB_OPP, _OPEN, _OPEN,               # Daumen opponiert, Hand offen
        _OPEN, _OPEN, _OPEN,                    # Zeigefinger
        _OPEN, _OPEN, _OPEN,                    # Mittelfinger
        _OPEN, _OPEN, _OPEN,                    # Ringfinger
        _OPEN, _OPEN, _OPEN,                    # Kleinfinger
    ]

    # Step 3 — Grasp: Arme wie Approach, alle Finger auf _G
    grasp = [
        90.0, 90.0, 0.1, -45.0, -0.2,
        62.5, 90.0, 17.7, 1.4, 4.0,
        _THUMB_OPP, _G, _G,
        _G, _G, _G,
        _G, _G, _G,
        _G, _G, _G,
        _G, _G, _G,
    ]

    # Step 4 — Lift: elbow_right auf 55.4° (index 7), Finger bleiben geschlossen
    lift = [
        90.0, 90.0, 0.1, -45.0, -0.2,
        62.5, 90.0, 55.4, 1.4, 4.0,    # elbow_right 17.7 → 55.4 hebt die Dose
        _THUMB_OPP, _G, _G,
        _G, _G, _G,
        _G, _G, _G,
        _G, _G, _G,
        _G, _G, _G,
    ]

    return [
        pt(neutral,  sec=0),
        pt(approach, sec=2),
        pt(grasp,    sec=4),
        pt(lift,     sec=6),
    ]


class PibPickupClient(Node):

    def __init__(self):
        super().__init__("pib_pickup_client")
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
            "Action-Server bereit. Starte Pickup-Demo (Dose greifen und heben)."
        )

        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = PICKUP_JOINTS
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
        # Nur ~1× pro Sekunde loggen (Feedback kommt mit 50 Hz)
        if not hasattr(self, "_last_fb_t"):
            self._last_fb_t = -1.0
        if t - self._last_fb_t < 0.9:
            return
        self._last_fb_t = t

        # Schlüsselgelenke: Ellbogen (Arm-Fortschritt) + ein Finger (Greif-Fortschritt)
        tracked = {
            "elbow_right":         7,   # Arm angehoben?
            "thumb_right_rotator": 10,  # Daumen opponiert?
            "index_right_proximal":13,  # Finger geschlossen?
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
    client = PibPickupClient()
    client.send_pickup()

    while rclpy.ok() and not client._done:
        rclpy.spin_once(client, timeout_sec=0.1)

    client.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
