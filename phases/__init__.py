# phases/ — Phasen-spezifische Logik für pib-Hand-Sim
#
# Phase 1 (phase1_direct.py): Identity — direkte Gelenkwinkel, keine Transformation
# Phase 2 (phase2_linear.py): Sehnenkopplung — Servo-Werte → 15 DOF-Winkel
# Phase 3 (phase3_lstm.py):   LSTM — Servo-Werte + Sensorik → präzise Winkel
#
# Alle Phasen teilen dieselbe Signatur:
#   compute_joint_targets(input_dict: dict, side: str) -> dict
