"""
Legt in Isaac Sim einen Action Graph an, der jeden Finger ueber EINEN Wert steuert.
Ablauf pro Frame:  OnPlaybackTick -> ScriptNode (LUT: MCP -> MCP, PIP, DIP) -> ArticulationController

Ausfuehren im Script Editor von Isaac Sim (Window > Script Editor).
Danach steht der Wert "inputs:finger_deg" am Knoten "FingerLUT" im Property-Fenster.
Du kannst dort Werte eintippen oder den Eingang mit einem anderen Knoten verbinden
(zum Beispiel ROS2 Subscribe JointState oder einer Graph-Variablen).
"""
import omni.graph.core as og

# ---- Anpassen ------------------------------------------------------------
ROBOT_PRIM = "/World/Hand"                       # Prim mit ArticulationRootAPI
CSV_PATH = "/pfad/zu/finger_kopplung.csv"        # CSV aus finger_kinematik.py
FINGERS = ["index", "middle"]                    # ein Eintrag pro Finger
JOINTS = {                                       # Gelenknamen aus deinem USD/URDF
    "index":  ["index_mcp", "index_pip", "index_dip"],
    "middle": ["middle_mcp", "middle_pip", "middle_dip"],
}
GRAPH_PATH = "/World/FingerCouplingGraph"
# Isaac Sim >= 4.5: "isaacsim.core.nodes...", aeltere Versionen: "omni.isaac.core_nodes..."
CONTROLLER_TYPE = "isaacsim.core.nodes.IsaacArticulationController"
# --------------------------------------------------------------------------

SCRIPT = r'''
import numpy as np

def setup(db):
    lut = np.loadtxt(db.inputs.csv_path, delimiter=",", skiprows=1)
    s = db.per_instance_state
    s.mcp, s.pip, s.dip = (np.radians(lut[:, i]) for i in range(3))

def compute(db):
    s = db.per_instance_state
    cmd = np.radians(np.asarray(db.inputs.finger_deg, dtype=float))
    cmd = np.clip(cmd, s.mcp[0], min(s.mcp[-1], np.radians(90.0)))  # Totpunkt vermeiden
    pip = np.interp(cmd, s.mcp, s.pip)
    dip = np.interp(cmd, s.mcp, s.dip)
    # Reihenfolge: Finger1 (MCP, PIP, DIP), Finger2 (MCP, PIP, DIP), ...
    db.outputs.position_command = np.stack([cmd, pip, dip], axis=1).ravel().tolist()
    return True
'''

joint_names = [j for f in FINGERS for j in JOINTS[f]]

og.Controller.edit(
    {"graph_path": GRAPH_PATH, "evaluator_name": "execution"},
    {
        og.Controller.Keys.CREATE_NODES: [
            ("Tick", "omni.graph.action.OnPlaybackTick"),
            ("FingerLUT", "omni.graph.scriptnode.ScriptNode"),
            ("Controller", CONTROLLER_TYPE),
        ],
        og.Controller.Keys.CREATE_ATTRIBUTES: [
            ("FingerLUT.inputs:finger_deg", "double[]"),
            ("FingerLUT.inputs:csv_path", "string"),
            ("FingerLUT.outputs:position_command", "double[]"),
        ],
        og.Controller.Keys.SET_VALUES: [
            ("FingerLUT.inputs:script", SCRIPT),
            ("FingerLUT.inputs:csv_path", CSV_PATH),
            ("FingerLUT.inputs:finger_deg", [0.0] * len(FINGERS)),
            ("Controller.inputs:robotPath", ROBOT_PRIM),
            ("Controller.inputs:jointNames", joint_names),
        ],
        og.Controller.Keys.CONNECT: [
            ("Tick.outputs:tick", "FingerLUT.inputs:execIn"),
            ("FingerLUT.outputs:execOut", "Controller.inputs:execIn"),
            ("FingerLUT.outputs:position_command", "Controller.inputs:positionCommand"),
        ],
    },
)
print("Action Graph angelegt:", GRAPH_PATH, "| Gelenke:", joint_names)
