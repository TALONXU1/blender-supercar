# -*- coding: utf-8 -*-
"""diag_speed.py — 查看速度/曲率分布，定位圈速偏慢的原因"""
import json, sys, math

f = sys.argv[1] if len(sys.argv) > 1 else "silverstone_track.json"
d = json.load(open(f, encoding="utf-8"))
P = d["points"]
V = [p["v_mps"] for p in P]
K = [p["curv_1pm"] for p in P]
S = [p["s"] for p in P]

Vs = sorted(V)
def q(x):
    return Vs[min(len(Vs) - 1, int(x * len(Vs)))]
print("points", len(V))
print("v m/s: min %.1f p10 %.1f p50 %.1f p90 %.1f max %.1f" % (V[0], q(.1), q(.5), q(.9), V[-1]))
print("straight share (v>85): %.1f%%" % (100.0 * sum(1 for v in V if v > 85) / len(V)))
print("slow (<40 m/s): %.1f%%" % (100.0 * sum(1 for v in V if v < 40) / len(V)))
Ks = sorted(K)
print("curv: max %.4f  p99 %.4f  p90 %.4f" % (Ks[-1], Ks[int(.99*len(Ks))], Ks[int(.9*len(Ks))]))
# 曲率分布的占比
big = [(i, K[i], V[i]) for i in range(len(K)) if K[i] > 0.02]
print("points with R<50m: %d (%.1f%% of lap)" % (len(big), 100.0*len(big)/len(K)))
print("lap dist %.0f m" % S[-1])
