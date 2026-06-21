"""
control/servo.py — Virtueller Servo: Servo-Winkel → Fingergelenk-Winkel.

Schnittstelle identisch zu direct.py und neural.py:
  compute_joint_targets(input_dict: dict, side: str) -> dict

input_dict : {servo_name: angle_deg}
  Bekannte Servo-Namen: thumb_opp, thumb, index, middle, ring, pinky
  Fehlende Servos werden als 0° angenommen.

Kopplung (aus _SERVO_FACTORS in config):
  Alle Gelenke eines Fingers × 1.0 — jedes Gelenk folgt dem Servo direkt.
  Das Handgelenk ist kein Servo-gekoppeltes Gelenk (Body-DOF).
"""
import importlib
import importlib.util
from pathlib import Path

# Isaac-Sim-safe Config-Reload (verhindert stale .pyc-Bytecode)
importlib.invalidate_caches()
import sys as _sys
_sys.modules.pop("pib_hand_config", None)
_cfg_path = Path(__file__).parent.parent / "config" / "pib_hand_config.py"
_spec = importlib.util.spec_from_file_location("pib_hand_config", _cfg_path)
_cfg  = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cfg)

_servo_pose_to_joints = _cfg.servo_pose_to_joints


def compute_joint_targets(input_dict: dict, side: str = "left") -> dict:
    """
    Virtueller Servo → 15 DOF-Winkel (lineare Näherung).

    Parameters
    ----------
    input_dict : {servo_name: angle_deg}  — 0° = offen, 90° = geschlossen
    side       : "left" oder "right"

    Returns
    -------
    {dof_name: angle_deg}  — 15 Einträge, alle in Grad (0–90°)
    """
    return _servo_pose_to_joints(input_dict, side)
