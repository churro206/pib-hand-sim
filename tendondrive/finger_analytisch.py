"""
Geschlossene (analytische) Loesung der Fingerkopplung.

Jede Kopplung ist ein Viergelenkgetriebe, betrachtet im Koordinatensystem des Gliedes dazwischen:
  Kette 1 (im Grundglied):  Steg MCP-PIP, Kurbel am MCP (Pin A, Palm), Koppel D51, Schwinge am PIP (Pin B)
  Kette 2 (im Mittelglied): Steg PIP-DIP, Kurbel am PIP (Pin C),        Koppel D53, Schwinge am DIP (Pin D)
Beide Ketten haben dieselbe Form:  theta_aus = F(theta_ein).  Deshalb gilt:
  theta_PIP = F1(theta_MCP),   theta_DIP = F2(theta_PIP)

Herleitung (fuer eine Kette):
  O1, O2  Drehpunkte (Steg),  r  Kurbel-/Schwingenradius,  L  Koppellaenge,
  alpha   Richtung der Kurbel (gestreckt),  beta  Richtung der Schwinge (gestreckt).
  Im Glied-System dreht die Kurbel um -theta_ein, die Schwinge um +theta_aus:
     A = O1 + r*e(alpha - theta_ein),   B = O2 + r*e(beta + theta_aus)
  Schliessbedingung |B - A| = L.  Mit d = O2 - A und phi = beta + theta_aus:
     |d|^2 + r^2 + 2 r (d_x cos phi + d_y sin phi) = L^2
  =>  d_x cos phi + d_y sin phi = K,   K = (L^2 - |d|^2 - r^2) / (2 r)
  =>  phi = atan2(d_y, d_x) + s * arccos(K / |d|),   s = +1 oder -1 (Montagezweig)
  =>  theta_aus = phi - beta
  Die Loesung existiert, solange |K| <= |d|. Bei |K| = |d| liegt der Totpunkt.
"""
import numpy as np

# Geometrie aus der Skizze "Side view" (mm)
MCP = np.array([9.3, 38.0])
PIP = np.array([8.4, 74.0])
DIP = np.array([7.5, 105.0])
R = 7.0                         # #coupling_bars_arm_1 = #coupling_bars_arm_2
ALPHA = np.deg2rad(225.0)       # Kurbel (unten links)
BETA = np.deg2rad(315.0)        # Schwinge (unten rechts)


def e(a):
    return np.stack([np.cos(a), np.sin(a)], axis=-1)


class Viergelenk:
    def __init__(self, O1, O2, r=R, alpha=ALPHA, beta=BETA):
        self.O1, self.O2, self.r, self.alpha, self.beta = O1, O2, r, alpha, beta
        A0 = O1 + r * e(alpha)
        B0 = O2 + r * e(beta)
        self.L = np.linalg.norm(B0 - A0)          # Koppellaenge aus gestreckter Lage
        # Montagezweig s so waehlen, dass theta_aus(0) = 0
        self.s = 1.0
        if abs(self(0.0)) > 1e-9:
            self.s = -1.0

    def __call__(self, t_in):
        t_in = np.asarray(t_in, float)
        A = self.O1 + self.r * e(self.alpha - t_in)
        d = self.O2 - A
        dn = np.linalg.norm(d, axis=-1)
        K = (self.L**2 - dn**2 - self.r**2) / (2 * self.r)
        phi = np.arctan2(d[..., 1], d[..., 0]) + self.s * np.arccos(np.clip(K / dn, -1, 1))
        t_out = phi - self.beta
        return (t_out + np.pi) % (2 * np.pi) - np.pi   # auf (-pi, pi] normieren

    def uebersetzung(self, t_in, h=1e-6):
        """lokales Uebersetzungsverhaeltnis d theta_aus / d theta_ein"""
        return (self(t_in + h) - self(t_in - h)) / (2 * h)

    def totpunkt(self):
        """groesster Eingangswinkel, fuer den die Kette schliesst"""
        t = np.radians(np.linspace(0, 179, 17901))
        A = self.O1 + self.r * e(self.alpha - t)
        d = np.linalg.norm(self.O2 - A, axis=-1)
        K = (self.L**2 - d**2 - self.r**2) / (2 * self.r)
        ok = np.abs(K) <= d
        return t[np.argmin(ok)] if not ok.all() else t[-1]


F1 = Viergelenk(MCP, PIP)   # theta_PIP = F1(theta_MCP)
F2 = Viergelenk(PIP, DIP)   # theta_DIP = F2(theta_PIP)


def finger(t_mcp):
    t_pip = F1(t_mcp)
    t_dip = F2(t_pip)
    return t_pip, t_dip


if __name__ == "__main__":
    print(f"Kette 1: Steg {np.linalg.norm(PIP-MCP):.3f} mm, Koppel L1 = {F1.L:.3f} mm, Zweig s = {F1.s:+.0f}, "
          f"Totpunkt bei MCP = {np.degrees(F1.totpunkt()):.1f} deg")
    print(f"Kette 2: Steg {np.linalg.norm(DIP-PIP):.3f} mm, Koppel L2 = {F2.L:.3f} mm, Zweig s = {F2.s:+.0f}, "
          f"Totpunkt bei PIP = {np.degrees(F2.totpunkt()):.1f} deg")
    for deg in (0, 30, 60, 73.75, 90):
        t = np.radians(deg)
        p, d = finger(t)
        print(f"MCP {deg:6.2f} -> PIP {np.degrees(p):6.2f}  DIP {np.degrees(d):6.2f}   "
              f"dPIP/dMCP {F1.uebersetzung(t):.3f}  dDIP/dPIP {F2.uebersetzung(p):.3f}")
