"""
quantisiere_int8.py — Policy (ONNX, float) nach ST-Vorgabe in int8 QDQ quantisieren und für den STM32N6 analysieren (M2).

Ablauf (docs/conventions.md → „ST Edge AI“): onnxruntime quant_pre_process → quantize_static mit QuantFormat.QDQ,
QInt8/QInt8, per_channel=True, Kalibrierdaten aus Sim-Rollouts (tools/kalibrierdaten_int8.py, MinMax). Danach:
Abweichung int8 ↔ float auf einer getrennten Testmenge (Aktion auf ±1 begrenzt wie im Einsatz) und `stedgeai analyze
--target stm32n6 --st-neural-art` (welche Schichten laufen auf der NPU, Speicher, MACC). Läuft mit dem Python der
conda-Umgebung env_isaaclab, ohne Isaac. Bericht: <out>/bericht.txt; int8-Modell <out>/policy_int8_qdq.onnx.

  conda activate env_isaaclab
  python isaac_lab/tools/quantisiere_int8.py --onnx <run>/exported/policy.onnx --daten logs/int8/<name>/daten.npz \
      --out logs/int8/<name>
"""
import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import onnxruntime as ort
from onnxruntime.quantization import CalibrationDataReader, QuantFormat, QuantType, quantize_static
from onnxruntime.quantization.shape_inference import quant_pre_process

parser = argparse.ArgumentParser()
parser.add_argument("--onnx", required=True)
parser.add_argument("--daten", required=True)
parser.add_argument("--out", required=True)
args = parser.parse_args()
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
data = np.load(args.daten)
calib, test = data["calib"], data["test"]
name = ort.InferenceSession(args.onnx, providers=["CPUExecutionProvider"]).get_inputs()[0].name


class Reader(CalibrationDataReader):
    def __init__(self, rows):
        self.it = iter(rows)

    def get_next(self):
        row = next(self.it, None)
        return None if row is None else {name: row[None, :]}


pre = out / "policy_pre.onnx"
q8 = out / "policy_int8_qdq.onnx"
quant_pre_process(args.onnx, str(pre))
quantize_static(str(pre), str(q8), Reader(calib), quant_format=QuantFormat.QDQ, activation_type=QuantType.QInt8,
                weight_type=QuantType.QInt8, per_channel=True)

# int8 ↔ float auf der Testmenge
s_f = ort.InferenceSession(args.onnx, providers=["CPUExecutionProvider"])
s_q = ort.InferenceSession(str(q8), providers=["CPUExecutionProvider"])
a_f = np.concatenate([s_f.run(None, {name: r[None, :]})[0] for r in test]).clip(-1, 1)
a_q = np.concatenate([s_q.run(None, {name: r[None, :]})[0] for r in test]).clip(-1, 1)
d = np.abs(a_f - a_q)
lines = [f"== int8-Quantisierung: {args.onnx}",
         f"Kalibrierung {len(calib)}, Test {len(test)} Beobachtungen ({args.daten})",
         f"Aktion (auf ±1 begrenzt) int8 − float: Mittel |Δ| {d.mean():.4f}, 99-%-Quantil {np.quantile(d, 0.99):.4f}, "
         f"max {d.max():.4f}; je Servo Mittel " + " ".join(f"{v:.3f}" for v in d.mean(0)),
         f"Vorzeichen gleich: {100 * np.mean(np.sign(a_f) == np.sign(a_q)):.1f} %  |  Modellgröße float "
         f"{Path(args.onnx).stat().st_size / 1024:.0f} kB, int8 QDQ {q8.stat().st_size / 1024:.0f} kB", ""]

# ST Edge AI: Analyse für den STM32N6 mit Neural-ART
st = shutil.which("stedgeai") or str(Path.home() / "ST/STEdgeAI/4.0/4.0/Utilities/linux/stedgeai")
cmd = [st, "analyze", "--model", str(q8.resolve()), "--target", "stm32n6", "--st-neural-art",
       "--input-data-type", "float32", "--output-data-type", "float32"]
env = dict(os.environ, STEDGEAI_CORE_DIR=str(Path.home() / "ST/STEdgeAI/4.0/4.0"))
res = subprocess.run(cmd, cwd=out, capture_output=True, text=True, env=env, timeout=1800)
(out / "stedgeai_analyze.txt").write_text(res.stdout + "\n" + res.stderr, encoding="utf-8")
lines.append(f"stedgeai analyze (Rückgabe {res.returncode}) → {out / 'stedgeai_analyze.txt'}")
keep = re.compile(r"(?i)(epoch|macc|weights|activations|ram|rom|error|hw|sw|npu)")
lines += ["  " + l.rstrip() for l in res.stdout.splitlines() if keep.search(l)][:60]
text = "\n".join(lines)
(out / "bericht.txt").write_text(text + "\n", encoding="utf-8")
print(text, flush=True)
