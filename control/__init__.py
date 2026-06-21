# control/ — Steuerlogik zwischen Eingabe und robot_io
#
# direct.py: Direktsteuerung — Gelenkwinkel 1:1 weitergeben         [vorhanden]
# servo.py:  Virtueller Servo → DOF-Winkel (lineare Näherung, 1:1)  [vorhanden]
# neural.py: LSTM-Inferenz — Servo-Werte + Sensorik → präzise Winkel [ausstehend]
#
# Alle Module teilen dieselbe Signatur:
#   compute_joint_targets(input_dict: dict, side: str) -> dict
