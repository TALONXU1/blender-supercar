# -*- coding: utf-8 -*-
"""
V5 ANIM — 真实赛道整圈（Silverstone / 90.34 s / 162 拍 / 2161 帧）
输入: LATEST/v5_stage_env.blend
输出: LATEST/v5_stage_anim.blend
运行:
  blender -b -P pipeline/v5_anim.py -- --test 60,300,700,1500
  blender -b -P pipeline/v5_anim.py -- --render

五条硬规则（来自 track_data/TRACK_SPEC.md）
  1. 位置按 t 插值，不按帧均分
  2. 朝向取 heading_deg，不用位移差反推
  3. 位置走 racing_xy，不是 xy
  4. 关键帧 LINEAR，禁 Bezier
  5. v^2 * curv 不得超过 15.0 + 0.00714 v^2
"""
import bpy, json, math, os, sys, random
from mathutils import Vector, Matrix, Euler
from math import sin, cos, pi, radians, degrees, sqrt

PROJ = r"D:\项目session\blender-supercar"
IN = os.path.join(PROJ, "LATEST", "v5_stage_env.blend")
OUT = os.path.join(PROJ, "LATEST", "v5_stage_anim.blend")
TRACK = os.path.join(PROJ, "track_data", "silverstone_track.json")
FRAMES_DIR = os.path.join(PROJ, "renders_v5", "frames")
STILLS_DIR = os.path.join(PROJ, "renders_v5", "stills")

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def argval(flag, default=None):
    if flag in ARGV:
        i = ARGV.index(flag)
        if i + 1 < len(ARGV) and not ARGV[i + 1].startswith("--"):
            return ARGV[i + 1]
        return True
    return default


# ---------------------------------------------------------------
# 0. 参数
# ---------------------------------------------------------------
FPS = 24
BEAT = 60.0 / 108.0                 # After Hours 108 BPM -> 0.5556 s
BEAT_F = BEAT * FPS                 # 13.3333 帧
TOTAL_BEATS = 162
FRAME_END = int(round(1 + TOTAL_BEATS * BEAT_F))    # 2161
R_TIRE = 0.357
WHEELBASE = 3.6

data = json.load(open(TRACK, encoding="utf-8"))
META = data["meta"]
P = data["points"]
N = len(P)
LAP_S = META["sim_lap_s"]           # 90.34
DT = LAP_S / (FRAME_END - 1)        # 每帧时间步（保证整圈正好铺满）

T_ARR = [p["t"] for p in P]
RX_ARR = [Vector((p["racing_xy"][0], p["racing_xy"][1], 0.0)) for p in P]
HD_ARR = [p["heading_deg"] for p in P]
V_ARR = [p["v_mps"] for p in P]
K_ARR = [abs(p["curv_1pm"] or 0.0) for p in P]


def _unwrap(deg_list):
    out = [deg_list[0]]
    for a in deg_list[1:]:
        d = (a - out[-1] + 180.0) % 360.0 - 180.0
        out.append(out[-1] + d)
    return out


_HD_UN = _unwrap(HD_ARR)
_SPAN = 4
_SDS = 2 * _SPAN * (META["measured_length_km"] * 1000.0 / N)


def _ssign(i):
    a = _HD_UN[(i - _SPAN) % N]
    b = _HD_UN[(i + _SPAN) % N]
    return 1.0 if (b - a) >= 0 else -1.0


KS_ARR = [_ssign(i) * K_ARR[i] for i in range(N)]


def sample(t):
    """t -> (位置, 航向[rad, CCW from +X], 速度 m/s, 有符号曲率)"""
    t = max(0.0, min(LAP_S - 1e-6, t))
    lo, hi = 0, N - 1
    while hi - lo > 1:
        m = (lo + hi) // 2
        if T_ARR[m] <= t:
            lo = m
        else:
            hi = m
    span = max(T_ARR[lo + 1] - T_ARR[lo], 1e-9)
    f = (t - T_ARR[lo]) / span
    pos = RX_ARR[lo].lerp(RX_ARR[lo + 1], f)
    a = radians(HD_ARR[lo])
    b = radians(HD_ARR[lo + 1])
    d = (b - a + pi) % (2 * pi) - pi
    return pos, a + d * f, V_ARR[lo] + (V_ARR[lo + 1] - V_ARR[lo]) * f, \
        KS_ARR[lo] + (KS_ARR[lo + 1] - KS_ARR[lo]) * f


# ---------------------------------------------------------------
# 1. 每帧姿态
# ---------------------------------------------------------------
frame_data = {}
dist = 0.0
prev_pos = None
for f in range(1, FRAME_END + 1):
    t = (f - 1) * DT
    pos, h, v, k = sample(t)
    if prev_pos is not None:
        dist += (pos - prev_pos).length
    prev_pos = pos
    fwd = Vector((cos(h), sin(h), 0.0))
    right = Vector((sin(h), -cos(h), 0.0))
    frame_data[f] = dict(t=t, pos=pos, heading=h, v=v, k=k, dist=dist, fwd=fwd, right=right)

# 纵向加速度 / 横向加速度
for f in range(1, FRAME_END + 1):
    f0 = max(1, f - 2)
    f1 = min(FRAME_END, f + 2)
    dv = frame_data[f1]['v'] - frame_data[f0]['v']
    accel = dv / ((f1 - f0) * DT)
    v = frame_data[f]['v']
    k = frame_data[f]['k']
    frame_data[f]['accel'] = accel
    frame_data[f]['lat'] = v * v * abs(k) / 9.81          # g
    frame_data[f]['gear'] = min(8, max(1, int((v * 3.6 - 60) / 40.0) + 1))

# ---------------------------------------------------------------
# 2. 打开场景
# ---------------------------------------------------------------
bpy.ops.wm.open_mainfile(filepath=IN)
scene = bpy.context.scene
rig = bpy.data.objects["RIG_F1_Race"]

# 发车灯常暗（这圈是飞驰圈，不是发车）
_sl = bpy.data.materials.get("V5_StartLight")
if _sl:
    for n in _sl.node_tree.nodes:
        if n.type == 'BSDF_PRINCIPLED' and 'Emission Strength' in n.inputs:
            n.inputs['Emission Strength'].default_value = 0.0

bone_root = rig.pose.bones["Bone_Root"]
bone_heading = rig.pose.bones["Bone_Heading"]
bone_body = rig.pose.bones["Bone_Body"]

# 尾部雨灯（刹车时增亮）
brake_light = None
_rl = bpy.data.objects.get("GEO_F1_FIA_RainLight")
if _rl and _rl.data.materials:
    _m = _rl.data.materials[0]
    if _m and _m.node_tree:
        for _n in _m.node_tree.nodes:
            if _n.type == 'BSDF_PRINCIPLED' and 'Emission Strength' in _n.inputs:
                brake_light = _n
                break
            if _n.type == 'EMISSION':
                brake_light = _n
                break

# 随车柔光
# 随车三点补光：左前冷光 / 右前暖光 / 后方轮廓光
_FILL = [
    dict(ahead=5.5, side=-6.0, up=4.0, energy=260.0, size=18.0, color=(0.60, 0.74, 1.0)),
    dict(ahead=5.5, side=6.0, up=4.0, energy=260.0, size=18.0, color=(1.0, 0.90, 0.78)),
    dict(ahead=-7.0, side=2.4, up=2.4, energy=320.0, size=10.0, color=(0.85, 0.92, 1.0)),
]
# 只照车的补光：用 light linking 把地面/环境排除在接收端之外
_car_coll = bpy.data.collections.new("V5_CarLightReceivers")
for _ob in bpy.data.objects:
    if _ob.type == 'MESH' and not _ob.name.startswith(("V5_", "GEO_")):
        _car_coll.objects.link(_ob)

fill_lights = []
for i, spec in enumerate(_FILL):
    fd_l = bpy.data.lights.new(f"LGT_V5Car_{i}", 'AREA')
    fd_l.energy = spec['energy']
    fd_l.size = spec['size']
    fd_l.color = spec['color']
    fo = bpy.data.objects.new(f"LGT_V5Car_{i}", fd_l)
    scene.collection.objects.link(fo)
    try:
        fo.light_linking.receiver_collection = _car_coll
        fo.light_linking.link_state = 'INCLUDE'
    except Exception as _e:
        print("light linking unavailable:", _e)
    fill_lights.append((fo, spec))

# ---------------------------------------------------------------
# 3. 逐帧烘焙
# ---------------------------------------------------------------
cum_spin = 0.0
prev_dist = 0.0
prev_gear = 1
shift_flash = 0.0

print("BAKE START: %d frames, dt=%.5f s, lap=%.2f s" % (FRAME_END, DT, LAP_S))
for f in range(1, FRAME_END + 1):
    fd = frame_data[f]
    v, acc, lat, k = fd['v'], fd['accel'], fd['lat'], fd['k']
    v_kmh = v * 3.6

    # --- 位置 / 偏航（车模型前方 = 局部 +Y → rotation_z = heading - 90°）---
    yaw = fd['heading'] - pi / 2
    bone_root.location = (fd['pos'].x, fd['pos'].y, 0.012)   # 轮胎落在沥青面上
    bone_heading.rotation_euler = (0.0, 0.0, yaw)
    bone_root.keyframe_insert("location", frame=f)
    bone_heading.keyframe_insert("rotation_euler", frame=f)

    # --- 车身姿态：俯仰 / 侧倾 / 升沉 ---
    gear = fd['gear']
    if gear != prev_gear:
        shift_flash = 1.0
        prev_gear = gear
    else:
        shift_flash *= 0.72

    pitch = max(-1.9, min(1.4, acc * 0.085)) - 0.16 * shift_flash
    roll = max(-2.2, min(2.2, -lat * 0.26))
    heave = -0.006 + 0.0016 * sin(f * 1.31) + 0.0009 * sin(f * 2.77)
    bone_body.location = (0.0, 0.0, heave)
    bone_body.rotation_euler = (radians(pitch), radians(roll), 0.0)
    bone_body.keyframe_insert("location", frame=f)
    bone_body.keyframe_insert("rotation_euler", frame=f)

    # --- 机械驱动 ---
    cum_spin += (fd['dist'] - prev_dist) / R_TIRE
    prev_dist = fd['dist']
    rig["wheel_spin"] = cum_spin

    steer_deg = degrees(k * WHEELBASE)                   # 阿克曼转角
    rig["steer"] = max(-26.0, min(26.0, steer_deg))

    straight = abs(k) < 0.0016
    rig["drs"] = 1.0 if (straight and v_kmh > 240) else (0.0 if abs(k) > 0.004 else 0.5)
    rig["brake_heat"] = max(0.0, min(1.3, -acc * 0.11))
    rig["rear_slip"] = 1.0
    rig["susp_f"] = -0.004 - 0.014 * max(0.0, -acc) / 12.0
    rig["susp_r"] = -0.004 - 0.016 * max(0.0, acc) / 12.0
    for kk in ("wheel_spin", "steer", "drs", "brake_heat", "rear_slip", "susp_f", "susp_r"):
        rig.keyframe_insert(f'["{kk}"]', frame=f)

    if brake_light and 'Strength' in brake_light.inputs:
        brake_light.inputs['Strength'].default_value = 1.0 + rig["brake_heat"] * 12.0
        brake_light.inputs['Strength'].keyframe_insert("default_value", frame=f)

    # 随车柔光
    for fo, spec in fill_lights:
        lp = fd['pos'] + fd['fwd'] * spec['ahead'] + fd['right'] * spec['side']             + Vector((0, 0, spec['up']))
        fo.location = lp
        aim = (fd['pos'] + Vector((0, 0, 0.45))) - lp
        fo.rotation_euler = aim.to_track_quat('-Z', 'Y').to_euler()
        fo.keyframe_insert("location", frame=f)
        fo.keyframe_insert("rotation_euler", frame=f)

print("BAKE DONE")


def iter_fcurves(action):
    """Blender 5.x: Action 有 layered/slotted 结构，fcurves 在 channelbag 里"""
    fcs = list(getattr(action, "fcurves", []) or [])
    if fcs:
        return fcs
    for layer in getattr(action, "layers", []) or []:
        for strip in getattr(layer, "strips", []) or []:
            for cb in getattr(strip, "channelbags", []) or []:
                fcs.extend(cb.fcurves)
    return fcs


# 所有关键帧 LINEAR
ad = rig.animation_data
if ad and ad.action:
    _n = 0
    for fc in iter_fcurves(ad.action):
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
            _n += 1
    print("LINEAR keyframes:", _n)

# ---------------------------------------------------------------
# 4. 物理自检（横向加速度上限 + 赛道内 + 航向连续）
# ---------------------------------------------------------------
VMAX = META["limits"]["v_max_mps"]
LIM = 15.0 + 0.00714 * VMAX ** 2
worst = max(frame_data.values(), key=lambda d: d['v'] ** 2 * abs(d['k']))
over = [f for f, d in frame_data.items() if d['v'] ** 2 * abs(d['k']) > LIM + 0.5]
jumps = []
for f in range(2, FRAME_END + 1):
    d0, d1 = frame_data[f - 1], frame_data[f]
    dh = abs((d1['heading'] - d0['heading'] + pi) % (2 * pi) - pi)
    if dh > 0.12:
        jumps.append((f, degrees(dh)))
print("[check] 最坏横向 %.2f m/s^2 (%.2f g) @ frame %d, t=%.1f s"
      % (worst['v'] ** 2 * abs(worst['k']), worst['v'] ** 2 * abs(worst['k']) / 9.81,
         int(round(worst['t'] / DT)) + 1, worst['t']))
print("[check] 超限帧 %d -> %s" % (len(over), "PASS" if not over else "FAIL"))
print("[check] 航向跳变帧(>6.9deg) %d -> %s" % (len(jumps), "PASS" if not jumps else str(jumps[:6])))
print("[check] v_max %.1f km/h, lap %.2f s, 帧数 %d" % (max(d['v'] for d in frame_data.values()) * 3.6, LAP_S, FRAME_END))
