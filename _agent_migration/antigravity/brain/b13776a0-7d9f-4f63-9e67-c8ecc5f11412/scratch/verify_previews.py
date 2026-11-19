import json
import math
import os
import time
import numpy as np
from PIL import Image

PROJ = r"D:\项目session\blender-supercar"
PREV_DIR = os.path.join(PROJ, "renders_v5", "preview")

print("=== PREVIEW IMAGE METRICS (PIL + NumPy) ===")
for fn in sorted(os.listdir(PREV_DIR)):
    if not fn.lower().endswith((".jpg", ".png")):
        continue
    fp = os.path.join(PREV_DIR, fn)
    im = Image.open(fp).convert("RGB")
    arr = np.asarray(im, dtype=np.float32) / 255.0
    lum = 0.2126 * arr[:, :, 0] + 0.7152 * arr[:, :, 1] + 0.0722 * arr[:, :, 2]
    clip_pct = float((lum > 0.98).mean() * 100.0)
    # Sky gradient smoothness on upper 28% of frame (for low-angle shots)
    h, w = lum.shape
    sky_band = lum[: int(h * 0.28), :] * 255.0
    row_means = sky_band.mean(axis=1)
    sky_step_max = float(np.abs(np.diff(row_means)).max()) if len(row_means) > 1 else 0.0
    # Lower-center road region specular wedge check (fraction of pixels > 0.85 in bottom 35%)
    road_patch = lum[int(h * 0.65) :, int(w * 0.25) : int(w * 0.75)]
    road_bright_pct = float((road_patch > 0.85).mean() * 100.0)
    print(
        f"{fn:24s} | size={im.size} | mean={lum.mean():.3f} p05={np.percentile(lum,5):.3f} "
        f"p95={np.percentile(lum,95):.3f} | clip>0.98={clip_pct:.2f}% | "
        f"SkyStepMax={sky_step_max:.2f}/255 | RoadBright>0.85={road_bright_pct:.2f}%"
    )
