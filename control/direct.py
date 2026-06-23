from control.base import ControlMode


class DirectMode(ControlMode):
    """Direktsteuerung — command ist bereits {dof_name: angle_deg}, pass-through."""

    def to_joint_targets(self, command: dict) -> dict:
        return dict(command)
