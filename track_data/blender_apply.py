# -*- coding: utf-8 -*-
"""
blender_apply.py — 把 *_track.json 变成 Blender 里不会漂移的车动画

用法（Blender 内部，Scripting 面板）:
  1. 改下面 CONFIG 里的 JSON 路径、车物体名、轮子名、慢放倍数
  2. Run Script

规则（这是防漂移的核心，别改）:
  - 位置：沿 racing_xy 按 t 线性插值，不是按帧均分
  - 朝向：用 heading_deg（切线），不是用位移差反推
  - 速度：v_mps 决定经过每个点的时间，不是匀速
  - 关键帧插值：LINEAR。贝塞尔在弯心会过冲，看起来就是漂移
  - 自检：脚本末尾会重算每帧横向加速度，超限直接报 FAIL
"""
import bpy, json, math, os
from mathutils import Vector

# ============================ CONFIG ============================
CONFIG = {
    "json": r"silverstone_track.json",   # 绝对路径或与 blend 同目录
    "car_obj": "F1_Car",                 # 车物体名；不存在则自动建空物体
    "wheels": ["Wheel_FL", "Wheel_FR", "Wheel_RL", "Wheel_RR"],
    "front_wheels": ["Wheel_FL", "Wheel_FR"],
    "fps": 30,
    "slow_motion": 1.0,                  # 0.5 = 半速播放，物理曲线不变
    "wheel_radius_m": 0.33,              # 18 寸胎
    "wheelbase_m": 3.6,
    "loop": True,                        # 首尾关键帧对齐，可无缝循环
    "create_track_curve": True,          # 顺带把赛道中心线建成曲线
}
# ================================================================

CFG = CONFIG
HERE = os.path.dirname(bpy.data.filepath) or os.getcwd()
jp = CFG["json"] if os.path.isabs(CFG["json"]) else os.path.join(HERE, CFG["json"])
data = json.load(open(jp, encoding="utf-8"))
meta, P = data["meta"], data["points"]
n = len(P)
print("[track] %s  %.3f km  %.2f s  %d pts  lat_max %.2f g"
      % (meta["circuit"], meta["measured_length_km"], meta["sim_lap_s"],
         n, meta["anti_drift_check"]["max_lat_g"]))

sc = bpy.context.scene
sc.render.fps = CFG["fps"]
fps = CFG["fps"]
lap_t = meta["sim_lap_s"] * CFG["slow_motion"]
frames = int(round(lap_t * fps))
sc.frame_start, sc.frame_end = 1, frames

# ---------------- 赛道中心线（可选，用来对位校核） ----------------
if CFG["create_track_curve"] and "TrackCenterline" not in bpy.data.objects:
    cu = bpy.data.curves.new("TrackCenterline", 'CURVE')
    cu.dimensions = '3D'
    sp = cu.splines.new('POLY')
    sp.points.add(n - 1)
    for i, p in enumerate(P):
        sp.points[i].co = (p["xy"][0], p["xy"][1], 0.0, 1.0)
    cu.bevel_depth = meta["track_half_width_m"]
    cu.bevel_resolution = 2
    ob = bpy.data.objects.new("TrackCenterline", cu)
    sc.collection.objects.link(ob)
    print("[track] 已生成中心线曲线，bevel_depth = 半宽 %.1f m" % meta["track_half_width_m"])

# ---------------- 采样：t -> (位置, 航向, 速度) ----------------
T = [p["t"] for p in P]
T.append(meta["sim_lap_s"])
XY = [Vector((p["racing_xy"][0], p["racing_xy"][1], 0.0)) for p in P]
HD = [math.radians(p["heading_deg"]) for p in P]
VV = [p["v_mps"] for p in P]
KK = [p["curv_1pm"] for p in P]


def sample(t):
    t = t % meta["sim_lap_s"]
    lo, hi = 0, n
    while hi - lo > 1:
        m = (lo + hi) // 2
        if T[m] <= t:
            lo = m
        else:
            hi = m
    f = (t - T[lo]) / max(T[lo + 1] - T[lo], 1e-9)
    pos = XY[lo].lerp(XY[(lo + 1) % n], f)
    a, b = HD[lo], HD[(lo + 1) % n]
    d = (b - a + math.pi) % (2 * math.pi) - math.pi      # 最短角差
    return pos, a + d * f, VV[lo], KK[lo]


# ---------------- 取/建车物体 ----------------
car = bpy.data.objects.get(CFG["car_obj"])
if car is None:
    car = bpy.data.objects.new(CFG["car_obj"], None)
    car.empty_display_size = 2.0
    sc.collection.objects.link(car)
    print("[car] '%s' 不存在，已建空物体占位；把模型 parent 到它即可" % CFG["car_obj"])
if car.animation_data is None:
    car.animation_data_create()
act = bpy.data.actions.new("F1_Lap")
car.animation_data.action = act
if hasattr(car.animation_data, "action_slot"):          # Blender 4.4+ slotted actions
    try:
        car.animation_data.action_slot = act.slots[0] if act.slots else None
    except Exception:
        pass

# ---------------- 烘焙关键帧 ----------------
W = {}
for w in CFG["wheels"]:
    ob = bpy.data.objects.get(w)
    if ob is not None:
        W[w] = ob
spin = {w: 0.0 for w in W}
prev_pos, prev_ang = None, None
lat_accel = []

for fr in range(1, frames + 1):
    t = (fr - 1) / fps
    pos, ang, v, k = sample(t)
    car.location = pos
    car.rotation_euler = (0.0, 0.0, ang)
    car.keyframe_insert("location", frame=fr)
    car.keyframe_insert("rotation_euler", frame=fr)

    if prev_pos is not None:
        ds = (pos - prev_pos).length
        for w in spin:
            spin[w] += ds / CFG["wheel_radius_m"]
        # 自检：a_lat = v^2 * kappa
        lat_accel.append((v * v * abs(k), fr))
    prev_pos = pos

    steer = k * CFG["wheelbase_m"]
    for w in CFG["front_wheels"]:
        if w in W:
            W[w].rotation_euler = (0.0, 0.0, ang + steer)
            W[w].keyframe_insert("rotation_euler", frame=fr)
    for w in W:
        if w not in CFG["front_wheels"]:
            W[w].rotation_euler = (spin[w], 0.0, ang)
            W[w].keyframe_insert("rotation_euler", frame=fr)

# 插值必须是线性，贝塞尔过冲 = 漂移
for fc in act.fcurves:
    for kp in fc.keyframe_points:
        kp.interpolation = 'LINEAR'

if CFG["loop"]:
    for fc in act.fcurves:
        mod = fc.modifiers.new('CYCLES')
        mod.mode_before = 'REPEAT'
        mod.mode_after = 'REPEAT'

# ---------------- 防漂移自检 ----------------
lim = 15.0 + 0.00714 * meta["limits"]["v_max_mps"] ** 2
worst = max(lat_accel, key=lambda x: x[0]) if lat_accel else (0, 0)
bad = [x for x in lat_accel if x[0] > lim + 0.5]
print("[check] 帧数 %d  最坏横向加速度 %.1f m/s^2 (%.2f g) 于第 %d 帧"
      % (frames, worst[0], worst[0] / 9.81, worst[1]))
print("[check] 超限帧数 %d  ->  %s" % (len(bad), "PASS" if not bad else "FAIL"))
print("[check] 单圈 %.2f s（慢放 x%.2f 后播放 %.2f s）"
      % (meta["sim_lap_s"], CFG["slow_motion"], lap_t))
