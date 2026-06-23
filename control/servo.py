"""
control/servo.py — ServoMode: Servo-Kommandos → Fingergelenk-Winkel.

command-Keys:
  servo_name (thumb_opp, thumb, index, middle, ring, pinky) → Sehnen-Mapping
  dof_*-Keys (Arm, Kopf, Handgelenk)                        → Pass-through

Nur die im command enthaltenen Keys werden zurückgegeben — fehlende Servos
zwingen andere Finger NICHT auf 0 (wichtig für persistente Teil-Kommandos).
"""
import importlib
import importlib.util
from pathlib import Path

from control.base import ControlMode

importlib.invalidate_caches()
import sys as _sys
_sys.modules.pop("pib_hand_config", None)
_cfg_path = Path(__file__).parent.parent / "config" / "pib_hand_config.py"
_spec = importlib.util.spec_from_file_location("pib_hand_config", _cfg_path)
_cfg  = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cfg)

_servo_pose_to_joints = _cfg.servo_pose_to_joints
_HAND_DOFS            = _cfg.HAND_DOFS


class ServoMode(ControlMode):
    """Virtueller Servo — command = {servo_name: deg} und/oder {dof_*: deg}."""

    def __init__(self, side: str = "left"):
        self._side = side

    def to_joint_targets(self, command: dict) -> dict:
        hand    = _HAND_DOFS[self._side]
        servos  = hand["servos"]
        result  = {}

        for key, val in command.items():
            if key.startswith("dof_"):
                result[key] = val                       # Pass-through (Body / direkt)
            elif key in servos:
                # nur die Gelenke dieses Servos expandieren
                full = _servo_pose_to_joints({key: val}, self._side)
                for usd_idx in servos[key]:
                    dof = hand["names"][hand["indices"].index(usd_idx)]
                    result[dof] = full[dof]
            else:
                print(f"[ServoMode] unbekannter Servo/DOF: {key!r} — übersprungen")

        return result
