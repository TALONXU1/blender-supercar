# -*- coding: utf-8 -*-
import os, sys, glob
import numpy as np
from PIL import Image

def audit_sv_image(path):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    full = np.asarray(im, dtype=np.float32)
    if w == 1920 and h == 1080:
        bar_l = float(0.5 * (full[:136].mean() + full[944:].mean()))
        arr = full[138:942, :, :]
    else:
        bar_l = -1.0
        arr = full

    ah, aw = arr.shape[:2]
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    mx = arr.max(axis=-1)
    mn = arr.min(axis=-1)
    sat = np.where(mx > 5.0, (mx - mn) / np.maximum(mx, 1.0), 0.0)

    mean_l = float(lum.mean())
    mr, mg, mb = float(r.mean()), float(g.mean()), float(b.mean())
    p10, p50, p95 = [float(x) for x in np.percentile(lum, [10, 50, 95])]
    clip_pct = float((mx >= 253.0).mean() * 100.0)
    mean_sat = float(sat.mean() * 100.0)

    gy, gx = np.gradient(lum)
    edge = np.hypot(gx, gy)
    car_sharp = float(edge[int(ah * 0.28):int(ah * 0.86), int(aw * 0.24):int(aw * 0.76)].mean())
    bg_sharp = float(edge[int(ah * 0.04):int(ah * 0.30), int(aw * 0.06):int(aw * 0.94)].mean())
    pop_ratio = car_sharp / max(bg_sharp, 0.01)

    bg_rb_diff = float(np.abs(r[:int(ah * 0.35), :] - b[:int(ah * 0.35), :]).mean())

    white_pct = float(((r > 215) & (g > 210) & (b > 200)).mean() * 100.0)
    crimson_pct = float(((r > 180) & (g < 85) & (b < 105)).mean() * 100.0)
    black_pct = float((mx < 22).mean() * 100.0)

    bar_str = f"Bar={bar_l:3.1f} " if bar_l >= 0 else ""
    print(f"{os.path.basename(path):30s} {bar_str}MeanL={mean_l:5.1f} RGB=[{mr:4.1f},{mg:4.1f},{mb:4.1f}] "
          f"P10/50/95={p10:4.1f}/{p50:5.1f}/{p95:5.1f} Sat={mean_sat:4.1f}% Clip={clip_pct:4.2f}% "
          f"Pop={pop_ratio:4.2f}({car_sharp:4.2f}/{bg_sharp:4.2f}) BgRB={bg_rb_diff:4.1f} "
          f"Tri={white_pct:4.1f}/{crimson_pct:4.1f}/{black_pct:4.1f}%")

if __name__ == "__main__":
    files = []
    for pat in sys.argv[1:]:
        if os.path.isdir(pat):
            files.extend(sorted(glob.glob(os.path.join(pat, "*.jpg"))))
        else:
            files.extend(sorted(glob.glob(pat)))
    for f in files:
        audit_sv_image(f)
