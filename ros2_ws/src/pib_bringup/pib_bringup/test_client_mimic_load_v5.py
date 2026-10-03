#!/usr/bin/env python3
"""
test_client_mimic_load_v5.py — Lasttest der Mimic Joints (v5): linke Hand fährt mit den Fingern
gegen den Tisch. Replik des Tischtests aus der verworfenen Kraft-Rückwirkung (ADR-010,
früher tendondrive/test_coupling_reflection.sh), jetzt mit Diagnose.

Ablauf:
  1. Linker Arm in Testpose (Hand knapp über dem Tisch, Werte aus dem Physics Inspector):
     shoulder_vertical_left 1.4050, shoulder_horizontal_left 1.5708, upper_arm_left 0.1152,
     elbow_left 0.4677, forearm_left 1.5708, wrist_left 0.0 rad (3 s). Pose wird gegengeprüft.
  2. MCP des Zielfingers 0° → 90° in --close-time s (Standard 4 s), danach --hold s (Standard 3 s)
     weiter auf 90° gehalten — die Fingerspitze drückt dabei gegen den Tisch.
  3. Auswertung aus /pib/hw/joint_states (Roh-Zustand aus Isaac, inkl. Effort falls vorhanden).

Diagnose:
  - Zeitverlauf alle 0,5 s: MCP/PIP/DIP-Ist, Δ zur Kopplung, MCP-Effort
  - Gelenkbereich: PIP/DIP dürfen nicht aus [-5°, 95°] ausbrechen (alter Fehler: PIP -87,8°)
  - Kopplung unter Last: |Δ PIP/DIP − MCP| am Ende ≤ --tol (Standard 3°)
  - MCP-Effort max/final (falls Isaac Effort publiziert) gegen maxForce 2,94 Nm
  - Chattern: Spannweite des MCP in den letzten 2 s (> 5° = kein Stall, sondern Schwingen),
    max. Winkelgeschwindigkeit, Verletzung der MCP-Grenzen [0°, 90°]
  - NaN in /pib/hw/joint_states = Simulation numerisch explodiert -> Abbruch (Stop -> Play)

Alter Referenzwert (ohne Mimic, mit/ohne Rückwirkung): MCP blieb bei 82,7° stehen.

Voraussetzung:
  1. Isaac Sim läuft (pib_upperbody_v5.usd, start.py ausgeführt → Mimic Joints gesetzt, Play)
  2. ros2 launch pib_bringup pib_sim_v5.launch.py

Start:
  ros2 run pib_bringup test_client_mimic_load_v5                      # index_left
  ros2 run pib_bringup test_client_mimic_load_v5 --finger fingers_left # alle 4 Finger links
  ros2 run pib_bringup test_client_mimic_load_v5 --skip-arm            # Arm schon in Pose
  ros2 run pib_bringup test_client_mimic_load_v5 --reset               # danach zurück auf 0
  ros2 run pib_bringup test_client_mimic_load_v5 --reset-only          # nur zurücksetzen

Exit-Code 0 = bestanden, 1 = Gelenkbereich/Kopplung verletzt, 2 = Goal fehlgeschlagen/keine Daten.
"""
import argparse
import math
import sys

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.utilities import remove_ros_args
from control_msgs.action import FollowJointTrajectory
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectoryPoint
from builtin_interfaces.msg import Duration

ARM_JOINTS = ["shoulder_vertical_left", "shoulder_horizontal_left", "upper_arm_left",
              "elbow_left", "forearm_left", "wrist_left"]
ARM_TEST_POSE = [1.4050, 1.5708, 0.1152, 0.4677, 1.5708, 0.0]  # rad
ARM_MOVE_S = 3.0
ARM_TOL_DEG = 2.0

FINGERS_LEFT = ("index_left", "middle_left", "ring_left", "pinky_left")
RANGE_MIN_DEG, RANGE_MAX_DEG = -5.0, 95.0
STALL_MIN_DEG = 3.0          # MCP bleibt mindestens so weit vor dem Ziel stehen -> Ziel nicht erreicht
CHATTER_WINDOW_S = 2.0       # Fenster am Ende für die Chatter-Auswertung
CHATTER_MAX_DEG = 5.0        # Spannweite MCP im Fenster, ab der es kein Stall mehr ist
MCP_LIMIT_DEG = (-1.0, 91.0) # MCP-Grenzen [0°, 90°] mit 1° Toleranz
MCP_MAX_FORCE_NM = 2.94      # ST3215, siehe isaac_sim/setup_stage.py
TOPIC = "/pib/hw/joint_states"


def _joints(finger: str) -> tuple:
    return f"{finger}_proximal", f"{finger}_distal", f"{finger}_tip"   # MCP, PIP, DIP


class PibMimicLoadTestV5(Node):

    def __init__(self):
        super().__init__("pib_mimic_load_test_v5")
        self._ac = ActionClient(self, FollowJointTrajectory, "/joint_trajectory_controller/follow_joint_trajectory")
        self.create_subscription(JointState, TOPIC, self._cb, 50)
        self.t0 = None
        self.rows = []      # (t, {name: rad}, {name: effort}, {name: rad/s})
        self.latest = {}    # name -> rad
        self.has_effort = False

    def _cb(self, msg: JointState):
        pos = dict(zip(msg.name, msg.position))
        self.latest = pos
        if self.t0 is None:
            return
        eff = dict(zip(msg.name, msg.effort)) if len(msg.effort) == len(msg.name) else {}
        vel = dict(zip(msg.name, msg.velocity)) if len(msg.velocity) == len(msg.name) else {}
        self.has_effort |= any(abs(v) > 1e-9 for v in eff.values())
        t = (self.get_clock().now() - self.t0).nanoseconds * 1e-9
        self.rows.append((t, pos, eff, vel))

    def run_goal(self, names, waypoints, label, record=False) -> bool:
        """waypoints: [(sec, [rad,...])]. Wartet auf das Ergebnis. Bei record=True: t=0 bei Goal-Annahme."""
        self._ac.wait_for_server()
        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = list(names)
        for sec, positions in waypoints:
            pt = JointTrajectoryPoint()
            pt.positions = list(positions)
            pt.time_from_start = Duration(sec=int(sec), nanosec=int((sec % 1) * 1e9))
            goal.trajectory.points.append(pt)

        fut = self._ac.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, fut)
        handle = fut.result()
        if not handle.accepted:
            self.get_logger().error(f"{label}: Goal abgelehnt")
            return False
        if record:
            self.rows.clear()
            self.t0 = self.get_clock().now()
        res = handle.get_result_async()
        rclpy.spin_until_future_complete(self, res)
        code = res.result().result.error_code
        if code != 0:
            self.get_logger().error(f"{label}: error_code={code}")
            return False
        return True

    def settle(self, seconds: float):
        end = self.get_clock().now().nanoseconds + int(seconds * 1e9)
        while rclpy.ok() and self.get_clock().now().nanoseconds < end:
            rclpy.spin_once(self, timeout_sec=0.05)


def _mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def _deg(x):
    return math.degrees(x)


def has_nan(positions: dict) -> bool:
    return any(math.isnan(v) or math.isinf(v) for v in positions.values())


def check_arm(node: PibMimicLoadTestV5) -> bool:
    print("\n=== Arm-Testpose (Soll vs. Ist) ===")
    ok = True
    for name, soll in zip(ARM_JOINTS, ARM_TEST_POSE):
        ist = node.latest.get(name)
        if ist is None:
            print(f"  {name:<26} keine Daten")
            ok = False
            continue
        err = _deg(ist - soll)
        good = abs(err) <= ARM_TOL_DEG
        ok &= good
        print(f"  {name:<26} soll {_deg(soll):7.1f}°  ist {_deg(ist):7.1f}°  Δ{err:+6.1f}°  {'OK' if good else 'ABWEICHUNG'}")
    if not ok:
        print("  -> Arm nicht in Pose (Kollision/Limit?). Tischtest nicht aussagekräftig.")
    return ok


def report(node: PibMimicLoadTestV5, fingers: list, target_deg: float, tol_deg: float) -> int:
    rows = node.rows
    if not rows:
        node.get_logger().error(f"Keine {TOPIC}-Daten empfangen.")
        return 2
    if any(has_nan(p) for _, p, _, _ in rows):
        first = next(t for t, p, _, _ in rows if has_nan(p))
        print(f"\nABBRUCH: NaN/Inf in {TOPIC} ab t={first:.1f} s — Simulation numerisch explodiert.")
        print("  Isaac: Stop -> Play (start.py erneut), Ergebnisse dieses Laufs sind unbrauchbar.")
        return 2
    t_end = rows[-1][0]
    failed = False

    for finger in fingers:
        mcp, pip, dip = _joints(finger)
        series = [(t, p[mcp], p[pip], p[dip], e.get(mcp), e.get(pip), e.get(dip), v.get(mcp))
                  for t, p, e, v in rows if mcp in p and pip in p and dip in p]
        if not series:
            print(f"\n{finger}: keine Daten")
            failed = True
            continue

        print(f"\n=== {finger}: Zeitverlauf (Soll-MCP → {target_deg:.0f}°) ===")
        eff_hdr = "  MCP-Effort" if node.has_effort else ""
        print(f"{'t[s]':>5}{'MCP':>9}{'PIP':>9}{'DIP':>9}{'Δ PIP':>9}{'Δ DIP':>9}{eff_hdr}")
        next_print = 0.0
        for t, m, p, d, em, _, _, _ in series:
            if t < next_print:
                continue
            next_print += 0.5
            eff = f"{em:>10.2f} Nm" if (node.has_effort and em is not None) else ""
            print(f"{t:5.1f}{_deg(m):8.1f}°{_deg(p):8.1f}°{_deg(d):8.1f}°{_deg(p - m):+8.2f}°{_deg(d - m):+8.2f}° {eff}")

        last = [s for s in series if s[0] >= t_end - 0.5]
        m_f = _deg(_mean([s[1] for s in last]))
        p_f = _deg(_mean([s[2] for s in last]))
        d_f = _deg(_mean([s[3] for s in last]))
        p_all = [_deg(s[2]) for s in series]
        d_all = [_deg(s[3]) for s in series]
        stall = target_deg - m_f
        delta_p, delta_d = p_f - m_f, d_f - m_f

        print(f"\n--- Auswertung {finger} ---")
        print(f"  MCP final {m_f:.1f}° (Ziel {target_deg:.0f}°, Rest {stall:.1f}°)   "
              f"PIP final {p_f:.1f}°   DIP final {d_f:.1f}°")
        print(f"  PIP Bereich [{min(p_all):.1f}°, {max(p_all):.1f}°]   DIP Bereich [{min(d_all):.1f}°, {max(d_all):.1f}°]")
        print(f"  Δ final: PIP {delta_p:+.2f}°  DIP {delta_d:+.2f}°   "
              f"max |Δ| über die Fahrt: PIP {max(abs(_deg(s[2] - s[1])) for s in series):.1f}°  "
              f"DIP {max(abs(_deg(s[3] - s[1])) for s in series):.1f}°")

        efforts = [abs(s[4]) for s in series if s[4] is not None]
        if node.has_effort and efforts:
            print(f"  MCP-Effort: max {max(efforts):.2f} Nm, final {_mean([abs(s[4]) for s in last if s[4] is not None]):.2f} Nm "
                  f"(maxForce {MCP_MAX_FORCE_NM:.2f} Nm)")
        else:
            print("  MCP-Effort: von Isaac nicht publiziert (alle 0/leer) — nicht auswertbar")

        win = [s for s in series if s[0] >= t_end - CHATTER_WINDOW_S]
        win_mcp = [_deg(s[1]) for s in win]
        span = max(win_mcp) - min(win_mcp)
        speeds = [abs(s[7]) for s in series if s[7] is not None]
        v_max = _deg(max(speeds)) if speeds else float("nan")
        mcp_all = [_deg(s[1]) for s in series]
        limit_viol = sum(1 for m in mcp_all if m < MCP_LIMIT_DEG[0] or m > MCP_LIMIT_DEG[1])
        t_contact = next((s[0] for s in series if s[0] > 0.6 and abs(_deg(s[2] - s[1])) > tol_deg), None)

        in_range = min(p_all + d_all) >= RANGE_MIN_DEG and max(p_all + d_all) <= RANGE_MAX_DEG
        coupled = abs(delta_p) <= tol_deg and abs(delta_d) <= tol_deg
        steady = span <= CHATTER_MAX_DEG
        print(f"  MCP letzte {CHATTER_WINDOW_S:g} s: Spannweite {span:.1f}°   max. Winkelgeschwindigkeit {v_max:.0f}°/s   "
              f"MCP außerhalb [0°,90°]: {limit_viol} Samples")
        if t_contact is not None:
            print(f"  Kopplung bricht (|Δ PIP| > {tol_deg:g}°) erstmals bei t={t_contact:.2f} s")
        print(f"  [{'OK' if in_range else 'FEHLER'}] Gelenkbereich PIP/DIP in [{RANGE_MIN_DEG:.0f}°, {RANGE_MAX_DEG:.0f}°]")
        print(f"  [{'OK' if coupled else 'FEHLER'}] Kopplung unter Last: |Δ final| ≤ {tol_deg:g}°")
        print(f"  [{'OK' if steady else 'FEHLER'}] Ruhe unter Last: MCP-Spannweite ≤ {CHATTER_MAX_DEG:g}° (sonst Chattern, kein Stall)")
        print(f"  [{'OK' if limit_viol == 0 else 'FEHLER'}] MCP-Grenzen eingehalten")
        print("  [INFO] " + (f"MCP erreicht das Ziel nicht (Rest {stall:.1f}°)" if stall >= STALL_MIN_DEG
                               else "MCP erreicht das Ziel — kein Kontakt erkennbar (Handpose/Tischhöhe prüfen)"))
        failed |= not (in_range and coupled and steady and limit_viol == 0)

    # Arm-Beteiligung: Bewegt sich der Arm, während die Finger gegen den Tisch drücken?
    print("\n=== Arm-Drift während der Fingerphase (Δ gegenüber Start der Phase) ===")
    first = rows[0][1]
    for name in ARM_JOINTS:
        series_a = [_deg(p[name] - first[name]) for _, p, _, _ in rows if name in p and name in first]
        if not series_a:
            print(f"  {name:<26} keine Daten")
            continue
        worst = max(series_a, key=abs)
        onset = next((tt for (tt, p, _, _) in rows
                      if name in p and name in first and abs(_deg(p[name] - first[name])) > 1.0), None)
        flag = f"  <-- bewegt sich ab t={onset:.2f} s" if onset is not None else ""
        print(f"  {name:<26} max |Δ| {abs(worst):8.2f}°  (Ende {series_a[-1]:+8.2f}°){flag}")

    print(f"\nGesamt: {'FEHLGESCHLAGEN' if failed else 'BESTANDEN'}")
    return 1 if failed else 0


def main(args=None):
    parser = argparse.ArgumentParser(description="Mimic-Joint-Lasttest v5 (Finger gegen Tisch)")
    parser.add_argument("--finger", default="index_left",
                        help=f"{', '.join(FINGERS_LEFT)} oder 'fingers_left' (Standard: index_left)")
    parser.add_argument("--close-time", type=float, default=4.0, help="Dauer 0°→Ziel in s (Standard 4)")
    parser.add_argument("--hold", type=float, default=3.0, help="Haltezeit am Ziel in s (Standard 3)")
    parser.add_argument("--target", type=float, default=90.0, help="MCP-Zielwinkel in Grad (Standard 90)")
    parser.add_argument("--tol", type=float, default=3.0, help="Toleranz Δ final in Grad (Standard 3)")
    parser.add_argument("--skip-arm", action="store_true", help="Arm nicht bewegen (schon in Testpose)")
    parser.add_argument("--reset", action="store_true", help="Arm + Finger danach auf 0 zurück")
    parser.add_argument("--reset-only", action="store_true", help="nur zurücksetzen, kein Test")
    ns = parser.parse_args(remove_ros_args(sys.argv if args is None else args)[1:])

    if ns.finger == "fingers_left":
        fingers = list(FINGERS_LEFT)
    elif ns.finger in FINGERS_LEFT:
        fingers = [ns.finger]
    else:
        parser.error(f"unbekannter Finger '{ns.finger}'")

    mcps = [_joints(f)[0] for f in FINGERS_LEFT]

    rclpy.init(args=args)
    node = PibMimicLoadTestV5()

    def reset() -> bool:
        node.get_logger().info("Reset: linker Arm + Finger-MCPs → 0° ...")
        return node.run_goal(ARM_JOINTS + mcps, [(3.0, [0.0] * (len(ARM_JOINTS) + len(mcps)))], "Reset")

    code = 0
    if ns.reset_only:
        code = 0 if reset() else 2
    else:
        node.settle(1.5)   # DDS-Discovery + erste joint_states abwarten
        if not node.latest:
            node.get_logger().error(f"Keine {TOPIC}-Daten — läuft Isaac (Play) und die Bridge?")
            sys.exit(2)
        if has_nan(node.latest):
            node.get_logger().error("Gelenkzustand enthält NaN — Simulation numerisch explodiert. "
                                    "Isaac: Stop -> Play (start.py), dann erneut starten.")
            sys.exit(2)
        if not ns.skip_arm:
            node.get_logger().info(f"1/2: Arm in Testpose ({ARM_MOVE_S:.0f} s) ...")
            if not node.run_goal(ARM_JOINTS, [(ARM_MOVE_S, ARM_TEST_POSE)], "Arm"):
                code = 2
            node.settle(1.0)
        if code == 0:
            check_arm(node)
            node.get_logger().info(
                f"2/2: {', '.join(fingers)}: MCP 0° → {ns.target:.0f}° in {ns.close_time:g} s, dann {ns.hold:g} s halten ...")
            names = [_joints(f)[0] for f in fingers]
            target = math.radians(ns.target)
            wps = [(0.5, [0.0] * len(names)),
                   (0.5 + ns.close_time, [target] * len(names)),
                   (0.5 + ns.close_time + ns.hold, [target] * len(names))]
            if not node.run_goal(names, wps, "Finger", record=True):
                code = 2
            else:
                node.settle(0.3)
                code = report(node, fingers, ns.target, ns.tol)
        if ns.reset:
            reset()

    node.destroy_node()
    rclpy.shutdown()
    sys.exit(code)


if __name__ == "__main__":
    main()
