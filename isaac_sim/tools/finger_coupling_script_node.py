"""
finger_coupling_script_node.py — Inhalt des Script-Node-Blocks "FingerCoupling"
im Action Graph von pib_upperbody_v5.usd.

Stellt den Zusammenhang zwischen MCP- und PIP/DIP- bzw. Daumen-MCP- und
IP-Gelenkwinkel her (Viergelenk-Kopplung, Formel/Geometrie validiert gegen
tendondrive/finger_analytisch.py und tendondrive/daumen_analytisch.py — siehe
dort für die Herleitung der Schließbedingung). Kein externer Import nötig,
der Block ist vollständig eigenständig (Muster wie tendondrive/finger_action_graph.py).

Erwartete Node-Attribute (beim Verkabeln anzulegen):
  inputs:measuredJointNames     token[]  <- IsaacArticulationState.outputs:jointNames
  inputs:measuredJointPositions double[] <- IsaacArticulationState.outputs:jointPositions
  inputs:cmdJointNames           token[] <- ROS2SubscribeJointState.outputs:jointNames
  inputs:cmdPositions            double[] <- ROS2SubscribeJointState.outputs:positionCommand
  outputs:jointNames             token[]  -> IsaacArticulationController.inputs:jointNames
  outputs:positionCommand        double[] -> IsaacArticulationController.inputs:positionCommand

IsaacArticulationState muss mit jointNames = den 18 unten gelesenen
"<finger>_<side>_proximal"/"<finger>_<side>_distal"/"thumb_<side>_proximal"
konfiguriert sein (gemessene Ist-Werte, geschlossener Regelkreis).

WICHTIG (Bug gefunden 2026-09-27): Alles, was Isaac Sim's Script-Node-Sandbox
braucht, MUSS innerhalb von setup()/compute() definiert werden, NICHT auf
Modulebene. Beobachteter Fehler bei Modulebene-Konstruktion (`MCP_PIP =
FourBar(...)` direkt nach `import numpy as np`):

    NameError: name 'np' is not defined

Ursache: der Sandbox-Exec fuehrt Top-Level-Code offenbar mit getrennten
globals/locals-Dicts aus. `import numpy as np` landet dabei nur im
locals-Dict, aber Methoden einer auf Modulebene definierten Klasse bekommen
als __globals__ das (numpy-lose) globals-Dict -- klassische Python-Falle bei
exec() mit getrennten globals/locals. Fix: Klasse + Instanzen als echte
Closures innerhalb von setup(db) anlegen (schliesst korrekt ueber setup()s
eigenen Laufzeit-Namensraum, unabhaengig vom Sandbox-Mechanismus), Instanzen
in db.per_instance_state ablegen -- genau das Muster aus der urspruenglichen
Referenz tendondrive/finger_action_graph.py.

Getriggert von OnPlaybackTick (nicht On Physics Step) -- an die bestehende,
bereits verifizierte Verkabelung angepasst, siehe build_finger_coupling_graph.py.
"""

SCRIPT = r'''
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
    # Geometrie aus der Onshape-Skizze (mm), fuer beide Haende identisch
    # angenommen (gespiegelt, gleiche Winkelbetraege) -- nicht separat am
    # Roboter verifiziert.
    s.mcp_pip = FourBar((9.3, 38.0), (8.4, 74.0), 7.0, alpha, beta)
    s.pip_dip = FourBar((8.4, 74.0), (7.5, 105.0), 7.0, alpha, beta)
    s.thumb = FourBar((9.3, 13.0), (7.5, 58.0), 7.4, alpha, beta)


def compute(db):
    s = db.per_instance_state
    meas = dict(zip(db.inputs.measuredJointNames, list(db.inputs.measuredJointPositions)))
    cmd_names = list(db.inputs.cmdJointNames)
    cmd = dict(zip(cmd_names, list(db.inputs.cmdPositions)))
    # Ausgabeliste separat fuehren: wenn noch nie ein ROS2-Kommando ankam (z.B.
    # manueller Test im Physics Inspector ohne laufenden ros2_control-Stack) ist
    # cmd_names leer -- die 18 gekoppelten Gelenke muessen trotzdem ausgegeben
    # werden, sonst bekommt der ArticulationController leere Arrays und bewegt
    # nichts.
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
