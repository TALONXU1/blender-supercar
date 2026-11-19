import datetime
import os
import numpy as np
from PIL import Image, ImageFilter

PROJ = r"D:\项目session\blender-supercar"
PDIR = os.path.join(PROJ, "renders_v6", "preview")

print("=== V6 SPIDER-VERSE 3D MEGA-CIRCUIT PREVIEW QUANTITATIVE AUDIT ===")
act_fg = {}
for fn in sorted(os.listdir(PDIR)):
    if not (fn.endswith(".jpg") or fn.endswith(".png")):
        continue
    fp = os.path.join(PDIR, fn)
    im = Image.open(fp).convert("RGB")
    arr = np.asarray(im, dtype=np.float32) / 255.0
    blur = np.asarray(im.filter(ImageFilter.BoxBlur(3)), dtype=np.float32) / 255.0
    lum = 0.2126 * arr[:, :, 0] + 0.7152 * arr[:, :, 1] + 0.0722 * arr[:, :, 2]
    sat = arr.max(axis=2) - arr.min(axis=2)
    H, W = lum.shape
    fg = np.abs(arr[int(H * 0.28):] - blur[int(H * 0.28):]).mean() * 255.0
    # 45-deg diagonal gradient vs axial gradient anisotropy in foreground
    L_fg = lum[int(H * 0.32):]
    d1 = np.abs(L_fg[1:, 1:] - L_fg[:-1, :-1]).mean()
    d2 = np.abs(L_fg[1:, :-1] - L_fg[:-1, 1:]).mean()
    ax = 0.5 * (np.abs(L_fg[1:, :] - L_fg[:-1, :]).mean() + np.abs(L_fg[:, 1:] - L_fg[:, :-1]).mean()) + 1e-6
    diag_anis = 0.5 * (d1 + d2) / ax
    ink_pct = float((lum < 0.045).mean() * 100.0)
    clip_pct = float((lum > 0.985).mean() * 100.0)
    road_lum = lum[int(H * 0.68):, :]
    road_sat = sat[int(H * 0.68):, :]
    white_wedge_pct = float(((road_lum > 0.82) & (road_sat < 0.12)).mean() * 100.0)
    neon_refl_pct = float(((road_lum > 0.16) & (road_sat > 0.32)).mean() * 100.0)
    sky_rgb = arr[:int(H * 0.28)].mean(axis=(0, 1)).round(3)
    fg_rgb = arr[int(H * 0.35):].mean(axis=(0, 1)).round(3)
    act_fg[fn] = (sky_rgb, fg_rgb)
    print(
        f"{fn:34s} | mean={lum.mean():.3f} p05={np.percentile(lum,5):.3f} p95={np.percentile(lum,95):.3f} "
        f"| sat={sat.mean():.3f} | clip={clip_pct:.2f}% | ink={ink_pct:.1f}% | DiagAnis={diag_anis:.2f} "
        f"| roadWedge={white_wedge_pct:.2f}% neonRefl={neon_refl_pct:.1f}% | HF={fg:.2f} | sky={sky_rgb} fg={fg_rgb}"
    )
    if "moon" in fn:
        uc = arr[int(H * 0.08):int(H * 0.52), int(W * 0.32):int(W * 0.68)]
        uc_lum = 0.2126 * uc[:, :, 0] + 0.7152 * uc[:, :, 1] + 0.0722 * uc[:, :, 2]
        uc_sat = uc.max(axis=2) - uc.min(axis=2)
        print(f"   -> Moon/SkyBridge center window: mean_lum={uc_lum.mean():.3f}, p90_lum={np.percentile(uc_lum,90):.3f}, mean_sat={uc_sat.mean():.3f}")

print("\n=== 3-ACT FOREGROUND MEAN RGB SUMMARY ===")
for fn, (srgb, frgb) in act_fg.items():
    print(f"  {fn:34s} | sky={srgb} | fg={frgb}")

print("\n=== V5 ISOLATION & BLEND ARTIFACT CHECK ===")
for rel in (
    r"LATEST\v5_stage_env.blend",
    r"LATEST\v5_stage_anim.blend",
    r"pipeline\v5_env.py",
    r"v6_spiderverse\v6_stage_lookdev.blend",
    r"v6_spiderverse\v6_stage_lookdev.blend1",
):
    p = os.path.join(PROJ, rel)
    if os.path.exists(p):
        st = os.stat(p)
        dt = datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        print(f"  EXISTS  {rel:42s} | {st.st_size/1e6:6.2f} MB | mtime={dt}")
    else:
        print(f"  ABSENT  {rel}")
