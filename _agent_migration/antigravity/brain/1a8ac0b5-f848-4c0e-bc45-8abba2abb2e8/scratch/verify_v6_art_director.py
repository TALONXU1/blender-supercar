# -*- coding: utf-8 -*-
"""
Ruthless Spider-Verse Art-Director + Quantitative Critique Sensor
Runs inside Blender headless (for exact 3D->2D car ROI projection per shot) + PIL/NumPy on renders_v6/stills & clips_frames:
1. Ink Weight Across Scales: % dark ink pixels inside exact projected 2D Car ROI on Close-Up vs Chase vs Telephoto shots
2. 1080p Halftone (3-12px band) & 45-deg Crosshatching Anisotropy inside midtone/shadow bands
3. 3-Act Universe Color Palette & Shadow Indigo Tint (never muddy gray-black!) + Kuwahara BG vs Hero-Car Sharpness Pop + CMYK Background Misregistration vs Clean Car
4. Portal Glitch & Impact Frame punch + 3D ComicFX visibility check
"""
import bpy
import os
import sys
import json
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

PROJ = r"D:\项目session\blender-supercar"
SCRATCH = r"C:\Users\86052\.gemini\antigravity\brain\1a8ac0b5-f848-4c0e-bc45-8abba2abb2e8\scratch"
ANIM_SV_BLEND = os.path.join(PROJ, "v6_spiderverse", "v6_stage_anim_sv.blend")
ROIS_JSON = os.path.join(SCRATCH, "v6_car_rois.json")

SHOTS = [
    (60, "01_rear_chase"), (160, "02_onboard"), (250, "03_chase_rise"),
    (350, "04_hairpin"), (440, "05_chase_aintree"), (520, "06_orbit1"),
    (600, "07_chase_accel"), (700, "08_fast_pan"), (760, "09_wheel_macro"),
    (820, "10_chase_fast"), (870, "11_orbit_brooklands"), (950, "12_luffield"),
    (1040, "13_chase_woodcote"), (1120, "14_woodcote_tele"), (1200, "15_heli_drop"),
    (1300, "16_orbit_copse"), (1380, "17_chase_copse"), (1470, "18_maggotts"),
    (1560, "19_chase_rise2"), (1640, "20_onboard3"), (1730, "21_stowe_tele"),
    (1830, "22_orbit_stowe"), (1920, "23_chase_low"), (2010, "24_heli_reveal"),
    (2090, "25_club"), (2145, "26_aerial_out"),
]

if "--blender-rois" in sys.argv:
    bpy.ops.wm.open_mainfile(filepath=ANIM_SV_BLEND)
    sc = bpy.context.scene
    rig = bpy.data.objects["RIG_F1_Race"]
    markers = sorted(sc.timeline_markers, key=lambda m: m.frame)

    def active_cam(f):
        cur = sc.camera
        for mk in markers:
            if mk.frame <= f and mk.camera:
                cur = mk.camera
        return cur

    car_objs = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith(("GEO_F1_", "GEO_MERC_"))]
    rois = {}
    for f, sname in SHOTS:
        cam = active_cam(f)
        sc.camera = cam
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        cam_e = cam.evaluated_get(dg)
        us, vs = [], []
        for o in car_objs[::3]:
            oe = o.evaluated_get(dg)
            for c in oe.bound_box:
                w = oe.matrix_world @ Vector(c)
                ndc = world_to_camera_view(sc, cam_e, w)
                if ndc.z > 0.2:
                    us.append(ndc.x)
                    vs.append(1.0 - ndc.y)  # top-left image coords
        if us:
            x0 = max(0.0, min(1.0, min(us)))
            x1 = max(0.0, min(1.0, max(us)))
            y0 = max(0.0, min(1.0, min(vs)))
            y1 = max(0.0, min(1.0, max(vs)))
            rois[sname] = {"f": f, "cam": cam.name, "box_norm": [round(x0, 4), round(y0, 4), round(x1, 4), round(y1, 4)]}
    with open(ROIS_JSON, "w", encoding="utf-8") as fp:
        json.dump(rois, fp, indent=2)
    print("WROTE ROIS:", ROIS_JSON)
    sys.exit(0)

# System Python PIL/NumPy deep art-director critique
import numpy as np
from PIL import Image

rois = json.load(open(ROIS_JSON, encoding="utf-8")) if os.path.exists(ROIS_JSON) else {}
stills_dir = os.path.join(PROJ, "renders_v6", "stills")
out_lines = []
out_lines.append("=== SPIDER-VERSE ART-DIRECTOR QUANTITATIVE CRITIQUE (26 STILLS) ===")
out_lines.append(f"{'Shot':<22} {'Act':<4} {'CarW_px':>7} {'CarInk%':>7} {'CarSharp':>8} {'BGSharp':>7} {'PopRatio':>8} {'HalftHP':>7} {'DiagAnis':>8} {'BG_CMYK':>7} {'ShadowRGB_P10'}")

act_stats = {1: [], 2: [], 3: []}

for f, sname in SHOTS:
    act = 1 if f <= 788 else (2 if f <= 1601 else 3)
    # Match shot_XX_*.jpg
    fn = f"shot_{sname}.jpg"
    fp = os.path.join(stills_dir, fn)
    if not os.path.exists(fp):
        # fallback glob
        import glob
        m = glob.glob(os.path.join(stills_dir, f"shot_{sname[:2]}_*.jpg"))
        fp = m[0] if m else ""
    if not fp or not os.path.exists(fp):
        out_lines.append(f"{sname:<22} MISSING")
        continue

    arr = np.asarray(Image.open(fp).convert("RGB"), dtype=np.float32)
    H, W, _ = arr.shape
    lum = 0.2126 * arr[:, :, 0] + 0.7152 * arr[:, :, 1] + 0.0722 * arr[:, :, 2]

    # Laplacian sharpness proxy
    lap = np.abs(4 * lum[1:-1, 1:-1] - lum[:-2, 1:-1] - lum[2:, 1:-1] - lum[1:-1, :-2] - lum[1:-1, 2:])

    # Car ROI vs Background mask
    rb = rois.get(sname, {}).get("box_norm", [0.35, 0.35, 0.65, 0.75])
    x0, y0, x1, y1 = int(rb[0] * W), int(rb[1] * H), int(rb[2] * W), int(rb[3] * H)
    car_w_px = max(1, x1 - x0)
    car_mask = np.zeros((H, W), dtype=bool)
    car_mask[max(0, y0):min(H, y1), max(0, x0):min(W, x1)] = True
    bg_mask = ~car_mask

    car_lum = lum[car_mask] if car_mask.any() else lum
    car_ink_pct = float((car_lum < 20.0).mean() * 100.0)
    car_sharp = float(lap[car_mask[1:-1, 1:-1]].mean()) if car_mask[1:-1, 1:-1].any() else 0.0
    bg_sharp = float(lap[bg_mask[1:-1, 1:-1]].mean()) if bg_mask[1:-1, 1:-1].any() else 1.0
    pop_ratio = car_sharp / max(bg_sharp, 0.1)

    # Halftone 4-10px spatial pattern energy in midtones (50..185): difference from 5x5 box-blurred lum
    # Fast 5x5 box blur via cumulative sum
    pad = np.pad(lum, 2, mode='edge')
    cs = np.cumsum(np.cumsum(pad, axis=0), axis=1)
    blur5 = (cs[4:, 4:] - cs[:-4, 4:] - cs[4:, :-4] + cs[:-4, :-4]) / 25.0 # shape (H+1, W+1) -> trim
    blur5 = blur5[:H, :W]
    mid_mask = (lum > 48.0) & (lum < 185.0)
    halftone_hp = float(np.abs(lum[mid_mask] - blur5[mid_mask]).mean()) if mid_mask.any() else 0.0

    # 45-deg Crosshatching diagonal gradient anisotropy in shadow-mid terminator (22..95)
    d_pos = np.abs(lum[1:, 1:] - lum[:-1, :-1])  # +45 deg
    d_neg = np.abs(lum[1:, :-1] - lum[:-1, 1:])  # -45 deg
    sh_mask = (lum[:-1, :-1] > 22.0) & (lum[:-1, :-1] < 95.0)
    if sh_mask.any():
        p_m, n_m = float(d_pos[sh_mask].mean()), float(d_neg[sh_mask].mean())
        diag_anis = max(p_m, n_m) / max(min(p_m, n_m), 0.05)
    else:
        diag_anis = 1.0

    # Background Red-Cyan CMYK chromatic edge separation: |grad(R) - grad(B)| on BG edges
    r_ch, b_ch = arr[:, :, 0], arr[:, :, 2]
    bg_edge = bg_mask[1:-1, 1:-1] & (lap > np.percentile(lap, 85))
    if bg_edge.any():
        dr = np.abs(r_ch[1:-1, 2:] - r_ch[1:-1, :-2])[bg_edge]
        db = np.abs(b_ch[1:-1, 2:] - b_ch[1:-1, :-2])[bg_edge]
        bg_cmyk = float(np.abs(dr - db).mean())
    else:
        bg_cmyk = 0.0

    # Shadow RGB tint (5th-15th percentile luminance pixels)
    sh_band = (lum >= np.percentile(lum, 4)) & (lum <= np.percentile(lum, 16))
    sh_rgb = [round(float(x), 1) for x in arr[sh_band].mean(axis=0)] if sh_band.any() else [0, 0, 0]

    act_stats[act].append((lum.mean(), pop_ratio, halftone_hp, bg_cmyk, sh_rgb, arr.mean(axis=(0, 1))))
    out_lines.append(f"{sname:<22} A{act:<3} {car_w_px:>7} {car_ink_pct:>6.1f}% {car_sharp:>8.2f} {bg_sharp:>7.2f} {pop_ratio:>8.2f} {halftone_hp:>7.2f} {diag_anis:>8.2f} {bg_cmyk:>7.2f} {sh_rgb}")

out_lines.append("\n=== 3-ACT AGGREGATE SUMMARY ===")
for a in (1, 2, 3):
    st = act_stats[a]
    if st:
        mean_rgb = [round(float(x), 1) for x in np.mean([s[5] for s in st], axis=0)]
        mean_sh = [round(float(x), 1) for x in np.mean([s[4] for s in st], axis=0)]
        out_lines.append(f"  Act {a}: shots={len(st)} meanRGB={mean_rgb} shadowRGB={mean_sh} avgPopRatio={np.mean([s[1] for s in st]):.2f} avgHalftHP={np.mean([s[2] for s in st]):.2f} avgBG_CMYK={np.mean([s[3] for s in st]):.2f}")

out_txt = "\n".join(out_lines)
out_p = os.path.join(SCRATCH, "v6_art_director_report.txt")
with open(out_p, "w", encoding="utf-8") as fp:
    fp.write(out_txt)
print(out_txt)
