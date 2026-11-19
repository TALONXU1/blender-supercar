# -*- coding: utf-8 -*-
import os, sys, glob
import numpy as np
from PIL import Image

def inspect_image(path):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    arr = np.asarray(im, dtype=np.float32)
    lum = 0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]
    mx = arr.max(axis=-1)
    clip_pct = float((mx >= 253.0).mean() * 100.0)
    dark_pct = float((mx <= 3.0).mean() * 100.0)
    mean_l = float(lum.mean())
    p05, p50, p95 = [float(x) for x in np.percentile(lum, [5, 50, 95])]

    # Laplacian sharpness proxy: center car band vs upper background band
    gy, gx = np.gradient(lum)
    edge = np.hypot(gx, gy)
    car_roi = edge[int(h * 0.35):int(h * 0.80), int(w * 0.25):int(w * 0.75)]
    bg_roi = edge[int(h * 0.15):int(h * 0.35), int(w * 0.10):int(w * 0.90)]
    car_sharp = float(car_roi.mean())
    bg_sharp = float(bg_roi.mean())

    # Warm red-orange glow pixels (brake glow / tail light) in lower-mid ROI
    mid = arr[int(h * 0.30):int(h * 0.88), int(w * 0.15):int(w * 0.85)]
    hot_px = int(((mid[..., 0] > 195) & ((mid[..., 0] - mid[..., 2]) > 115) & (mid[..., 1] < 210)).sum())

    # Cockpit shift LED / LCD pixels in lower third
    low = arr[int(h * 0.55):int(h * 0.96), int(w * 0.25):int(w * 0.75)]
    cockpit_detail = float(edge[int(h * 0.55):int(h * 0.96), int(w * 0.25):int(w * 0.75)].mean())
    led_px = int(((low[..., 1] > 170) & ((low[..., 1] - low[..., 0]) > 50)).sum() +
                 ((low[..., 0] > 180) & ((low[..., 0] - low[..., 2]) > 90)).sum())

    print(f"{os.path.basename(path):32s} {w}x{h} MeanL={mean_l:5.1f} P05/50/95={p05:4.1f}/{p50:5.1f}/{p95:5.1f} "
          f"Clip={clip_pct:4.2f}% Dark={dark_pct:4.1f}% Sharp(car/bg)={car_sharp:4.2f}/{bg_sharp:4.2f} "
          f"HotGlowPx={hot_px:5d} LowDetail={cockpit_detail:4.2f} LEDPx={led_px:5d}")

if __name__ == "__main__":
    targets = sys.argv[1:]
    files = []
    for t in targets:
        if os.path.isdir(t):
            files.extend(sorted(glob.glob(os.path.join(t, "*.jpg"))))
        else:
            files.extend(sorted(glob.glob(t)))
    for f in files:
        inspect_image(f)
