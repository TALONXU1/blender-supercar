# -*- coding: utf-8 -*-
import json
d = json.load(open(r"D:\项目session\blender-supercar\track_data\spiderverse_circuit.json", encoding="utf-8"))
m = d["meta"]
pts = d["points"]
print("META:", m)
DT = m["sim_lap_s"] / 1280.0
BF = (60.0 / 108.0) * 24.0
for b in range(0, 97, 2):
    f = 1 + int(round(b * BF))
    t = min(m["sim_lap_s"] - 1e-4, (f - 1) * DT)
    p = next(x for x in pts if x["t"] >= t)
    print(f"Beat {b:2d}  f={f:4d}  t={t:5.2f}s  {p['zone']:21s} s={p['s']:6.1f}  z={p['z']:5.1f}  pt={p['pitch_deg']:+5.1f}  bk={p['bank_deg']:+5.1f}  k={p['curv_1pm']:+.4f}  off={p['racing_offset_m']:+5.2f}  v={p['v_mps']*3.6:5.1f}  tun={int(p['tunnel'])} br={int(p['bridge'])}")
