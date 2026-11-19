# -*- coding: utf-8 -*-
"""
V5 ENV — 真实赛道环境（Silverstone / OpenStreetMap 几何）
输入: pipeline/v4_stage_rig.blend   (模型 + 骨架，无环境无动画)
输出: pipeline/v5_stage_env.blend
运行: blender -b -P pipeline/v5_env.py

要点
  - 路面/路肩/缓冲带/护栏/看台/维修区全部按真实赛道中心线生成（2 m 采样，闭环）
  - 弯道位置由真实曲率决定，不是手摆的
  - 光照重做：低角度硬光 + 低环境光，解决 V4 画面发灰发白
"""
import bpy, bmesh, math, os, sys, json, random
from mathutils import Vector, Matrix, Euler
from math import sin, cos, pi, radians, degrees, atan2, sqrt, hypot

PROJ = r"D:\项目session\blender-supercar"
IN = os.path.join(PROJ, "pipeline", "v4_stage_rig.blend")
OUT = os.path.join(PROJ, "LATEST", "v5_stage_env.blend")
TRACK = os.path.join(PROJ, "track_data", "silverstone_track.json")
TEX = os.path.join(PROJ, "textures")

# ---------------------------------------------------------------
# 0. 赛道数据
# ---------------------------------------------------------------
bpy.ops.wm.open_mainfile(filepath=IN)          # 载入 模型 + 骨架

data = json.load(open(TRACK, encoding="utf-8"))
META = data["meta"]
PTS = data["points"]
N = len(PTS)
HALF_W = META["track_half_width_m"]          # 7.0 -> 14 m
TW = HALF_W * 2

S = [p["s"] for p in PTS]
XY = [Vector((p["xy"][0], p["xy"][1], 0.0)) for p in PTS]
RXY = [Vector((p["racing_xy"][0], p["racing_xy"][1], 0.0)) for p in PTS]
ROFF = [p["racing_offset_m"] for p in PTS]
KAPPA = [abs(p["curv_1pm"] or 0.0) for p in PTS]        # 无符号曲率
VEL = [p["v_mps"] for p in PTS]
LAP_LEN = S[-1]


def _unwrap(deg_list):
    out = [deg_list[0]]
    for a in deg_list[1:]:
        d = (a - out[-1] + 180.0) % 360.0 - 180.0
        out.append(out[-1] + d)
    return out


HDEG = _unwrap([p["heading_deg"] for p in PTS])          # 展开后的切线角（度，从 +X 逆时针）
HEAD = [radians(a) for a in HDEG]

# 有符号曲率：曲率幅值取数据，符号取航向的一阶差分（平滑后）
_span = 4
KSIGN = []
for i in range(N):
    a = HEAD[(i - _span) % N]
    b = HEAD[(i + _span) % N]
    ds = 2 * _span * (LAP_LEN / N)
    if b - a > pi / 2:      # 跨 ±pi 处理
        b -= 2 * pi
    KSIGN.append(1.0 if (b - a) >= 0 else -1.0)
SIGNED_K = [KSIGN[i] * KAPPA[i] for i in range(N)]


def at(i):
    """第 i 点：位置 / 航向 / 右向 / 曲率"""
    i %= N
    h = HEAD[i]
    return XY[i], h, Vector((sin(h), -cos(h), 0.0)), SIGNED_K[i]


def at_s(s):
    s %= LAP_LEN
    lo, hi = 0, N - 1
    while hi - lo > 1:
        m = (lo + hi) // 2
        if S[m] <= s:
            lo = m
        else:
            hi = m
    f = (s - S[lo]) / max(S[lo + 1] - S[lo], 1e-9)
    p = XY[lo].lerp(XY[lo + 1], f)
    a, b = HEAD[lo], HEAD[lo + 1]
    d = (b - a + pi) % (2 * pi) - pi
    h = a + d * f
    return p, h, Vector((sin(h), -cos(h), 0.0)), SIGNED_K[lo]


# ---------------------------------------------------------------
# 1. 工具
# ---------------------------------------------------------------
scene = bpy.context.scene
COLL = scene.collection


def _bsdf(mat_or_nt):
    """按类型取 Principled BSDF（不依赖界面语言的节点显示名）；兼容 material 或 node_tree"""
    nt = getattr(mat_or_nt, 'node_tree', mat_or_nt)
    for n in nt.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            return n
    return None


def new_mat(name, color, rough=0.5, metal=0.0, emission=None, estrength=0.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = _bsdf(m)
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if emission:
        b.inputs['Emission Color'].default_value = (*emission, 1)
        b.inputs['Emission Strength'].default_value = estrength
    return m


def fix_normals(ob, up=True):
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()
    if up and len(me.polygons):
        nz = sum(p.normal.z for p in me.polygons)
        if nz < 0:
            bm = bmesh.new()
            bm.from_mesh(me)
            bmesh.ops.reverse_faces(bm, faces=bm.faces)
            bm.to_mesh(me)
            bm.free()
            me.update()
    return ob


def mesh_from(name, verts, faces, mats, face_mat=None, smooth=False, uvs=None, up=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate()
    me.update()
    ob = bpy.data.objects.new(name, me)
    COLL.objects.link(ob)
    if not isinstance(mats, (list, tuple)):
        mats = [mats]
    for m in mats:
        me.materials.append(m)
    if face_mat:
        for p, mi in zip(me.polygons, face_mat):
            p.material_index = mi
    for p in me.polygons:
        p.use_smooth = smooth
    if uvs:
        uv = me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            for li in poly.loop_indices:
                uv.data[li].uv = uvs[me.loops[li].vertex_index]
    fix_normals(ob, up=up)
    return ob


def box(name, center, size, mat, rot_z=0.0, up=False):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    COLL.objects.link(ob)
    ob.location = center
    ob.rotation_euler = (0, 0, rot_z)
    me.materials.append(mat)
    return ob


# ---------------------------------------------------------------
# 2. 材质
# ---------------------------------------------------------------
_cx = sum(v.x for v in XY) / N
_cy = sum(v.y for v in XY) / N

M_ASPHALT = new_mat("V5_Asphalt", (0.026, 0.026, 0.028), 0.84)
M_RUBBER = new_mat("V5_RubberLine", (0.0215, 0.0218, 0.0232), 0.76)
M_WHITE = new_mat("V5_WhiteLine", (0.68, 0.68, 0.66), 0.60)
M_GRASS = new_mat("V5_Grass", (0.038, 0.062, 0.026), 0.92)
M_GRAVEL = new_mat("V5_Gravel", (0.30, 0.26, 0.20), 0.95)
M_CURB_R = new_mat("V5_CurbRed", (0.52, 0.030, 0.028), 0.55)
M_CURB_W = new_mat("V5_CurbWhite", (0.74, 0.74, 0.72), 0.55)
M_BARRIER = new_mat("V5_Barrier", (0.055, 0.058, 0.065), 0.48, 0.25)
M_CONC = new_mat("V5_Concrete", (0.24, 0.24, 0.245), 0.72)
M_STEEL = new_mat("V5_Steel", (0.09, 0.095, 0.105), 0.42, 0.75)
M_STRIP = new_mat("V5_LightStrip", (0.02, 0.06, 0.07), 0.4,
                  emission=(0.05, 0.85, 1.0), estrength=7.5)
M_CROWD = new_mat("V5_Crowd", (0.035, 0.035, 0.042), 0.92)
M_ROOF = new_mat("V5_Roof", (0.10, 0.11, 0.12), 0.55, 0.3)
M_HANGAR = new_mat("V5_Hangar", (0.14, 0.15, 0.16), 0.75)
M_ADPANEL = new_mat("V5_AdPanel", (0.02, 0.05, 0.13), 0.5,
                    emission=(0.06, 0.55, 0.9), estrength=2.2)

# 沥青：程序化颗粒 + 补丁色差
_am = M_ASPHALT.node_tree
_ab = _bsdf(_am)
_ab.inputs['Specular IOR Level'].default_value = 0.0
_tc = _am.nodes.new('ShaderNodeTexCoord')
_n1 = _am.nodes.new('ShaderNodeTexNoise')
_n1.inputs['Scale'].default_value = 120.0
_n1.inputs['Detail'].default_value = 12.0
_n1.inputs['Roughness'].default_value = 0.75
_bp = _am.nodes.new('ShaderNodeBump')
_bp.inputs['Strength'].default_value = 0.22
_am.links.new(_tc.outputs['Object'], _n1.inputs['Vector'])
_am.links.new(_n1.outputs['Fac'], _bp.inputs['Height'])
_am.links.new(_bp.outputs['Normal'], _ab.inputs['Normal'])
# 大尺度补丁（沥青翻新/油污）
_n2 = _am.nodes.new('ShaderNodeTexNoise')
_n2.inputs['Scale'].default_value = 0.35
_n2.inputs['Detail'].default_value = 5.0
_mix = _am.nodes.new('ShaderNodeMixRGB')
_mix.blend_type = 'MIX'
_mix.inputs['Color1'].default_value = (0.0330, 0.0332, 0.0355, 1)
_mix.inputs['Color2'].default_value = (0.0580, 0.0565, 0.0570, 1)
_mix.inputs['Fac'].default_value = 0.5
_am.links.new(_tc.outputs['Object'], _n2.inputs['Vector'])
_am.links.new(_n2.outputs['Fac'], _mix.inputs['Fac'])
_am.links.new(_mix.outputs['Color'], _ab.inputs['Base Color'])

# 所有路面相关材质压掉镜面（防低角度太阳反光）
for _mn in ("V5_RubberLine", "V5_WhiteLine", "V5_CurbRed", "V5_CurbWhite", "V5_Gravel"):
    _mm = bpy.data.materials.get(_mn)
    if _mm and _mm.node_tree:
        _bb = _bsdf(_mm)
        if _bb and 'Specular IOR Level' in _bb.inputs:
            _bb.inputs['Specular IOR Level'].default_value = 0.03

# 草地：噪波色差
_gm = M_GRASS.node_tree
_gb = _bsdf(_gm)
_gb.inputs['Specular IOR Level'].default_value = 0.15
_gtc = _gm.nodes.new('ShaderNodeTexCoord')
_gn = _gm.nodes.new('ShaderNodeTexNoise')
_gn.inputs['Scale'].default_value = 2.2
_gn.inputs['Detail'].default_value = 9.0
_gmix = _gm.nodes.new('ShaderNodeMixRGB')
_gmix.inputs['Color1'].default_value = (0.036, 0.056, 0.024, 1)
_gmix.inputs['Color2'].default_value = (0.062, 0.086, 0.036, 1)
_gmix.inputs['Fac'].default_value = 0.5
_gm.links.new(_gtc.outputs['Object'], _gn.inputs['Vector'])
_gm.links.new(_gn.outputs['Fac'], _gmix.inputs['Fac'])
# 割草条纹（机场草坪特征）：沿世界 X 的方波，8 m 一条
_gtc2 = _gm.nodes.new('ShaderNodeTexCoord')
_gsep = _gm.nodes.new('ShaderNodeSeparateXYZ')
_gm.links.new(_gtc2.outputs['Object'], _gsep.inputs['Vector'])
_gmul = _gm.nodes.new('ShaderNodeMath')
_gmul.operation = 'MULTIPLY'
_gmul.inputs[1].default_value = 6.28318 / 16.0
_gm.links.new(_gsep.outputs['X'], _gmul.inputs[0])
_gsin = _gm.nodes.new('ShaderNodeMath')
_gsin.operation = 'SINE'
_gm.links.new(_gmul.outputs['Value'], _gsin.inputs[0])
_gstripe = _gm.nodes.new('ShaderNodeMath')
_gstripe.operation = 'MULTIPLY'
_gstripe.inputs[1].default_value = 0.55
_gm.links.new(_gsin.outputs['Value'], _gstripe.inputs[0])
_gadd = _gm.nodes.new('ShaderNodeMath')
_gadd.operation = 'ADD'
_gadd.inputs[1].default_value = 1.0
_gm.links.new(_gstripe.outputs['Value'], _gadd.inputs[0])
_gmul2 = _gm.nodes.new('ShaderNodeMixRGB')
_gmul2.blend_type = 'MULTIPLY'
_gmul2.inputs['Fac'].default_value = 1.0
_gm.links.new(_gmix.outputs['Color'], _gmul2.inputs['Color1'])
_gm.links.new(_gadd.outputs['Value'], _gmul2.inputs['Color2'])
_gm.links.new(_gmul2.outputs['Color'], _gb.inputs['Base Color'])
_gbump = _gm.nodes.new('ShaderNodeBump')
_gbump.inputs['Strength'].default_value = 0.25
_gm.links.new(_gn.outputs['Fac'], _gbump.inputs['Height'])
_gm.links.new(_gbump.outputs['Normal'], _gb.inputs['Normal'])

# 看台人群贴图
_crowd_img = None
_p = os.path.join(TEX, "crowd_silverstone.png")
if os.path.exists(_p):
    _crowd_img = bpy.data.images.load(_p, check_existing=True)
    _cm = M_CROWD.node_tree
    _cb = _bsdf(_cm)
    _ctex = _cm.nodes.new('ShaderNodeTexImage')
    _ctex.image = _crowd_img
    _ctex.extension = 'REPEAT'
    _cm.links.new(_ctex.outputs['Color'], _cb.inputs['Base Color'])
    _cm.links.new(_ctex.outputs['Color'], _cb.inputs['Emission Color'])
    _cb.inputs['Emission Strength'].default_value = 0.55


# ---------------------------------------------------------------
# 2b. 贴图材质（维修区 / 广告板 / 刹车牌 / 大屏）
# ---------------------------------------------------------------
def tex_mat(name, img_file, emission=0.0, spec=0.0, rough=0.7):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs['Specular IOR Level'].default_value = spec
    b.inputs['Roughness'].default_value = rough
    tex = nt.nodes.new('ShaderNodeTexImage')
    img = bpy.data.images.load(os.path.join(TEX, img_file), check_existing=True)
    tex.image = img
    tex.extension = 'REPEAT'
    nt.links.new(tex.outputs['Color'], b.inputs['Base Color'])
    if emission > 0:
        nt.links.new(tex.outputs['Color'], b.inputs['Emission Color'])
        b.inputs['Emission Strength'].default_value = emission
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(b.outputs['BSDF'], out.inputs['Surface'])
    return m, img


M_GARAGE, _garage_img = tex_mat("V5_PitGarage", "pit_garage.png", emission=0.18, spec=0.05, rough=0.6)
M_AD, _ad_img = tex_mat("V5_AdBoard", "ad_boards.png", emission=0.75, spec=0.05, rough=0.55)
M_SCREEN, _screen_img = tex_mat("V5_BigScreen", "bigscreen.png", emission=1.6, spec=0.05, rough=0.4)
M_BRAKE = {}
for _n in ("150", "100", "50"):
    M_BRAKE[_n], _ = tex_mat(f"V5_Brake{_n}", f"brake_{_n}.png", emission=0.12, spec=0.1, rough=0.5)

# ---------------------------------------------------------------
# 3. 天空 / 太阳（重做对比度）
# ---------------------------------------------------------------
world = bpy.data.worlds.get("World_V5Dusk") or bpy.data.worlds.new("World_V5Dusk")
scene.world = world
world.use_nodes = True
_nt = world.node_tree
_nt.nodes.clear()
_bg = _nt.nodes.new('ShaderNodeBackground')
_bg.inputs['Color'].default_value = (0.055, 0.075, 0.130, 1)
_bg.inputs['Strength'].default_value = 1.15
_wo = _nt.nodes.new('ShaderNodeOutputWorld')
_nt.links.new(_bg.outputs[0], _wo.inputs[0])

_sl = bpy.data.lights.new("LGT_V5Sun", 'SUN')
_sl.energy = 5.6
_sl.angle = radians(1.4)
_sl.color = (1.0, 0.86, 0.70)
_sl.use_shadow = True
_sun = bpy.data.objects.new("LGT_V5Sun", _sl)
COLL.objects.link(_sun)
# 与天空 sun_rotation 对齐：方位 232° → 光从西南低角入射
_az = radians(232.0)
_sun.rotation_euler = Euler((radians(90.0 - 22.0), 0.0, _az - pi / 2), 'XYZ')

# 冷补光（天空反向，抬暗部，避免死黑）
_fill = bpy.data.lights.new("LGT_V5SkyFill", 'SUN')
_fill.energy = 0.45
_fill.angle = radians(25.0)
_fill.color = (0.55, 0.70, 1.0)
_fill.use_shadow = False
_fo = bpy.data.objects.new("LGT_V5SkyFill", _fill)
COLL.objects.link(_fo)
_fo.rotation_euler = Euler((radians(52.0), 0.0, _az + pi / 2), 'XYZ')

# ---------------------------------------------------------------
# ---------------------------------------------------------------
# 3b. 天空穹顶：黄昏渐变（顶点色自发光）
# ---------------------------------------------------------------
_sky_mat = bpy.data.materials.new("V5_SkyDome")
_sky_mat.use_nodes = True
_snt = _sky_mat.node_tree
_snt.nodes.clear()
_sout = _snt.nodes.new('ShaderNodeOutputMaterial')
_sem = _snt.nodes.new('ShaderNodeEmission')
_sem.inputs['Strength'].default_value = 1.0
_svc = _snt.nodes.new('ShaderNodeVertexColor')
_svc.layer_name = "Col"
_snt.links.new(_svc.outputs['Color'], _sem.inputs['Color'])
_snt.links.new(_sem.outputs['Emission'], _sout.inputs['Surface'])

_bm = bmesh.new()
try:
    bmesh.ops.create_uvsphere(_bm, u_segments=64, v_segments=32, radius=1.0)
except TypeError:
    bmesh.ops.create_uvsphere(_bm, u_segments=64, v_segments=32, diameter=1.0)
_mesh = bpy.data.meshes.new("V5_SkyDome")
_bm.to_mesh(_mesh)
_bm.free()
_ca = _mesh.color_attributes.new(name="Col", type='FLOAT_COLOR', domain='POINT')


def _sky_color(z):
    stops = [(-0.10, (0.030, 0.026, 0.024)),
             (0.000, (0.60, 0.30, 0.16)),
             (0.030, (0.33, 0.19, 0.20)),
             (0.110, (0.13, 0.17, 0.30)),
             (0.300, (0.045, 0.085, 0.200)),
             (0.650, (0.016, 0.038, 0.115)),
             (1.000, (0.008, 0.020, 0.070))]
    if z <= stops[0][0]:
        return stops[0][1]
    for _k in range(len(stops) - 1):
        z0, c0 = stops[_k]
        z1, c1 = stops[_k + 1]
        if z0 <= z <= z1:
            f = (z - z0) / max(z1 - z0, 1e-9)
            f = f * f * (3 - 2 * f)
            return tuple(c0[j] + (c1[j] - c0[j]) * f for j in range(3))
    return stops[-1][1]


for _i, _v in enumerate(_mesh.vertices):
    _r, _g, _b = _sky_color(_v.co.z)
    _ca.data[_i].color = (_r, _g, _b, 1.0)

_skyob = bpy.data.objects.new("V5_SkyDome", _mesh)
COLL.objects.link(_skyob)
_skyob.location = (_cx, _cy, 0.0)
_skyob.scale = (4200.0, 4200.0, 4200.0)
_skyob.visible_shadow = False
_mesh.materials.append(_sky_mat)

# 4. 地面
# ---------------------------------------------------------------
GR = 2600.0
mesh_from("V5_Ground", [(_cx - GR, _cy - GR, -0.004), (_cx + GR, _cy - GR, -0.004),
                        (_cx + GR, _cy + GR, -0.004), (_cx - GR, _cy + GR, -0.004)],
          [(0, 1, 2, 3)], M_GRASS)

# ---------------------------------------------------------------
# 5. 路面 / 赛车线 / 边线
# ---------------------------------------------------------------
def ribbon(off_a, off_b, z, mat, name, step=1, ups=True, uv_scale=None):
    """沿中心线生成带状网格；off 为右向偏移（m），可为常数或 f(i)；首尾自动闭合"""
    v, fc, uv = [], [], []
    idxs = list(range(0, N, step))
    if idxs[-1] != N - 1:
        idxs.append(N - 1)
    idxs.append(N)                              # at(N) -> 第 0 点，闭环
    fa = off_a if callable(off_a) else (lambda i: off_a)
    fb = off_b if callable(off_b) else (lambda i: off_b)
    for i in idxs:
        p, h, r, k = at(i)
        a, b = fa(i), fb(i)
        v.append((p.x + r.x * a, p.y + r.y * a, z))
        v.append((p.x + r.x * b, p.y + r.y * b, z))
        if uv_scale:
            uv.append((0.0, S[i % N] / uv_scale))
            uv.append((1.0, S[i % N] / uv_scale))
    for j in range(len(idxs) - 1):
        a = j * 2
        fc.append((a, a + 1, a + 3, a + 2))
    return mesh_from(name, v, fc, mat, uvs=uv if uv_scale else None, up=ups)


# 主路面
ribbon(-HALF_W, HALF_W, 0.010, M_ASPHALT, "V5_Track", uv_scale=8.0)
# 边线（白实线）
ribbon(-HALF_W + 0.05, -HALF_W + 0.20, 0.014, M_WHITE, "V5_Line_L")
ribbon(HALF_W - 0.20, HALF_W - 0.05, 0.014, M_WHITE, "V5_Line_R")

# 赛车线橡胶带（沿 racing_xy，宽 3.4 m）
def _rl(i):
    return ROFF[i % N] - 1.7


def _rr(i):
    return ROFF[i % N] + 1.7


ribbon(_rl, _rr, 0.013, M_RUBBER, "V5_RacingLine", step=1)

# ---------------------------------------------------------------
# 6. 路肩（弯道）
# ---------------------------------------------------------------
def corner_runs(thresh=0.0045, min_len=18.0, gap=8.0):
    runs, cur = [], None
    for i in range(N):
        if KAPPA[i] > thresh:
            if cur is None:
                cur = [i, i]
            else:
                cur[1] = i
        else:
            if cur and S[cur[1]] - S[cur[0]] >= min_len:
                runs.append(tuple(cur))
            cur = None
    if cur and LAP_LEN - S[cur[0]] + S[cur[1]] >= min_len:
        runs.append((cur[0], cur[1]))
    # 合并近邻（同一弯的碎段）
    merged = []
    for r in runs:
        if merged and S[r[0]] - S[merged[-1][1]] < gap:
            merged[-1] = (merged[-1][0], r[1])
        else:
            merged.append(list(r))
    return [(a, b) for a, b in merged]


KERB_IN_W = 1.35
KERB_Z_IN = 0.012
KERB_Z_OUT = 0.075
BLOCK_M = 3.2

_runs = corner_runs()
print("corner runs:", len(_runs))


def build_kerb(i0, i1, side, mat, phase, name):
    """沿弯道内侧/外侧生成路肩块（红白交替，按全局弧长对齐）"""
    s0, s1 = S[i0], S[i1]
    v, fc = [], []
    s = s0 - ((s0 / BLOCK_M) % 1.0) * BLOCK_M
    while s < s1 - 0.3:
        kb = int(round(s / BLOCK_M))
        if kb % 2 == phase:
            a0 = max(s0, s)
            a1 = min(s1, s + BLOCK_M)
            if a1 - a0 > 0.5:
                base = len(v)
                for ss in (a0, a1):
                    p, h, r, k = at_s(ss)
                    o0 = side * HALF_W
                    o1 = side * (HALF_W + KERB_IN_W)
                    v.append((p.x + r.x * o0, p.y + r.y * o0, KERB_Z_IN))
                    v.append((p.x + r.x * o1, p.y + r.y * o1, KERB_Z_OUT))
                fc.append((base, base + 1, base + 3, base + 2))
        s += BLOCK_M
    if fc:
        return mesh_from(name, v, fc, mat)


for ki, (a, b) in enumerate(_runs):
    # 内外侧都铺（真实赛道：apex 内侧 + 出弯外侧）
    for side, nm in ((-1, "L"), (1, "R")):
        build_kerb(a, b, side, M_CURB_R, 0, f"V5_Kerb_{ki}_{nm}_R")
        build_kerb(a, b, side, M_CURB_W, 1, f"V5_Kerb_{ki}_{nm}_W")

# ---------------------------------------------------------------
# 7. 缓冲带（草地 / 砾石）
# ---------------------------------------------------------------
VERGE_W = 26.0
ribbon(-HALF_W - KERB_IN_W, -HALF_W - VERGE_W, 0.004, M_GRASS, "V5_Verge_L", step=2)
ribbon(HALF_W + KERB_IN_W, HALF_W + VERGE_W, 0.004, M_GRASS, "V5_Verge_R", step=2)

# 砾石坑：慢弯外侧
GRAV_OUT = 22.0


def build_gravel(i0, i1, side, name):
    v, fc = [], []
    step = 2
    idxs = list(range(i0, i1, step))
    for i in idxs:
        p, h, r, k = at(i)
        for o, z in ((side * (HALF_W + KERB_IN_W), 0.006), (side * GRAV_OUT, 0.006)):
            v.append((p.x + r.x * o, p.y + r.y * o, z))
    for j in range(len(idxs) - 1):
        a = j * 2
        fc.append((a, a + 1, a + 3, a + 2))
    if fc:
        return mesh_from(name, v, fc, M_GRAVEL)


_gi = 0
for (a, b) in _runs:
    vmin = min(VEL[a:b + 1]) * 3.6
    if vmin < 180 and (b - a) > 12:
        side = 1 if SIGNED_K[a] > 0 else -1    # 弯外侧 = 转向的反侧
        build_gravel(a, b, side, f"V5_Gravel_{_gi}")
        _gi += 1
print("gravel traps:", _gi)

# ---------------------------------------------------------------
# 8. 护栏 + 灯带 + 防护网
# ---------------------------------------------------------------
WALL_OFF = HALF_W + VERGE_W            # 33 m
WALL_H = 1.05
BASE_H = 0.24


def _wall_band(z0, z1, off, mat, name):
    wv, wf = [], []
    for side in (-1, 1):
        base = len(wv)
        for i in range(N):
            p, h, r, k = at(i)
            o = side * off
            px, py = p.x + r.x * o, p.y + r.y * o
            wv.append((px, py, z0))
            wv.append((px, py, z1))
        for j in range(N):
            aa = base + j * 2
            bb = base + ((j + 1) % N) * 2
            wf.append((aa, aa + 1, bb + 1, bb))
            wf.append((bb, bb + 1, aa + 1, aa))
    return mesh_from(name, wv, wf, mat, up=False)


_wall_band(0.0, BASE_H, WALL_OFF, M_CONC, "V5_BarrierBase")
_wall_band(BASE_H, WALL_H, WALL_OFF + 0.04, M_BARRIER, "V5_Barrier")

# 顶部灯带
_sv, _sf = [], []
for side in (-1, 1):
    base = len(_sv)
    for i in range(N):
        p, h, r, k = at(i)
        o = side * (WALL_OFF - 0.02)
        px, py = p.x + r.x * o, p.y + r.y * o
        _sv.append((px, py, WALL_H - 0.10))
        _sv.append((px, py, WALL_H - 0.02))
    for j in range(N):
        a = base + j * 2
        b = base + ((j + 1) % N) * 2
        _sf.append((a, a + 1, b + 1, b))
        _sf.append((b, b + 1, a + 1, a))
mesh_from("V5_BarrierStrip", _sv, _sf, M_STRIP, up=False)

# 防护网立柱（每 12 m 一根，简化：只建柱子顶点 + 稀疏网面）
_pv, _pf = [], []
POST_STEP = 12.0
for side in (-1, 1):
    s = 0.0
    while s < LAP_LEN:
        p, h, r, k = at_s(s)
        o = side * (WALL_OFF + 0.35)
        px, py = p.x + r.x * o, p.y + r.y * o
        base = len(_pv)
        for dx, dy in ((-0.07, 0), (0.07, 0)):
            _pv.append((px, py, WALL_H))
            _pv.append((px, py, WALL_H + 3.4))
        _pf.append((base, base + 1, base + 3, base + 2))
        s += POST_STEP
mesh_from("V5_FencePosts", _pv, _pf, M_STEEL, up=False)

# ---------------------------------------------------------------
# 9. 起跑龙门架 + 发车灯 + 起跑线
# ---------------------------------------------------------------
SF_S = 40.0                     # 起终点位置（沿中心线弧长）
gp, gh, gr, gk = at_s(SF_S)

# 路面方格线
_gv, _gf = [], []
for k in range(2):
    _gv.append((gp.x + gr.x * (-HALF_W), gp.y + gr.y * (-HALF_W), 0.016))
    _gv.append((gp.x + gr.x * (HALF_W), gp.y + gr.y * (HALF_W), 0.016))
    gp2, gh2, gr2, _ = at_s(SF_S + (k + 1) * 0.6)
    _gv.append((gp2.x + gr2.x * (-HALF_W), gp2.y + gr2.y * (-HALF_W), 0.016))
    _gv.append((gp2.x + gr2.x * (HALF_W), gp2.y + gr2.y * (HALF_W), 0.016))
for k in range(2):
    a = k * 4
    _gf.append((a, a + 1, a + 3, a + 2))
mesh_from("V5_StartLine", _gv, _gf, M_WHITE)

# 门架
GANT_H = 7.2
for sd in (-1, 1):
    px = gp.x + gr.x * sd * (HALF_W + 1.6)
    py = gp.y + gr.y * sd * (HALF_W + 1.6)
    box(f"V5_Gantry_Post_{sd}", (px, py, GANT_H / 2), (0.45, 0.45, GANT_H), M_STEEL, rot_z=gh)
beam = box("V5_Gantry_Beam", (gp.x, gp.y, GANT_H), (HALF_W * 2 + 3.6, 0.55, 0.85), M_STEEL, rot_z=gh)
ban = box("V5_Gantry_Banner", (gp.x - sin(gh) * 0.32, gp.y + cos(gh) * 0.32, GANT_H),
          (HALF_W * 2 + 2.2, 0.06, 0.6), M_ADPANEL, rot_z=gh)

# 5 盏发车灯（红灯，随动画熄灭）
M_SLIGHT = new_mat("V5_StartLight", (0.06, 0.004, 0.003), 0.3,
                   emission=(1.0, 0.05, 0.02), estrength=18.0)
for i in range(5):
    ox = -1.6 + i * 0.8
    px = gp.x + gr.x * ox
    py = gp.y + gr.y * ox
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=0.18)
    me = bpy.data.meshes.new(f"V5_StartLight_{i}")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(f"V5_StartLight_{i}", me)
    COLL.objects.link(ob)
    ob.location = (px, py, GANT_H - 0.62)
    me.materials.append(M_SLIGHT)

# ---------------------------------------------------------------
# 10. 看台（含人群贴图）
# ---------------------------------------------------------------
def grandstand(s_center, side, length, rows=11, dist=30.0, name="Stand"):
    p, h, r, k = at_s(s_center)
    fwd = Vector((cos(h), sin(h), 0.0))
    out = Vector((r.x, r.y, 0.0)) * side
    row_d = 0.92
    row_h = 0.58
    L = length / 2.0

    # ---- 阶梯分块（每 28 m 一块，块间 2 m 通道，避免一整条）----
    block, gap = 28.0, 2.0
    spans, x0 = [], -L
    while x0 < L - 4:
        x1 = min(x0 + block, L)
        spans.append((x0, x1))
        x0 = x1 + gap
    for bi, (x0, x1) in enumerate(spans):
        bl = x1 - x0
        v, fc, uv = [], [], []
        for rr in range(rows + 1):
            d0 = dist + rr * row_d
            z = rr * row_h
            for sd, xs in ((-1, x0), (1, x1)):
                c = p + out * d0 + fwd * xs
                v.append((c.x, c.y, z))
                uv.append((sd * bl / 7.5 + 0.5, rr / float(rows)))
        for rr in range(rows):
            a = rr * 2
            b = (rr + 1) * 2
            fc.append((a, a + 1, b + 1, b))     # 座面
            fc.append((a, b, b + 1, a + 1))     # 立面
        mesh_from(f"{name}_{bi}", v, fc, M_CROWD, uvs=uv, up=False)

    # ---- 后墙 + VIP 玻璃带 ----
    back = dist + rows * row_d
    box(name + "_Back", (p.x + out.x * back, p.y + out.y * back, rows * row_h / 2),
        (length, 0.5, rows * row_h), M_CONC, rot_z=h)
    gz = (rows - 1) * row_h
    box(name + "_VIP", (p.x + out.x * (back - 0.3), p.y + out.y * (back - 0.3), gz + 0.9),
        (length - 4, 0.12, 1.2), M_STRIP, rot_z=h)

    # ---- 斜顶棚（前低后高）+ 支撑 ----
    zf = rows * row_h + 3.0
    zb = rows * row_h + 5.8
    rf = dist - 0.6
    rb = back + 1.6
    rv = []
    for sd in (-1, 1):
        cf = p + out * rf + fwd * (L * sd)
        cb = p + out * rb + fwd * (L * sd)
        rv += [(cf.x, cf.y, zf), (cb.x, cb.y, zb)]
    mesh_from(name + "_Roof", rv, [(0, 1, 3, 2)], M_ROOF, up=False)
    # 顶棚下沿灯带
    lp = p + out * (rf + 0.1)
    box(name + "_RoofStrip", (lp.x, lp.y, zf - 0.3), (length * 0.96, 0.10, 0.10), M_STRIP, rot_z=h)
    # 后支撑柱（每 8 m）
    _n = int(length / 14)
    for i in range(_n + 1):
        xs = -L + i * 14.0
        cph = p + out * rb + fwd * xs
        box(name + f"_Col{i}", (cph.x, cph.y, zb / 2), (0.24, 0.24, zb), M_STEEL, rot_z=h)
    # 横向钢梁（每 4 m 一根）
    _m = int(length / 8)
    for i in range(_m + 1):
        xs = -L + i * 8.0
        bf = p + out * rf + fwd * xs
        bb = p + out * rb + fwd * xs
        box(name + f"_Truss{i}", (bf.x, bf.y, zf - 0.12), (0.16, 0.16, 0.16), M_STEEL, rot_z=h)
        box(name + f"_TrussB{i}", (bb.x, bb.y, zb - 0.12), (0.16, 0.16, 0.16), M_STEEL, rot_z=h)

    # ---- 前立柱 + 前沿围栏 ----
    for sd in (-1, 1):
        cp = p + out * (dist + 0.4) + fwd * (L * sd * 0.92)
        box(name + f"_Post{sd}", (cp.x, cp.y, zf / 2), (0.28, 0.28, zf), M_STEEL, rot_z=h)
    rail = p + out * (dist - 1.5)
    box(name + "_Rail", (rail.x, rail.y, 0.55), (length, 0.06, 0.06), M_STEEL, rot_z=h)
    # 旗杆 + 旗（沿前沿，每 24 m）
    _n = int(length / 40)
    for i in range(_n + 1):
        xs = -L + i * 40.0
        fp = p + out * (dist - 2.2) + fwd * xs
        box(name + f"_Flagpole{i}", (fp.x, fp.y, 3.0), (0.08, 0.08, 6.0), M_STEEL, rot_z=h)
        col = random.choice(M_FLAGS)
        fv = [(fp.x, fp.y, 6.0),
              (fp.x + out.x * 1.5, fp.y + out.y * 1.5, 5.65),
              (fp.x, fp.y, 5.3)]
        mesh_from(f"V5_Flag_{name}_{i}", fv, [(0, 1, 2)], col, up=False)
    return name


STANDS = [
    (120.0, 1, 150.0, 13, 26.0, "V5_Stand_Main"),
    (1120.0, -1, 90.0, 11, 30.0, "V5_Stand_T1"),
    (2600.0, 1, 110.0, 12, 30.0, "V5_Stand_Mid"),
    (3540.0, -1, 120.0, 12, 30.0, "V5_Stand_Complex"),
    (4370.0, 1, 95.0, 11, 32.0, "V5_Stand_South"),
    (5560.0, -1, 100.0, 11, 28.0, "V5_Stand_Club"),
]
M_FLAGS = [new_mat(f"V5_Flag_{i}", c, 0.6, 0.0)
           for i, c in enumerate(((200, 30, 30), (20, 60, 200), (240, 240, 240),
                                  (255, 160, 0), (20, 140, 90)))]
for args in STANDS:
    grandstand(*args)
print("stands:", len(STANDS))

# ---------------------------------------------------------------
# 11. 维修区（主直道内侧）：pit wall + pit lane + pit box + garage 楼
# ---------------------------------------------------------------
PIT_S0, PIT_S1 = 60.0, 420.0
_p, _h, _r, _k = at_s((PIT_S0 + PIT_S1) / 2)
_pit_fwd = Vector((cos(_h), sin(_h), 0.0))
_pit_out = Vector((- _r.x, - _r.y, 0.0))      # 内侧（-right），与 Stand_Main 错开
PIT_WALL = -(HALF_W + 3.0)                     # -10 m 处维修墙
PIT_LANE = -(HALF_W + 3.0 + 9.0)               # -19 m 处车道内边
PIT_FACE = -(HALF_W + 3.0 + 12.0)              # -22 m 处车库楼正面
PIT_BACK = -(HALF_W + 3.0 + 26.0)              # -36 m 楼背
GAR_H = 8.0
PIT_LEN = PIT_S1 - PIT_S0


def strip_uv(s0, s1, off_a, off_b, z, mat, name, u_repeat, v_repeat=1.0, step=2.0, up=True):
    """局部带状（非闭环），u 沿弧长 / v 沿横向"""
    v, fc, uv = [], [], []
    ss, s = [], s0
    while s <= s1 + 1e-6:
        ss.append(s)
        s += step
    if ss[-1] < s1:
        ss.append(s1)
    for s in ss:
        p, h, r, k = at_s(s)
        for (o, vv) in ((off_a, 0.0), (off_b, 1.0)):
            v.append((p.x + r.x * o, p.y + r.y * o, z))
            uv.append(((s - s0) / u_repeat, vv * v_repeat))
    for j in range(len(ss) - 1):
        a = j * 2
        fc.append((a, a + 1, a + 3, a + 2))
    return mesh_from(name, v, fc, mat, uvs=uv, up=up)


def wall_uv(s0, s1, off, z0, z1, mat, name, u_repeat, v_repeat=1.0, step=2.0):
    """局部竖直墙（garage 正面 / 维修墙），u 沿弧长 / v 沿高度"""
    v, fc, uv = [], [], []
    ss, s = [], s0
    while s <= s1 + 1e-6:
        ss.append(s)
        s += step
    if ss[-1] < s1:
        ss.append(s1)
    for s in ss:
        p, h, r, k = at_s(s)
        px, py = p.x + r.x * off, p.y + r.y * off
        v.append((px, py, z0))
        v.append((px, py, z1))
        uv.append(((s - s0) / u_repeat, 0.0))
        uv.append(((s - s0) / u_repeat, v_repeat))
    for j in range(len(ss) - 1):
        a = j * 2
        fc.append((a, a + 1, a + 3, a + 2))
    return mesh_from(name, v, fc, mat, uvs=uv, up=False)


# ① pit lane 沥青车道（覆盖掉草地缓冲带）
strip_uv(PIT_S0, PIT_S1, PIT_WALL, PIT_LANE, 0.010, M_ASPHALT, "V5_PitLane", PIT_LEN)
# ② pit lane 两条白线
strip_uv(PIT_S0, PIT_S1, PIT_WALL - 0.25, PIT_WALL - 0.02, 0.014, M_WHITE, "V5_PitLineIn", PIT_LEN)
strip_uv(PIT_S0, PIT_S1, PIT_LANE + 0.02, PIT_LANE + 0.25, 0.014, M_WHITE, "V5_PitLineOut", PIT_LEN)
# ③ 维修墙（分段矮墙）+ 顶部队名灯牌
wall_uv(PIT_S0, PIT_S1, PIT_WALL, 0.0, 1.10, M_CONC, "V5_PitWall", PIT_LEN)
strip_uv(PIT_S0, PIT_S1, PIT_WALL - 0.08, PIT_WALL + 0.08, 1.12, M_STRIP, "V5_PitWallStrip", PIT_LEN)
# ④ pit box 划线：每 6 m 一条横向白线（garage 分格）
_bk = 0
_s = PIT_S0 + 3.0
while _s < PIT_S1 - 1.0:
    p, h, r, k = at_s(_s)
    fwd = Vector((cos(h), sin(h), 0.0))
    v = []
    for (o, sd) in ((PIT_WALL, -1), (PIT_WALL, 1), (PIT_LANE, 1), (PIT_LANE, -1)):
        c = p + r * o + fwd * sd * 0.06
        v.append((c.x, c.y, 0.015))
    mesh_from(f"V5_PitBoxLine_{_bk}", v, [(0, 1, 2, 3)], M_WHITE)
    _bk += 1
    _s += 6.0
# ⑤ garage 楼体（混凝土）+ 正面贴图面板
_c = _p + _pit_out * ((abs(PIT_FACE) + abs(PIT_BACK)) / 2)
_dep = abs(PIT_BACK - PIT_FACE)
box("V5_PitGarage", (_c.x, _c.y, GAR_H / 2), (PIT_LEN, _dep, GAR_H), M_CONC, rot_z=_h)
wall_uv(PIT_S0, PIT_S1, PIT_FACE, 0.0, GAR_H, M_GARAGE, "V5_PitGarageFront", PIT_LEN, v_repeat=GAR_H / 4.0)
# ⑥ garage 楼顶赞助灯箱（发光）
strip_uv(PIT_S0, PIT_S1, PIT_FACE + 1.0, PIT_BACK - 1.0, GAR_H + 0.05, M_AD, "V5_PitRoofBanner", PIT_LEN, up=True)
# ⑦ garage 楼顶主看台（4 排小阶梯，用人群贴图）
for _rr in range(4):
    _o0 = PIT_BACK - 1.5 + _rr * 1.2
    _o1 = _o0 + 1.2
    _z = GAR_H + 0.06 + _rr * 0.55
    strip_uv(PIT_S0, PIT_S1, _o0, _o1, _z, M_CROWD, f"V5_PitTopTier_{_rr}", PIT_LEN, up=True)
# 楼顶围栏（发光细条）
strip_uv(PIT_S0, PIT_S1, PIT_BACK + 0.3, PIT_BACK + 0.5, GAR_H + 2.4, M_STRIP, "V5_PitTopRail", PIT_LEN)

# ---------------------------------------------------------------
# 11b. 赛道道具：广告板 / 刹车牌 / 大屏 / 天桥 / 裁判点
# ---------------------------------------------------------------
def ad_board(s, side, w=11.0, hgt=3.6, off=WALL_OFF + 2.5, name=""):
    p, h, r, k = at_s(s)
    base = p + r * (side * off)
    box(name, (base.x, base.y, 1.0 + hgt / 2), (w, 0.12, hgt), M_AD, rot_z=h)


def brake_board(s, side, num, off=HALF_W + 2.4, name=""):
    p, h, r, k = at_s(s)
    base = p + r * (side * off)
    box(name, (base.x, base.y, 1.05), (1.0, 0.08, 1.25), M_BRAKE[num], rot_z=h)
    # 两根细杆
    for d in (-0.32, 0.32):
        box(name + "_pole", (base.x, base.y, 0.5), (0.05, 0.05, 1.0), M_STEEL, rot_z=h)


def bigscreen(s, side, off=WALL_OFF + 8.0, w=22.0, hgt=9.0, name="V5_Screen"):
    p, h, r, k = at_s(s)
    base = p + r * (side * off)
    box(name, (base.x, base.y, 5.5), (w, 0.45, hgt), M_SCREEN, rot_z=h)
    for dx in (-w / 2 + 0.5, w / 2 - 0.5):
        box(name + "_leg", (base.x + cos(h) * dx, base.y + sin(h) * dx, 2.0),
            (0.5, 0.5, 4.0), M_STEEL, rot_z=h)


def footbridge(s, name="V5_Bridge"):
    p, h, r, k = at_s(s)
    fwd = Vector((cos(h), sin(h), 0.0))
    off = HALF_W + 7.0
    # 桥面：横跨赛道，宽（沿 fwd）4.5 m，高 6.0 m
    a = p - r * off - fwd * 2.25
    b = p + r * off - fwd * 2.25
    c = p + r * off + fwd * 2.25
    d = p - r * off + fwd * 2.25
    v = [(a.x, a.y, 6.0), (b.x, b.y, 6.0), (c.x, c.y, 6.0), (d.x, d.y, 6.0),
         (a.x, a.y, 5.4), (b.x, b.y, 5.4), (c.x, c.y, 5.4), (d.x, d.y, 5.4)]
    fc = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 4, 5, 1), (1, 5, 6, 2),
          (2, 6, 7, 3), (3, 7, 4, 0)]
    mesh_from(name, v, fc, M_STEEL, up=False)
    # 桥墩
    for sd in (-1, 1):
        bp = p + r * (sd * off)
        box(name + "_pier", (bp.x, bp.y, 2.8), (0.6, 0.6, 5.6), M_CONC)
    # 栏杆（桥面两侧发光条）
    for sd in (-1, 1):
        rr = fwd * (2.25 * sd)
        l0 = p - r * off + rr
        l1 = p + r * off + rr
        lv = [(l0.x, l0.y, 6.4), (l1.x, l1.y, 6.4)]
        # 简化成两根细 box
        mid = (l0 + l1) / 2
        box(name + "_rail", (mid.x, mid.y, 6.5), (0.1, off * 2, 0.1), M_STRIP, rot_z=h)


# ① 广告板：沿整圈每 60 m 一块（护栏外侧；跳过维修区主直道段，避免与车库楼/看台穿插）
_ad_i = 0
_s = 30.0
while _s < LAP_LEN - 5:
    side = 1 if _ad_i % 2 == 0 else -1
    if not (PIT_S0 - 10 < _s < PIT_S1 + 10):
        ad_board(_s, side, name=f"V5_Ad_{_ad_i}")
        _ad_i += 1
    _s += 60.0
print("ad boards:", _ad_i)

# ② 刹车距离牌：慢弯（vmin<130）外侧，弯前 150/100/50 m
_bi = 0
for (a, b) in _runs:
    vmin = min(VEL[a:b + 1]) * 3.6
    if vmin < 130 and (b - a) > 15 and _bi < 3:
        apex_s = (S[a] + S[b]) / 2
        side = 1 if SIGNED_K[a] > 0 else -1
        for dist_, num in ((150, "150"), (100, "100"), (50, "50")):
            brake_board(apex_s - dist_, side, num, name=f"V5_Brake_{_bi}_{num}")
        _bi += 1
print("brake boards:", _bi * 3)

# ③ 大屏：维修区出口内侧 + 赛道中段（避开车库楼遮挡）
bigscreen(560.0, -1, name="V5_Screen_A")
bigscreen(2600.0, -1, name="V5_Screen_B")

# ④ 人行天桥：两条直道
footbridge(950.0, "V5_Bridge_A")
footbridge(2950.0, "V5_Bridge_B")

# ⑤ 裁判点小棚（沿赛道每 ~830 m 一个）
_mi = 0
for i in range(7):
    sp = LAP_LEN * i / 7.0
    p, h, r, k = at_s(sp)
    side = 1 if i % 2 == 0 else -1
    bp = p + r * (side * (HALF_W + 5.0))
    box(f"V5_Marshal_{i}", (bp.x, bp.y, 0.7), (1.6, 1.1, 1.4), M_CONC, rot_z=h)
    box(f"V5_Marshal_{i}_lamp", (bp.x, bp.y, 1.55), (0.25, 0.25, 0.12), M_STRIP, rot_z=h)
print("marshal posts:", 7)


# ---------------------------------------------------------------
# 12. 场地外围：机库 / 树线 / 灯柱
# ---------------------------------------------------------------
random.seed(23)
for i in range(6):
    a = random.uniform(0, 2 * pi)
    rad = random.uniform(700, 1250)
    bx = _cx + cos(a) * rad
    by = _cy + sin(a) * rad
    w = random.uniform(40, 90)
    d = random.uniform(30, 60)
    hgt = random.uniform(9, 18)
    box(f"V5_Hangar_{i}", (bx, by, hgt / 2), (w, d, hgt), M_HANGAR, rot_z=random.uniform(0, pi))

# 场地边界：低矮灌篱 + 围网（远景轮廓，不做树）
_tree_mat = new_mat("V5_Tree", (0.016, 0.030, 0.013), 0.9)
_tv, _tf = [], []
_hedge_v = []
for i in range(240):
    a = 2 * pi * i / 240.0
    rad = 1150.0 + 220.0 * sin(a * 2.3 + 0.7) + 90.0 * sin(a * 5.1)
    bx = _cx + cos(a) * rad
    by = _cy + sin(a) * rad
    hgt = 2.4 + 1.6 * (0.5 + 0.5 * sin(a * 7.0))
    _hedge_v.append((bx, by, hgt))
for i in range(239):
    a = len(_tv)
    x0, y0, h0 = _hedge_v[i]
    x1, y1, h1 = _hedge_v[i + 1]
    _tv += [(x0, y0, 0), (x1, y1, 0), (x1, y1, h1), (x0, y0, h0)]
    _tf.append((a, a + 1, a + 2, a + 3))
mesh_from("V5_HedgeRing", _tv, _tf, _tree_mat, up=False)

# 场地灯柱（12 根，沿赛道每 480 m）
_lv, _lf = [], []
for i in range(12):
    sp = LAP_LEN * i / 12.0
    p, h, r, k = at_s(sp)
    side = 1 if i % 2 == 0 else -1
    o = side * (HALF_W + 42.0)
    px, py = p.x + r.x * o, p.y + r.y * o
    base = len(_lv)
    _lv += [(px - 0.12, py - 0.12, 0), (px + 0.12, py - 0.12, 0), (px + 0.12, py + 0.12, 0),
            (px - 0.12, py + 0.12, 0), (px - 0.12, py - 0.12, 16), (px + 0.12, py - 0.12, 16),
            (px + 0.12, py + 0.12, 16), (px - 0.12, py + 0.12, 16)]
    _lf += [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    # 灯头
    hb = len(_lv)
    _lv += [(px - 0.9, py - 0.25, 15.6), (px + 0.9, py - 0.25, 15.6),
            (px + 0.9, py + 0.25, 15.6), (px - 0.9, py + 0.25, 15.6)]
    _lf += [(hb, hb + 1, hb + 2, hb + 3)]
mesh_from("V5_FieldMasts", _lv, _lf, M_STEEL, up=False)

print("ENV BUILD DONE")
print("objects:", len(bpy.data.objects), "materials:", len(bpy.data.materials))


# ---------------------------------------------------------------
# 13. 工程整理：原点归位 + 集合分组（让场景在 Blender 里能手工编辑）
# ---------------------------------------------------------------
_GROUPS = {
    "V5_01_Road": ("V5_Track", "V5_RacingLine", "V5_Line_", "V5_Kerb_",
                   "V5_StartLine", "V5_PitLane", "V5_PitLine", "V5_PitBoxLine"),
    "V5_02_Terrain": ("V5_Ground", "V5_Verge_", "V5_Gravel_", "V5_HedgeRing", "V5_SkyDome"),
    "V5_03_Barriers": ("V5_Barrier", "V5_FencePosts"),
    "V5_04_Stands": ("V5_Stand_", "V5_Flag_"),
    "V5_05_Pit": ("V5_PitWall", "V5_PitGarage", "V5_PitRoof", "V5_PitTop"),
    "V5_06_Props": ("V5_Ad_", "V5_Brake_", "V5_Screen_", "V5_Bridge_",
                    "V5_Marshal_", "V5_FieldMasts", "V5_Hangar_",
                    "V5_Gantry", "V5_StartLight"),
    "V5_07_Lighting": ("LGT_V5",),
}

_moved = 0
for _ob in list(bpy.data.objects):
    if _ob.type != 'MESH' or not _ob.name.startswith(("V5_", "GEO_Race")):
        continue
    if not _ob.data.vertices:
        continue
    _bb = [_ob.matrix_world @ Vector(c) for c in _ob.bound_box]
    _c = Vector((sum(v.x for v in _bb) / 8.0, sum(v.y for v in _bb) / 8.0, sum(v.z for v in _bb) / 8.0))
    _lc = _ob.matrix_world.inverted() @ _c
    for _v in _ob.data.vertices:
        _v.co -= _lc
    _ob.location = _c
    _ob.data.update()
    _moved += 1

_root = scene.collection
_cols = {}
for _g in _GROUPS:
    _cc = bpy.data.collections.get(_g) or bpy.data.collections.new(_g)
    if _cc.name not in _root.children:
        _root.children.link(_cc)
    _cols[_g] = _cc


def _bucket(nm):
    for _g, _ps in _GROUPS.items():
        for _p in _ps:
            if nm.startswith(_p):
                return _g
    return None


_reg = 0
for _ob in list(bpy.data.objects):
    _g = _bucket(_ob.name)
    if not _g:
        continue
    for _c in list(_ob.users_collection):
        _c.objects.unlink(_ob)
    _cols[_g].objects.link(_ob)
    _reg += 1
print("organize: origin_to_geometry=%d  regrouped=%d" % (_moved, _reg))

bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("ENV SAVED:", OUT)
