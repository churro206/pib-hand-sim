"""
isaac_sim/autostart.py — Automatischer Startup für Isaac Sim.

Wird via --exec gestartet (kein Script Editor nötig):
  ~/isaacsim/isaac-sim.sh --exec /home/leon/repos/pib-hand-sim/isaac_sim/autostart.py

Ablauf (vollautomatisch):
  1. USD laden
  2. start.py ausführen (Drives, Limits, T-Pose)
  3. Simulation starten (Play)
  4. pib_bridge.py ausführen (ros2_control-Bridge)
"""
import sys
import os
import importlib
import importlib.util
import asyncio

import carb  # type: ignore

_log = carb.log_warn


def _find_root() -> str:
    if "PIB_HAND_SIM_ROOT" in os.environ:
        return os.environ["PIB_HAND_SIM_ROOT"]
    from pathlib import Path
    candidate = Path(__file__).parent.parent
    if (candidate / "config" / "pib_hand_config.py").is_file():
        return str(candidate)
    for p in ["~/repos/pib-hand-sim", "~/pib-hand-sim"]:
        expanded = os.path.expanduser(p)
        if os.path.isfile(os.path.join(expanded, "config", "pib_hand_config.py")):
            return expanded
    raise FileNotFoundError("Projekt nicht gefunden. PIB_HAND_SIM_ROOT setzen.")


def _load_mod(name, path, **pre_attrs):
    sys.modules.pop(name, None)
    importlib.invalidate_caches()
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    for k, v in pre_attrs.items():
        setattr(mod, k, v)
    spec.loader.exec_module(mod)
    return mod


async def _main() -> None:
    import omni.kit.app as _app_mod  # type: ignore
    import omni.usd            # type: ignore
    import omni.timeline        # type: ignore

    app      = _app_mod.get_app()
    timeline = omni.timeline.get_timeline_interface()
    root     = _find_root()

    # ── 1. USD laden ─────────────────────────────────────────────────────────
    usd_path = os.path.join(root, "isaac_sim", "usd", "pib_upperbody_7_flattened.usd")
    if not os.path.isfile(usd_path):
        _log(f"[autostart] FEHLER: USD nicht gefunden: {usd_path}")
        return

    _log(f"[autostart] Lade USD: {usd_path}")
    success, _ = await omni.usd.get_context().open_stage_async(usd_path)
    if not success:
        _log("[autostart] FEHLER: USD konnte nicht geladen werden.")
        return
    await app.next_update_async()
    _log("[autostart] USD geladen.")

    # ── 2. start.py ausführen (Drives, Limits, T-Pose) ───────────────────────
    _log("[autostart] Führe start.py aus...")
    start = _load_mod("start", os.path.join(root, "isaac_sim", "start.py"))
    # start.py ist ein async-Skript → nutzt ensure_future intern
    # Wir warten einige Frames damit configure_* abgeschlossen ist
    for _ in range(10):
        await app.next_update_async()
    _log("[autostart] start.py abgeschlossen.")

    # ── 3. Simulation starten ─────────────────────────────────────────────────
    _log("[autostart] Starte Simulation (Play)...")
    timeline.play()
    await app.next_update_async()
    _log("[autostart] Simulation läuft.")

    # ── 4. rclpy-Path vorbereiten (Python 3.11 / Jazzy-Mismatch) ─────────────
    # jazzy/rclpy/ ist das Python-3.11-site-packages-Verzeichnis von Isaac.
    # Gecachte System-rclpy (Python 3.12) aus sys.modules entfernen damit
    # pib_bridge.py das korrekte rclpy importiert.
    _rclpy_path = os.path.expanduser(
        "~/isaacsim/exts/isaacsim.ros2.bridge/jazzy/rclpy"
    )
    if os.path.isdir(_rclpy_path):
        for _k in [k for k in sys.modules if k.startswith("rclpy")]:
            del sys.modules[_k]
        if _rclpy_path not in sys.path:
            sys.path.insert(0, _rclpy_path)

    # ── 5. pib_bridge.py starten ──────────────────────────────────────────────
    _log("[autostart] Starte pib_bridge...")
    _load_mod("pib_bridge", os.path.join(root, "isaac_sim", "pib_bridge.py"))
    _log("[autostart] pib_bridge gestartet. Bereit.")


asyncio.ensure_future(_main())
