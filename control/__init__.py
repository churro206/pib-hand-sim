# control/ — ControlMode-Architektur (Sprint 2)
#
# base.py:   ControlMode ABC — to_joint_targets(command) -> dict
# direct.py: DirectMode   — {dof_name: deg} pass-through
# servo.py:  ServoMode    — {servo_name: deg} → DOF-Winkel via Sehnenkopplung
# nn.py:     NNMode       — LSTM-Inferenz (Phase 5, Stub)
from control.base   import ControlMode
from control.direct import DirectMode
from control.servo  import ServoMode
from control.nn     import NNMode
