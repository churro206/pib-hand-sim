"""
Kinematik des gekoppelten Fingers (Onshape-Skizze "Side view").
Koordinaten in mm, Ursprung = linke untere Ecke der Skizze, y = Fingerachse.
Beugung (Flexion) = positiver Winkel (Drehung zur Handflaechenseite, im Bild nach links).

Annahme zur Zuordnung der Kopplungsstangen (bitte in Onshape pruefen):
  D51-Coupling-Bar-Proximal: Pin A (Palm, am MCP, unten-links) -> Pin B (Mittelglied, am PIP, unten-rechts)
  D53-Coupling-Bar-Distal:   Pin C (Grundglied, am PIP, unten-links) -> Pin D (Endglied, am DIP, unten-rechts)
"""
import numpy as np
from scipy.optimize import brentq

# --- Geometrie aus der Skizze -------------------------------------------
MCP = np.array([9.3, 38.0])
PIP = np.array([8.4, 38.0 + 36.0])
DIP = np.array([7.5, 38.0 + 36.0 + 31.0])
R1 = 7.0      # #coupling_bars_arm_1
R2 = 7.0      # #coupling_bars_arm_2
PRE = 0.0     # #pretension in Grad (Wirkung im Modell noch unklar -> Offset der Kurbeln)

A_ANG = np.deg2rad(225.0 + PRE)   # Kurbel am MCP (Palm)
B_ANG = np.deg2rad(315.0)         # Kurbel am PIP (Mittelglied)
C_ANG = np.deg2rad(225.0 + PRE)   # Kurbel am PIP (Grundglied)
D_ANG = np.deg2rad(315.0)         # Kurbel am DIP (Endglied)


def rot(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s], [s, c]])


def pol(r, a):
    return r * np.array([np.cos(a), np.sin(a)])


# Stangenlaengen aus der gestreckten Lage
A0 = MCP + pol(R1, A_ANG)
B0 = PIP + pol(R1, B_ANG)
C0 = PIP + pol(R2, C_ANG)
D0 = DIP + pol(R2, D_ANG)
L1 = np.linalg.norm(B0 - A0)
L2 = np.linalg.norm(D0 - C0)


def solve_chain(t1):
    """Liefert (t2, t3) fuer einen MCP-Winkel t1 [rad]."""
    pip = MCP + rot(t1) @ (PIP - MCP)
    A = A0

    def f2(t2):
        B = pip + pol(R1, B_ANG + t1 + t2)
        return np.linalg.norm(B - A) - L1

    t2 = brentq(f2, -0.2, np.deg2rad(150))

    dip = pip + rot(t1 + t2) @ (DIP - PIP)
    C = pip + pol(R2, C_ANG + t1)

    def f3(t3):
        D = dip + pol(R2, D_ANG + t1 + t2 + t3)
        return np.linalg.norm(D - C) - L2

    t3 = brentq(f3, -0.2, np.deg2rad(150))
    return t2, t3


if __name__ == "__main__":
    import csv
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    print(f"L1 (Stange proximal) = {L1:.3f} mm, L2 (Stange distal) = {L2:.3f} mm")
    t1 = np.deg2rad(np.linspace(0, 95, 96))
    rows = []
    for a in t1:
        try:
            t2, t3 = solve_chain(a)
        except ValueError:
            break
        rows.append((a, t2, t3))
    data = np.degrees(np.array(rows))
    q1, q2, q3 = data.T

    with open("finger_kopplung.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["theta_MCP_deg", "theta_PIP_deg", "theta_DIP_deg"])
        w.writerows(np.round(data, 4))

    # Polynomfit (Grad 5) in rad
    r1, r2, r3 = np.radians(q1), np.radians(q2), np.radians(q3)
    p2 = np.polyfit(r1, r2, 5)
    p3 = np.polyfit(r1, r3, 5)
    p32 = np.polyfit(r2, r3, 5)
    for name, p, x, y in [("PIP(MCP)", p2, r1, r2), ("DIP(MCP)", p3, r1, r3), ("DIP(PIP)", p32, r2, r3)]:
        err = np.degrees(np.max(np.abs(np.polyval(p, x) - y)))
        print(f"{name}: Koeff. (hoechste Potenz zuerst) = {np.round(p, 5).tolist()}  max. Fehler = {err:.3f} deg")

    for d in (0, 30, 60, 90):
        i = np.argmin(np.abs(q1 - d))
        g2 = np.gradient(q2, q1)[i]
        g3 = np.gradient(q3, q1)[i]
        print(f"MCP={q1[i]:5.1f}  PIP={q2[i]:6.2f}  DIP={q3[i]:6.2f}  dPIP/dMCP={g2:.3f}  dDIP/dMCP={g3:.3f}")

    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    ax[0].plot(q1, q2, label="PIP"); ax[0].plot(q1, q3, label="DIP")
    ax[0].plot(q1, q1, "k:", label="1:1")
    ax[0].set_xlabel("MCP [deg]"); ax[0].set_ylabel("Gelenkwinkel [deg]"); ax[0].legend(); ax[0].grid()
    ax[1].plot(q1, np.gradient(q2, q1), label="dPIP/dMCP")
    ax[1].plot(q1, np.gradient(q3, q1), label="dDIP/dMCP")
    ax[1].set_xlabel("MCP [deg]"); ax[1].set_ylabel("lokale Uebersetzung [-]"); ax[1].legend(); ax[1].grid()
    fig.tight_layout(); fig.savefig("finger_kopplung.png", dpi=120)
