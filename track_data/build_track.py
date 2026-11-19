# -*- coding: utf-8 -*-
"""
build_track.py — 真实赛道 -> 机器可读的轨迹数据包（供 agent / Blender 直接消费）

用法:
    python build_track.py "Silverstone" 5.891 87.0
    python build_track.py "Silverstone" 5.891 87.0 --probe   # 只检测数据质量

输出（与脚本同目录）:
    <slug>_track.json   agent 契约 + 逐点数据
    <slug>_path.csv     表格版
    <slug>_map.png      视觉核对图

数据源: OpenStreetMap type=circuit 关系 (ODbL)，剔除 pit_lane，按几何拼接。
"""
import sys, json, math, os, time, urllib.request

ARGS    = [a for a in sys.argv[1:] if not a.startswith('--')]
PROBE   = '--probe' in sys.argv
NAME    = ARGS[0] if len(ARGS) > 0 else "Silverstone"
OFF_KM  = float(ARGS[1]) if len(ARGS) > 1 else 5.891
OFF_LAP = float(ARGS[2]) if len(ARGS) > 2 else 87.0
SLUG    = NAME.lower().replace(" ", "_").replace("'", "").replace(".", "")
OUT     = os.path.dirname(os.path.abspath(__file__))

HOSTS = ['https://lz4.overpass-api.de/api/interpreter',
         'https://overpass-api.de/api/interpreter',
         'https://overpass.kumi.systems/api/interpreter']


def ov(q):
    for h in HOSTS:
        for _ in range(3):
            try:
                r = urllib.request.Request(h, data=q.encode(),
                                           headers={'User-Agent': 'rc-track/1.0'})
                return json.loads(urllib.request.urlopen(r, timeout=120).read())
            except Exception as e:
                print("  retry", h.split('/')[2], type(e).__name__)
                time.sleep(4)
    raise SystemExit("overpass unreachable")


def gd(a, b):
    """经纬度 -> 米（局部等距近似）"""
    return math.hypot((a[0] - b[0]) * 111320.0 * math.cos(math.radians(a[1])),
                      (a[1] - b[1]) * 110540.0)


def plen(p):
    return sum(gd(p[i - 1], p[i]) for i in range(1, len(p)))


# ---------------------------------------------------------------- 1. 取数据
d = ov('[out:json][timeout:90];rel["type"="circuit"]["name"~"%s"];out body;>;out skel qt;' % NAME)
els = d['elements']
rels = [e for e in els if e['type'] == 'relation']
if not rels:
    raise SystemExit("no circuit relation for %r" % NAME)
rel = rels[0]
ways = {e['id']: e for e in els if e['type'] == 'way'}
nodes = {e['id']: (e['lon'], e['lat']) for e in els if e['type'] == 'node'}
print("relation %s %r members=%d" % (rel['id'], (rel.get('tags') or {}).get('name'),
                                     len(rel['members'])))

raw = []
for m in rel['members']:
    if m['type'] != 'way':
        continue
    if 'pit' in (m.get('role') or '').lower():
        continue
    w = ways.get(m['ref'])
    if not w or len(w['nodes']) < 2:
        continue
    seg = [nodes[i] for i in w['nodes'] if i in nodes]
    if len(seg) >= 2:
        raw.append(seg)

# ---------------------------------------------------------------- 2. 去重
keep = []
for p in sorted(raw, key=plen, reverse=True):
    dup = False
    for k in keep:
        if abs(plen(k) - plen(p)) > plen(k) * 0.35:
            continue
        if gd(p[len(p) // 2], k[len(k) // 2]) < 15:
            dup = True
            break
    if not dup:
        keep.append(p)

# ---------------------------------------------------------------- 3. 拼接成闭环
unused = list(range(len(keep)))
chain = list(keep[0])
unused.remove(0)
gaps = []
while unused:
    p = chain[-1]
    a = chain[max(0, len(chain) - 8)]
    vx, vy = p[0] - a[0], p[1] - a[1]
    vm = math.hypot(vx, vy) or 1e-9
    best = None
    for k in unused:
        w = keep[k]
        for rev in (0, 1):
            st = w[-1] if rev else w[0]
            dd = gd(p, st)
            en = w[0] if rev else w[-1]
            dx = (en[0] - p[0]) * 111320.0 * math.cos(math.radians(p[1]))
            dy = (en[1] - p[1]) * 110540.0
            dm = math.hypot(dx, dy) or 1e-9
            cosv = max(-1.0, min(1.0, (dx / dm) * (vx / vm) + (dy / dm) * (vy / vm)))
            sc = dd * (2.0 - cosv)
            if best is None or sc < best[0]:
                best = (sc, k, rev, dd)
    sc, k, rev, dd = best
    unused.remove(k)
    gaps.append(dd)
    w = keep[k][::-1] if rev else keep[k]
    chain.extend(w[1:] if dd < 1.0 else w)

close_gap = gd(chain[0], chain[-1])
raw_len = sum(plen(p) for p in raw)
chain_len = plen(chain)
print("ways raw=%d kept=%d  raw_len=%.0fm chain_len=%.0fm close_gap=%.1fm maxgap=%.0fm"
      % (len(raw), len(keep), raw_len, chain_len, close_gap, max(gaps) if gaps else 0))

if PROBE:
    print("QUALITY: length_error=%+.1f%%  big_gaps=%d"
          % ((chain_len / (OFF_KM * 1000) - 1) * 100, len([g for g in gaps if g > 20])))
    raise SystemExit(0)

# ---------------------------------------------------------------- 4. 闭合 + 投影到米
if close_gap > 1.0:
    chain.append(chain[0])
lat0, lon0 = chain[0][1], chain[0][0]
KX = 111320.0 * math.cos(math.radians(lat0))
KY = 110540.0
XY = [((lo - lon0) * KX, (la - lat0) * KY) for lo, la in chain]
if math.hypot(XY[0][0] - XY[-1][0], XY[0][1] - XY[-1][1]) < 1.0:
    XY.pop()


def resample(P, step=2.0):
    out = [P[0]]
    acc = 0.0
    for i in range(1, len(P) + 1):
        a = P[i - 1]
        b = P[i % len(P)]
        seg = math.hypot(b[0] - a[0], b[1] - a[1])
        if seg < 1e-9:
            continue
        while acc + seg >= step:
            t = (step - acc) / seg
            a = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            out.append(a)
            seg -= (step - acc)
            acc = 0.0
        acc += seg
    return out


CL = resample(XY, 2.0)


def smooth(P, half=5, passes=3):
    """周期性箱式平滑：削掉 OSM 折线顶点造成的曲率尖刺，不动真实弯道半径"""
    Q = P
    for _ in range(passes):
        R = []
        m = len(Q)
        for i in range(m):
            sx = sy = 0.0
            for k in range(-half, half + 1):
                p = Q[(i + k) % m]
                sx += p[0]
                sy += p[1]
            R.append((sx / (2 * half + 1), sy / (2 * half + 1)))
        Q = R
    return Q


CL = smooth(CL, 5, 3)
n = len(CL)
S = [0.0]
for i in range(1, n + 1):
    a, b = CL[i - 1], CL[i % n]
    S.append(S[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
LAP = S[-1]


def curv(L, i):
    a, b, c = L[(i - 1) % n], L[i], L[(i + 1) % n]
    ab = math.hypot(b[0] - a[0], b[1] - a[1])
    bc = math.hypot(c[0] - b[0], c[1] - b[1])
    ca = math.hypot(a[0] - c[0], a[1] - c[1])
    cr = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    den = ab * bc * ca
    return 0.0 if den < 1e-12 else 2.0 * abs(cr) / den


NM = []
for i in range(n):
    a, b = CL[(i - 1) % n], CL[(i + 1) % n]
    tx, ty = b[0] - a[0], b[1] - a[1]
    mm = math.hypot(tx, ty) or 1.0
    NM.append((-ty / mm, tx / mm))

# ---------------------------------------------------------------- 5. 赛车线
HALF_W, MARGIN = 7.0, 1.3
LIM = HALF_W - MARGIN
off = [0.0] * n
for _ in range(500):
    L = [(CL[i][0] + NM[i][0] * off[i], CL[i][1] + NM[i][1] * off[i]) for i in range(n)]
    for i in range(n):
        px = (L[(i - 1) % n][0] + 2.0 * L[i][0] + L[(i + 1) % n][0]) / 4.0
        py = (L[(i - 1) % n][1] + 2.0 * L[i][1] + L[(i + 1) % n][1]) / 4.0
        dv = (px - CL[i][0]) * NM[i][0] + (py - CL[i][1]) * NM[i][1]
        off[i] = max(-LIM, min(LIM, dv))
LINE = [(CL[i][0] + NM[i][0] * off[i], CL[i][1] + NM[i][1] * off[i]) for i in range(n)]

KL = [curv(LINE, i) for i in range(n)]
SL = [0.0]
for i in range(1, n + 1):
    a, b = LINE[i - 1], LINE[i % n]
    SL.append(SL[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))

# ---------------------------------------------------------------- 6. 速度剖面
# 下压力模型：横向极限随速度平方增长（F1 低速约 1.5g，250km/h 约 5g）
G = 9.81
A0_LAT, C_LAT = 15.0, 0.00714
A_BRK_BASE, C_BRK, A_BRK_CAP = 20.0, 0.0050, 55.0
A_TRACTION, P_POWER = 16.0, 937.0
VMAX = 92.0


def a_brake(v):
    return min(A_BRK_CAP, A_BRK_BASE + C_BRK * v * v)


def a_accel(v):
    return min(A_TRACTION, P_POWER / max(v, 1.0))


def v_corner(k):
    if k <= C_LAT:
        return VMAX
    return min(VMAX, math.sqrt(A0_LAT / (k - C_LAT)))


V = [v_corner(k) for k in KL]
for _ in range(6):
    for i in range(n - 1, -1, -1):
        ds = SL[i + 1] - SL[i]
        vn = V[(i + 1) % n]
        vi = math.sqrt(vn * vn + 2 * a_brake(vn) * ds)
        for _ in range(3):
            vi = math.sqrt(vn * vn + 2 * a_brake(vi) * ds)
        V[i] = min(V[i], vi)
    for i in range(1, n + 1):
        ds = SL[i] - SL[i - 1]
        vp = V[i - 1]
        V[i % n] = min(V[i % n], math.sqrt(vp * vp + 2 * a_accel(vp) * ds))

TM = [0.0]
for i in range(n):
    ds = SL[i + 1] - SL[i]
    TM.append(TM[-1] + ds / max((V[i] + V[(i + 1) % n]) / 2.0, 0.5))
LAP_T = TM[-1]
lat_g = [V[i] ** 2 * KL[i] / G for i in range(n)]
over = [i for i in range(n) if V[i] ** 2 * KL[i] > A0_LAT + C_LAT * V[i] ** 2 + 0.5]

# ---------------------------------------------------------------- 7. 导出
pts = []
for i in range(n):
    a, b = LINE[(i - 1) % n], LINE[(i + 1) % n]
    hx, hy = b[0] - a[0], b[1] - a[1]
    hm = math.hypot(hx, hy) or 1.0
    pts.append({
        "i": i, "s": round(S[i], 3),
        "xy": [round(CL[i][0], 3), round(CL[i][1], 3)], "z": 0.0,
        "half_width": HALF_W,
        "heading_deg": round(math.degrees(math.atan2(hy / hm, hx / hm)), 3),
        "curv_1pm": round(KL[i], 6),
        "radius_m": (round(1.0 / KL[i], 2) if KL[i] > 1e-6 else None),
        "racing_xy": [round(LINE[i][0], 3), round(LINE[i][1], 3)],
        "racing_offset_m": round(off[i], 3),
        "v_mps": round(V[i], 3), "v_kmh": round(V[i] * 3.6, 1),
        "t": round(TM[i], 4), "lat_g": round(lat_g[i], 3)})

meta = {
    "schema": "race-path/1.0",
    "circuit": NAME,
    "source": "OpenStreetMap type=circuit relation (ODbL), pit lane removed, resampled 2m",
    "osm_relation": rel['id'],
    "units": "SI: meters, seconds, m/s, degrees CCW from +X",
    "georef": {"lat0": lat0, "lon0": lon0,
               "kx_m_per_deg": round(KX, 3), "ky_m_per_deg": round(KY, 3),
               "world_xy_from_wgs84": "x=(lon-lon0)*kx, y=(lat-lat0)*ky"},
    "closed_loop": True,
    "official_length_km": OFF_KM,
    "measured_length_km": round(LAP / 1000.0, 4),
    "length_error_pct": round((LAP / 1000.0 - OFF_KM) / OFF_KM * 100, 2),
    "official_lap_s": OFF_LAP,
    "sim_lap_s": round(LAP_T, 2),
    "lap_error_pct": round((LAP_T - OFF_LAP) / OFF_LAP * 100, 2),
    "sim_avg_kmh": round(LAP / LAP_T * 3.6, 1),
    "points": n, "sample_step_m": 2.0, "track_half_width_m": HALF_W,
    "limits": {
        "a_lat_model": "a_lat(v) = 15.0 + 0.00714 * v^2  [m/s^2, 含下压力]",
        "a_brake_model": "min(55, 20 + 0.005 * v^2)",
        "a_accel_model": "min(16, 937 / v)",
        "v_max_mps": VMAX},
    "geometry_quality": {"raw_ways": len(raw), "kept_ways": len(keep),
                         "raw_len_m": round(raw_len, 1),
                         "stitch_close_gap_m": round(close_gap, 1),
                         "gaps_over_20m": len([g for g in gaps if g > 20])},
    "anti_drift_check": {"max_lat_g": round(max(lat_g), 3),
                         "points_over_limit": len(over),
                         "verdict": "PASS" if not over else "FAIL"},
    "agent_contract": [
        "位置沿 racing_xy 按 t 插值，不要用 xy（那是中心线）",
        "朝向取 heading_deg（切线方向），禁止用位移差反推朝向",
        "速度取 v_mps，按 t 驱动时间轴",
        "硬约束: v^2 * curv_1pm 不得超过 limits.a_lat_model，超出即判为漂移",
        "帧间线性插值；贝塞尔过冲会在弯心把车甩出赛道",
        "轮速 = v_mps / 0.33 (18寸胎半径m)",
        "前轮转角 = curv_1pm * 3.6 (轴距m)，单位弧度"],
}

json.dump({"meta": meta, "points": pts},
          open(os.path.join(OUT, SLUG + "_track.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

with open(os.path.join(OUT, SLUG + "_path.csv"), "w", encoding="utf-8") as f:
    f.write("t,x,y,heading_deg,v_mps,v_kmh,curv,offset_m,lat_g\n")
    for p in pts:
        f.write("%.4f,%.3f,%.3f,%.3f,%.3f,%.1f,%.6f,%.3f,%.3f\n" % (
            p["t"], p["racing_xy"][0], p["racing_xy"][1], p["heading_deg"],
            p["v_mps"], p["v_kmh"], p["curv_1pm"], p["racing_offset_m"], p["lat_g"]))

# ---------------------------------------------------------------- 8. 出图
try:
    from PIL import Image, ImageDraw
    W = H = 1500
    xs = [p[0] for p in CL]
    ys = [p[1] for p in CL]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    pad = 80
    sc = min((W - 2 * pad) / max(x1 - x0, 1), (H - 2 * pad) / max(y1 - y0, 1))

    def px(p):
        return (pad + (p[0] - x0) * sc, H - pad - (p[1] - y0) * sc)

    img = Image.new("RGB", (W, H), "white")
    dr = ImageDraw.Draw(img)
    dr.line([px(p) for p in CL] + [px(CL[0])], fill=(228, 228, 228),
            width=max(4, int(HALF_W * 2 * sc)))
    for i in range(n):
        v = V[i] / VMAX
        dr.line([px(LINE[i]), px(LINE[(i + 1) % n])],
                fill=(int(235 * v), int(50 + 140 * v), int(235 * (1 - v))), width=4)
    dr.text((30, 24), "%s  %.3f km  sim %.1fs  avg %.0f km/h" % (
        NAME, LAP / 1000, LAP_T, LAP / LAP_T * 3.6), fill=(20, 20, 20))
    img.save(os.path.join(OUT, SLUG + "_map.png"))
except Exception as e:
    print("plot skipped:", e)

print("QUALITY len %.3f km vs %.3f (%+.2f%%)  lap %.2fs vs %.1fs (%+.2f%%)"
      % (LAP / 1000, OFF_KM, meta["length_error_pct"], LAP_T, OFF_LAP, meta["lap_error_pct"]))
print("DRIFT", json.dumps(meta["anti_drift_check"]))
print("SPEED vmax %.0f  vmin %.0f  pts %d" % (max(V) * 3.6, min(V) * 3.6, n))
