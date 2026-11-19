import json, os, math
from PIL import Image
import numpy as np

proj = r"D:\项目session\blender-supercar"
td = json.load(open(os.path.join(proj, "track_data", "silverstone_track.json"), encoding="utf-8"))
pts = td["points"]
N = len(pts)
cx = sum(p["xy"][0] for p in pts) / N
cy = sum(p["xy"][1] for p in pts) / N
max_r = max(math.hypot(p["xy"][0] - cx, p["xy"][1] - cy) for p in pts)
print(f"Track center=({cx:.1f}, {cy:.1f}), max_r from center={max_r:.1f} m")

# Signed curvature like v5_env.py
def _unwrap(deg_list):
    out = [deg_list[0]]
    for a in deg_list[1:]:
        d = (a - out[-1] + 180.0) % 360.0 - 180.0
        out.append(out[-1] + d)
    return out

hdeg = _unwrap([p["heading_deg"] for p in pts])
head = [math.radians(a) for a in hdeg]
signed_k = []
for i in range(N):
    a = head[(i - 4) % N]
    b = head[(i + 4) % N]
    if b - a > math.pi / 2:
        b -= 2 * math.pi
    sgn = 1.0 if (b - a) >= 0 else -1.0
    signed_k.append(sgn * abs(pts[i]["curv_1pm"] or 0.0))

print("--- TRACK MAP BY ARC LENGTH ---")
for s_tgt in range(0, 5834, 100):
    i = min(range(N), key=lambda k: abs(pts[k]["s"] - s_tgt))
    p = pts[i]
    r_c = math.hypot(p["xy"][0] - cx, p["xy"][1] - cy)
    turn_dir = "LEFT" if signed_k[i] > 0.003 else ("RIGHT" if signed_k[i] < -0.003 else "STR")
    print(f"s={p['s']:6.1f} t={p['t']:5.2f} xy=({p['xy'][0]:7.1f},{p['xy'][1]:7.1f}) r_c={r_c:6.1f} h={p['heading_deg']:6.1f} v={p['v_kmh']:5.1f} sk={signed_k[i]:+.4f} ({turn_dir:5s}) roff={p['racing_offset_m']:+.2f}")

# Check deceleration zones (dv/dt < -8 m/s^2)
print("\n--- HEAVY BRAKING ZONES (decel > 8 m/s^2) ---")
in_brk = None
for i in range(1, N - 1):
    dt = max(1e-4, pts[i + 1]["t"] - pts[i - 1]["t"])
    acc = (pts[i + 1]["v_mps"] - pts[i - 1]["v_mps"]) / dt
    if acc < -8.0:
        if in_brk is None:
            in_brk = [i, i, acc]
        else:
            in_brk[1] = i
            in_brk[2] = min(in_brk[2], acc)
    else:
        if in_brk is not None and pts[in_brk[1]]["s"] - pts[in_brk[0]]["s"] > 20.0:
            a0, a1, min_acc = in_brk
            print(f"Braking s={pts[a0]['s']:6.1f}..{pts[a1]['s']:6.1f}m (len={pts[a1]['s']-pts[a0]['s']:5.1f}m) t={pts[a0]['t']:5.2f}..{pts[a1]['t']:5.2f}s v={pts[a0]['v_kmh']:.0f}->{pts[a1]['v_kmh']:.0f}km/h min_acc={min_acc:.1f}m/s^2 roff={pts[a0]['racing_offset_m']:+.1f}->{pts[a1]['racing_offset_m']:+.1f}")
        in_brk = None

# Inspect texture contents / bands
print("\n--- TEXTURE ROW/COL STATS ---")
for fn in ["pit_garage.png", "ad_boards.png", "bigscreen.png"]:
    fp = os.path.join(proj, "textures", fn)
    im = Image.open(fp).convert("RGB")
    arr = np.asarray(im, dtype=np.float32) / 255.0
    # gradient energy (edge sharpness)
    gx = np.abs(np.diff(arr, axis=1)).mean()
    gy = np.abs(np.diff(arr, axis=0)).mean()
    print(f"{fn:18s}: size={im.size} mean_rgb={arr.mean(axis=(0,1)).round(3)} std={arr.std():.3f} edge_gx={gx:.4f} edge_gy={gy:.4f}")
