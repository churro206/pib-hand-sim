"""
phases/phase1_direct.py — Phase 1: Direkte Gelenkwinkel (Identity-Mapping).

Schnittstelle ist identisch zu Phase 2 und Phase 3 — nur die Logik ändert sich:
  Phase 1: input_dict sind direkte Gelenkwinkel → 1:1 weitergeben
  Phase 2: input_dict sind Servo-Werte → Sehnenkopplung anwenden
  Phase 3: input_dict sind Servo-Werte + LSTM → präzise Winkel ausgeben
"""


def compute_joint_targets(input_dict: dict, side: str = "left") -> dict:
    """
    Phase 1 — Identity. Gibt input_dict unverändert zurück.

    Parameters
    ----------
    input_dict : {dof_name: angle_deg}  — direkte Gelenkwinkel in Grad
    side       : "left" oder "right"  — für Konsistenz mit Phase 2/3, hier ungenutzt

    Returns
    -------
    {dof_name: angle_deg}  — identisch mit input_dict
    """
    return dict(input_dict)
