from control.base import ControlMode


class NNMode(ControlMode):
    """LSTM-Inferenz — Phase 5, noch nicht implementiert."""

    def to_joint_targets(self, command: dict) -> dict:
        raise NotImplementedError("NNMode ist Phase 5")
