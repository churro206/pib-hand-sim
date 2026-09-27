"""
build_finger_coupling_graph.py — Hängt die analytische Finger-/Daumenkopplung in
den bestehenden Action Graph /Graph/ROS_JointStates von pib_upperbody_v5.usd ein.

Hintergrund: tendondrive/PROMPT_sehnendynamik_isaac.md. MCP (Fingergrundgelenk)
bleibt normale ROS2-Positions-Drive wie bisher. PIP/DIP (Finger) bzw. IP (Daumen)
bekommen ihren Zielwinkel jeden Tick aus dem GEMESSENEN Ist-Winkel des jeweils
vorgelagerten Gelenks berechnet (Viergelenk-Kopplung, siehe
isaac_sim/tools/finger_coupling_script_node.py), statt einen eigenen Wert aus
ROS2 zu bekommen. Kein Sehnen-/Kraftmodell, keine Effort-Steuerung — reine
kinematische Umleitung der Positions-Commands.

Bestandsaufnahme (isaac_sim/tools/inspect_action_graph.py):
  ArticulationController.inputs:jointNames        <- SubscriberJointState.outputs:jointNames
  ArticulationController.inputs:positionCommand   <- SubscriberJointState.outputs:positionCommand
  ArticulationController.inputs:execIn            <- OnPlaybackTick.outputs:tick  (NICHT über
                                                       SubscriberJointState.outputs:execOut!)
Alle Knoten in diesem Graph hängen direkt und parallel an OnPlaybackTick, nicht
verkettet — Datenwerte werden unabhängig vom Exec-Trigger zwischengehalten. Die
neuen Knoten folgen demselben Muster (kein On Physics Step, um nicht einen
zweiten, konkurrierenden Trigger auf denselben Controller zu legen).

Ändert NUR:
  - fügt MeasuredJointState und FingerCoupling neu hinzu
  - hängt ArticulationController.inputs:jointNames/positionCommand um (FingerCoupling
    statt SubscriberJointState)
  effortCommand/velocityCommand, alle anderen Knoten (Publisher, Contact Sensor,
  Context, ReadSimTime) bleiben unverändert.

WICHTIG:
  - Vor dem Ausführen: Stage sichern/Backup (siehe Absprache — direkt in
    pib_upperbody_v5.usd, wie bei flip_joint_sign.py/ADR-008 üblich).
  - Danach im Action-Graph-Editor visuell prüfen, dann Play, dann erst Ctrl+S.

Im Script Editor ausführen, bei geöffneter pib_upperbody_v5.usd.
"""
import omni.graph.core as og
import omni.usd
from pxr import Sdf

stage = omni.usd.get_context().get_stage()

GRAPH_PATH = "/Graph/ROS_JointStates"
ROBOT_ROOT = "/World/pib_upperbody_urdf_v5/root_joint"

_SIDES = ("left", "right")
_FINGERS = ("index", "middle", "ring", "pinky")


def _measured_joint_names():
    names = []
    for side in _SIDES:
        for finger in _FINGERS:
            names.append(f"{finger}_{side}_proximal")
            names.append(f"{finger}_{side}_distal")
        names.append(f"thumb_{side}_proximal")
    return names


MEASURED_JOINTS = _measured_joint_names()
assert len(MEASURED_JOINTS) == 18, len(MEASURED_JOINTS)

# Inhalt aus isaac_sim/tools/finger_coupling_script_node.py (dort auch dokumentiert
# und gegen die Referenztabelle aus dem Prompt validiert).
# WICHTIG: alles (Klasse + Instanzen) innerhalb von setup(db) definieren, NICHT
# auf Modulebene -- sonst NameError: name 'np' is not defined beim Aufruf der
# Methoden (Script-Node-Sandbox execut Top-Level-Code offenbar mit getrennten
# globals/locals-Dicts, siehe finger_coupling_script_node.py fuer Details).
FINGER_COUPLING_SCRIPT = r'''
def setup(db):
    import numpy as np

    class FourBar:
        """Eine Viergelenk-Kopplungsstufe: theta_out = F(theta_in).
        Herleitung: tendondrive/finger_analytisch.py."""

        def __init__(self, o1, o2, r, alpha, beta):
            self.o1 = np.array(o1, dtype=float)
            self.o2 = np.array(o2, dtype=float)
            self.r, self.alpha, self.beta = r, alpha, beta
            a0 = self.o1 + r * np.array([np.cos(alpha), np.sin(alpha)])
            b0 = self.o2 + r * np.array([np.cos(beta), np.sin(beta)])
            self.l = np.linalg.norm(b0 - a0)
            self.s = 1.0
            if abs(self._raw(np.array(0.0))) > 1e-9:
                self.s = -1.0
            self.work_max = min(np.radians(90.0), self._totpunkt())

        def _raw(self, t_in):
            t_in = np.asarray(t_in, dtype=float)
            a = self.o1 + self.r * np.stack([np.cos(self.alpha - t_in), np.sin(self.alpha - t_in)], axis=-1)
            d = self.o2 - a
            dn = np.linalg.norm(d, axis=-1)
            k = (self.l ** 2 - dn ** 2 - self.r ** 2) / (2 * self.r)
            phi = np.arctan2(d[..., 1], d[..., 0]) + self.s * np.arccos(np.clip(k / dn, -1.0, 1.0))
            t_out = phi - self.beta
            return (t_out + np.pi) % (2 * np.pi) - np.pi

        def _totpunkt(self):
            t = np.radians(np.linspace(0.0, 179.0, 17901))
            a = self.o1 + self.r * np.stack([np.cos(self.alpha - t), np.sin(self.alpha - t)], axis=-1)
            dn = np.linalg.norm(self.o2 - a, axis=-1)
            k = (self.l ** 2 - dn ** 2 - self.r ** 2) / (2 * self.r)
            ok = np.abs(k) <= dn
            idx = int(np.argmin(ok)) if not ok.all() else len(t) - 1
            return float(t[idx])

        def __call__(self, t_in):
            t_in = np.clip(np.asarray(t_in, dtype=float), 0.0, self.work_max)
            return float(self._raw(t_in))

    alpha = np.radians(225.0)
    beta = np.radians(315.0)

    s = db.per_instance_state
    s.mcp_pip = FourBar((9.3, 38.0), (8.4, 74.0), 7.0, alpha, beta)
    s.pip_dip = FourBar((8.4, 74.0), (7.5, 105.0), 7.0, alpha, beta)
    s.thumb = FourBar((9.3, 13.0), (7.5, 58.0), 7.4, alpha, beta)


def compute(db):
    s = db.per_instance_state
    meas = dict(zip(db.inputs.measuredJointNames, list(db.inputs.measuredJointPositions)))
    cmd_names = list(db.inputs.cmdJointNames)
    cmd = dict(zip(cmd_names, list(db.inputs.cmdPositions)))
    out_names = list(cmd_names)

    def _set(name, value):
        if name not in cmd:
            out_names.append(name)
        cmd[name] = value

    for side in ("left", "right"):
        for finger in ("index", "middle", "ring", "pinky"):
            mcp_ist = meas.get(f"{finger}_{side}_proximal")
            pip_ist = meas.get(f"{finger}_{side}_distal")
            if mcp_ist is None or pip_ist is None:
                continue
            _set(f"{finger}_{side}_distal", s.mcp_pip(mcp_ist))
            _set(f"{finger}_{side}_tip", s.pip_dip(pip_ist))
        thumb_mcp_ist = meas.get(f"thumb_{side}_proximal")
        if thumb_mcp_ist is not None:
            _set(f"thumb_{side}_tip", s.thumb(thumb_mcp_ist))

    db.outputs.jointNames = out_names
    db.outputs.positionCommand = [cmd[n] for n in out_names]
    return True
'''

og.Controller.edit(
    GRAPH_PATH,
    {
        og.Controller.Keys.CREATE_NODES: [
            ("MeasuredJointState", "isaacsim.core.nodes.IsaacArticulationState"),
            ("FingerCoupling", "omni.graph.scriptnode.ScriptNode"),
        ],
        og.Controller.Keys.CREATE_ATTRIBUTES: [
            ("FingerCoupling.inputs:measuredJointNames", "token[]"),
            ("FingerCoupling.inputs:measuredJointPositions", "double[]"),
            ("FingerCoupling.inputs:cmdJointNames", "token[]"),
            ("FingerCoupling.inputs:cmdPositions", "double[]"),
            ("FingerCoupling.outputs:jointNames", "token[]"),
            ("FingerCoupling.outputs:positionCommand", "double[]"),
        ],
        og.Controller.Keys.SET_VALUES: [
            ("MeasuredJointState.inputs:jointNames", MEASURED_JOINTS),
            ("FingerCoupling.inputs:script", FINGER_COUPLING_SCRIPT),
        ],
        og.Controller.Keys.DISCONNECT: [
            (f"{GRAPH_PATH}/SubscriberJointState.outputs:jointNames", f"{GRAPH_PATH}/ArticulationController.inputs:jointNames"),
            (f"{GRAPH_PATH}/SubscriberJointState.outputs:positionCommand", f"{GRAPH_PATH}/ArticulationController.inputs:positionCommand"),
        ],
        og.Controller.Keys.CONNECT: [
            (f"{GRAPH_PATH}/OnPlaybackTick.outputs:tick", "MeasuredJointState.inputs:execIn"),
            (f"{GRAPH_PATH}/OnPlaybackTick.outputs:tick", "FingerCoupling.inputs:execIn"),
            ("MeasuredJointState.outputs:jointNames", "FingerCoupling.inputs:measuredJointNames"),
            ("MeasuredJointState.outputs:jointPositions", "FingerCoupling.inputs:measuredJointPositions"),
            (f"{GRAPH_PATH}/SubscriberJointState.outputs:jointNames", "FingerCoupling.inputs:cmdJointNames"),
            (f"{GRAPH_PATH}/SubscriberJointState.outputs:positionCommand", "FingerCoupling.inputs:cmdPositions"),
            ("FingerCoupling.outputs:jointNames", f"{GRAPH_PATH}/ArticulationController.inputs:jointNames"),
            ("FingerCoupling.outputs:positionCommand", f"{GRAPH_PATH}/ArticulationController.inputs:positionCommand"),
        ],
    },
)

# targetPrim ist eine Relationship, nicht per SET_VALUES in CONNECT-Syntax setzbar
# -- direkt am Prim gesetzt, wie bei den anderen targetPrim-Knoten in diesem Graph.
measured_state_prim = stage.GetPrimAtPath(f"{GRAPH_PATH}/MeasuredJointState")
target_rel = measured_state_prim.GetRelationship("inputs:targetPrim")
if not target_rel:
    target_rel = measured_state_prim.CreateRelationship("inputs:targetPrim")
target_rel.SetTargets([Sdf.Path(ROBOT_ROOT)])

print(f"FingerCoupling + MeasuredJointState in {GRAPH_PATH} eingehaengt.")
print(f"Gemessene Gelenke ({len(MEASURED_JOINTS)}): {MEASURED_JOINTS}")
print("Bitte im Action-Graph-Editor pruefen, dass ArticulationController.jointNames/"
      "positionCommand jetzt von FingerCoupling kommen (nicht mehr direkt von SubscriberJointState).")
