#!/usr/bin/env python3
"""
test_client.py — Stub für Phase 3/4.

Sendet eine Test-Trajektorie an /pib/joint_trajectory.
Wird in Sprint 4 ausgebaut wenn IK-Team Interface feststeht.
"""
import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint


class PibTestClient(Node):
    def __init__(self):
        super().__init__("pib_test_client")
        self._pub = self.create_publisher(JointTrajectory, "/pib/joint_trajectory", 1)
        self.get_logger().info("PibTestClient bereit — noch kein Test implementiert (Stub)")


def main():
    rclpy.init()
    node = PibTestClient()
    rclpy.spin_once(node, timeout_sec=1.0)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
