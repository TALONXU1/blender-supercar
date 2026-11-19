# -*- coding: utf-8 -*-
"""验证赛道几何：总转角 + 赛道带自交检测（复现 v4_anim 的积分）"""
import math

FPS = 24
SUB = 25
DT = 1.0 / (FPS * SUB)
FRAME_END = 720

SPEED_KEYS = [
    (1, 0), (10, 2), (18, 16), (26, 46), (38, 92), (52, 140), (68, 186),
    (88, 226), (110, 258), (136, 280), (160, 296),
    (200, 300), (270, 300), (318, 298),
    (330, 262), (342, 210), (352, 168), (362, 138), (372, 132),
    (410, 134), (445, 136),
    (470, 152), (500, 166),
    (520, 164), (550, 162), (575, 162),
    (600, 196), (630, 238), (660, 272), (690, 292), (710, 299), (720, 300),
]
KAPPA_KEYS = [
    (1, 0.0), (334, 0.0),
    (346, 0.0038), (356, 0.0092), (366, 0.0118),
    (448, 0.0118),
    (458, 0.0090), (466, 0.0068), (474, 0.0016),
    (490, 0.0),
    (500, -0.0044), (508, -0.0098), (516, -0.0120),
    (576, -0.0120),
    (586, -0.0090), (594, -0.0056), (602, -0.0012),
    (614, 0.0), (720, 0.0),
]

def interp(keys, f):
    if f <= keys[0][0]:
        return keys[0][1]
    for i in range(len(keys) - 1):
        f0, v0 = keys[i]; f1, v1 = keys[i + 1]
        if f0 <= f <= f1:
            t = (f - f0) / (f1 - f0)
            t = t * t * (3 - 2 * t)
            return v0 + (v1 - v0) * t
    return keys[-1][1]

N = FRAME_END * SUB + 2
x, y, h = 0.0, -30.0, 0.0
dist = 0.0
pts = []
for i in range(N):
    f = i / SUB + 1
    v = interp(SPEED_KEYS, f) / 3.6
    k = interp(KAPPA_KEYS, f)
    if i % SUB == 0:
        pts.append((x, y, h, dist, f))
    h += k * v * DT
    x += math.sin(h) * v * DT
    y += math.cos(h) * v * DT
    dist += v * DT

print(f"total distance : {dist:.0f} m")
print(f"net heading    : {math.degrees(h):.1f}°   (abs>180 means track loops back)")

# 每 100 m 的航向
print("\n  dist     heading")
for (px, py, ph, pd, pf) in pts:
    if int(pd // 100) != int((pd - interp(SPEED_KEYS, pf) / 3.6 / FPS) // 100):
        pass
for m in range(0, int(dist) + 1, 100):
    best = min(pts, key=lambda p: abs(p[3] - m))
    print(f"  {m:5d} m  {math.degrees(best[2]):7.1f}°")

# 自交检测（赛道半宽 6.4 m -> 中心线间距 < 13 m 视为穿模）
TRACK_HALF = 6.4
GRID = 13.0
samples = []
acc = None
for (px, py, ph, pd, pf) in pts:
    if acc is None or pd - acc >= 4.0:
        samples.append((px, py, pd, pf))
        acc = pd
print(f"\nsamples for self-intersection test: {len(samples)}")

cells = {}
def cell(v):
    return (int(v[0] // GRID), int(v[1] // GRID))

for idx, sp in enumerate(samples):
    cells.setdefault(cell(sp), []).append(idx)

bad = []
for idx, sp in enumerate(samples):
    cx, cy = cell(sp)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for jdx in cells.get((cx + dx, cy + dy), []):
                if jdx <= idx:
                    continue
                sp2 = samples[jdx]
                if abs(sp2[2] - sp[2]) < 30.0:      # 里程相近 -> 相邻段，跳过
                    continue
                d = math.hypot(sp2[0] - sp[0], sp2[1] - sp[1])
                if d < TRACK_HALF * 2 + 1.0:
                    bad.append((round(sp[2]), round(sp2[2]), round(d, 1)))

if bad:
    print(f"!! SELF-INTERSECTION: {len(bad)} pairs")
    for b in bad[:12]:
        print("   dist", b[0], "m  vs", b[1], "m   gap", b[2], "m")
else:
    print("OK: no self-intersection (min gap >= track width)")

# 最小间距（排除相邻 30 m 内）
mind = 1e9
for i in range(len(samples)):
    for j in range(i + 1, len(samples)):
        if abs(samples[j][2] - samples[i][2]) < 30:
            continue
        d = math.hypot(samples[j][0] - samples[i][0], samples[j][1] - samples[i][1])
        mind = min(mind, d)
print(f"min non-adjacent centerline gap: {mind:.1f} m  (track width = {TRACK_HALF*2:.1f} m)")

# 各弯的半径与速度
print("\n  frame    v(km/h)   radius(m)   lat-g")
for f in (300, 340, 360, 400, 440, 460, 500, 530, 560, 600, 660, 710):
    v = interp(SPEED_KEYS, f) / 3.6
    k = interp(KAPPA_KEYS, f)
    r = (1 / k) if abs(k) > 1e-6 else float("inf")
    g = (v * v * k) / 9.81
    print(f"  {f:5d}   {v*3.6:7.1f}   {r:9.1f}   {g:6.2f}")