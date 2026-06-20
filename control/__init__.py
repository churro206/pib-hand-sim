# control/ — Steuerlogik zwischen Eingabe und robot_io
#
# direct.py: Direktsteuerung — Gelenkwinkel 1:1 weitergeben
# servo.py:  Sehnenkopplung — Servo-Werte → DOF-Winkel (lineare Näherung)
# neural.py: LSTM-Inferenz — Servo-Werte + Sensorik → präzise Winkel
#
# Alle Module teilen dieselbe Signatur:
#   compute_joint_targets(input_dict: dict, side: str) -> dict
