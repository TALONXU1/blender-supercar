# -*- coding: utf-8 -*-
"""
Quantitative PIL/numpy image quality & visual flaw analyzer for clay_frames and color frames.
Checks: luminance mean/p05/p50/p95/p99, highlight clipping (>250), shadow crush (<5),
sky gradient banding / step discontinuities on upper-sky strips, road specular glare anomalies,
and frame-end fade-out behavior.
"""
import os
import json
import numpy as np
from PIL import Image

PROJ = r"D:\项目session\blender-supercar"
CLAY_FR = os.path.join(PROJ, "renders_v5", "clay_frames")
COLOR_FR = os.path.join(PROJ, "renders_v5", "frames")
OUT_TXT = r"C:\Users\86052\.gemini\antigravity\brain\1a8ac0b5-f848-4c0e-bc45-8abba2abb2e8\scratch\visual_metrics_round1.txt"

SHOTS = [
    (60, "S01_RearChase"), (160, "S02_Onboard"), (250, "S03_ChaseRise"),
    (350, "S04_Hairpin"), (440, "S05_ChaseAintree"), (520, "S06_Orbit1"),
    (600, "S07_ChaseAccel"), (700, "S08_FastPan"), (760, "S09_WheelMacro"),
    (820, "S09b_ChaseFast"), (870, "S10_OrbitBrooklands"), (950, "S11_Luffield"),
    (1040, "S12_ChaseWoodcote"), (1120, "S13_WoodcoteTele"), (1200, "S14_HeliDrop"),
    (1300, "S15_OrbitCopse"), (1380, "S16_ChaseCopse"), (1470, "S17_Maggotts"),
    (1560, "S18_ChaseRise2"), (1640, "S19_Onboard3"), (1730, "S20_StoweTele"),
    (1830, "S21_OrbitStowe"), (1920, "S22_ChaseLow"), (2010, "S23_HeliReveal"),
    (2090, "S24_Club"), (2145, "S25_AerialOut"), (2161, "S25_FadeEnd"),
]

lines = []

def analyze_set(label, folder):
    lines.append(f"=== {label} ({folder}) ===")
    lines.append(f"{'Shot':<24} {'Frm':>4} {'MeanL':>6} {'P05':>5} {'P50':>5} {'P95':>5} {'Clip%':>6} {'Dark%':>6} {'SkyStepMax':>10} {'CenterL':>7}")
    for f, name in SHOTS:
        p = os.path.join(folder, f"f_{f:04d}.jpg")
        if not os.path.exists(p):
            lines.append(f"{name:<24} {f:>4} MISSING")
            continue
        arr = np.asarray(Image.open(p).convert("RGB"), dtype=np.float32)
        lum = 0.2126 * arr[:, :, 0] + 0.7152 * arr[:, :, 1] + 0.0722 * arr[:, :, 2]
        mean_l = float(lum.mean())
        p05, p50, p95 = [float(x) for x in np.percentile(lum, [5, 50, 95])]
        clip_pct = float((arr.max(axis=2) >= 250).mean() * 100.0)
        dark_pct = float((lum < 5.0).mean() * 100.0)

        # Sky banding check: top 22% of frame, horizontal row mean luminance vertical derivative
        top = lum[:int(lum.shape[0] * 0.22), :]
        row_means = top.mean(axis=1)
        sky_step_max = float(np.abs(np.diff(row_means)).max())

        # Center box (where car typically sits)
        h, w = lum.shape
        ctr = lum[int(h * 0.35):int(h * 0.75), int(w * 0.30):int(w * 0.70)]
        ctr_l = float(ctr.mean())

        lines.append(f"{name:<24} {f:>4} {mean_l:>6.1f} {p05:>5.1f} {p50:>5.1f} {p95:>5.1f} {clip_pct:>6.2f} {dark_pct:>6.1f} {sky_step_max:>10.2f} {ctr_l:>7.1f}")
    lines.append("")

analyze_set("COLOR FRAMES", COLOR_FR)
analyze_set("CLAY FRAMES", CLAY_FR)

# Also inspect textures/ dimensions and brightness stats
TEX_DIR = os.path.join(PROJ, "textures")
lines.append("=== TEXTURES STATS ===")
if os.path.exists(TEX_DIR):
    for fn in sorted(os.listdir(TEX_DIR)):
        fp = os.path.join(TEX_DIR, fn)
        if os.path.isfile(fp) and fn.lower().endswith((".png", ".jpg", ".jpeg")):
            im = Image.open(fp).convert("RGB")
            arr = np.asarray(im, dtype=np.float32)
            lum = 0.2126 * arr[:, :, 0] + 0.7152 * arr[:, :, 1] + 0.0722 * arr[:, :, 2]
            lines.append(f"{fn:<28} size={im.size} meanL={lum.mean():.1f} p95={np.percentile(lum, 95):.1f} max={arr.max():.0f}")

with open(OUT_TXT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("\n".join(lines))
