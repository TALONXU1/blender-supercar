# -*- coding: utf-8 -*-
"""
V4 ENV + ANIMATION — 赛道环境 + 赛车运镜动画（多机位剪辑）
输入: pipeline/v4_stage_rig.blend
输出: pipeline/v4_stage_anim.blend
运行:
  blender -b -P v4_anim.py -- --stage all
  blender -b -P v4_anim.py -- --test 1,60,140,200,260
  blender -b -P v4_anim.py -- --render
"""
import bpy, bmesh, math, os, sys, random, subprocess
from mathutils import Vector, Matrix, Euler
from math import sin, cos, pi, radians, sqrt, atan2, degrees

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def argval(flag, default=None):
    if flag in ARGV:
        i = ARGV.index(flag)
        if i + 1 < len(ARGV) and not ARGV[i + 1].startswith("--"):
            return ARGV[i + 1]
        return True
    return default

IN = r"D:\项目session\blender-supercar\pipeline\v4_stage_rig.blend"
OUT = r"D:\项目session\blender-supercar\pipeline\v4_stage_anim.blend"
PROJ = r"D:\项目session\blender-supercar"
FRAMES_DIR = os.path.join(PROJ, "renders_v4", "frames")
STILLS_DIR = os.path.join(PROJ, "renders_v4", "stills")

FPS = 24
FRAME_END = 720
R_TIRE = 0.357

bpy.ops.wm.open_mainfile(filepath=IN)
scene = bpy.context.scene
rig = bpy.data.objects["RIG_F1_Race"]


# ============================================================
# 1. 速度 / 曲率 编排 -> 轨迹积分
# ============================================================
SPEED_KEYS = [  # (frame, km/h) —— 赛道节奏（与音乐段落对齐）
    # 发车直道：0 → 300
    (1, 0), (10, 2), (18, 16), (26, 46), (38, 92), (52, 140), (68, 186),
    (88, 226), (110, 258), (136, 280), (160, 296),
    # 全速直道（音乐最强段）
    (200, 300), (270, 300), (318, 298),
    # 刹车区 → T1 右 90°
    (330, 262), (342, 210), (352, 168), (362, 138), (372, 132),
    # T1 弯中（半径 85m，稳定 132）
    (410, 134), (445, 136),
    # 短直道加速
    (470, 152), (500, 166),
    # T2 左 90°（半径 83m，稳定 162）
    (520, 164), (550, 162), (575, 162),
    # 出弯加速 → 冲线
    (600, 196), (630, 238), (660, 272), (690, 292), (710, 299), (720, 300),
]
KAPPA_KEYS = [  # (frame, 1/m) 正=向右；右 90° 后接左 90°，净转角 ≈ 0 → 赛道不自交
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
        f0, v0 = keys[i]
        f1, v1 = keys[i + 1]
        if f0 <= f <= f1:
            t = (f - f0) / (f1 - f0)
            t = t * t * (3 - 2 * t)  # smoothstep
            return v0 + (v1 - v0) * t
    return keys[-1][1]

# 以 1/600 s 细分积分
SUB = 25                     # 每帧子步
DT = 1.0 / (FPS * SUB)
N = FRAME_END * SUB + 2
pos = Vector((0.0, -30.0, 0.0))
heading = 0.0
dist = 0.0
traj = []                    # (x, y, heading, v, kappa, dist)
for i in range(N):
    f = i / SUB + 1
    v_kmh = interp(SPEED_KEYS, f)
    v = v_kmh / 3.6
    k = interp(KAPPA_KEYS, f)
    traj.append((pos.x, pos.y, heading, v, k, dist))
    # 积分（半隐式）
    heading += k * v * DT
    d = Vector((sin(heading), cos(heading), 0.0))
    pos += d * (v * DT)
    dist += v * DT

def sample_frame(f):
    i = min(N - 1, max(0, int((f - 1) * SUB)))
    return traj[i]

# 每帧姿态数据
frame_data = {}
for f in range(1, FRAME_END + 1):
    x, y, h, v, k, d = sample_frame(f)
    f0 = max(1, f - 1)
    f1 = min(FRAME_END, f + 1)
    v_prev = sample_frame(f0)[3]
    v_next = sample_frame(f1)[3]
    accel = (v_next - v_prev) / ((f1 - f0) / FPS + 1e-6)
    lat = (v * v) * k
    frame_data[f] = dict(x=x, y=y, heading=h, v=v, k=k, dist=d,
                         accel=accel, lat=lat,
                         pos=Vector((x, y, 0.0)),
                         fwd=Vector((sin(h), cos(h), 0.0)),
                         right=Vector((cos(h), -sin(h), 0.0)))

# 漂移编排：弯心区间侧滑角
def drift_slip(f):
    # 真实 F1：滑移角只有几度，入弯 1° 以内，弯心最大 -4.5°，出弯迅速回正
    # 真实 F1：干地光头胎过弯滑移角 1-1.5°，只在弯中轻微存在
    if f < 345 or f > 600:
        return 0.0
    if f < 380:
        return radians(-0.4) * (f - 345) / 35.0
    if f < 450:
        return radians(-1.3) - radians(0.3) * math.sin((f - 380) / 70.0 * math.pi)
    if f < 500:
        return radians(-0.5) * (1 - (f - 450) / 50.0)
    if f < 530:
        return radians(-0.5) - radians(0.7) * (f - 500) / 30.0
    if f < 580:
        return radians(-1.2) - radians(0.3) * math.sin((f - 530) / 50.0 * math.pi)
    return radians(-1.2) * max(0.0, (600 - f) / 20.0)

# ============================================================
# 2. 环境：天空 / 地面 / 赛道 / 护栏 / 灯柱 / 龙门架 / 远景
# ============================================================
def new_mat(name, color, rough=0.5, metal=0.0, emission=None, estrength=0.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if emission:
        b.inputs['Emission Color'].default_value = (*emission, 1)
        b.inputs['Emission Strength'].default_value = estrength
    return m


def mesh_from(name, verts, faces, mat=None, smooth=False, uvs=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate()
    me.update()
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    if mat:
        me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = smooth
    if uvs:
        uv = me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            for li in poly.loop_indices:
                uv.data[li].uv = uvs[me.loops[li].vertex_index]
    return ob


# ---- 天空 ----
world = bpy.data.worlds.get("World_RaceDusk") or bpy.data.worlds.new("World_RaceDusk")
scene.world = world
world.use_nodes = True
nt = world.node_tree
nt.nodes.clear()
sky = nt.nodes.new('ShaderNodeTexSky')
try:
    sky.sky_type = 'MULTIPLE_SCATTERING'
except Exception:
    pass
sky.sun_elevation = radians(4.5)
sky.sun_rotation = radians(215.0)
sky.sun_intensity = 0.9
sky.turbidity = 3.4
bg = nt.nodes.new('ShaderNodeBackground')
bg.inputs['Strength'].default_value = 0.85
nt.links.new(sky.outputs['Color'], bg.inputs['Color'])
wout = nt.nodes.new('ShaderNodeOutputWorld')
nt.links.new(bg.outputs[0], wout.inputs[0])

# ---- 太阳灯 ----
sun_data = bpy.data.lights.new("LGT_RaceSun", 'SUN')
sun_data.energy = 3.1
sun_data.angle = radians(0.8)
sun_data.color = (1.0, 0.82, 0.62)
sun = bpy.data.objects.new("LGT_RaceSun", sun_data)
scene.collection.objects.link(sun)
sun.rotation_euler = Euler((radians(86.0), 0, radians(35.0)))
# 与 sky sun_rotation 对齐：太阳从左后方打来（逆光）

# ---- 地面 ----
ground_mat = new_mat("Mat_RaceGround", (0.030, 0.028, 0.026), 0.86)
gm = ground_mat.node_tree
b = gm.nodes.get("Principled BSDF")
nz = gm.nodes.new('ShaderNodeTexNoise')
nz.inputs['Scale'].default_value = 240.0
nz.inputs['Detail'].default_value = 10.0
nz.inputs['Roughness'].default_value = 0.7
ct = gm.nodes.new('ShaderNodeTexCoord')
gm.links.new(ct.outputs['Object'], nz.inputs['Vector'])
cmix = gm.nodes.new('ShaderNodeMixRGB')
cmix.blend_type = 'MULTIPLY'
cmix.inputs['Fac'].default_value = 0.5
cmix.inputs['Color1'].default_value = (0.030, 0.028, 0.026, 1)
cmix.inputs['Color2'].default_value = (0.075, 0.070, 0.062, 1)
gm.links.new(nz.outputs['Fac'], cmix.inputs['Fac'])
gm.links.new(cmix.outputs['Color'], b.inputs['Base Color'])
bump = gm.nodes.new('ShaderNodeBump')
bump.inputs['Strength'].default_value = 0.35
gm.links.new(nz.outputs['Fac'], bump.inputs['Height'])
gm.links.new(bump.outputs['Normal'], b.inputs['Normal'])

verts = [(-1400, -400, 0), (1400, -400, 0), (1400, 2600, 0), (-1400, 2600, 0)]
mesh_from("GEO_Race_Ground", verts, [(0, 1, 2, 3)], ground_mat)

# ---- 赛道带（沿轨迹）----
asphalt = new_mat("Mat_RaceAsphalt", (0.017, 0.017, 0.019), 0.62)
traj_pts = []
STEP_M = 1.2
last = None
acc = 0.0
for i in range(N):
    x, y, h, v, k, d = traj[i]
    if last is None or d - last >= STEP_M:
        traj_pts.append((x, y, h, d))
        last = d
    if d > 2400:
        break

HALF_W = 6.4
tv, tf, tuv = [], [], []
for idx, (x, y, h, d) in enumerate(traj_pts):
    rx, ry = cos(h), -sin(h)
    tv.append((x - rx * HALF_W, y - ry * HALF_W, 0.012))
    tv.append((x + rx * HALF_W, y + ry * HALF_W, 0.012))
    tuv.append((0.0, d / 8.0))
    tuv.append((1.0, d / 8.0))
for i in range(len(traj_pts) - 1):
    a = i * 2
    tf.append((a, a + 1, a + 3, a + 2))
track = mesh_from("GEO_Race_Track", tv, tf, asphalt, uvs=tuv)
track["v4_track"] = True

# 赛道材质：沥青颗粒 + 车辙
am = asphalt.node_tree
ab = am.nodes.get("Principled BSDF")
an = am.nodes.new('ShaderNodeTexNoise')
an.inputs['Scale'].default_value = 420.0
an.inputs['Detail'].default_value = 12.0
an.inputs['Roughness'].default_value = 0.8
atc = am.nodes.new('ShaderNodeTexCoord')
am.links.new(atc.outputs['Object'], an.inputs['Vector'])
abump = am.nodes.new('ShaderNodeBump')
abump.inputs['Strength'].default_value = 0.28
am.links.new(an.outputs['Fac'], abump.inputs['Height'])
am.links.new(abump.outputs['Normal'], ab.inputs['Normal'])

# ---- 边线 ----
line_mat = new_mat("Mat_RaceLine", (0.82, 0.82, 0.80), 0.42)
def ribbon(offset, width, mat, z=0.02, name="GEO_Race_Line", skip=1):
    v, f = [], []
    pts = traj_pts[::skip]
    for (x, y, h, d) in pts:
        rx, ry = cos(h), -sin(h)
        v.append((x + rx * (offset - width / 2), y + ry * (offset - width / 2), z))
        v.append((x + rx * (offset + width / 2), y + ry * (offset + width / 2), z))
    for i in range(len(pts) - 1):
        a = i * 2
        f.append((a, a + 1, a + 3, a + 2))
    return mesh_from(name, v, f, mat)

ribbon(-HALF_W + 0.35, 0.16, line_mat, 0.021, "GEO_Race_Line_L", skip=2)
ribbon(HALF_W - 0.35, 0.16, line_mat, 0.021, "GEO_Race_Line_R", skip=2)
ribbon(-HALF_W + 1.55, 0.10, line_mat, 0.020, "GEO_Race_Line_L2", skip=2)
ribbon(HALF_W - 1.55, 0.10, line_mat, 0.020, "GEO_Race_Line_R2", skip=2)

# ---- 护栏（单网格）----
wall_mat = new_mat("Mat_RaceWall", (0.62, 0.60, 0.58), 0.55)
wall_dark = new_mat("Mat_RaceWallDark", (0.10, 0.11, 0.13), 0.5)
wv, wf = [], []
seg = traj_pts[::6]
for side in (-1, 1):
    base = len(wv)
    for (x, y, h, d) in seg:
        rx, ry = cos(h), -sin(h)
        off = side * (HALF_W + 3.4)
        px, py = x + rx * off, y + ry * off
        wv.append((px, py, 0.0))
        wv.append((px, py, 1.05))
    for i in range(len(seg) - 1):
        a = base + i * 2
        wf.append((a, a + 1, a + 3, a + 2))
    for i in range(len(seg) - 1):
        a = base + i * 2
        wf.append((a + 2, a + 3, a + 1, a))
walls = mesh_from("GEO_Race_Walls", wv, wf, wall_dark)
# 护栏顶灯带
strip_mat = new_mat("Mat_RaceWallStrip", (0.02, 0.05, 0.06), 0.4, emission=(0.05, 0.85, 1.0), estrength=6.0)
sv, sf = [], []
for side in (-1, 1):
    base = len(sv)
    for (x, y, h, d) in seg:
        rx, ry = cos(h), -sin(h)
        off = side * (HALF_W + 3.38)
        px, py = x + rx * off, y + ry * off
        sv.append((px, py, 1.05))
        sv.append((px, py, 1.12))
    for i in range(len(seg) - 1):
        a = base + i * 2
        sf.append((a, a + 1, a + 3, a + 2))
mesh_from("GEO_Race_WallStrip", sv, sf, strip_mat)

# ---- 灯柱 ----
pole_mat = new_mat("Mat_Pole", (0.06, 0.065, 0.07), 0.35, 0.7)
lamp_mat = new_mat("Mat_LampHead", (0.9, 0.95, 1.0), 0.3, emission=(0.85, 0.95, 1.0), estrength=18.0)
pole_objs = []
idx = 0
for i in range(0, len(traj_pts) - 1, int(46 / STEP_M)):
    x, y, h, d = traj_pts[i]
    rx, ry = cos(h), -sin(h)
    for side in (-1, 1):
        px = x + rx * side * (HALF_W + 6.0)
        py = y + ry * side * (HALF_W + 6.0)
        me = bpy.data.meshes.new(f"GEO_Race_Pole_{idx}")
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.10, radius2=0.07, depth=9.0)
        bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, 4.5))
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(f"GEO_Race_Pole_{idx}", me)
        scene.collection.objects.link(ob)
        ob.location = (px, py, 0)
        me.materials.append(pole_mat)
        head = bpy.data.meshes.new(f"GEO_Race_LampHead_{idx}")
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(1.6, 0.25, 0.16), verts=bm.verts)
        bm.to_mesh(head)
        bm.free()
        ho = bpy.data.objects.new(f"GEO_Race_LampHead_{idx}", head)
        scene.collection.objects.link(ho)
        ho.location = (px - rx * side * 1.5, py - ry * side * 1.5, 8.8)
        ho.rotation_euler = (radians(12), 0, h)
        head.materials.append(lamp_mat)
        idx += 1

# ---- 起跑龙门架 ----
gantry = traj_pts[6]
gx, gy, gh, gd = gantry
rx, ry = cos(gh), -sin(gh)
post_mat = new_mat("Mat_Gantry", (0.05, 0.06, 0.07), 0.4, 0.8)
for s in (-1, 1):
    px = gx + rx * s * (HALF_W + 1.2)
    py = gy + ry * s * (HALF_W + 1.2)
    me = bpy.data.meshes.new(f"GEO_Gantry_Post_{s}")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(0.35, 0.35, 7.0), verts=bm.verts)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, 3.5))
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(f"GEO_Gantry_Post_{s}", me)
    scene.collection.objects.link(ob)
    ob.location = (px, py, 0)
    me.materials.append(post_mat)
# 横梁 + 灯箱
beam_v = []
for s in (-1, 1):
    for z in (6.2, 7.1):
        beam_v.append((gx + rx * s * (HALF_W + 1.2), gy + ry * s * (HALF_W + 1.2), z))
# 简化：用立方体
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1.0)
bmesh.ops.scale(bm, vec=((HALF_W + 1.2) * 2, 0.4, 0.9), verts=bm.verts)
bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, 6.65))
me = bpy.data.meshes.new("GEO_Gantry_Beam")
bm.to_mesh(me)
bm.free()
gob = bpy.data.objects.new("GEO_Gantry_Beam", me)
scene.collection.objects.link(gob)
gob.location = (gx, gy, 0)
gob.rotation_euler = (0, 0, gh)
me.materials.append(post_mat)

banner_mat = new_mat("Mat_GantryBanner", (0.02, 0.05, 0.12), 0.5, emission=(0.1, 0.8, 1.0), estrength=2.5)
bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=1.0)
bmesh.ops.scale(bm, vec=(HALF_W + 1.0, 0.55, 1.0), verts=bm.verts)
bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(radians(90), 3, 'X'))
me = bpy.data.meshes.new("GEO_Gantry_Banner")
bm.to_mesh(me)
bm.free()
ban = bpy.data.objects.new("GEO_Gantry_Banner", me)
scene.collection.objects.link(ban)
ban.location = (gx, gy, 6.65)
ban.rotation_euler = (0, 0, gh)
me.materials.append(banner_mat)

# ---- 发车灯组（5 盏，起步时熄灭）----
start_light_mat = new_mat("Mat_StartLight", (0.05, 0.002, 0.002), 0.35,
                          emission=(1.0, 0.06, 0.02), estrength=14.0)
start_lights = []
for i in range(5):
    lx = -1.6 + i * 0.8
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=0.16)
    me = bpy.data.meshes.new(f"GEO_StartLight_{i}")
    bm.to_mesh(me)
    bm.free()
    lo = bpy.data.objects.new(f"GEO_StartLight_{i}", me)
    scene.collection.objects.link(lo)
    me.materials.append(start_light_mat)
    lo.location = (gx + rx * lx, gy + ry * lx, 6.05)
    start_lights.append(lo)

# ---- 弯道路肩（红白相间）----
curb_red = new_mat("Mat_Curb_Red", (0.62, 0.035, 0.030), 0.62)
curb_white = new_mat("Mat_Curb_White", (0.78, 0.78, 0.76), 0.62)
CURB_W = 0.95
CURB_H = 0.055
seg_frames = list(range(352, 606, 3))
for mat, phase, nm in ((curb_red, 0, "Red"), (curb_white, 1, "White")):
    cv, cf = [], []
    for idx, f in enumerate(seg_frames):
        if idx % 2 != phase:
            continue
        for side in (-1, 1):
            fd_a = frame_data[f]
            fd_b = frame_data[min(FRAME_END, f + 3)]
            base = len(cv)
            for fd_p in (fd_a, fd_b):
                rx_, ry_ = fd_p['right'].x, fd_p['right'].y
                off = side * (HALF_W + CURB_W / 2)
                cv.append((fd_p['pos'].x + rx_ * off, fd_p['pos'].y + ry_ * off, 0.010))
                cv.append((fd_p['pos'].x + rx_ * off, fd_p['pos'].y + ry_ * off, 0.010 + CURB_H))
            cf.append((base, base + 1, base + 3, base + 2))
    if cf:
        mesh_from(f"GEO_Curb_{nm}", cv, cf, mat)

# ---- 远景塔楼 ----
tower_mat = new_mat("Mat_Tower", (0.020, 0.022, 0.030), 0.75)
win_mat = new_mat("Mat_TowerWin", (0.9, 0.7, 0.4), 0.4, emission=(1.0, 0.72, 0.35), estrength=2.2)
random.seed(11)
for i in range(14):
    k = int((i / 14.0) * (len(traj_pts) - 1))
    tx, ty, th, td = traj_pts[k]
    side_dir = 1 if i % 2 == 0 else -1
    rad = random.uniform(520, 980)
    bx = tx + cos(th) * side_dir * rad + random.uniform(-60, 60)
    by = ty - sin(th) * side_dir * rad + random.uniform(-60, 60)
    w = random.uniform(14, 44)
    dpt = random.uniform(14, 44)
    hgt = random.uniform(24, 72)
    me = bpy.data.meshes.new(f"GEO_Tower_{i}")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(w, dpt, hgt), verts=bm.verts)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, hgt / 2))
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(f"GEO_Tower_{i}", me)
    scene.collection.objects.link(ob)
    ob.location = (bx, by, 0)
    me.materials.append(tower_mat)
    # 竖向灯条
    wm = bpy.data.meshes.new(f"GEO_TowerWin_{i}")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(w * 0.06, dpt * 1.02, hgt * 0.7), verts=bm.verts)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(w * 0.22, 0, hgt * 0.5))
    bm.to_mesh(wm)
    bm.free()
    wo = bpy.data.objects.new(f"GEO_TowerWin_{i}", wm)
    scene.collection.objects.link(wo)
    wo.location = (bx, by, 0)
    wm.materials.append(win_mat)


# ---- 车底接触阴影（伪 AO，增强贴地感）----
sh_mat = bpy.data.materials.new("Mat_CarContactShadow")
sh_mat.use_nodes = True
sh_nt = sh_mat.node_tree
sh_nt.nodes.clear()
sh_out = sh_nt.nodes.new('ShaderNodeOutputMaterial')
sh_bsdf = sh_nt.nodes.new('ShaderNodeBsdfPrincipled')
sh_bsdf.inputs['Base Color'].default_value = (0.0, 0.0, 0.0, 1)
sh_bsdf.inputs['Roughness'].default_value = 1.0
sh_grad = sh_nt.nodes.new('ShaderNodeTexGradient')
sh_grad.gradient_type = 'SPHERICAL'
sh_map = sh_nt.nodes.new('ShaderNodeMapping')
sh_tex = sh_nt.nodes.new('ShaderNodeTexCoord')
sh_ramp = sh_nt.nodes.new('ShaderNodeValToRGB')
sh_ramp.color_ramp.elements[0].position = 0.0
sh_ramp.color_ramp.elements[0].color = (1, 1, 1, 1)
sh_ramp.color_ramp.elements[1].position = 0.62
sh_ramp.color_ramp.elements[1].color = (0, 0, 0, 1)
sh_nt.links.new(sh_tex.outputs['Object'], sh_map.inputs['Vector'])
sh_map.inputs['Scale'].default_value = (0.62, 1.25, 1.0)
sh_nt.links.new(sh_map.outputs['Vector'], sh_grad.inputs['Vector'])
sh_nt.links.new(sh_grad.outputs['Fac'], sh_ramp.inputs['Fac'])
sh_nt.links.new(sh_ramp.outputs['Color'], sh_bsdf.inputs['Alpha'])
sh_nt.links.new(sh_bsdf.outputs['BSDF'], sh_out.inputs['Surface'])
sh_mat.surface_render_method = 'BLENDED'
sh_mat.use_transparent_shadow = False

fill_lights = []
for i, sgn in ((0, -1.0), (1, 1.0)):
    fd_light = bpy.data.lights.new(f"LGT_CarFill_{i}", 'AREA')
    fd_light.energy = 420.0
    fd_light.size = 6.0
    fd_light.color = (0.62, 0.76, 1.0) if i == 0 else (1.0, 0.92, 0.82)
    fo = bpy.data.objects.new(f"LGT_CarFill_{i}", fd_light)
    scene.collection.objects.link(fo)
    fill_lights.append((fo, sgn))

sh_verts = [(-1.45, -3.0, 0), (1.45, -3.0, 0), (1.45, 3.0, 0), (-1.45, 3.0, 0)]
sh_ob = mesh_from("GEO_Car_ContactShadow", sh_verts, [(0, 1, 2, 3)], sh_mat)
sh_ob.location = (0, 0, 0.021)

# ---- 轮胎烟（漂移段，随车尾生成、膨胀、消散）----
smoke_mat = bpy.data.materials.new("Mat_TireSmoke")
smoke_mat.use_nodes = True
sm_nt = smoke_mat.node_tree
sm_nt.nodes.clear()
sm_out = sm_nt.nodes.new('ShaderNodeOutputMaterial')
sm_bsdf = sm_nt.nodes.new('ShaderNodeBsdfPrincipled')
sm_bsdf.inputs['Base Color'].default_value = (0.62, 0.62, 0.64, 1)
sm_bsdf.inputs['Roughness'].default_value = 1.0
sm_bsdf.inputs['Metallic'].default_value = 0.0
sm_info = sm_nt.nodes.new('ShaderNodeObjectInfo')
sm_lw = sm_nt.nodes.new('ShaderNodeLayerWeight')
sm_lw.inputs['Blend'].default_value = 0.45
sm_ramp = sm_nt.nodes.new('ShaderNodeValToRGB')
sm_ramp.color_ramp.elements[0].position = 0.15
sm_ramp.color_ramp.elements[0].color = (1, 1, 1, 1)
sm_ramp.color_ramp.elements[1].position = 0.95
sm_ramp.color_ramp.elements[1].color = (0, 0, 0, 1)
sm_mul = sm_nt.nodes.new('ShaderNodeMath')
sm_mul.operation = 'MULTIPLY'
sm_nt.links.new(sm_lw.outputs['Facing'], sm_ramp.inputs['Fac'])
sm_nt.links.new(sm_ramp.outputs['Color'], sm_mul.inputs[0])
sm_nt.links.new(sm_info.outputs['Alpha'], sm_mul.inputs[1])
sm_nt.links.new(sm_mul.outputs['Value'], sm_bsdf.inputs['Alpha'])
sm_nt.links.new(sm_bsdf.outputs['BSDF'], sm_out.inputs['Surface'])
smoke_mat.surface_render_method = 'DITHERED'
smoke_mat.use_transparent_shadow = False

smoke_puffs = []
for k, fs in enumerate([]):
    break
    fd_s = frame_data[fs]
    side = -1 if k % 2 == 0 else 1
    ang_s = fd_s['heading'] + drift_slip(fs)
    rx_, ry_ = math.cos(ang_s), -math.sin(ang_s)
    wx = fd_s['pos'].x - fd_s['fwd'].x * 1.55 + rx_ * side * 0.86
    wy = fd_s['pos'].y - fd_s['fwd'].y * 1.55 + ry_ * side * 0.86
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=14, v_segments=9, radius=1.0)
    me = bpy.data.meshes.new(f"GEO_Smoke_{k}")
    bm.to_mesh(me)
    bm.free()
    so = bpy.data.objects.new(f"GEO_Smoke_{k}", me)
    scene.collection.objects.link(so)
    me.materials.append(smoke_mat)
    smoke_puffs.append((so, fs, wx, wy))

# ============================================================
# 3. 车辆动画（数据驱动）
# ============================================================
bpy.context.view_layer.objects.active = rig
bone_root = rig.pose.bones["Bone_Root"]
bone_heading = rig.pose.bones["Bone_Heading"]
bone_body = rig.pose.bones["Bone_Body"]

cum_spin = 0.0
prev_dist = 0.0
prev_gear = 1
shift_flash = 0.0

brake_light_em = None
_rl = bpy.data.objects.get("GEO_F1_FIA_RainLight")
if _rl and _rl.data.materials:
    _m = _rl.data.materials[0]
    if _m and _m.node_tree:
        for _n in _m.node_tree.nodes:
            if _n.type == 'EMISSION':
                brake_light_em = _n
                break
            if _n.type == 'BSDF_PRINCIPLED' and 'Emission Strength' in _n.inputs:
                brake_light_em = _n
                _emis_key = 'Emission Strength'
                break

for f in range(1, FRAME_END + 1):
    fd = frame_data[f]
    slip = drift_slip(f)
    v = fd['v']
    lat = fd['lat']
    acc = fd['accel']

    scene.frame_set(f)

    # 位置 / 偏航
    bone_root.location = (fd['pos'].x, fd['pos'].y, 0.0)
    bone_heading.rotation_euler = (0.0, 0.0, fd['heading'] + slip)
    bone_root.keyframe_insert("location", frame=f)
    bone_heading.keyframe_insert("rotation_euler", frame=f)

    # ---- 现实赛车逻辑：档位 / 换挡冲击 / 载荷转移 ----
    v_kmh = v * 3.6
    gear = min(8, max(1, int((v_kmh - 45) / 42) + 1))
    if gear != prev_gear:
        shift_flash = 1.0
        prev_gear = gear
    else:
        shift_flash *= 0.70
    launch = 1.0 if f < 30 else 0.0

    # 车身姿态：俯仰 + 侧倾 + 升沉 + 路面颠簸
    pitch = max(-1.6, min(1.2, acc * 0.055)) + 0.55 * launch - 0.18 * shift_flash
    roll = max(-2.0, min(2.0, -lat * 0.20 - (0.4 if abs(slip) > 0.03 else 0.0)))
    heave = -0.008 + 0.004 * sin(f * 1.7) + 0.002 * sin(f * 3.1) - 0.004 * shift_flash
    bone_body.location = (0.0, 0.0, heave)
    bone_body.rotation_euler = (radians(pitch), radians(roll), 0.0)
    bone_body.keyframe_insert("location", frame=f)
    bone_body.keyframe_insert("rotation_euler", frame=f)

    # 机械属性 -> 驱动器
    spin_delta = (fd['dist'] - prev_dist) / R_TIRE
    prev_dist = fd['dist']
    cum_spin += spin_delta
    rig["wheel_spin"] = cum_spin
    rig["steer"] = max(-5.0, min(5.0, degrees(-slip) * 0.9)) if abs(slip) > 0.005 else max(-4.5, min(4.5, -lat * 0.34))
    rig["drs"] = 1.0 if (v > 72 and abs(lat) < 1.5) else (0.0 if abs(lat) > 1.5 else 0.6)
    rig["brake_heat"] = min(1.4, max(0.0, -acc * 0.10))
    if f < 26:
        rig["rear_slip"] = 1.55                     # 起步瞬间后轮空转
    elif 596 < f < 656:
        rig["rear_slip"] = 1.03                     # 出弯动力滑移（轻微）
    else:
        rig["rear_slip"] = 1.0
    rig["susp_f"] = -0.006 - 0.010 * max(0.0, -acc) / 10.0 + 0.002 * sin(f * 2.3)
    rig["susp_r"] = -0.006 - 0.012 * max(0.0, acc) / 10.0 + 0.002 * sin(f * 1.9 + 1.0)
    for k in ("wheel_spin", "steer", "drs", "brake_heat", "rear_slip", "susp_f", "susp_r"):
        rig.keyframe_insert(f'["{k}"]', frame=f)

    # 尾部刹车/雨灯随刹车力度亮起
    if brake_light_em:
        brake_light_em.inputs['Strength'].default_value = 1.2 + rig["brake_heat"] * 11.0
        brake_light_em.inputs['Strength'].keyframe_insert("default_value", frame=f)

    sh_ob.location = (fd['pos'].x, fd['pos'].y, 0.021)
    sh_ob.rotation_euler = (0.0, 0.0, fd['heading'] + slip)
    sh_ob.keyframe_insert("location", frame=f)
    sh_ob.keyframe_insert("rotation_euler", frame=f)

    # 随车柔光：前侧上方 45°，永远给车身一层可读的亮面
    for fo, sgn in fill_lights:
        lp = fd['pos'] + fd['fwd'] * 4.5 + fd['right'] * (sgn * 5.5) + Vector((0, 0, 3.6))
        fo.location = lp
        aim_v = (fd['pos'] + Vector((0, 0, 0.45))) - lp
        fo.rotation_euler = aim_v.to_track_quat('-Z', 'Y').to_euler()
        fo.keyframe_insert("location", frame=f)
        fo.keyframe_insert("rotation_euler", frame=f)

    # 悬挂/轮胎接地补偿：漂移时后轮外抛

print("CAR ANIMATION KEYED")

# ============================================================
# 4. 轮胎拖痕（漂移烟雾与胎痕）
# ============================================================
skid_mat = new_mat("Mat_SkidMark", (0.008, 0.008, 0.009), 0.75)
skid_mat.use_nodes = True
sk_mat = skid_mat.node_tree
skb = sk_mat.nodes.get("Principled BSDF")
skb.inputs['Alpha'].default_value = 0.85
skid_mat.surface_render_method = 'BLENDED'

for side in (-1, 1):
    v, fc = [], []
    prev = None
    for f in range(0, 0):
        fd = frame_data[f]
        slip = drift_slip(f)
        if -acc < 6.0 and abs(slip) < 0.02:
            prev = None
            continue
        rx, ry = cos(fd['heading']), -sin(fd['heading'])
        cx = fd['pos'].x - fd['fwd'].x * 1.55 + rx * side * 0.86
        cy = fd['pos'].y - fd['fwd'].y * 1.55 + ry * side * 0.86
        halfw = 0.16
        v.append((cx - rx * halfw, cy - ry * halfw, 0.019))
        v.append((cx + rx * halfw, cy + ry * halfw, 0.019))
        if prev is not None:
            a = len(v) - 4
            fc.append((a, a + 1, a + 3, a + 2))
        prev = f
    if fc:
        ob = mesh_from(f"GEO_Skid_{side}", v, fc, skid_mat)
        ob["v4_skid"] = True
print("SKID MARKS BUILT")

# ============================================================
# 4b. 轮胎烟 / 发车灯 关键帧
# ============================================================
for so, fs, wx, wy in smoke_puffs:
    for ff, sc, al, dz in ((fs - 1, 0.02, 0.0, 0.0), (fs, 0.40, 0.72, 0.06),
                           (fs + 9, 1.20, 0.42, 0.50), (fs + 34, 2.55, 0.0, 1.20)):
        if ff < 1 or ff > FRAME_END:
            continue
        so.location = (wx, wy, 0.24 + dz)
        so.scale = (sc, sc, sc * 0.82)
        so.color = (1.0, 1.0, 1.0, al)
        so.keyframe_insert("location", frame=ff)
        so.keyframe_insert("scale", frame=ff)
        so.keyframe_insert("color", frame=ff)

# 发车灯：前 9 帧全亮，起步瞬间熄灭
_sl_em = next((n for n in start_light_mat.node_tree.nodes if n.type == 'EMISSION'), None)
if _sl_em:
    for ff, val in ((1, 16.0), (8, 16.0), (9, 0.0), (FRAME_END, 0.0)):
        _sl_em.inputs['Strength'].default_value = val
        _sl_em.inputs['Strength'].keyframe_insert("default_value", frame=ff)
print("SMOKE + START LIGHTS KEYED")

# ============================================================
# 5. 摄影机运镜
# ============================================================
def make_cam(name, lens=50, fstop=4.0):
    cd = bpy.data.cameras.new(name + "_DATA")
    cd.lens = lens
    cd.clip_start = 0.05
    cd.clip_end = 2500
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
    return (math.sin(t * 2.3 + seed) * 0.55 + math.sin(t * 5.7 + seed * 2.3) * 0.3
            + math.sin(t * 11.3 + seed * 4.1) * 0.15) * amp


# 切点全部落在 BPM108 拍点上：帧号 = 1 + j * 13.334
SHOTS = [
    ("Cam_S1_LaunchRear", 1, 53),      # 拍 0
    ("Cam_S2_SideLow", 54, 120),       # 拍 4
    ("Cam_S3_WheelMacro", 121, 160),   # 拍 9
    ("Cam_S4_Onboard", 161, 240),      # 拍 12
    ("Cam_S5_Tele", 241, 320),         # 拍 18
    ("Cam_S6_ChaseRise", 321, 427),    # 拍 24（重刹入弯）
    ("Cam_S7_Orbit", 428, 533),        # 拍 32
    ("Cam_S8_SideTrack", 534, 600),    # 拍 40
    ("Cam_S9_Frontal", 601, 667),      # 拍 45
    ("Cam_S10_Aerial", 668, 720),      # 拍 50
]

cams = {}
for name, f0, f1 in SHOTS:
    cams[name] = make_cam(name, 50, 4.0)


def smooth(t):
    return t * t * (3 - 2 * t)


def key_cam(cam, f, loc, tgt, roll=0.0, fstop=4.0, lens=50, lens_key=True):
    cam_look(cam, loc, tgt, roll_deg=roll, fstop=fstop, lens=lens)
    cam.keyframe_insert("location", frame=f)
    cam.keyframe_insert("rotation_euler", frame=f)
    cam.data.dof.keyframe_insert("focus_distance", frame=f)
    cam.data.dof.keyframe_insert("aperture_fstop", frame=f)
    if lens_key:
        cam.data.keyframe_insert("lens", frame=f)


# ---- S1（1-53）发车尾追：灯灭起步，后轮空转把镜头甩开 ----
cam = cams["Cam_S1_LaunchRear"]
for f in range(1, 54):
    t = (f - 1) / 52.0
    e = smooth(t)
    fd = frame_data[f]
    back = 4.2 + 7.0 * e
    side = 0.9 - 0.5 * e
    loc = fd['pos'] - fd['fwd'] * back + fd['right'] * side + Vector((0, 0, 0.38 + 0.50 * e))
    loc += Vector((noise(f * 0.07, 1.0, 0.03), noise(f * 0.06, 2.0, 0.03), noise(f * 0.09, 3.0, 0.02)))
    tgt = fd['pos'] + fd['fwd'] * (1.5 - 0.7 * e) + Vector((0, 0, 0.50 + 0.10 * e))
    key_cam(cam, f, loc, tgt, roll=noise(f * 0.04, 4.0, 1.2), fstop=2.8, lens=42 - 12 * e)

# ---- S2（54-120）低机位侧掠 + 甩镜 ----
cam = cams["Cam_S2_SideLow"]
fd0 = frame_data[96]
loc2 = fd0['pos'] + fd0['right'] * 7.4 + Vector((0, 0, 0.50))
aim2 = None
for f in range(54, 121):
    fd = frame_data[f]
    tgt = fd['pos'] + Vector((0, 0, 0.16))
    aim2 = tgt if aim2 is None else aim2.lerp(tgt, 0.8)
    key_cam(cam, f, loc2, aim2, roll=-2.0, fstop=4.5, lens=45, lens_key=False)

# ---- S3（121-160）前轮特写插切（跟拍轮组、刹车盘、悬挂）----
cam = cams["Cam_S3_WheelMacro"]
for f in range(121, 161):
    t = (f - 121) / 39.0
    e = smooth(t)
    fd = frame_data[f]
    side = 3.3 - 0.4 * e
    back = -0.9 + 0.7 * e
    height = 0.52 + 0.12 * e
    loc = fd['pos'] + fd['right'] * side - fd['fwd'] * back + Vector((0, 0, height))
    loc += Vector((noise(f * 0.16, 81.0, 0.012), noise(f * 0.16, 82.0, 0.012), noise(f * 0.2, 83.0, 0.008)))
    tgt = fd['pos'] + fd['right'] * 0.75 + fd['fwd'] * (1.45 - 0.35 * e) + Vector((0, 0, 0.36))
    key_cam(cam, f, loc, tgt, roll=1.5 - 3.0 * e, fstop=3.5, lens=46 - 6 * e)

# ---- S4（161-240）鼻锥机位：全速直道 ----
cam = cams["Cam_S4_Onboard"]
for f in range(161, 241):
    t = (f - 161) / 79.0
    fd = frame_data[f]
    vib = 0.006 + 0.004 * (fd['v'] / 80.0)
    loc = fd['pos'] + fd['fwd'] * 2.35 + Vector((0, 0, 0.46))
    loc += Vector((noise(f * 0.9, 31.0, vib), noise(f * 0.9, 32.0, vib), noise(f * 1.1, 33.0, vib * 0.6)))
    tgt = loc + fd['fwd'] * 18.0 + Vector((0, 0, -0.24 - 0.05 * t))
    key_cam(cam, f, loc, tgt, roll=noise(f * 0.3, 34.0, 1.0), fstop=5.6, lens=16, lens_key=False)

# ---- S5（241-320）长焦压缩：300km/h 逼近刹车点 ----
cam = cams["Cam_S5_Tele"]
fd4 = frame_data[300]
loc4 = fd4['pos'] + fd4['right'] * 26.0 + fd4['fwd'] * 22.0 + Vector((0, 0, 6.5))
aim4 = None
for f in range(241, 321):
    fd = frame_data[f]
    tgt = fd['pos'] + Vector((0, 0, 0.45))
    aim4 = tgt if aim4 is None else aim4.lerp(tgt, 0.78)
    key_cam(cam, f, loc4, aim4, roll=0.0, fstop=8.0, lens=135, lens_key=False)

# ---- S6（321-427）摇臂追车升起：重刹入弯（拍 24 起）----
cam = cams["Cam_S6_ChaseRise"]
for f in range(321, 428):
    t = (f - 321) / 106.0
    e = smooth(t)
    fd = frame_data[f]
    back = 8.0 - 1.6 * e
    side = -0.6 + 2.6 * e
    height = 1.25 + 2.20 * e
    loc = fd['pos'] - fd['fwd'] * back + fd['right'] * side + Vector((0, 0, height))
    loc += Vector((noise(f * 0.05, 41.0, 0.035), noise(f * 0.05, 42.0, 0.035), noise(f * 0.08, 43.0, 0.025)))
    tgt = fd['pos'] + fd['fwd'] * (4.4 - 1.6 * e) + Vector((0, 0, 0.55))
    key_cam(cam, f, loc, tgt, roll=-2.0 + 5.0 * e + noise(f * 0.05, 44.0, 0.7),
            fstop=3.2, lens=30, lens_key=False)

# ---- S7（428-533）弯心弧形跟拍（165km/h 跟随）----
cam = cams["Cam_S7_Orbit"]
for f in range(428, 534):
    t = (f - 428) / 105.0
    e = smooth(t)
    fd = frame_data[f]
    ang = radians(104 - 50 * e)
    radius = 9.4 - 1.2 * e
    ox = fd['fwd'].x * cos(ang) - fd['right'].x * sin(ang)
    oy = fd['fwd'].y * cos(ang) - fd['right'].y * sin(ang)
    loc = fd['pos'] + Vector((ox, oy, 0)) * radius + Vector((0, 0, 1.35 - 0.25 * e))
    loc += Vector((noise(f * 0.06, 51.0, 0.05), noise(f * 0.06, 52.0, 0.05), noise(f * 0.08, 53.0, 0.02)))
    tgt = fd['pos'] + Vector((0, 0, 0.42))
    key_cam(cam, f, loc, tgt, roll=-5 + 9 * e, fstop=3.2, lens=42, lens_key=False)

# ---- S8（534-600）出弯侧跟：动力滑移、车拉开 ----
cam = cams["Cam_S8_SideTrack"]
for f in range(534, 601):
    t = (f - 534) / 66.0
    e = smooth(t)
    fd = frame_data[f]
    side = 8.6 + 2.2 * e
    back = 2.6 + 6.5 * e
    height = 0.85 + 0.60 * e
    loc = fd['pos'] + fd['right'] * side - fd['fwd'] * back + Vector((0, 0, height))
    loc += Vector((noise(f * 0.05, 61.0, 0.03), noise(f * 0.05, 62.0, 0.03), noise(f * 0.07, 63.0, 0.02)))
    tgt = fd['pos'] + fd['fwd'] * (1.2 - 0.8 * e) + Vector((0, 0, 0.40))
    key_cam(cam, f, loc, tgt, roll=2.0 - 4.0 * e, fstop=3.2, lens=38, lens_key=False)

# ---- S9（601-667）正面低机位冲线：变焦 + 掠过 ----
cam = cams["Cam_S9_Frontal"]
fd8 = frame_data[650]
loc8 = fd8['pos'] + fd8['right'] * 7.5 + Vector((0, 0, 0.42))
aim8 = None
for f in range(601, 668):
    t = (f - 601) / 66.0
    fd = frame_data[f]
    tgt = fd['pos'] + Vector((0, 0, 0.30))
    if (fd['pos'] - loc8).dot(fd['fwd']) < 0 and aim8 is not None:
        tgt = aim8
    else:
        aim8 = tgt
    key_cam(cam, f, loc8, tgt, roll=2.0 - 4.0 * t, fstop=2.8 + 2.0 * t,
            lens=130 - 70 * smooth(min(1.0, t * 2.2)))

# ---- S10（668-720）航拍拉升收尾 + 淡出 ----
cam = cams["Cam_S10_Aerial"]
for f in range(668, 721):
    t = (f - 668) / 52.0
    e = smooth(t)
    fd = frame_data[f]
    back = 9.0 + 8.0 * e
    side = 2.5 + 6.5 * e
    height = 2.8 + 7.5 * e
    loc = fd['pos'] - fd['fwd'] * back + fd['right'] * side + Vector((0, 0, height))
    loc += Vector((noise(f * 0.04, 71.0, 0.03 * (1 - e)), noise(f * 0.04, 72.0, 0.03 * (1 - e)),
                   noise(f * 0.05, 73.0, 0.02 * (1 - e))))
    tgt = fd['pos'] + fd['fwd'] * 0.6 + Vector((0, 0, 0.55))
    key_cam(cam, f, loc, tgt, roll=-1.0 + 2.0 * e, fstop=4.0, lens=56 - 8 * e)

print("CAMERAS KEYED")

# ---- 机位切换标记 ----
scene.timeline_markers.clear()
for name, f0, f1 in SHOTS:
    mk = scene.timeline_markers.new(name, frame=f0)
    mk.camera = cams[name]
scene.camera = cams["Cam_S1_LaunchRear"]

# ============================================================
# 6. 渲染设置
# ============================================================
scene.render.engine = 'BLENDER_EEVEE'
scene.eevee.taa_render_samples = 32
scene.eevee.use_raytracing = True
scene.eevee.ray_tracing_method = 'SCREEN'
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.render.fps = FPS
scene.frame_start = 1
scene.frame_end = FRAME_END
scene.render.use_motion_blur = True
scene.render.motion_blur_shutter = 0.28
scene.render.keyframe_insert("motion_blur_shutter", frame=318)
scene.render.motion_blur_shutter = 0.22
scene.render.keyframe_insert("motion_blur_shutter", frame=322)
scene.render.keyframe_insert("motion_blur_shutter", frame=596)
scene.render.motion_blur_shutter = 0.18
scene.render.keyframe_insert("motion_blur_shutter", frame=602)
scene.render.keyframe_insert("motion_blur_shutter", frame=662)
scene.render.motion_blur_shutter = 0.22
scene.render.keyframe_insert("motion_blur_shutter", frame=669)
scene.render.motion_blur_position = 'CENTER'
scene.render.image_settings.file_format = 'JPEG'
scene.render.image_settings.quality = 94
scene.render.filepath = os.path.join(FRAMES_DIR, "f_")
scene.view_settings.view_transform = 'AgX'
try:
    scene.view_settings.look = 'High Contrast'
except Exception:
    pass
scene.view_settings.exposure = -0.15
scene.view_settings.gamma = 1.0

# 色彩校正/泛光（合成器）
try:
    ng = bpy.data.node_groups.new("Comp_Race", 'CompositorNodeTree')
    rl = ng.nodes.new("CompositorNodeRLayers")
    glare = ng.nodes.new("CompositorNodeGlare")
    for val in ("Bloom", "BLOOM", "bloom"):
        try:
            glare.inputs['Type'].default_value = val
            break
        except Exception:
            continue
    for nm, v in (("Threshold", 1.1), ("Strength", 0.35), ("Size", 7), ("Saturation", 1.0)):
        if nm in glare.inputs:
            try:
                glare.inputs[nm].default_value = v
            except Exception:
                pass
    comp = None
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
    print("COMPOSITOR GLARE OK")
except Exception as e:
    print("COMPOSITOR SETUP FAILED:", e)
    scene.use_nodes = False

bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("ANIM STAGE SAVED:", OUT)

# ============================================================
# 7. 测试渲染 / 最终渲染
# ============================================================
def render_frames(frames, outdir, res=960, samples=16):
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
    frames = [int(x) for x in str(test).split(",")]
    render_frames(frames, os.path.join(PROJ, "renders_v4", "test"), res=1280, samples=24)

if argval("--render"):
    os.makedirs(FRAMES_DIR, exist_ok=True)
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.eevee.taa_render_samples = 32
    scene.render.filepath = os.path.join(FRAMES_DIR, "f_")
    bpy.ops.render.render(animation=True)
    print("ANIMATION RENDER DONE")
