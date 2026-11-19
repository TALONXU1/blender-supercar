# -*- coding: utf-8 -*-
"""
V5 ANIM — 真实赛道整圈（Silverstone / 90.34 s / 162 拍 / 2161 帧）
输入: pipeline/v5_stage_env.blend
输出: pipeline/v5_stage_anim.blend
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

# ---------------------------------------------------------------
# 5. 机位
# ---------------------------------------------------------------
def make_cam(name, lens=50, fstop=4.0):
    cd = bpy.data.cameras.new(name + "_DATA")
    cd.lens = lens
    cd.clip_start = 0.5
    cd.clip_end = 9000
    cd.sensor_width = 36
    cd.dof.use_dof = True
    cd.dof.aperture_fstop = fstop
    cd.dof.aperture_blades = 9
    ob = bpy.data.objects.new(name, cd)
    scene.collection.objects.link(ob)
    return ob


def cam_look(ob, loc, target, roll_deg=0.0, fstop=None, lens=None):
    loc = Vector(loc)
    tgt = Vector(target)
    d = tgt - loc
    q = d.to_track_quat('-Z', 'Y')
    m = q.to_matrix().to_4x4()
    if abs(roll_deg) > 1e-6:
        m = m @ Matrix.Rotation(radians(roll_deg), 4, 'Z')
    ob.matrix_world = Matrix.Translation(loc) @ m
    if fstop is not None:
        ob.data.dof.aperture_fstop = fstop
        ob.data.dof.focus_distance = d.length
    if lens is not None:
        ob.data.lens = lens


def noise(t, seed=0.0, amp=1.0):
    return (sin(t * 2.3 + seed) * 0.55 + sin(t * 5.7 + seed * 2.3) * 0.3
            + sin(t * 11.3 + seed * 4.1) * 0.15) * amp


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def key_cam(cam, f, loc, tgt, roll=0.0, fstop=4.0, lens=50, lens_key=True):
    cam_look(cam, loc, tgt, roll_deg=roll, fstop=fstop, lens=lens)
    cam.keyframe_insert("location", frame=f)
    cam.keyframe_insert("rotation_euler", frame=f)
    cam.data.dof.keyframe_insert("focus_distance", frame=f)
    cam.data.dof.keyframe_insert("aperture_fstop", frame=f)
    if lens_key:
        cam.data.keyframe_insert("lens", frame=f)


def F(beat):
    return 1 + int(round(beat * BEAT_F))


# 车体坐标系里的机位
def C(fd, back=0.0, side=0.0, h=0.5):
    return fd['pos'] - fd['fwd'] * back + fd['right'] * side + Vector((0, 0, h))


def T(fd, ahead=0.0, side=0.0, h=0.45):
    return fd['pos'] + fd['fwd'] * ahead + fd['right'] * side + Vector((0, 0, h))


def fixed_point(f, back=0.0, side=0.0, h=0.5):
    """以某帧车体为参考，固定在世界的机位"""
    fd = frame_data[f]
    return C(fd, back, side, h)


CAR_LEN = 4.7          # 用于定焦：让车在画面里占固定比例
SENSOR_W = 36.0


def lens_for_framing(dist, frac):
    """给定距离与目标占比，算焦距"""
    return max(20.0, min(320.0, frac * SENSOR_W * max(dist, 1.0) / CAR_LEN))


CAR_LEN = 4.7          # 定焦用：让车在画面里的宽度占比稳定
SENSOR_W = 36.0


CAR_W = 2.2


def lens_for_framing(dist, frac, cos_a=0.0):
    """cos_a: 1=正对车头/车尾, 0=正侧面。按投影宽度算焦距"""
    w_eff = CAR_W + (CAR_LEN - CAR_W) * (1.0 - abs(cos_a))
    return max(20.0, min(320.0, frac * SENSOR_W * max(dist, 1.0) / max(w_eff, 0.5)))


SHOTS = [
    # (名字, t0, t1, 类型, 参数)  —— t 为赛道时间（秒），切点吸附 108 BPM 拍点
    ("Cam_S01_RearChase", 0.0, 4.6, "chase",
     dict(back0=8.0, back1=11.5, side0=1.1, side1=-1.1, h0=0.45, h1=1.15,
          aim0=2.4, aim1=3.6, lens0=38, lens1=31, fstop=4.0, roll1=1.5)),
    ("Cam_S02_Onboard", 4.6, 8.4, "onboard", dict(fwd=2.55, h=0.50, lens=17, fstop=5.6)),
    ("Cam_S03_ChaseRise", 8.4, 12.4, "chase",
     dict(back0=8.8, back1=6.9, side0=-1.2, side1=3.2, h0=1.30, h1=4.20,
          aim0=4.4, aim1=3.0, lens0=30, lens1=29, fstop=4.0, roll1=4.0)),
    ("Cam_S04_Hairpin", 12.4, 16.6, "fixed",
     dict(t_pass=16.00, lead=-14.0, side=-8.6, h=0.80,
          framing=0.34, fstop=5.0, aim_lerp=0.66, roll=-1.5)),
    ("Cam_S05_ChaseAintree", 16.6, 20.0, "chase",
     dict(back0=7.2, back1=9.0, side0=0.6, side1=-1.2, h0=0.60, h1=1.05,
          aim0=3.0, aim1=4.0, lens0=36, lens1=32, fstop=4.0, roll1=-1.5)),
    ("Cam_S06_Orbit1", 20.0, 23.4, "orbit",
     dict(a0=104, a1=52, r0=10.5, r1=8.0, h0=1.35, h1=1.05,
          lens=44, fstop=3.6, roll=-5.0, roll_end=4.0)),
    ("Cam_S07_ChaseAccel", 23.4, 26.6, "chase",
     dict(back0=9.4, back1=7.8, side0=-1.0, side1=1.2, h0=0.80, h1=0.55,
          aim0=4.4, aim1=3.6, lens0=32, lens1=34, fstop=4.0, roll1=1.0)),
    ("Cam_S08_FastPan", 26.6, 30.6, "fixed",
     dict(t_pass=29.50, lead=0.0, side=14.0, h=0.85,
          framing=0.26, fstop=5.6, aim_lerp=0.74, roll=-2.0)),
    ("Cam_S09_WheelMacro", 30.6, 32.8, "wheel",
     dict(side0=4.20, side1=3.90, back0=-1.20, back1=-0.45, h0=0.48, h1=0.62,
          lens0=34, lens1=30, fstop=3.2)),
    ("Cam_S09b_ChaseFast", 32.8, 35.2, "chase",
     dict(back0=6.4, back1=8.2, side0=-1.4, side1=1.0, h0=0.50, h1=0.85,
          aim0=3.6, aim1=4.6, lens0=30, lens1=27, fstop=3.0, roll1=2.2)),
    ("Cam_S10_OrbitBrooklands", 34.0, 37.4, "orbit",
     dict(a0=98, a1=44, r0=9.2, r1=7.0, h0=1.15, h1=0.95,
          lens=42, fstop=3.4, roll=3.0, roll_end=-2.5)),
    ("Cam_S11_Luffield", 37.4, 41.8, "fixed",
     dict(t_pass=41.40, lead=-9.0, side=10.5, h=1.0,
          framing=0.32, fstop=4.5, aim_lerp=0.66, roll=1.2)),
    ("Cam_S12_ChaseWoodcote", 41.8, 45.0, "chase",
     dict(back0=7.6, back1=9.4, side0=-0.8, side1=1.4, h0=0.75, h1=1.35,
          aim0=3.4, aim1=4.4, lens0=34, lens1=30, fstop=4.0, roll1=2.0)),
    ("Cam_S13_WoodcoteTele", 45.0, 48.4, "fixed",
     dict(t_pass=47.40, lead=-95.0, side=12.0, h=2.4,
          framing=0.24, fstop=8.0, aim_lerp=0.55, roll=0.0)),
    ("Cam_S14_HeliDrop", 48.4, 52.0, "heli", dict(h0=30.0, h1=12.0, back=24.0, lens=85, fstop=7.0)),
    ("Cam_S15_OrbitCopse", 52.0, 55.6, "orbit",
     dict(a0=108, a1=48, r0=11.0, r1=7.8, h0=1.5, h1=1.05,
          lens=40, fstop=3.4, roll=-6.0, roll_end=3.0)),
    ("Cam_S16_ChaseCopse", 55.6, 59.2, "chase",
     dict(back0=7.0, back1=8.4, side0=0.5, side1=-1.1, h0=0.55, h1=1.05,
          aim0=3.4, aim1=4.4, lens0=36, lens1=32, fstop=4.0, roll1=-2.0)),
    ("Cam_S17_Maggotts", 59.2, 63.2, "fixed",
     dict(t_pass=62.50, lead=2.0, side=11.5, h=1.35,
          framing=0.28, fstop=4.5, aim_lerp=0.66, roll=-1.0)),
    ("Cam_S18_ChaseRise2", 63.2, 66.8, "chase",
     dict(back0=9.0, back1=6.6, side0=-1.4, side1=3.8, h0=1.30, h1=4.6,
          aim0=4.6, aim1=2.8, lens0=30, lens1=28, fstop=4.0, roll1=5.0)),
    ("Cam_S19_Onboard3", 66.8, 70.4, "onboard", dict(fwd=2.48, h=0.48, lens=20, fstop=5.6)),
    ("Cam_S20_StoweTele", 70.4, 74.8, "fixed",
     dict(t_pass=74.60, lead=-130.0, side=-13.0, h=2.8,
          framing=0.22, fstop=8.0, aim_lerp=0.55, roll=0.0)),
    ("Cam_S21_OrbitStowe", 74.8, 78.4, "orbit",
     dict(a0=112, a1=50, r0=11.5, r1=8.0, h0=1.6, h1=1.1,
          lens=38, fstop=3.4, roll=5.0, roll_end=-3.0)),
    ("Cam_S22_ChaseLow", 78.4, 82.0, "chase",
     dict(back0=6.6, back1=9.6, side0=1.1, side1=-1.5, h0=0.52, h1=1.45,
          aim0=3.0, aim1=4.4, lens0=38, lens1=31, fstop=3.2, roll1=-3.0)),
    ("Cam_S23_HeliReveal", 82.0, 85.6, "heli", dict(h0=22.0, h1=44.0, back=32.0, lens=70, fstop=8.0)),
    ("Cam_S24_Club", 85.6, 88.4, "fixed",
     dict(t_pass=87.30, lead=-8.0, side=-9.0, h=1.2,
          framing=0.30, fstop=4.5, aim_lerp=0.66, roll=-1.0)),
    ("Cam_S25_AerialOut", 88.4, 90.34, "aerial",
     dict(back0=9.0, back1=17.0, side0=2.5, side1=9.0, h0=3.0, h1=11.0,
          lens0=56, lens1=46, fstop=4.5)),
]


def TF(t):
    """赛道时间 -> 帧号，吸附到最近拍点"""
    f = 1.0 + t / DT
    k = round((f - 1) / BEAT_F)
    return max(1, min(FRAME_END, int(round(1 + k * BEAT_F))))


_windows = []
for name, t0, t1, typ, pr in SHOTS:
    _windows.append([name, TF(t0), TF(t1), typ, pr])

# 顺序修正：严格递增、不许为负长度
for i in range(len(_windows)):
    _windows[i][1] = max(_windows[i][1], 1)
    _windows[i][2] = min(FRAME_END, max(_windows[i][2], _windows[i][1] + 2))
    if i and _windows[i][1] <= _windows[i - 1][2]:
        _windows[i][1] = _windows[i - 1][2] + 1
        _windows[i][2] = max(_windows[i][2], _windows[i][1] + 2)
_windows[-1][2] = FRAME_END

_cams = {}
_markers = []
for name, f0, f1, typ, pr in _windows:
    cam = make_cam(name, pr.get('lens', pr.get('lens0', 50)), pr.get('fstop', 4.0))
    _cams[name] = cam
    _markers.append((name, f0))
    span = max(1, f1 - f0)

    if typ == "chase":
        for f in range(f0, f1 + 1):
            e = smooth((f - f0) / span)
            fd = frame_data[f]
            loc = C(fd, pr['back0'] + (pr['back1'] - pr['back0']) * e,
                    pr['side0'] + (pr['side1'] - pr['side0']) * e,
                    pr['h0'] + (pr['h1'] - pr['h0']) * e)
            loc += Vector((noise(f * 0.06, 11.0, 0.026), noise(f * 0.06, 12.0, 0.026),
                           noise(f * 0.09, 13.0, 0.018)))
            tgt = T(fd, pr['aim0'] + (pr['aim1'] - pr['aim0']) * e, 0, 0.52)
            key_cam(cam, f, loc, tgt,
                    roll=pr.get('roll0', 0.0) + (pr.get('roll1', 0.0) - pr.get('roll0', 0.0)) * e
                    + noise(f * 0.05, 14.0, 0.5),
                    fstop=pr['fstop'],
                    lens=pr['lens0'] + (pr['lens1'] - pr['lens0']) * e)

    elif typ == "fixed":
        fr = max(f0, min(f1, int(round(1 + pr['t_pass'] / DT))))
        loc = C(frame_data[fr], pr['lead'], pr['side'], pr['h'])
        aim = None
        for f in range(f0, f1 + 1):
            fd = frame_data[f]
            tgt = fd['pos'] + Vector((0, 0, 0.34))
            aim = tgt if aim is None else aim.lerp(tgt, pr.get('aim_lerp', 0.7))
            dv = loc - fd['pos']
            d = max(2.0, dv.length)
            cos_a = abs(fd['fwd'].dot(dv.normalized()))
            key_cam(cam, f, loc, aim, roll=pr.get('roll', 0.0), fstop=pr['fstop'],
                    lens=lens_for_framing(d, pr['framing'], cos_a), lens_key=True)

    elif typ == "wheel":
        for f in range(f0, f1 + 1):
            e = smooth((f - f0) / span)
            fd = frame_data[f]
            loc = C(fd, pr['back0'] + (pr['back1'] - pr['back0']) * e,
                    pr['side0'] + (pr['side1'] - pr['side0']) * e,
                    pr['h0'] + (pr['h1'] - pr['h0']) * e)
            loc += Vector((noise(f * 0.17, 81.0, 0.010), noise(f * 0.17, 82.0, 0.010),
                           noise(f * 0.21, 83.0, 0.007)))
            tgt = fd['pos'] + fd['right'] * 0.72 + fd['fwd'] * (1.35 - 0.5 * e) + Vector((0, 0, 0.34))
            key_cam(cam, f, loc, tgt, roll=1.2 - 2.4 * e, fstop=pr['fstop'],
                    lens=pr['lens0'] + (pr['lens1'] - pr['lens0']) * e)

    elif typ == "onboard":
        for f in range(f0, f1 + 1):
            fd = frame_data[f]
            vib = 0.005 + 0.004 * (fd['v'] / 90.0)
            loc = fd['pos'] + fd['fwd'] * pr['fwd'] + Vector((0, 0, pr['h']))
            loc += Vector((noise(f * 0.95, 31.0, vib), noise(f * 0.95, 32.0, vib),
                           noise(f * 1.15, 33.0, vib * 0.6)))
            tgt = loc + fd['fwd'] * 22.0 + Vector((0, 0, -0.34))
            key_cam(cam, f, loc, tgt, roll=noise(f * 0.3, 34.0, 0.8), fstop=pr['fstop'],
                    lens=pr['lens'], lens_key=False)

    elif typ == "orbit":
        for f in range(f0, f1 + 1):
            e = smooth((f - f0) / span)
            fd = frame_data[f]
            ang = radians(pr['a0'] + (pr['a1'] - pr['a0']) * e)
            rad = pr['r0'] + (pr['r1'] - pr['r0']) * e
            ox = fd['fwd'].x * cos(ang) - fd['right'].x * sin(ang)
            oy = fd['fwd'].y * cos(ang) - fd['right'].y * sin(ang)
            loc = fd['pos'] + Vector((ox, oy, 0)) * rad + Vector(
                (0, 0, pr['h0'] + (pr['h1'] - pr['h0']) * e))
            loc += Vector((noise(f * 0.07, 51.0, 0.035), noise(f * 0.07, 52.0, 0.035),
                           noise(f * 0.09, 53.0, 0.018)))
            tgt = fd['pos'] + Vector((0, 0, 0.42))
            key_cam(cam, f, loc, tgt, roll=pr['roll'] + (pr['roll_end'] - pr['roll']) * e,
                    fstop=pr['fstop'], lens=pr['lens'], lens_key=False)

    elif typ == "heli":
        for f in range(f0, f1 + 1):
            e = smooth((f - f0) / span)
            fd = frame_data[f]
            loc = C(fd, pr['back'], 0.0, pr['h0'] + (pr['h1'] - pr['h0']) * e)
            loc += Vector((noise(f * 0.03, 71.0, 0.09), noise(f * 0.03, 72.0, 0.09), 0))
            tgt = fd['pos'] + fd['fwd'] * 2.0 + Vector((0, 0, 0.6))
            key_cam(cam, f, loc, tgt, roll=noise(f * 0.02, 73.0, 1.1), fstop=pr['fstop'],
                    lens=pr['lens'], lens_key=False)

    elif typ == "aerial":
        for f in range(f0, f1 + 1):
            e = smooth((f - f0) / span)
            fd = frame_data[f]
            loc = C(fd, pr['back0'] + (pr['back1'] - pr['back0']) * e,
                    pr['side0'] + (pr['side1'] - pr['side0']) * e,
                    pr['h0'] + (pr['h1'] - pr['h0']) * e)
            loc += Vector((noise(f * 0.04, 91.0, 0.03 * (1 - e)), noise(f * 0.04, 92.0, 0.03 * (1 - e)),
                           noise(f * 0.05, 93.0, 0.02)))
            tgt = fd['pos'] + fd['fwd'] * 1.2 + Vector((0, 0, 0.55))
            key_cam(cam, f, loc, tgt, roll=-1.0 + 2.0 * e, fstop=pr['fstop'],
                    lens=pr['lens0'] + (pr['lens1'] - pr['lens0']) * e)

    print("CAM %-24s %4d-%4d  t=%5.2f..%5.2f s  %-8s" %
          (name, f0, f1, frame_data[f0]['t'], frame_data[f1]['t'], typ))


# 机位切换
scene.timeline_markers.clear()
for name, f0 in _markers:
    mk = scene.timeline_markers.new(name, frame=f0)
    mk.camera = _cams[name]
scene.camera = _cams[SHOTS[0][0]]

# 收尾淡出：最后 14 帧压曝光
scene.view_settings.exposure = 0.50
scene.view_settings.keyframe_insert("exposure", frame=FRAME_END - 16)
scene.view_settings.exposure = -3.6
scene.view_settings.keyframe_insert("exposure", frame=FRAME_END)


# ---------------------------------------------------------------
# 6. 渲染设置
# ---------------------------------------------------------------
scene.render.engine = 'BLENDER_EEVEE'
scene.eevee.taa_render_samples = 40
scene.eevee.use_raytracing = True
try:
    scene.eevee.ray_tracing_method = 'SCREEN'
except Exception:
    pass
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.render.fps = FPS
scene.frame_start = 1
scene.frame_end = FRAME_END
scene.render.use_motion_blur = True
scene.render.motion_blur_shutter = 0.17
scene.render.motion_blur_position = 'CENTER'
scene.render.image_settings.file_format = 'JPEG'
scene.render.image_settings.quality = 95
scene.render.filepath = os.path.join(FRAMES_DIR, "f_")
scene.view_settings.view_transform = 'AgX'
for look in ('High Contrast', 'AgX - High Contrast', 'Medium High Contrast'):
    try:
        scene.view_settings.look = look
        break
    except Exception:
        continue
scene.view_settings.exposure = 0.50
scene.view_settings.gamma = 1.0

# 泛光
try:
    ng = bpy.data.node_groups.new("Comp_V5", 'CompositorNodeTree')
    rl = ng.nodes.new("CompositorNodeRLayers")
    glare = ng.nodes.new("CompositorNodeGlare")
    for val in ("Bloom", "BLOOM", "bloom"):
        try:
            glare.inputs['Type'].default_value = val
            break
        except Exception:
            continue
    for nm, v in (("Threshold", 2.0), ("Strength", 0.16), ("Size", 6)):
        if nm in glare.inputs:
            try:
                glare.inputs[nm].default_value = v
            except Exception:
                pass
    try:
        comp = ng.nodes.new("CompositorNodeComposite")
    except Exception:
        comp = ng.nodes.new("NodeGroupOutput")
        if not any(s.name == "Image" for s in ng.interface.items_tree):
            ng.interface.new_socket(name="Image", in_out='OUTPUT', socket_type='NodeSocketColor')
    ng.links.new(rl.outputs['Image'], glare.inputs['Image'])
    ng.links.new(glare.outputs['Image'], comp.inputs['Image'])
    scene.compositing_node_group = ng
    scene.use_nodes = True
    print("COMPOSITOR OK")
except Exception as e:
    print("COMPOSITOR FAILED:", e)

bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("ANIM SAVED:", OUT)

# ---------------------------------------------------------------
# 7. 测试渲染
# ---------------------------------------------------------------
def render_frames(frames, outdir, res=1280, samples=24):
    os.makedirs(outdir, exist_ok=True)
    scene.render.resolution_x = res
    scene.render.resolution_y = int(res * 9 / 16)
    scene.eevee.taa_render_samples = samples
    for f in frames:
        scene.frame_set(f)
        scene.render.filepath = os.path.join(outdir, f"test_{f:04d}.jpg")
        bpy.ops.render.render(write_still=True)
        print("TEST FRAME", f)


test = argval("--test")
if test:
    render_frames([int(x) for x in str(test).split(",")], os.path.join(PROJ, "renders_v5", "test"),
                  res=1600, samples=24)

if argval("--render"):
    os.makedirs(FRAMES_DIR, exist_ok=True)
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.filepath = os.path.join(FRAMES_DIR, "f_")
    bpy.ops.render.render(animation=True)
    print("RENDER DONE")
