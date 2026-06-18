# _deprecated/

Diese Skripte werden nicht mehr benötigt und können ignoriert werden.

## fix_joints.py / unfix_joints.py

Froren Nicht-Hand-Gelenke ein (stiffness=∞) damit Schwerkraft den Roboter
nicht zusammensacken lässt. Nötig war das weil die Gelenke keine aktiven
Drives hatten.

**Ersatz:** `setup_stage.py configure_drives()` — setzt für alle Gelenke
physikalisch sinnvolle Stiffness/Damping-Werte. Der Roboter hält sich damit
selbst aufrecht, ohne dass Gelenke eingefroren werden müssen.
