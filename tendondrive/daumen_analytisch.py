"""Analytische Kopplung des Daumens (Skizze Daumen, Ursprung = linke untere Ecke, mm).
Gelenk 1 (unten): (9.3, 13)   Kurbel Pin bei 225 deg, r = 7.4 mm (am Basisteil)
Gelenk 2 (oben):  (7.5, 58)   Schwinge Pin bei 315 deg, r = 7.4 mm (am Endglied)
theta_2 = F(theta_1), gleiche Formel wie beim Finger."""
import numpy as np
from finger_analytisch import Viergelenk

G1 = np.array([9.3, 13.0])
G2 = np.array([7.5, 13.0 + 45.0])
R_DAUMEN = 7.4
F_D = Viergelenk(G1, G2, r=R_DAUMEN)

if __name__ == "__main__":
    print(f"Steg {np.linalg.norm(G2-G1):.3f} mm, Koppel L = {F_D.L:.3f} mm, Zweig s = {F_D.s:+.0f}, "
          f"Totpunkt bei Gelenk 1 = {np.degrees(F_D.totpunkt()):.1f} deg")
    for d in (0, 15, 30, 45, 60, 75, 90):
        t = np.radians(d)
        print(f"G1 {d:3d} -> G2 {np.degrees(F_D(t)):6.2f}   dG2/dG1 {F_D.uebersetzung(t):.3f}")
