"""
patch_finger_coupling_script.py — Aktualisiert NUR den inputs:script-Text des
bereits vorhandenen FingerCoupling-Knotens in /Graph/ROS_JointStates.

Fix (2026-09-27): NameError: name 'np' is not defined, aufgetreten beim Aufbau
von MCP_PIP = FourBar(...) auf Modulebene. Die Script-Node-Sandbox von Isaac
Sim execut Top-Level-Code offenbar mit getrennten globals/locals-Dicts --
`import numpy as np` landet nur im locals-Dict, Methoden einer auf Modulebene
definierten Klasse bekommen aber das (numpy-lose) globals-Dict als
__globals__ und sehen `np` deshalb nicht, sobald sie aufgerufen werden.
Fix: Klasse + Instanzen als Closures innerhalb von setup(db) anlegen,
Instanzen in db.per_instance_state ablegen -- schliesst korrekt ueber
setup()s eigenen Laufzeit-Namensraum, unabhaengig vom Sandbox-Mechanismus.
Siehe isaac_sim/tools/finger_coupling_script_node.py fuer den vollstaendigen,
kommentierten Stand.

Ausserdem: Ausgabeliste (jointNames/positionCommand) wird um neu berechnete
Gelenke erweitert statt auf die eingehende ROS2-Kommandoliste beschraenkt zu
bleiben -- sonst bekommt der ArticulationController leere Arrays, wenn (noch)
kein ROS2-Kommando eingetroffen ist.

Rührt NUR das inputs:script-Attribut an -- keine Knoten/Verbindungen werden
neu angelegt (im Gegensatz zu build_finger_coupling_graph.py, das den Graphen
erstmalig aufgebaut hat).

WICHTIG: setup(db) legt db.per_instance_state neu an und läuft laut
Isaac-Sim-Doku beim nächsten compute() nach einer Skript-Änderung erneut --
sicherheitshalber trotzdem einmal Stop -> Play, falls sich nichts tut.

Im Script Editor ausführen, bei geöffneter pib_upperbody_v5.usd.
"""
import omni.usd

stage = omni.usd.get_context().get_stage()

NODE_PATH = "/Graph/ROS_JointStates/FingerCoupling"

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

prim = stage.GetPrimAtPath(NODE_PATH)
if not prim:
    raise RuntimeError(f"Node nicht gefunden: {NODE_PATH} -- ist die Stage korrekt geladen?")

attr = prim.GetAttribute("inputs:script")
if not attr:
    raise RuntimeError(f"Attribut inputs:script an {NODE_PATH} nicht gefunden.")

attr.Set(FINGER_COUPLING_SCRIPT)
print(f"inputs:script an {NODE_PATH} aktualisiert (Fix: Closures statt Modulebene, "
      f"Ausgabeliste um neue Gelenke erweitert).")
print("Danach zur Sicherheit einmal Stop -> Play, damit setup() sauber neu laeuft.")
