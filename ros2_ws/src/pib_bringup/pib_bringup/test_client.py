#!/usr/bin/env python3
"""
test_client.py — Demo-Client für pib ros2_control-Stack.

Sendet eine Wellbewegung der rechten Hand als FollowJointTrajectory-Goal.
Gibt Feedback und Result aus. Empfängt joint_states und zeigt Endzustand.

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


# Rechte Hand: Zeige-, Mittel-, Ring- und Kleinfinger wellen
WAVE_JOINTS = [
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
]

def _deg(d: float) -> float:
    """Grad → Radiant (ros2_control-Konvention)."""
    return math.radians(d)


def _make_wave_trajectory():
    """Erzeugt 4-Punkt-Wellbewegung: offen → geschlossen → offen → halb."""
    n = len(WAVE_JOINTS)
    points = []

    # Punkt 0 — Startposition (offen, 0°), sofort
    points.append(JointTrajectoryPoint(
        positions=[_deg(0.0)] * n,
        time_from_start=Duration(sec=0, nanosec=0),
    ))
    # Punkt 1 — Geschlossen (90°) nach 1.0s
    points.append(JointTrajectoryPoint(
        positions=[_deg(90.0)] * n,
        time_from_start=Duration(sec=1, nanosec=0),
    ))
    # Punkt 2 — Offen nach 2.0s
    points.append(JointTrajectoryPoint(
        positions=[_deg(0.0)] * n,
        time_from_start=Duration(sec=2, nanosec=0),
    ))
    # Punkt 3 — Halb geschlossen (45°) nach 3.0s (Endpose)
    points.append(JointTrajectoryPoint(
        positions=[_deg(45.0)] * n,
        time_from_start=Duration(sec=3, nanosec=0),
    ))

    return points


class PibTestClient(Node):

    def __init__(self):
        super().__init__("pib_test_client")
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

    def send_wave(self):
        self.get_logger().info("Warte auf Action-Server...")
        self._action_client.wait_for_server()
        self.get_logger().info("Action-Server bereit. Sende Wellbewegung.")

        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = WAVE_JOINTS
        goal.trajectory.points = _make_wave_trajectory()

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
        self.get_logger().info("Goal akzeptiert — Ausführung läuft...")
        result_future = handle.get_result_async()
        result_future.add_done_callback(self._on_result)

    def _on_feedback(self, feedback_msg):
        fb = feedback_msg.feedback
        # Zeige aktuellen Zeigefinger-Winkel als Fortschrittsindikator
        if fb.actual.positions:
            deg = math.degrees(fb.actual.positions[0])
            self.get_logger().info(f"  Fortschritt — index_proximal: {deg:.1f}°")

    def _on_result(self, future):
        result = future.result().result
        self.get_logger().info(f"Fertig! Error-Code: {result.error_code}")

        # Joint-States ausgeben
        if self._last_joint_states:
            self.get_logger().info("Aktueller Roboterzustand (Auswahl rechte Hand):")
            for name, pos in zip(
                self._last_joint_states.name,
                self._last_joint_states.position,
            ):
                if "right" in name:
                    self.get_logger().info(f"  {name}: {math.degrees(pos):.1f}°")

        self._done = True


def main(args=None):
    rclpy.init(args=args)
    client = PibTestClient()
    client.send_wave()

    while rclpy.ok() and not client._done:
        rclpy.spin_once(client, timeout_sec=0.1)

    client.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
