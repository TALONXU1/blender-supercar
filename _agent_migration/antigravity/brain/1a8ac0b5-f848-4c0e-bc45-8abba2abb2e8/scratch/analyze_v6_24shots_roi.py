# -*- coding: utf-8 -*-
"""
24-Shot Car-ROI vs Background Pop, Ink Clumping, Crosshatching & CMYK Separation Sensor
Operates strictly on active 2.39:1 image area (y=142..938).
"""
import os, json, glob
import numpy as np
from PIL import Image

PROJ = r"D:\项目session\blender-supercar"
SCRATCH = r"C:\Users\86052\.gemini\antigravity\brain\1a8ac0b5-f848-4c0e-bc45-8abba2abb2e8\scratch"
rep = json.load(open(os.path.join(SCRATCH, "v6_3d_blender_report.json"), encoding="utf-8"))
rois = rep["rois_2d"]
shots = rep["shot_audit"]
stills_dir = os.path.join(PROJ, "renders_v6", "stills")

print(f"{'Idx':<3} {'ShotName':<28} {'Act':<3} {'CarW':>5} {'CarL':>5} {'CarInk%':>7} {'CarShp':>6} {'BGShp':>6} {'Pop':>5} {'BG_CMYK':>7} {'Car_CMYK':>8} {'DiagAnis':>8}")
act_rgb = {1: [], 2: [], 3: []}
for idx, s in enumerate(shots, 1):
    sname = s["shot"]
    f0 = s["f0"]
    act = 1 if f0 <= 427 else (2 if f0 <= 894 else 3)
    m = sorted(glob.glob(os.path.join(stills_dir, f"shot_{idx:02d}_*.jpg")))
    if not m:
        continue
    arr = np.asarray(Image.open(m[0]).convert("RGB"), dtype=np.float32)
    H, W, _ = arr.shape
    y_top, y_bot = 142, H - 142
    act_arr = arr[y_top:y_bot, :, :]
    AH = act_arr.shape[0]
    lum = 0.2126 * act_arr[:, :, 0] + 0.7152 * act_arr[:, :, 1] + 0.0722 * act_arr[:, :, 2]
    lap = np.abs(4 * lum[1:-1, 1:-1] - lum[:-2, 1:-1] - lum[2:, 1:-1] - lum[1:-1, :-2] - lum[1:-1, 2:])

    bx = rois.get(sname, {}).get("box", [0.3, 0.3, 0.7, 0.7])
    x0, x1 = int(bx[0] * W), int(bx[2] * W)
    # Convert full-frame y [0..1] into active crop [y_top..y_bot]
    cy0 = max(0, min(AH, int(bx[1] * H) - y_top))
    cy1 = max(0, min(AH, int(bx[3] * H) - y_top))
    if x1 - x0 < 20 or cy1 - cy0 < 20:
        x0, x1, cy0, cy1 = int(0.3 * W), int(0.7 * W), int(0.25 * AH), int(0.75 * AH)

    cmask = np.zeros((AH, W), dtype=bool)
    cmask[cy0:cy1, x0:x1] = True
    bmask = ~cmask

    car_lum = lum[cmask]
    car_l = float(car_lum.mean())
    car_ink = float((car_lum < 16.0).mean() * 100.0)
    c_shp = float(lap[cmask[1:-1, 1:-1]].mean()) if cmask[1:-1, 1:-1].any() else 0.0
    b_shp = float(lap[bmask[1:-1, 1:-1]].mean()) if bmask[1:-1, 1:-1].any() else 1.0
    pop = c_shp / max(b_shp, 0.1)

    # Red-Cyan CMYK separation on strong edges in BG vs Car
    r_c, b_c = act_arr[:, :, 0], act_arr[:, :, 2]
    dr = np.abs(r_c[1:-1, 2:] - r_c[1:-1, :-2])
    db = np.abs(b_c[1:-1, 2:] - b_c[1:-1, :-2])
    cmyk_map = np.abs(dr - db)
    bg_e = bmask[1:-1, 1:-1] & (lap > np.percentile(lap, 85))
    car_e = cmask[1:-1, 1:-1] & (lap > np.percentile(lap, 85))
    bg_cmyk = float(cmyk_map[bg_e].mean()) if bg_e.any() else 0.0
    car_cmyk = float(cmyk_map[car_e].mean()) if car_e.any() else 0.0

    # Diagonal crosshatching anisotropy
    dp = np.abs(lum[1:, 1:] - lum[:-1, :-1])
    dn = np.abs(lum[1:, :-1] - lum[:-1, 1:])
    shm = (lum[:-1, :-1] > 18.0) & (lum[:-1, :-1] < 95.0)
    anis = (max(float(dp[shm].mean()), float(dn[shm].mean())) / max(min(float(dp[shm].mean()), float(dn[shm].mean())), 0.1)) if shm.any() else 1.0

    act_rgb[act].append(act_arr.mean(axis=(0, 1)))
    print(f"{idx:>2}  {sname:<28} A{act}  {x1-x0:>5} {car_l:>5.1f} {car_ink:>6.1f}% {c_shp:>6.1f} {b_shp:>6.1f} {pop:>5.2f} {bg_cmyk:>7.1f} {car_cmyk:>8.1f} {anis:>8.2f}")

for a in (1, 2, 3):
    print(f"Act {a} mean active RGB: {[round(float(x),1) for x in np.mean(act_rgb[a], axis=0)]}")
