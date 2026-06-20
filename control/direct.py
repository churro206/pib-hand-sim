"""
control/direct.py — Direktsteuerung: Gelenkwinkel 1:1 weitergeben (Identity-Mapping).

Schnittstelle ist identisch zu servo.py und neural.py — nur die Logik ändert sich:
  direct: input_dict sind direkte Gelenkwinkel → 1:1 weitergeben
  servo:  input_dict sind Servo-Werte → Sehnenkopplung anwenden
  neural: input_dict sind Servo-Werte + LSTM → präzise Winkel ausgeben
"""


def compute_joint_targets(input_dict: dict, side: str = "left") -> dict:
    """
    Direktsteuerung — Identity. Gibt input_dict unverändert zurück.

    Parameters
    ----------
    input_dict : {dof_name: angle_deg}  — direkte Gelenkwinkel in Grad
    side       : "left" oder "right"  — für Konsistenz mit servo/neural, hier ungenutzt

    Returns
    -------
    {dof_name: angle_deg}  — identisch mit input_dict
    """
    return dict(input_dict)
