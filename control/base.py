from abc import ABC, abstractmethod


class ControlMode(ABC):
    @abstractmethod
    def to_joint_targets(self, command: dict) -> dict:
        """command → {dof_name: winkel_deg} (Onshape-Konvention)"""
