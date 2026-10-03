#!/usr/bin/env python3
"""
test_client_mimic_v5.py — Test der Mimic Joints (Stufe 1, linear, gearing=-1) für die v5-Hand.

Fährt nur das MCP-Gelenk (`<finger>_<seite>_proximal`) per FollowJointTrajectory und
misst, ob PIP/DIP (bzw. Daumen-IP) rein über die PhysX-Zwangsbedingung mitlaufen. PIP/DIP
werden bewusst NICHT mitgesendet (controllers_v5.yaml: allow_partial_joints_goal: true) —
ihre Antriebe sind ohnehin neutralisiert (isaac_sim/setup_stage.py: configure_drives).

Sequenz (MCP): 0° → 45° (3 s) → halten (2 s) → 90° (3 s) → halten (2 s) → 0° (3 s) → halten (2 s)
Ausgewertet wird jeweils das letzte 1,0 s jeder Haltephase (Ruhelage, ohne Einschwingen):
  Δ = θ_folge − θ_MCP   (erwartet 0°, Toleranz --tol, Standard 1,0°)
Zusätzlich: maximale Abweichung über die gesamte Fahrt (dynamisch, nur zur Info) und der
MCP-Regelfehler (θ_MCP − Soll) — wächst der, trägt der MCP-Servo Last aus der Kopplung.

Voraussetzung:
  1. Isaac Sim läuft (pib_upperbody_v5.usd, start.py ausgeführt → Mimic Joints gesetzt,
     Stop → Play)
  2. ros2 launch pib_bringup pib_sim_v5.launch.py

Start:
  ros2 run pib_bringup test_client_mimic_v5                 # index_left
  ros2 run pib_bringup test_client_mimic_v5 --finger thumb_right
  ros2 run pib_bringup test_client_mimic_v5 --finger all    # alle 10 MCPs gleichzeitig
  ros2 run pib_bringup test_client_mimic_v5 --tol 0.5

Exit-Code 0 = alle Haltepunkte innerhalb der Toleranz, 1 = mindestens einer außerhalb,
2 = Goal abgelehnt/abgebrochen oder keine Messdaten.
"""
import argparse
import math
import sys

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.utilities import remove_ros_args
from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint
from builtin_interfaces.msg import Duration

FINGERS = ("index", "middle", "ring", "pinky")
SIDES = ("left", "right")
ALL_TARGETS = [f"{f}_{s}" for s in SIDES for f in FINGERS] + [f"thumb_{s}" for s in SIDES]

# (Zeit s, MCP-Sollwinkel °) — Haltephasen enden bei 6 / 11 / 16 s
WAYPOINTS = [
    (1.0, 0.0),     # Startpunkt
    (4.0, 45.0),
    (6.0, 45.0),    # Halten 45°
    (9.0, 90.0),
    (11.0, 90.0),   # Halten 90°
    (14.0, 0.0),
    (16.0, 0.0),    # Halten 0°
]
HOLD_WINDOW_S = 1.0
HOLDS = [(6.0, 45.0), (11.0, 90.0), (16.0, 0.0)]  # (Ende der Haltephase, Soll °)


def _chain(target: str) -> list:
    """(Name, Folgegelenk, Referenzgelenk) für einen Finger/Daumen — alle gegen das MCP gemessen."""
    if target.startswith("thumb"):
        side = target.split("_")[1]
        return [("IP", f"thumb_{side}_tip")]
    return [("PIP", f"{target.split('_')[0]}_{target.split('_')[1]}_distal"),
            ("DIP", f"{target.split('_')[0]}_{target.split('_')[1]}_tip")]


def _mcp(target: str) -> str:
    return f"{target}_proximal"


class PibMimicTestV5(Node):

    def __init__(self, targets: list):
        super().__init__("pib_mimic_test_v5")
        self.targets = targets
        self._action_client = ActionClient(
            self, FollowJointTrajectory, "/joint_trajectory_controller/follow_joint_trajectory"
        )
        self.recorder = None   # wird bei Goal-Annahme gestartet (t=0 ~ Trajektorienstart)
        self.accepted = None
        self.error_code = None
        self.done = False

    def send(self):
        self.get_logger().info("Warte auf Action-Server...")
        self._action_client.wait_for_server()

        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = [_mcp(t) for t in self.targets]
        for sec, deg in WAYPOINTS:
            pt = JointTrajectoryPoint()
            pt.positions = [math.radians(deg)] * len(self.targets)
            pt.time_from_start = Duration(sec=int(sec), nanosec=int((sec % 1) * 1e9))
            goal.trajectory.points.append(pt)

        self.get_logger().info(
            f"Starte Mimic-Test v5: {', '.join(self.targets)} (nur MCP wird kommandiert, "
            f"Dauer {WAYPOINTS[-1][0]:.0f} s)"
        )
        self._action_client.send_goal_async(goal).add_done_callback(self._on_goal_response)

    def _on_goal_response(self, future):
        handle = future.result()
        self.accepted = handle.accepted
        if not handle.accepted:
            self.get_logger().error("Goal abgelehnt!")
            self.done = True
            return
        if self.recorder is not None:
            self.recorder.start()
        handle.get_result_async().add_done_callback(self._on_result)

    def _on_result(self, future):
        self.error_code = future.result().result.error_code
        self.done = True


def _mean(values):
    return sum(values) / len(values) if values else float("nan")


class _JointStateRecorder:
    """Zeichnet /joint_states mit Zeit relativ zum Goal-Start auf (Folgegelenke stehen nicht im Feedback)."""

    def __init__(self, node: Node):
        from sensor_msgs.msg import JointState
        self._node = node
        self.t0 = None
        self.rows = []  # (t, {name: rad})
        node.create_subscription(JointState, "/joint_states", self._cb, 50)

    def start(self):
        self.t0 = self._node.get_clock().now()

    def _cb(self, msg):
        if self.t0 is None:
            return
        t = (self._node.get_clock().now() - self.t0).nanoseconds * 1e-9
        self.rows.append((t, dict(zip(msg.name, msg.position))))


def report(node: PibMimicTestV5, rec: _JointStateRecorder, tol_deg: float) -> int:
    rows = [(t, d) for t, d in rec.rows if t >= 0.0]
    if not rows:
        node.get_logger().error("Keine /joint_states empfangen — läuft die Bridge (pib_sim_v5.launch.py)?")
        return 2

    # Trajektorie startet erst nach Goal-Annahme; Versatz zwischen Recorder-t0 und Trajektorien-t0
    # ist klein (< 0,2 s) gegenüber den 1-s-Auswertefenstern am Ende der Haltephasen.
    failed = False
    print()
    print(f"{'Gelenk':<22}{'Halten':>8}{'MCP-Ist':>10}{'Folge-Ist':>11}{'Δ (Folge-MCP)':>15}{'MCP-Fehler':>12}  Ergebnis")
    print("-" * 92)
    for target in node.targets:
        mcp = _mcp(target)
        for label, follower in _chain(target):
            for end, soll in HOLDS:
                win = [d for t, d in rows if end - HOLD_WINDOW_S <= t <= end]
                win = [d for d in win if mcp in d and follower in d]
                if not win:
                    print(f"{follower:<22}{soll:>7.0f}°  keine Daten im Fenster [{end - HOLD_WINDOW_S:.0f}, {end:.0f}] s")
                    failed = True
                    continue
                m = math.degrees(_mean([d[mcp] for d in win]))
                f = math.degrees(_mean([d[follower] for d in win]))
                delta = f - m
                ok = abs(delta) <= tol_deg
                failed |= not ok
                print(f"{follower:<22}{soll:>7.0f}°{m:>9.1f}°{f:>10.1f}°{delta:>+14.2f}°{m - soll:>+11.1f}°  "
                      f"{'OK' if ok else 'ABWEICHUNG'}")
            dyn = [abs(math.degrees(d[follower] - d[mcp])) for _, d in rows if mcp in d and follower in d]
            print(f"{'':<22}  dynamisch (gesamte Fahrt): max |Δ| = {max(dyn):.2f}°  ({label})")
        print()

    print(f"Toleranz Haltepunkte: ±{tol_deg:g}°  →  {'FEHLGESCHLAGEN' if failed else 'BESTANDEN'}")
    return 1 if failed else 0


def main(args=None):
    parser = argparse.ArgumentParser(description="Mimic-Joint-Test v5 (Stufe 1)")
    parser.add_argument("--finger", default="index_left",
                        help=f"Ziel: {', '.join(ALL_TARGETS)} oder 'all' (Standard: index_left)")
    parser.add_argument("--tol", type=float, default=1.0, help="Toleranz an den Haltepunkten in Grad (Standard 1.0)")
    ns = parser.parse_args(remove_ros_args(sys.argv if args is None else args)[1:])

    if ns.finger == "all":
        targets = list(ALL_TARGETS)
    elif ns.finger in ALL_TARGETS:
        targets = [ns.finger]
    else:
        parser.error(f"unbekanntes Ziel '{ns.finger}' — erlaubt: {', '.join(ALL_TARGETS)}, all")

    rclpy.init(args=args)
    node = PibMimicTestV5(targets)
    rec = _JointStateRecorder(node)
    node.recorder = rec
    node.send()

    while rclpy.ok() and not node.done:
        rclpy.spin_once(node, timeout_sec=0.1)

    # kurzes Nachlaufen, damit die letzten /joint_states noch eingesammelt werden
    for _ in range(5):
        rclpy.spin_once(node, timeout_sec=0.05)

    if node.accepted is False or (node.error_code not in (None, 0)):
        node.get_logger().error(f"Goal nicht erfolgreich (accepted={node.accepted}, error_code={node.error_code})")
        code = 2
    else:
        code = report(node, rec, ns.tol)

    node.destroy_node()
    rclpy.shutdown()
    sys.exit(code)


if __name__ == "__main__":
    main()
