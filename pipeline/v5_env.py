# -*- coding: utf-8 -*-
"""
V5 ENV — 真实赛道环境（Silverstone / OpenStreetMap 几何）
输入: pipeline/v4_stage_rig.blend   (模型 + 骨架，无环境无动画)
输出: LATEST/v5_stage_env.blend
运行: blender -b -P pipeline/v5_env.py

要点
  - 路面/路肩/缓冲带/护栏/看台/维修区全部按真实赛道中心线生成（2 m 采样，闭环）
  - 弯道位置由真实曲率决定，不是手摆的
  - 光照重做：低角度硬光 + 低环境光，解决 V4 画面发灰发白

可编辑性（给手工改场景的人）
  - 每个"组件"（看台 / 天桥 / 大屏 / 刹车牌组 / 裁判点 / 龙门架+发车灯）有一个 Empty 父物体，
    放在组件中心、Z 轴朝向沿赛道方向；选 Empty 按 G/R 就能整体挪动/旋转。
  - 重复小零件按"每座看台每类一个网格"合并（柱 / 钢梁 / 旗杆 / 旗 / 前立柱），多材质槽保留原材质。
  - 所有网格原点都在自身几何中心。
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


def panel_box(name, center, size, mat, rot_z=0.0, u_range=(0.0, 1.0), edge_mat=None):
    """带正确正立 UV 的双面展板盒：±Y 宽面贴图 mat（UV [u0..u1]x[0..1]），四条窄边用 edge_mat。"""
    hx, hy, hz = size[0] / 2.0, size[1] / 2.0, size[2] / 2.0
    verts = [
        (-hx, -hy, -hz), (hx, -hy, -hz), (hx, -hy, hz), (-hx, -hy, hz),   # 0..3: -Y 面
        (hx, hy, -hz), (-hx, hy, -hz), (-hx, hy, hz), (hx, hy, hz),       # 4..7: +Y 面
    ]
    faces = [
        (0, 1, 2, 3),   # -Y 正面
        (4, 5, 6, 7),   # +Y 背面
        (1, 4, 7, 2),   # +X 侧边
        (5, 0, 3, 6),   # -X 侧边
        (3, 2, 7, 6),   # +Z 顶边
        (5, 4, 1, 0),   # -Z 底边
    ]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate()
    me.update()
    ob = bpy.data.objects.new(name, me)
    COLL.objects.link(ob)
    ob.location = center
    ob.rotation_euler = (0, 0, rot_z)
    me.materials.append(mat)
    emat = edge_mat or mat
    if emat != mat:
        me.materials.append(emat)
    u0, u1 = u_range
    uv_layer = me.uv_layers.new(name="UVMap")
    quad_uv = [(u0, 0.0), (u1, 0.0), (u1, 1.0), (u0, 1.0)]
    for pi, poly in enumerate(me.polygons):
        poly.material_index = 0 if pi < 2 else (1 if emat != mat else 0)
        for k, li in enumerate(poly.loop_indices):
            uv_layer.data[li].uv = quad_uv[k % 4]
    return ob


_CUBE_FACES = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]


class Parts:
    """把一组重复小零件累积成【一个】网格对象（世界坐标烘焙，第 13 步再把原点挪到几何中心）。
    每个零件可用不同材质 -> 多材质槽。用法:
        P = Parts("V5_Stand_Main_Columns"); P.box(...); P.beam(...); ob = P.build()
    """

    def __init__(self, name):
        self.name = name
        self.v, self.f, self.fm, self.mats = [], [], [], []

    def _mi(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def _cuboid(self, corners, mat):
        mi = self._mi(mat)
        base = len(self.v)
        self.v += [tuple(c) for c in corners]
        for fc in _CUBE_FACES:
            self.f.append(tuple(base + i for i in fc))
            self.fm.append(mi)

    def box(self, center, size, mat, rot_z=0.0):
        """与 box() 同参数：中心 + 尺寸 + 绕 Z 旋转"""
        hx, hy, hz = size[0] / 2.0, size[1] / 2.0, size[2] / 2.0
        c, s = cos(rot_z), sin(rot_z)
        pts = []
        for sz in (-1, 1):
            for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                x, y = sx * hx, sy * hy
                pts.append((center[0] + x * c - y * s, center[1] + x * s + y * c, center[2] + sz * hz))
        self._cuboid(pts, mat)

    def beam(self, a, b, side, w, hgt, mat):
        """从 a 到 b 的方截面梁；side = 水平横向单位向量，截面 w(横) x hgt(竖)"""
        a, b = Vector(a), Vector(b)
        sv = Vector(side).normalized() * (w / 2.0)
        uv = Vector((0.0, 0.0, hgt / 2.0))
        pts = []
        for e in (a, b):
            pts += [e - sv - uv, e + sv - uv, e + sv + uv, e - sv + uv]
        self._cuboid(pts, mat)

    def poly(self, verts, faces, mat):
        mi = self._mi(mat)
        base = len(self.v)
        self.v += [tuple(p) for p in verts]
        for fc in faces:
            self.f.append(tuple(base + i for i in fc))
            self.fm.append(mi)

    def build(self, up=False):
        if not self.f:
            return None
        ob = mesh_from(self.name, self.v, self.f, self.mats, face_mat=self.fm, up=up)
        if up:      # 多个互不相连的平面片：逐面保证朝上（recalc 只能保证每个岛内一致）
            me = ob.data
            bm = bmesh.new()
            bm.from_mesh(me)
            bm.normal_update()
            down = [f for f in bm.faces if f.normal.z < 0]
            if down:
                bmesh.ops.reverse_faces(bm, faces=down)
                bm.to_mesh(me)
                me.update()
            bm.free()
        return ob


# 组件 Empty：(empty, [子物体])；第 13 步原点归位之后统一挂父子关系（保持世界变换）
ASSEMBLIES = []


def assembly(name, center, heading, parts, size=4.0):
    em = bpy.data.objects.new(name, None)
    em.empty_display_type = 'ARROWS'
    em.empty_display_size = size
    COLL.objects.link(em)
    em.location = (center[0], center[1], center[2] if len(center) > 2 else 0.0)
    em.rotation_euler = (0.0, 0.0, heading)
    ASSEMBLIES.append((em, [p for p in parts if p is not None]))
    return em


# ---------------------------------------------------------------
# 2. 材质
# ---------------------------------------------------------------
_cx = sum(v.x for v in XY) / N
_cy = sum(v.y for v in XY) / N

M_ASPHALT = new_mat("V5_Asphalt", (0.038, 0.039, 0.042), 0.85)
M_RUBBER = new_mat("V5_RubberLine", (0.0195, 0.0198, 0.0215), 0.78)
M_SKID = new_mat("V5_BrakingRubber", (0.0115, 0.0116, 0.0128), 0.88)
M_WHITE = new_mat("V5_WhiteLine", (0.68, 0.68, 0.66), 0.60)
M_GRASS = new_mat("V5_Grass", (0.048, 0.076, 0.032), 0.92)
M_GRAVEL = new_mat("V5_Gravel", (0.31, 0.27, 0.21), 0.95)
M_CURB_R = new_mat("V5_CurbRed", (0.52, 0.030, 0.028), 0.56)
M_CURB_W = new_mat("V5_CurbWhite", (0.74, 0.74, 0.72), 0.56)
M_SAUSAGE_Y = new_mat("V5_SausageYellow", (0.62, 0.44, 0.02), 0.58)
M_SAUSAGE_K = new_mat("V5_SausageBlack", (0.022, 0.022, 0.025), 0.68)
M_BOLLARD = new_mat("V5_ApexBollard", (0.72, 0.52, 0.02), 0.45,
                    emission=(0.85, 0.60, 0.04), estrength=0.25)
M_PIT_GREEN = new_mat("V5_PitGreenLED", (0.02, 0.25, 0.06), 0.25,
                      emission=(0.04, 1.0, 0.22), estrength=14.0)
M_PIT_GLASS = new_mat("V5_PitGlass", (0.03, 0.045, 0.065), 0.14, 0.15)
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

# 沥青：程序化颗粒 + 补丁色差 + 赛车线外侧橡胶碎屑(marbles)/浮尘变化（世界坐标）
_am = M_ASPHALT.node_tree
_ab = _bsdf(_am)
_ab.inputs['Specular IOR Level'].default_value = 0.015
_tc = _am.nodes.new('ShaderNodeNewGeometry')
_n1 = _am.nodes.new('ShaderNodeTexNoise')
_n1.inputs['Scale'].default_value = 135.0
_n1.inputs['Detail'].default_value = 12.0
_n1.inputs['Roughness'].default_value = 0.78
_bp = _am.nodes.new('ShaderNodeBump')
_bp.inputs['Strength'].default_value = 0.22
_am.links.new(_tc.outputs['Position'], _n1.inputs['Vector'])
_am.links.new(_n1.outputs['Fac'], _bp.inputs['Height'])
_am.links.new(_bp.outputs['Normal'], _ab.inputs['Normal'])
# 大尺度补丁（沥青翻新/油污）+ 线外顶点属性 OffLine 驱动的浮尘与橡胶碎粒(marbles)
_n2 = _am.nodes.new('ShaderNodeTexNoise')
_n2.inputs['Scale'].default_value = 0.38
_n2.inputs['Detail'].default_value = 5.0
_mix = _am.nodes.new('ShaderNodeMixRGB')
_mix.blend_type = 'MIX'
_mix.inputs['Color1'].default_value = (0.0365, 0.0370, 0.0398, 1)
_mix.inputs['Color2'].default_value = (0.0650, 0.0638, 0.0645, 1)
_am.links.new(_tc.outputs['Position'], _n2.inputs['Vector'])
_am.links.new(_n2.outputs['Fac'], _mix.inputs['Fac'])

_attr_off = _am.nodes.new('ShaderNodeAttribute')
_attr_off.attribute_name = "OffLine"
_n_marb = _am.nodes.new('ShaderNodeTexNoise')
_n_marb.inputs['Scale'].default_value = 34.0
_n_marb.inputs['Detail'].default_value = 8.0
_n_marb.inputs['Roughness'].default_value = 0.82
_am.links.new(_tc.outputs['Position'], _n_marb.inputs['Vector'])
_cr_marb = _am.nodes.new('ShaderNodeValToRGB')
_cr_marb.color_ramp.elements[0].position = 0.56
_cr_marb.color_ramp.elements[0].color = (0.066, 0.064, 0.060, 1)   # 线外浅灰浮尘
_cr_marb.color_ramp.elements[1].position = 0.72
_cr_marb.color_ramp.elements[1].color = (0.014, 0.014, 0.016, 1)   # 橡胶碎粒黑点
_am.links.new(_n_marb.outputs['Fac'], _cr_marb.inputs['Fac'])
_mix_marb = _am.nodes.new('ShaderNodeMixRGB')
_mix_marb.blend_type = 'MIX'
_am.links.new(_attr_off.outputs['Fac'], _mix_marb.inputs['Fac'])
_am.links.new(_mix.outputs['Color'], _mix_marb.inputs['Color1'])
_am.links.new(_cr_marb.outputs['Color'], _mix_marb.inputs['Color2'])
_am.links.new(_mix_marb.outputs['Color'], _ab.inputs['Base Color'])

# 重刹区双轮迹橡胶压痕材质（DITHERED 半透明羽化，Specular <= 0.02）
try:
    M_SKID.surface_render_method = 'DITHERED'
except Exception:
    pass
_sm = M_SKID.node_tree
_sb = _bsdf(_sm)
_sb.inputs['Specular IOR Level'].default_value = 0.015
_sb.inputs['Roughness'].default_value = 0.88
_sb.inputs['Base Color'].default_value = (0.0105, 0.0106, 0.0118, 1)
_suv = _sm.nodes.new('ShaderNodeUVMap')
_suv.uv_map = "UVMap"
_ssep = _sm.nodes.new('ShaderNodeSeparateXYZ')
_sm.links.new(_suv.outputs['UV'], _ssep.inputs['Vector'])
_sattr = _sm.nodes.new('ShaderNodeAttribute')
_sattr.attribute_name = "SkidFade"
# 横向双轮迹轮廓：u in [0..1]，在 u=0.26 与 u=0.74 形成重刹轮胎黑印并向边缘羽化归零
_sramp = _sm.nodes.new('ShaderNodeValToRGB')
_sramp.color_ramp.interpolation = 'EASE'
_sramp.color_ramp.elements[0].position = 0.00
_sramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1)
_se1 = _sramp.color_ramp.elements.new(0.24)
_se1.color = (0.92, 0.92, 0.92, 1)
_se2 = _sramp.color_ramp.elements.new(0.50)
_se2.color = (0.48, 0.48, 0.48, 1)
_se3 = _sramp.color_ramp.elements.new(0.76)
_se3.color = (0.92, 0.92, 0.92, 1)
_sramp.color_ramp.elements[-1].position = 1.00
_sramp.color_ramp.elements[-1].color = (0.0, 0.0, 0.0, 1)
_sm.links.new(_ssep.outputs['X'], _sramp.inputs['Fac'])
# 纵向条纹噪波（沿弧长 v 方向拉丝）
_smap = _sm.nodes.new('ShaderNodeCombineXYZ')
_smul_u = _sm.nodes.new('ShaderNodeMath')
_smul_u.operation = 'MULTIPLY'
_smul_u.inputs[1].default_value = 18.0
_sm.links.new(_ssep.outputs['X'], _smul_u.inputs[0])
_sm.links.new(_smul_u.outputs['Value'], _smap.inputs['X'])
_sm.links.new(_ssep.outputs['Y'], _smap.inputs['Y'])
_snois = _sm.nodes.new('ShaderNodeTexNoise')
_snois.inputs['Scale'].default_value = 2.6
_snois.inputs['Detail'].default_value = 6.0
_sm.links.new(_smap.outputs['Vector'], _snois.inputs['Vector'])
_smul1 = _sm.nodes.new('ShaderNodeMath')
_smul1.operation = 'MULTIPLY'
_sm.links.new(_sramp.outputs['Color'], _smul1.inputs[0])
_sm.links.new(_sattr.outputs['Fac'], _smul1.inputs[1])
_smul2 = _sm.nodes.new('ShaderNodeMath')
_smul2.operation = 'MULTIPLY'
_sm.links.new(_smul1.outputs['Value'], _smul2.inputs[0])
_sm.links.new(_snois.outputs['Fac'], _smul2.inputs[1])
_smul3 = _sm.nodes.new('ShaderNodeMath')
_smul3.operation = 'MULTIPLY'
_smul3.inputs[1].default_value = 1.25
_smul3.use_clamp = True
_sm.links.new(_smul2.outputs['Value'], _smul3.inputs[0])
_sm.links.new(_smul3.outputs['Value'], _sb.inputs['Alpha'])

# 所有路面/标线/路肩/香肠路肩/砾石材质严格压制镜面 <= 0.03（杜绝低角度太阳纯白反光楔）
for _mn in ("V5_RubberLine", "V5_BrakingRubber", "V5_WhiteLine",
            "V5_CurbRed", "V5_CurbWhite", "V5_SausageYellow", "V5_SausageBlack", "V5_Gravel"):
    _mm = bpy.data.materials.get(_mn)
    if _mm and _mm.node_tree:
        _bb = _bsdf(_mm)
        if _bb and 'Specular IOR Level' in _bb.inputs:
            _bb.inputs['Specular IOR Level'].default_value = 0.025

# 草地：噪波色差（适度提亮草坪反照率，使 S14/S23 航拍俯视曝光通透均衡）
_gm = M_GRASS.node_tree
_gb = _bsdf(_gm)
_gb.inputs['Specular IOR Level'].default_value = 0.12
_gtc = _gm.nodes.new('ShaderNodeNewGeometry')          # 世界坐标，理由同沥青
_gn = _gm.nodes.new('ShaderNodeTexNoise')
_gn.inputs['Scale'].default_value = 2.2
_gn.inputs['Detail'].default_value = 9.0
_gmix = _gm.nodes.new('ShaderNodeMixRGB')
_gmix.inputs['Color1'].default_value = (0.045, 0.070, 0.030, 1)
_gmix.inputs['Color2'].default_value = (0.076, 0.106, 0.044, 1)
_gmix.inputs['Fac'].default_value = 0.5
_gm.links.new(_gtc.outputs['Position'], _gn.inputs['Vector'])
_gm.links.new(_gn.outputs['Fac'], _gmix.inputs['Fac'])
# 割草条纹（机场草坪特征）：沿世界 X 的正弦波，8 m 一条
_gsep = _gm.nodes.new('ShaderNodeSeparateXYZ')
_gm.links.new(_gtc.outputs['Position'], _gsep.inputs['Vector'])
_gmul = _gm.nodes.new('ShaderNodeMath')
_gmul.operation = 'MULTIPLY'
_gmul.inputs[1].default_value = 6.28318 / 16.0
_gm.links.new(_gsep.outputs['X'], _gmul.inputs[0])
_gsin = _gm.nodes.new('ShaderNodeMath')
_gsin.operation = 'SINE'
_gm.links.new(_gmul.outputs['Value'], _gsin.inputs[0])
_gstripe = _gm.nodes.new('ShaderNodeMath')
_gstripe.operation = 'MULTIPLY'
_gstripe.inputs[1].default_value = 0.46
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
# 2b. 贴图材质（维修区 / 广告板 / 刹车牌 / DRS 牌 / 大屏）
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


M_GARAGE, _garage_img = tex_mat("V5_PitGarage", "pit_garage.png", emission=0.22, spec=0.05, rough=0.58)
M_AD, _ad_img = tex_mat("V5_AdBoard", "ad_boards.png", emission=0.58, spec=0.05, rough=0.55)
M_SCREEN, _screen_img = tex_mat("V5_BigScreen", "bigscreen.png", emission=1.25, spec=0.05, rough=0.38)
M_DRS, _drs_img = tex_mat("V5_DRSBoard", "drs_board.png", emission=0.22, spec=0.08, rough=0.45)
M_BRAKE = {}
for _n in ("150", "100", "50"):
    M_BRAKE[_n], _ = tex_mat(f"V5_Brake{_n}", f"brake_{_n}.png", emission=0.14, spec=0.08, rough=0.48)


# ---------------------------------------------------------------
# 2c. 赛车漆面 / 碳纤维编织 / 轮胎橡胶 / 刹车盘与独立雨灯精修
# ---------------------------------------------------------------
def _polish_car_materials():
    # 1) 车漆清漆层与金属光泽：深海军蓝金属缎面漆 + 红/黄/银/青清漆层
    _paint_specs = {
        "Mat_RedBull_MatteNavy": dict(color=(0.014, 0.019, 0.036, 1.0), metal=0.28, rough=0.30, coat=0.68, crough=0.055),
        "Mat_RedBull_Crimson": dict(color=(0.78, 0.018, 0.012, 1.0), metal=0.20, rough=0.25, coat=0.88, crough=0.038),
        "Mat_RedBull_SolarYellow": dict(color=(0.92, 0.68, 0.01, 1.0), metal=0.18, rough=0.25, coat=0.88, crough=0.038),
        "Mat_Merc_Petronas": dict(color=(0.0, 0.60, 0.54, 1.0), metal=0.30, rough=0.24, coat=0.82, crough=0.042),
        "Mat_Merc_Silver": dict(color=(0.66, 0.69, 0.74, 1.0), metal=0.90, rough=0.18, coat=0.78, crough=0.040),
    }
    for _mn, _sp in _paint_specs.items():
        _m = bpy.data.materials.get(_mn)
        if _m and _m.node_tree:
            _b = _bsdf(_m)
            if _b:
                _b.inputs['Base Color'].default_value = _sp['color']
                _b.inputs['Metallic'].default_value = _sp['metal']
                _b.inputs['Roughness'].default_value = _sp['rough']
                if 'Coat Weight' in _b.inputs:
                    _b.inputs['Coat Weight'].default_value = _sp['coat']
                    _b.inputs['Coat Roughness'].default_value = _sp['crough']

    # 贴花融入车身清漆层（压低塑料感自发光，防黄昏下过曝发白）
    for _mn in ("Mat_DEC_Engine_RedBull", "Mat_DEC_Halo_Oracle", "Mat_DEC_Nose_Livery", "Mat_DEC_Sidepod_Oracle"):
        _m = bpy.data.materials.get(_mn)
        if _m and _m.node_tree:
            _b = _bsdf(_m)
            if _b:
                _b.inputs['Roughness'].default_value = 0.28
                if 'Coat Weight' in _b.inputs:
                    _b.inputs['Coat Weight'].default_value = 0.62
                    _b.inputs['Coat Roughness'].default_value = 0.055
                if 'Emission Strength' in _b.inputs:
                    _b.inputs['Emission Strength'].default_value = 0.02

    # 2) 碳纤维编织粗糙度对比（前后翼 / 底盘扩散器 / 悬挂 / Halo 导流片）
    for _mn, _rmin, _rmax, _coat in (("Mat_Forged_Carbon", 0.23, 0.47, 0.38),
                                     ("Mat_Carbon_Satin", 0.27, 0.52, 0.30)):
        _m = bpy.data.materials.get(_mn)
        if _m and _m.node_tree:
            _nt = _m.node_tree
            _b = _bsdf(_nt)
            _tcn = next((n for n in _nt.nodes if n.type == 'TEX_COORD'), None)
            _nsn = next((n for n in _nt.nodes if n.type == 'TEX_NOISE'), None)
            _mxn = next((n for n in _nt.nodes if n.type == 'MIX_RGB'), None)
            if _tcn and _nsn and not _nsn.inputs['Vector'].is_linked:
                _nt.links.new(_tcn.outputs['Object'], _nsn.inputs['Vector'])
            if _b and _mxn:
                _mr = _nt.nodes.new('ShaderNodeMapRange')
                _mr.inputs['From Min'].default_value = 0.2
                _mr.inputs['From Max'].default_value = 0.8
                _mr.inputs['To Min'].default_value = _rmin
                _mr.inputs['To Max'].default_value = _rmax
                _nt.links.new(_mxn.outputs['Color'], _mr.inputs['Value'])
                _nt.links.new(_mr.outputs['Result'], _b.inputs['Roughness'])
                if 'Coat Weight' in _b.inputs:
                    _b.inputs['Coat Weight'].default_value = _coat
                    _b.inputs['Coat Roughness'].default_value = 0.11

    for _mn, _r0, _r1 in (("Mat_Carbon_Endplate_Matte", 0.42, 0.66), ("Mat_Duct_Carbon", 0.34, 0.56)):
        _m = bpy.data.materials.get(_mn)
        if _m and _m.node_tree:
            _nt = _m.node_tree
            _b = _bsdf(_nt)
            if _b:
                _tc_c = _nt.nodes.new('ShaderNodeTexCoord')
                _wv_c = _nt.nodes.new('ShaderNodeTexWave')
                _wv_c.inputs['Scale'].default_value = 280.0
                _wv_c.inputs['Distortion'].default_value = 0.8
                _mr_c = _nt.nodes.new('ShaderNodeMapRange')
                _mr_c.inputs['To Min'].default_value = _r0
                _mr_c.inputs['To Max'].default_value = _r1
                _nt.links.new(_tc_c.outputs['Object'], _wv_c.inputs['Vector'])
                _nt.links.new(_wv_c.outputs['Fac'], _mr_c.inputs['Value'])
                _nt.links.new(_mr_c.outputs['Result'], _b.inputs['Roughness'])

    # 3) 轮胎胎面(磨砂热熔咬地) vs 胎壁(深黑半哑硫化橡胶)对比度
    _mtire = bpy.data.materials.get("Mat_Tire_Slick_Compound")
    if _mtire and _mtire.node_tree:
        _tnt = _mtire.node_tree
        _tb = _bsdf(_tnt)
        _ttc = next((n for n in _tnt.nodes if n.type == 'TEX_COORD'), None) or _tnt.nodes.new('ShaderNodeTexCoord')
        if _tb:
            # 局部 |X| < 0.125 为接地胎面，|X| > 0.145 为胎肩/胎壁（GEO_F1_Tire 局部 X 范围 ±0.1746）
            _tsep = _tnt.nodes.new('ShaderNodeSeparateXYZ')
            _tabs = _tnt.nodes.new('ShaderNodeMath')
            _tabs.operation = 'ABSOLUTE'
            _trmp = _tnt.nodes.new('ShaderNodeMapRange')
            _trmp.inputs['From Min'].default_value = 0.115
            _trmp.inputs['From Max'].default_value = 0.158
            _tnt.links.new(_ttc.outputs['Object'], _tsep.inputs['Vector'])
            _tnt.links.new(_tsep.outputs['X'], _tabs.inputs[0])
            _tnt.links.new(_tabs.outputs['Value'], _trmp.inputs['Value'])
            # 胎面略浅灰微亮(0.45)，胎肩更深哑光(0.74)
            _tcol = _tnt.nodes.new('ShaderNodeMixRGB')
            _tcol.inputs['Color1'].default_value = (0.019, 0.019, 0.022, 1.0)
            _tcol.inputs['Color2'].default_value = (0.010, 0.010, 0.012, 1.0)
            _tnt.links.new(_trmp.outputs['Result'], _tcol.inputs['Fac'])
            _tnt.links.new(_tcol.outputs['Color'], _tb.inputs['Base Color'])
            _trgh = _tnt.nodes.new('ShaderNodeMapRange')
            _trgh.inputs['From Min'].default_value = 0.0
            _trgh.inputs['From Max'].default_value = 1.0
            _trgh.inputs['To Min'].default_value = 0.45
            _trgh.inputs['To Max'].default_value = 0.74
            _tnt.links.new(_trmp.outputs['Result'], _trgh.inputs['Value'])
            _tnt.links.new(_trgh.outputs['Result'], _tb.inputs['Roughness'])
            _tb.inputs['Specular IOR Level'].default_value = 0.34

    _msw = bpy.data.materials.get("Mat_PZero_Pirelli_Sidewall")
    if _msw and _msw.node_tree:
        _swb = _bsdf(_msw)
        if _swb:
            _swb.inputs['Roughness'].default_value = 0.68
            _swb.inputs['Specular IOR Level'].default_value = 0.24

    # 4) 碳陶刹车盘径向热辐射环（Mat_BrakeDisc_CarbonCeramic）+ 卡钳金属阳极氧化 + 透明热辉光兼容
    _mdisc = bpy.data.materials.get("Mat_BrakeDisc_CarbonCeramic")
    if _mdisc and _mdisc.node_tree:
        _dnt = _mdisc.node_tree
        _db = _bsdf(_dnt)
        if _db:
            _db.inputs['Base Color'].default_value = (0.095, 0.088, 0.082, 1.0)
            _db.inputs['Metallic'].default_value = 0.55
            _db.inputs['Roughness'].default_value = 0.42
            # 径向摩擦环发光色（盘心暗 -> 钻孔摩擦带樱桃橙红 -> 外沿暗），Emission Strength 留 0.0 供 v5_anim 逐帧驱动
            _dtc = next((n for n in _dnt.nodes if n.type == 'TEX_COORD'), None) or _dnt.nodes.new('ShaderNodeTexCoord')
            _dsub = _dnt.nodes.new('ShaderNodeVectorMath')
            _dsub.operation = 'MULTIPLY'
            _dsub.inputs[1].default_value = (0.0, 1.0, 1.0)     # YZ 平面径向距离（局部半径 0.188 m）
            _dlen = _dnt.nodes.new('ShaderNodeVectorMath')
            _dlen.operation = 'LENGTH'
            _drmp = _dnt.nodes.new('ShaderNodeValToRGB')
            _drmp.color_ramp.interpolation = 'EASE'
            _drmp.color_ramp.elements[0].position = 0.085
            _drmp.color_ramp.elements[0].color = (0.02, 0.002, 0.0, 1.0)
            _de1 = _drmp.color_ramp.elements.new(0.138)
            _de1.color = (1.0, 0.22, 0.024, 1.0)
            _drmp.color_ramp.elements[-1].position = 0.186
            _drmp.color_ramp.elements[-1].color = (0.48, 0.05, 0.006, 1.0)
            _dnt.links.new(_dtc.outputs['Object'], _dsub.inputs[0])
            _dnt.links.new(_dsub.outputs['Vector'], _dlen.inputs[0])
            _dnt.links.new(_dlen.outputs['Value'], _drmp.inputs['Fac'])
            _dnt.links.new(_drmp.outputs['Color'], _db.inputs['Emission Color'])
            _db.inputs['Emission Strength'].default_value = 0.0

    _mcal = bpy.data.materials.get("Mat_Caliper_Anodized")
    if _mcal and _mcal.node_tree:
        _cb2 = _bsdf(_mcal)
        if _cb2:
            _cb2.inputs['Base Color'].default_value = (0.09, 0.095, 0.11, 1.0)
            _cb2.inputs['Metallic'].default_value = 0.88
            _cb2.inputs['Roughness'].default_value = 0.24
            if 'Coat Weight' in _cb2.inputs:
                _cb2.inputs['Coat Weight'].default_value = 0.45
                _cb2.inputs['Coat Roughness'].default_value = 0.06
            _cb2.inputs['Emission Color'].default_value = (1.0, 0.09, 0.012, 1.0)
            _cb2.inputs['Emission Strength'].default_value = 0.0

    # 5) 独立尾部 FIA 雨灯材质（Mat_FIA_RainLight），彻底解除与排气管/方向盘旋钮共用的 Mat_Neon_Orange
    _rl_ob = bpy.data.objects.get("GEO_F1_FIA_RainLight")
    if _rl_ob and hasattr(_rl_ob.data, "materials"):
        _m_fia = bpy.data.materials.get("Mat_FIA_RainLight") or bpy.data.materials.new("Mat_FIA_RainLight")
        _m_fia.use_nodes = True
        _fnt = _m_fia.node_tree
        _fnt.nodes.clear()
        _fb = _fnt.nodes.new("ShaderNodeBsdfPrincipled")
        _fb.inputs['Base Color'].default_value = (0.10, 0.005, 0.005, 1.0)
        _fb.inputs['Roughness'].default_value = 0.20
        if 'Coat Weight' in _fb.inputs:
            _fb.inputs['Coat Weight'].default_value = 0.80
        _fb.inputs['Emission Color'].default_value = (1.0, 0.018, 0.010, 1.0)
        _fb.inputs['Emission Strength'].default_value = 2.4
        _fout = _fnt.nodes.new("ShaderNodeOutputMaterial")
        _fnt.links.new(_fb.outputs['BSDF'], _fout.inputs['Surface'])
        if _rl_ob.data.materials:
            _rl_ob.data.materials[0] = _m_fia
        else:
            _rl_ob.data.materials.append(_m_fia)


_polish_car_materials()

# ---------------------------------------------------------------
# 3. 天空 / 太阳（重做对比度）
# ---------------------------------------------------------------
world = bpy.data.worlds.get("World_V5Dusk") or bpy.data.worlds.new("World_V5Dusk")
scene.world = world
world.use_nodes = True
_nt = world.node_tree
_nt.nodes.clear()
_bg = _nt.nodes.new('ShaderNodeBackground')
_bg.inputs['Color'].default_value = (0.062, 0.084, 0.142, 1)
_bg.inputs['Strength'].default_value = 1.22
_wo = _nt.nodes.new('ShaderNodeOutputWorld')
_nt.links.new(_bg.outputs[0], _wo.inputs[0])

_sl = bpy.data.lights.new("LGT_V5Sun", 'SUN')
_sl.energy = 5.65
_sl.angle = radians(1.4)
_sl.color = (1.0, 0.86, 0.70)
_sl.use_shadow = True
_sun = bpy.data.objects.new("LGT_V5Sun", _sl)
COLL.objects.link(_sun)
# 与天空太阳辉光方位精确对齐：方位 232° → 光从西南低角 22° 入射
_az = radians(232.0)
_sun.rotation_euler = Euler((radians(90.0 - 22.0), 0.0, _az - pi / 2), 'XYZ')
bpy.context.view_layer.update()
_SUN_DIR = (_sun.matrix_world.to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized()

# 冷补光（天空反向，抬暗部与航拍草坪亮度，避免死黑）
_fill = bpy.data.lights.new("LGT_V5SkyFill", 'SUN')
_fill.energy = 0.62
_fill.angle = radians(25.0)
_fill.color = (0.58, 0.72, 1.0)
_fill.use_shadow = False
_fo = bpy.data.objects.new("LGT_V5SkyFill", _fill)
COLL.objects.link(_fo)
_fo.rotation_euler = Euler((radians(52.0), 0.0, _az + pi / 2), 'XYZ')

# ---------------------------------------------------------------
# 3b. 天空穹顶：逐像素连续大气黄昏渐变 + 太阳方位暖色米氏散射辉光（彻底消除色带）
# ---------------------------------------------------------------
_sky_mat = bpy.data.materials.new("V5_SkyDome")
_sky_mat.use_nodes = True
_snt = _sky_mat.node_tree
_snt.nodes.clear()
_sout = _snt.nodes.new('ShaderNodeOutputMaterial')
_sem = _snt.nodes.new('ShaderNodeEmission')
_sem.inputs['Strength'].default_value = 1.0

# 用 Object 坐标归一化得到单位球面方向 d = (dx, dy, dz)，逐像素连续计算仰角与太阳夹角
_stc = _snt.nodes.new('ShaderNodeTexCoord')
_snrm = _snt.nodes.new('ShaderNodeVectorMath')
_snrm.operation = 'NORMALIZE'
_snt.links.new(_stc.outputs['Object'], _snrm.inputs[0])

_ssep_d = _snt.nodes.new('ShaderNodeSeparateXYZ')
_snt.links.new(_snrm.outputs['Vector'], _ssep_d.inputs['Vector'])

# 非线性地平线拉伸：u_elev = clamp((dz + 0.04) / 1.04, 0..1) ^ 0.52，使低仰角过渡极其细腻平滑
_smap_z = _snt.nodes.new('ShaderNodeMapRange')
_smap_z.inputs['From Min'].default_value = -0.04
_smap_z.inputs['From Max'].default_value = 1.00
_smap_z.inputs['To Min'].default_value = 0.0
_smap_z.inputs['To Max'].default_value = 1.0
_snt.links.new(_ssep_d.outputs['Z'], _smap_z.inputs['Value'])

_spow_z = _snt.nodes.new('ShaderNodeMath')
_spow_z.operation = 'POWER'
_spow_z.inputs[1].default_value = 0.55
_snt.links.new(_smap_z.outputs['Result'], _spow_z.inputs[0])

_sramp_sky = _snt.nodes.new('ShaderNodeValToRGB')
_sramp_sky.color_ramp.interpolation = 'B_SPLINE'
_sky_stops = [
    (0.00, (0.032, 0.026, 0.025, 1.0)),
    (0.14, (0.560, 0.285, 0.148, 1.0)),   # 地平线暖金橙
    (0.24, (0.355, 0.195, 0.198, 1.0)),   # 低空玫瑰暮色
    (0.38, (0.145, 0.172, 0.295, 1.0)),   # 暮光紫蓝过渡带
    (0.58, (0.048, 0.088, 0.205, 1.0)),   # 中高空深钴蓝
    (0.80, (0.018, 0.040, 0.118, 1.0)),
    (1.00, (0.008, 0.020, 0.068, 1.0)),   # 天顶深邃夜蓝
]
_sramp_sky.color_ramp.elements[0].position = _sky_stops[0][0]
_sramp_sky.color_ramp.elements[0].color = _sky_stops[0][1]
_sramp_sky.color_ramp.elements[1].position = _sky_stops[-1][0]
_sramp_sky.color_ramp.elements[1].color = _sky_stops[-1][1]
for _pos, _col in _sky_stops[1:-1]:
    _el = _sramp_sky.color_ramp.elements.new(_pos)
    _el.color = _col
_snt.links.new(_spow_z.outputs['Value'], _sramp_sky.inputs['Fac'])

# 太阳方位米氏大气暖色散射辉光：dot_sun = max(0, d · _SUN_DIR)
_sdot = _snt.nodes.new('ShaderNodeVectorMath')
_sdot.operation = 'DOT_PRODUCT'
_sdot.inputs[1].default_value = (_SUN_DIR.x, _SUN_DIR.y, _SUN_DIR.z)
_snt.links.new(_snrm.outputs['Vector'], _sdot.inputs[0])

_sclamp = _snt.nodes.new('ShaderNodeMath')
_sclamp.operation = 'MAXIMUM'
_sclamp.inputs[1].default_value = 0.0
_snt.links.new(_sdot.outputs['Value'], _sclamp.inputs[0])

# 宽广暖霞 (dot^5) + 太阳日冕柔和金辉 (dot^32)，地平线以下平滑遮罩
_spow_wide = _snt.nodes.new('ShaderNodeMath')
_spow_wide.operation = 'POWER'
_spow_wide.inputs[1].default_value = 5.0
_snt.links.new(_sclamp.outputs['Value'], _spow_wide.inputs[0])

_spow_core = _snt.nodes.new('ShaderNodeMath')
_spow_core.operation = 'POWER'
_spow_core.inputs[1].default_value = 32.0
_snt.links.new(_sclamp.outputs['Value'], _spow_core.inputs[0])

_shor_mask = _snt.nodes.new('ShaderNodeMapRange')
_shor_mask.inputs['From Min'].default_value = -0.02
_shor_mask.inputs['From Max'].default_value = 0.06
_snt.links.new(_ssep_d.outputs['Z'], _shor_mask.inputs['Value'])

_sglow_w = _snt.nodes.new('ShaderNodeMath')
_sglow_w.operation = 'MULTIPLY'
_snt.links.new(_spow_wide.outputs['Value'], _sglow_w.inputs[0])
_snt.links.new(_shor_mask.outputs['Result'], _sglow_w.inputs[1])

_sglow_c = _snt.nodes.new('ShaderNodeMath')
_sglow_c.operation = 'MULTIPLY'
_snt.links.new(_spow_core.outputs['Value'], _sglow_c.inputs[0])
_snt.links.new(_shor_mask.outputs['Result'], _sglow_c.inputs[1])

_sadd1 = _snt.nodes.new('ShaderNodeMixRGB')
_sadd1.blend_type = 'ADD'
_sadd1.inputs['Color2'].default_value = (0.34, 0.15, 0.045, 1.0)
_snt.links.new(_sglow_w.outputs['Value'], _sadd1.inputs['Fac'])
_snt.links.new(_sramp_sky.outputs['Color'], _sadd1.inputs['Color1'])

_sadd2 = _snt.nodes.new('ShaderNodeMixRGB')
_sadd2.blend_type = 'ADD'
_sadd2.inputs['Color2'].default_value = (0.58, 0.34, 0.13, 1.0)
_snt.links.new(_sglow_c.outputs['Value'], _sadd2.inputs['Fac'])
_snt.links.new(_sadd1.outputs['Color'], _sadd2.inputs['Color1'])

_snt.links.new(_sadd2.outputs['Color'], _sem.inputs['Color'])
_snt.links.new(_sem.outputs['Emission'], _sout.inputs['Surface'])

_bm = bmesh.new()
try:
    bmesh.ops.create_uvsphere(_bm, u_segments=96, v_segments=64, radius=1.0)
except TypeError:
    bmesh.ops.create_uvsphere(_bm, u_segments=96, v_segments=64, diameter=1.0)
_mesh = bpy.data.meshes.new("V5_SkyDome")
_bm.to_mesh(_mesh)
_bm.free()
for _p_sky in _mesh.polygons:
    _p_sky.use_smooth = True
_ca = _mesh.color_attributes.new(name="Col", type='FLOAT_COLOR', domain='POINT')


def _sky_color_dir(vec):
    d = vec.normalized()
    z = d.z
    u = max(0.0, min(1.0, (z + 0.04) / 1.04)) ** 0.55
    base = _sky_stops[-1][1][:3]
    for _k in range(len(_sky_stops) - 1):
        u0, c0 = _sky_stops[_k]
        u1, c1 = _sky_stops[_k + 1]
        if u0 <= u <= u1:
            f = (u - u0) / max(u1 - u0, 1e-9)
            f = f * f * (3 - 2 * f)
            base = tuple(c0[j] + (c1[j] - c0[j]) * f for j in range(3))
            break
    ds = max(0.0, d.dot(_SUN_DIR))
    hm = max(0.0, min(1.0, (z + 0.02) / 0.08))
    gw, gc = (ds ** 5.0) * hm, (ds ** 32.0) * hm
    return (
        base[0] + 0.34 * gw + 0.58 * gc,
        base[1] + 0.15 * gw + 0.34 * gc,
        base[2] + 0.045 * gw + 0.13 * gc,
    )


for _i, _v in enumerate(_mesh.vertices):
    _r, _g, _b = _sky_color_dir(_v.co)
    _ca.data[_i].color = (_r, _g, _b, 1.0)

_skyob = bpy.data.objects.new("V5_SkyDome", _mesh)
COLL.objects.link(_skyob)
_skyob.location = (_cx, _cy, 0.0)
_skyob.scale = (4200.0, 4200.0, 4200.0)
_skyob.visible_shadow = False
_mesh.materials.append(_sky_mat)

# 4. 地面（z=-0.035 消除高空俯视与 z=0.010 路面的深度精度竞争）
# ---------------------------------------------------------------
GR = 2600.0
mesh_from("V5_Ground", [(_cx - GR, _cy - GR, -0.035), (_cx + GR, _cy - GR, -0.035),
                        (_cx + GR, _cy + GR, -0.035), (_cx - GR, _cy + GR, -0.035)],
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


# 主路面（横向 5 列顶点，写入 OffLine 顶点属性以呈现线外浮尘与橡胶碎粒 marbles）
def _build_main_track():
    cols_off = (-HALF_W, -3.5, 0.0, 3.5, HALF_W)
    nc = len(cols_off)
    tv, tfc, tuv, toff = [], [], [], []
    idxs = list(range(0, N)) + [N]
    for i in idxs:
        p, h, r, k = at(i)
        ro = ROFF[i % N]
        kp = min(1.0, KAPPA[i % N] / 0.012)
        for ci, o in enumerate(cols_off):
            tv.append((p.x + r.x * o, p.y + r.y * o, 0.010))
            tuv.append((ci / float(nc - 1), S[i % N] / 8.0))
            d_rl = abs(o - ro)
            marb = max(0.0, min(1.0, (d_rl - 2.1) / 3.2)) * (0.35 + 0.55 * kp)
            toff.append(marb)
    for j in range(len(idxs) - 1):
        b0 = j * nc
        b1 = (j + 1) * nc
        for ci in range(nc - 1):
            tfc.append((b0 + ci, b0 + ci + 1, b1 + ci + 1, b1 + ci))
    ob = mesh_from("V5_Track", tv, tfc, M_ASPHALT, uvs=tuv, up=True)
    attr = ob.data.attributes.new(name="OffLine", type='FLOAT', domain='POINT')
    for vi, val in enumerate(toff):
        attr.data[vi].value = val
    return ob


_build_main_track()
# 边线（白实线）
ribbon(-HALF_W + 0.05, -HALF_W + 0.20, 0.014, M_WHITE, "V5_Line_L")
ribbon(HALF_W - 0.20, HALF_W - 0.05, 0.014, M_WHITE, "V5_Line_R")


# 赛车线橡胶带（沿 racing_xy，宽 3.4 m）
def _rl(i):
    return ROFF[i % N] - 1.7


def _rr(i):
    return ROFF[i % N] + 1.7


ribbon(_rl, _rr, 0.013, M_RUBBER, "V5_RacingLine", step=1)


# 重刹区轮胎橡胶压痕（Village/Loop、Brooklands/Luffield、Stowe、Vale/Club 等全部重刹点，合并为单个 V5_SkidMarks）
def _build_braking_skids():
    decel = [0.0] * N
    for i in range(1, N - 1):
        dt_loc = max(1e-4, PTS[i + 1]["t"] - PTS[i - 1]["t"])
        acc = (VEL[i + 1] - VEL[i - 1]) / dt_loc
        decel[i] = max(0.0, -acc)
    # 找出减速度 > 8.5 m/s^2 的连续重刹段，前后各外扩 7 点做平滑羽化
    zones, cur = [], None
    for i in range(N):
        if decel[i] > 8.5:
            cur = [i, i] if cur is None else [cur[0], i]
        else:
            if cur and (S[cur[1]] - S[cur[0]] >= 22.0):
                zones.append((max(0, cur[0] - 7), min(N - 1, cur[1] + 7)))
            cur = None
    sv, sfc, suv, sfade = [], [], [], []
    half_skid = 2.05
    for (i0, i1) in zones:
        span = max(1, i1 - i0)
        base = len(sv)
        cnt = 0
        for idx in range(i0, i1 + 1):
            p, h, r, k = at(idx)
            ro = ROFF[idx]
            u_long = (idx - i0) / float(span)
            env = sin(pi * u_long) ** 0.75
            inten = min(1.0, max(0.25, decel[idx] / 42.0)) * env
            for side_u, off in ((0.0, ro - half_skid), (1.0, ro + half_skid)):
                o_clamped = max(-HALF_W + 0.35, min(HALF_W - 0.35, off))
                sv.append((p.x + r.x * o_clamped, p.y + r.y * o_clamped, 0.0136))
                suv.append((side_u, S[idx] / 12.0))
                sfade.append(inten)
            cnt += 1
        for j in range(cnt - 1):
            a = base + j * 2
            sfc.append((a, a + 1, a + 3, a + 2))
    if sfc:
        ob = mesh_from("V5_SkidMarks", sv, sfc, M_SKID, uvs=suv, up=True)
        fa = ob.data.attributes.new(name="SkidFade", type='FLOAT', domain='POINT')
        for vi, val in enumerate(sfade):
            fa.data[vi].value = val
        print("heavy braking skid zones:", len(zones))


_build_braking_skids()

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

# 慢弯与连续弯内侧防切弯香肠路肩（V5_Kerb_Sausage，严格位于内路肩后缘 off=±(7.88..8.32) m，远离 racing_xy >=2.15 m）
_saus = Parts("V5_Kerb_Sausage")
_saus_cnt = 0
for (a, b) in _runs:
    vmin = min(VEL[a:b + 1]) * 3.6
    if vmin < 168.0 and (b - a) >= 10:
        amid = min(range(a, b + 1), key=lambda ii: VEL[ii])
        in_side = -1 if SIGNED_K[amid] > 0 else 1     # 弯内侧（左弯=-right，右弯=+right）
        sa = S[amid]
        for bi_s in range(-3, 4):
            ss = sa + bi_s * 1.35
            p, h, r, _ = at_s(ss)
            c = p + r * (in_side * (HALF_W + 1.06))
            mat_s = M_SAUSAGE_Y if (bi_s % 2 == 0) else M_SAUSAGE_K
            _saus.box((c.x, c.y, 0.095), (1.18, 0.42, 0.085), mat_s, rot_z=h)
        _saus_cnt += 1
_saus.build()
print("inner sausage kerbs:", _saus_cnt)

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

# 防护网立柱（每 12 m 一根薄板柱：沿切线 ±0.07 m 宽 0.14 m，高 3.4 m；全部在一个网格里）
_pv, _pf = [], []
POST_STEP = 12.0
for side in (-1, 1):
    s = 0.0
    while s < LAP_LEN:
        p, h, r, k = at_s(s)
        o = side * (WALL_OFF + 0.35)
        px, py = p.x + r.x * o, p.y + r.y * o
        tx, ty = cos(h), sin(h)                    # 切线方向
        base = len(_pv)
        for d in (-0.07, 0.07):
            _pv.append((px + tx * d, py + ty * d, WALL_H))
            _pv.append((px + tx * d, py + ty * d, WALL_H + 3.4))
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

# 门架（组件 Empty: V5_Gantry，含立柱/横梁/横幅/5 盏发车灯）
GANT_H = 7.2
_gant_parts = []
for sd, nm in ((-1, "L"), (1, "R")):
    px = gp.x + gr.x * sd * (HALF_W + 1.6)
    py = gp.y + gr.y * sd * (HALF_W + 1.6)
    _gant_parts.append(box(f"V5_Gantry_Post_{nm}", (px, py, GANT_H / 2), (0.45, 0.45, GANT_H), M_STEEL, rot_z=gh))
_gant_parts.append(box("V5_Gantry_Beam", (gp.x, gp.y, GANT_H), (HALF_W * 2 + 3.6, 0.55, 0.85), M_STEEL, rot_z=gh))
_gant_parts.append(box("V5_Gantry_Banner", (gp.x - sin(gh) * 0.32, gp.y + cos(gh) * 0.32, GANT_H),
                       (HALF_W * 2 + 2.2, 0.06, 0.6), M_ADPANEL, rot_z=gh))

# 5 盏发车灯（红灯；v5_anim 里把材质发光压到 0 = 常暗）
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
    _gant_parts.append(ob)
assembly("V5_Gantry", (gp.x, gp.y, 0.0), gh, _gant_parts, size=6.0)

# ---------------------------------------------------------------
# 10. 看台（含人群贴图）
# ---------------------------------------------------------------
def grandstand(s_center, side, length, rows=11, dist=30.0, name="Stand"):
    """一座看台 = 一个 Empty(name) + 子物体:
       _Tier{i} 阶梯块 / _Back 后墙 / _VIP 玻璃带 / _Roof 顶棚 / _RoofStrip 灯带 / _Rail 前沿围栏
       _Columns 后支撑柱(合并) / _Trusses 顶棚横向钢梁(合并) / _FrontPosts 前立柱(合并)
       _Flagpoles 旗杆(合并) / _Flags 旗(合并, 多材质)"""
    p, h, r, k = at_s(s_center)
    fwd = Vector((cos(h), sin(h), 0.0))
    out = Vector((r.x, r.y, 0.0)) * side
    row_d = 0.92
    row_h = 0.58
    L = length / 2.0
    parts = []

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
        parts.append(mesh_from(f"{name}_Tier{bi}", v, fc, M_CROWD, uvs=uv, up=False))

    # ---- 后墙 + VIP 玻璃带 ----
    back = dist + rows * row_d
    parts.append(box(name + "_Back", (p.x + out.x * back, p.y + out.y * back, rows * row_h / 2),
                     (length, 0.5, rows * row_h), M_CONC, rot_z=h))
    gz = (rows - 1) * row_h
    parts.append(box(name + "_VIP", (p.x + out.x * (back - 0.3), p.y + out.y * (back - 0.3), gz + 0.9),
                     (length - 4, 0.12, 1.2), M_STRIP, rot_z=h))

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
    parts.append(mesh_from(name + "_Roof", rv, [(0, 1, 3, 2)], M_ROOF, up=False))
    # 顶棚下沿灯带
    lp = p + out * (rf + 0.1)
    parts.append(box(name + "_RoofStrip", (lp.x, lp.y, zf - 0.3), (length * 0.96, 0.10, 0.10), M_STRIP, rot_z=h))
    # 后支撑柱（每 14 m）-> 一个网格
    cols = Parts(name + "_Columns")
    _n = int(length / 14)
    for i in range(_n + 1):
        xs = -L + i * 14.0
        cph = p + out * rb + fwd * xs
        cols.box((cph.x, cph.y, zb / 2), (0.24, 0.24, zb), M_STEEL, rot_z=h)
    parts.append(cols.build())
    # 顶棚横向钢梁（每 8 m 一根，从顶棚前沿斜拉到后沿，贴在顶棚下 0.12 m）-> 一个网格
    trs = Parts(name + "_Trusses")
    _m = int(length / 8)
    for i in range(_m + 1):
        xs = -L + i * 8.0
        bf = p + out * rf + fwd * xs
        bb = p + out * rb + fwd * xs
        trs.beam((bf.x, bf.y, zf - 0.12), (bb.x, bb.y, zb - 0.12), fwd, 0.16, 0.16, M_STEEL)
    parts.append(trs.build())

    # ---- 前立柱 + 前沿围栏 ----
    fps = Parts(name + "_FrontPosts")
    for sd in (-1, 1):
        cp = p + out * (dist + 0.4) + fwd * (L * sd * 0.92)
        fps.box((cp.x, cp.y, zf / 2), (0.28, 0.28, zf), M_STEEL, rot_z=h)
    parts.append(fps.build())
    rail = p + out * (dist - 1.5)
    parts.append(box(name + "_Rail", (rail.x, rail.y, 0.55), (length, 0.06, 0.06), M_STEEL, rot_z=h))
    # 旗杆 + 旗（沿前沿，每 40 m）-> 旗杆一个网格、旗一个网格（多材质）
    poles = Parts(name + "_Flagpoles")
    flags = Parts(name + "_Flags")
    _n = int(length / 40)
    for i in range(_n + 1):
        xs = -L + i * 40.0
        fp = p + out * (dist - 2.2) + fwd * xs
        poles.box((fp.x, fp.y, 3.0), (0.08, 0.08, 6.0), M_STEEL, rot_z=h)
        col = random.choice(M_FLAGS)
        fv = [(fp.x, fp.y, 6.0),
              (fp.x + out.x * 1.5, fp.y + out.y * 1.5, 5.65),
              (fp.x, fp.y, 5.3)]
        flags.poly(fv, [(0, 1, 2)], col)
    parts.append(poles.build())
    parts.append(flags.build())

    # ---- 组件 Empty：放在看台占地中心（地面），X 轴沿赛道 ----
    mid = p + out * ((dist - 2.2 + rb) / 2.0)
    assembly(name, (mid.x, mid.y, 0.0), h, parts, size=8.0)
    return name


STANDS = [
    (120.0, 1, 150.0, 13, 26.0, "V5_Stand_Main"),
    (1120.0, -1, 90.0, 11, 32.0, "V5_Stand_T1"),
    (2600.0, 1, 104.0, 12, 32.0, "V5_Stand_Mid"),
    (3540.0, -1, 96.0, 12, 42.0, "V5_Stand_Complex"),   # 退后至 dist=42m 彻底避开 Copse/Maggotts 弯道与追拍机位
    (4370.0, 1, 95.0, 11, 34.0, "V5_Stand_South"),
    (5560.0, -1, 96.0, 11, 32.0, "V5_Stand_Club"),
]
# 修复 0..255 整数导致 255 倍过曝 bug：使用物理合理的线性反照率浮点色值
M_FLAGS = [new_mat(f"V5_Flag_{i}", c, 0.62, 0.0)
           for i, c in enumerate(((0.50, 0.035, 0.035), (0.025, 0.095, 0.52), (0.58, 0.58, 0.56),
                                  (0.65, 0.28, 0.012), (0.025, 0.28, 0.14)))]
random.seed(11)                     # 旗色可复现
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
# ④ pit box 划线：每 6 m 一条横向白线（garage 分格）-> 全部在一个网格 V5_PitBoxLines
_bk = 0
_s = PIT_S0 + 3.0
_pbl = Parts("V5_PitBoxLines")
while _s < PIT_S1 - 1.0:
    p, h, r, k = at_s(_s)
    fwd = Vector((cos(h), sin(h), 0.0))
    v = []
    for (o, sd) in ((PIT_WALL, -1), (PIT_WALL, 1), (PIT_LANE, 1), (PIT_LANE, -1)):
        c = p + r * o + fwd * sd * 0.06
        v.append((c.x, c.y, 0.015))
    _pbl.poly(v, [(0, 1, 2, 3)], M_WHITE)
    _bk += 1
    _s += 6.0
_pbl.build(up=True)
print("pit box lines:", _bk)
# ⑤ garage 楼体（混凝土）+ 正面高精度 6 车位循环贴图面板（每 36 m 循环 6 座车库，与 6 m 车位线一一对齐）
_c = _p + _pit_out * ((abs(PIT_FACE) + abs(PIT_BACK)) / 2)
_dep = abs(PIT_BACK - PIT_FACE)
box("V5_PitGarage", (_c.x, _c.y, GAR_H / 2), (PIT_LEN, _dep, GAR_H), M_CONC, rot_z=_h)
wall_uv(PIT_S0, PIT_S1, PIT_FACE + 0.04, 0.0, GAR_H, M_GARAGE, "V5_PitGarageFront", u_repeat=36.0, v_repeat=1.0)
# ⑥ garage 楼顶竖向赞助灯箱横幅（面向赛道，48 m 循环 4 幅赞助商图）
wall_uv(PIT_S0, PIT_S1, PIT_FACE + 0.25, GAR_H, GAR_H + 1.18, M_AD, "V5_PitRoofBanner", u_repeat=48.0, v_repeat=1.0)
# ⑦ garage 楼顶主看台（4 排小阶梯，用人群贴图）
for _rr in range(4):
    _o0 = PIT_BACK - 1.5 + _rr * 1.2
    _o1 = _o0 + 1.2
    _z = GAR_H + 0.06 + _rr * 0.55
    strip_uv(PIT_S0, PIT_S1, _o0, _o1, _z, M_CROWD, f"V5_PitTopTier_{_rr}", u_repeat=12.0, up=True)
# 楼顶围栏（发光细条）
strip_uv(PIT_S0, PIT_S1, PIT_BACK + 0.3, PIT_BACK + 0.5, GAR_H + 2.4, M_STRIP, "V5_PitTopRail", PIT_LEN)

# ⑧ 维修墙指挥台（Pit-Wall Timing Stand，两座工程师遥测雨棚合并为 V5_PitWallTiming 组件）
def _build_pit_wall_timing():
    tw_frame = Parts("V5_PitWallTiming_Frame")
    tw_glass = Parts("V5_PitWallTiming_Glass")
    tw_parts = []
    for idx_t, s_tw in enumerate((165.0, 295.0)):
        ptw, htw, rtw, _ = at_s(s_tw)
        fwd_tw = Vector((cos(htw), sin(htw), 0.0))
        base_tw = ptw + rtw * (PIT_WALL - 0.55)
        # 钢结构支撑立柱与悬挑遮阳顶棚
        for dx in (-4.8, 0.0, 4.8):
            c_post = base_tw + fwd_tw * dx
            tw_frame.box((c_post.x, c_post.y, 1.95), (0.14, 0.14, 1.80), M_STEEL, rot_z=htw)
        c_roof = ptw + rtw * (PIT_WALL - 0.30)
        tw_frame.box((c_roof.x, c_roof.y, 2.92), (10.8, 1.65, 0.12), M_ROOF, rot_z=htw)
        tw_frame.box((c_roof.x, c_roof.y, 1.32), (10.2, 0.72, 0.08), M_STEEL, rot_z=htw)
        # 面向赛道的防风玻璃隔断
        c_gl = ptw + rtw * (PIT_WALL + 0.02)
        tw_glass.box((c_gl.x, c_gl.y, 1.95), (10.2, 0.05, 1.55), M_PIT_GLASS, rot_z=htw)
        # 多联遥测显示屏（带正立 UV）
        c_mon = ptw + rtw * (PIT_WALL - 0.36)
        tw_parts.append(panel_box(f"V5_PitWallTiming_Screens_{idx_t}",
                                  (c_mon.x, c_mon.y, 1.68), (8.6, 0.08, 0.58),
                                  M_SCREEN, rot_z=htw, edge_mat=M_STEEL))
    tw_parts.extend([tw_frame.build(), tw_glass.build()])
    p_mid, h_mid, r_mid, _ = at_s(230.0)
    b_mid = p_mid + r_mid * PIT_WALL
    assembly("V5_PitWallTiming", (b_mid.x, b_mid.y, 0.0), h_mid, tw_parts, size=4.0)


_build_pit_wall_timing()

# ⑨ 维修区出口绿色放行信号灯柱（Pit Exit Green LED Light Post，位于维修墙末端 s=424 m）
def _build_pit_exit_signal():
    px_p, px_h, px_r, _ = at_s(PIT_S1 + 4.0)
    base_px = px_p + px_r * PIT_WALL
    sig_post = Parts("V5_PitExitSignal_Post")
    sig_post.box((base_px.x, base_px.y, 2.15), (0.16, 0.16, 2.20), M_STEEL, rot_z=px_h)
    arm_c = px_p + px_r * (PIT_WALL - 0.55)
    sig_post.box((arm_c.x, arm_c.y, 3.18), (0.14, 1.25, 0.14), M_STEEL, rot_z=px_h)
    head_c = px_p + px_r * (PIT_WALL - 0.95)
    sig_post.box((head_c.x, head_c.y, 2.86), (0.28, 0.46, 0.78), M_BARRIER, rot_z=px_h)
    leds = Parts("V5_PitExitSignal_LEDs")
    fwd_px = Vector((cos(px_h), sin(px_h), 0.0))
    for dz in (2.68, 3.04):
        lc = head_c - fwd_px * 0.15
        leds.box((lc.x, lc.y, dz), (0.04, 0.28, 0.24), M_PIT_GREEN, rot_z=px_h)
    assembly("V5_PitExitSignal", (base_px.x, base_px.y, 0.0), px_h,
             [sig_post.build(), leds.build()], size=2.5)


_build_pit_exit_signal()


# ---------------------------------------------------------------
# 11b. 赛道道具：广告板 / 刹车牌 / DRS 标记牌 / 弯心防切柱 / 大屏 / 天桥 / 裁判点
# ---------------------------------------------------------------
def ad_board(s, side, idx=0, w=11.0, hgt=3.6, off=WALL_OFF + 2.5, name=""):
    p, h, r, k = at_s(s)
    base = p + r * (side * off)
    slot = idx % 4
    panel_box(name, (base.x, base.y, 1.0 + hgt / 2), (w, 0.14, hgt),
              M_AD, rot_z=h, u_range=(slot * 0.25, (slot + 1) * 0.25), edge_mat=M_STEEL)


def brake_board(s, side, num, poles, off=HALF_W + 2.9, name=""):
    """一块正对来车方向的刹车距离牌（rot_z = h + pi/2）；双立柱合入 poles。"""
    p, h, r, k = at_s(s)
    base = p + r * (side * off)
    rz = h + pi / 2.0 - side * radians(10.0)
    ob = panel_box(name, (base.x, base.y, 1.08), (1.08, 0.08, 0.72),
                   M_BRAKE[num], rot_z=rz, edge_mat=M_STEEL)
    rx, ry = cos(rz), sin(rz)
    for d in (-0.34, 0.34):
        poles.box((base.x + rx * d, base.y + ry * d, 0.54), (0.05, 0.05, 1.08), M_STEEL, rot_z=rz)
    return ob, base, h


def drs_board(s, side, off=HALF_W + 2.9, name="V5_DRS"):
    """FIA 绿色 DRS 激活区标志牌（正对来车方向，置于大直道入口外侧）"""
    p, h, r, k = at_s(s)
    base = p + r * (side * off)
    rz = h + pi / 2.0 - side * radians(10.0)
    bd = panel_box(name + "_Board", (base.x, base.y, 1.15), (1.16, 0.08, 0.76),
                   M_DRS, rot_z=rz, edge_mat=M_STEEL)
    poles = Parts(name + "_Poles")
    rx, ry = cos(rz), sin(rz)
    for d in (-0.36, 0.36):
        poles.box((base.x + rx * d, base.y + ry * d, 0.58), (0.05, 0.05, 1.16), M_STEEL, rot_z=rz)
    assembly(name, (base.x, base.y, 0.0), h, [bd, poles.build()], size=2.5)


def bigscreen(s, side, off=WALL_OFF + 8.0, w=22.0, hgt=9.0, name="V5_Screen"):
    """组件 Empty(name) + _Panel 16:9 广播级大屏（带完整 UV）+ _Legs 支撑钢柱"""
    p, h, r, k = at_s(s)
    base = p + r * (side * off)
    panel = panel_box(name + "_Panel", (base.x, base.y, 5.5), (w, 0.45, hgt),
                      M_SCREEN, rot_z=h, u_range=(0.0, 1.0), edge_mat=M_STEEL)
    legs = Parts(name + "_Legs")
    for dx in (-w / 2 + 0.5, w / 2 - 0.5):
        legs.box((base.x + cos(h) * dx, base.y + sin(h) * dx, 2.0), (0.5, 0.5, 4.0), M_STEEL, rot_z=h)
    assembly(name, (base.x, base.y, 0.0), h, [panel, legs.build()], size=5.0)


def footbridge(s, name="V5_Bridge"):
    """组件 Empty(name) + _Deck 桥面 + _Piers 两座桥墩（外扩至 ±16.5 m 避让长焦视线）+ _Rails 栏杆"""
    p, h, r, k = at_s(s)
    fwd = Vector((cos(h), sin(h), 0.0))
    off = HALF_W + 9.5
    a = p - r * off - fwd * 2.25
    b = p + r * off - fwd * 2.25
    c = p + r * off + fwd * 2.25
    d = p - r * off + fwd * 2.25
    v = [(a.x, a.y, 6.2), (b.x, b.y, 6.2), (c.x, c.y, 6.2), (d.x, d.y, 6.2),
         (a.x, a.y, 5.6), (b.x, b.y, 5.6), (c.x, c.y, 5.6), (d.x, d.y, 5.6)]
    fc = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 4, 5, 1), (1, 5, 6, 2),
          (2, 6, 7, 3), (3, 7, 4, 0)]
    deck = mesh_from(name + "_Deck", v, fc, M_STEEL, up=False)
    piers = Parts(name + "_Piers")
    for sd in (-1, 1):
        bp = p + r * (sd * off)
        piers.box((bp.x, bp.y, 2.9), (0.6, 0.6, 5.8), M_CONC)
    rails = Parts(name + "_Rails")
    for sd in (-1, 1):
        rr = fwd * (2.25 * sd)
        mid = p + rr
        rails.box((mid.x, mid.y, 6.7), (0.1, off * 2, 0.1), M_STRIP, rot_z=h)
    assembly(name, (p.x, p.y, 0.0), h, [deck, piers.build(), rails.build()], size=5.0)


# ① 广告板：沿整圈每 60 m 一块（跳过维修区主直道段，并在 Stowe 长焦段改放外侧以免遮挡弦向视线）
_ad_i = 0
_s = 30.0
while _s < LAP_LEN - 5:
    side = 1 if _ad_i % 2 == 0 else -1
    if 4450.0 < _s < 4760.0 and side == -1:
        side = 1
    if not (PIT_S0 - 10 < _s < PIT_S1 + 10):
        ad_board(_s, side, idx=_ad_i, name=f"V5_Ad_{_ad_i}")
        _ad_i += 1
    _s += 60.0
print("ad boards:", _ad_i)

# ② 刹车距离牌：4 处典型重刹弯外侧（Village/Loop、Brooklands/Luffield、Stowe、Vale/Club），弯前 150/100/50 m
_BRAKE_CORNERS = [
    (1282.0, -1),   # Village / Loop 外侧（左弯外侧为右侧，避开内侧发夹弯固定机位 S04）
    (2537.0, -1),   # Brooklands / Luffield 外侧
    (4700.0, 1),    # Stowe 外侧（左草地侧，与 S20_StoweTele 无遮挡）
    (5325.0, 1),    # Vale / Club 重刹外侧
]
for _bi, (apex_s, b_side) in enumerate(_BRAKE_CORNERS):
    _poles = Parts(f"V5_Brake_{_bi}_Poles")
    _boards, _bases, _hs = [], [], []
    for dist_, num in ((150, "150"), (100, "100"), (50, "50")):
        _ob, _bs, _hh = brake_board(apex_s - dist_, b_side, num, _poles, name=f"V5_Brake_{_bi}_{num}")
        _boards.append(_ob)
        _bases.append(_bs)
        _hs.append(_hh)
    _ctr = Vector(((min(b.x for b in _bases) + max(b.x for b in _bases)) / 2,
                   (min(b.y for b in _bases) + max(b.y for b in _bases)) / 2, 0.0))
    assembly(f"V5_Brake_{_bi}", (_ctr.x, _ctr.y, 0.0), _hs[1], _boards + [_poles.build()], size=3.0)
print("brake boards:", len(_BRAKE_CORNERS) * 3)

# ②b DRS 激活区标志牌：Wellington 大直道入口与 Hangar 大直道入口（S19 车载可见）
drs_board(1635.0, -1, name="V5_DRS_Wellington")
drs_board(4265.0, -1, name="V5_DRS_Hangar")
print("DRS marker boards: 2")

# ②c 慢弯/连续弯内侧弹性防切弯立柱（Apex Bollards，位于内侧香肠路肩后方 off=±8.85 m，绝不侵入 racing_xy）
_bollards = Parts("V5_ApexBollards")
_bol_cnt = 0
for (a, b) in _runs:
    vmin = min(VEL[a:b + 1]) * 3.6
    if vmin < 145.0 and (b - a) >= 12:
        amid = min(range(a, b + 1), key=lambda ii: VEL[ii])
        in_side = -1 if SIGNED_K[amid] > 0 else 1
        p_ap, h_ap, r_ap, _ = at(amid)
        bp_ap = p_ap + r_ap * (in_side * (HALF_W + KERB_IN_W + 0.50))
        _bollards.box((bp_ap.x, bp_ap.y, 0.04), (0.28, 0.28, 0.08), M_SAUSAGE_K, rot_z=h_ap)
        _bollards.box((bp_ap.x, bp_ap.y, 0.40), (0.14, 0.14, 0.68), M_BOLLARD, rot_z=h_ap)
        _bollards.box((bp_ap.x, bp_ap.y, 0.56), (0.148, 0.148, 0.14), M_WHITE, rot_z=h_ap)
        _bol_cnt += 1
_bollards.build()
print("apex bollards:", _bol_cnt)

# ③ 大屏：维修区出口内侧 + 赛道中段（避开车库楼遮挡）
bigscreen(560.0, -1, name="V5_Screen_A")
bigscreen(2600.0, -1, name="V5_Screen_B")

# ④ 人行天桥：两条直道（Bridge_B 移至 s=3320 m 直道中段，彻底避开 S13 长焦桥墩与 S14 直升机俯冲航线）
footbridge(950.0, "V5_Bridge_A")
footbridge(3320.0, "V5_Bridge_B")

# ⑤ 裁判点小棚（沿赛道每 ~830 m 一个）；每个一个 Empty V5_Marshal_{i}
for i in range(7):
    sp = LAP_LEN * i / 7.0
    p, h, r, k = at_s(sp)
    side = 1 if i % 2 == 0 else -1
    bp = p + r * (side * (HALF_W + 5.0))
    _hut = box(f"V5_Marshal_{i}_Hut", (bp.x, bp.y, 0.7), (1.6, 1.1, 1.4), M_CONC, rot_z=h)
    _lamp = box(f"V5_Marshal_{i}_Lamp", (bp.x, bp.y, 1.55), (0.25, 0.25, 0.12), M_STRIP, rot_z=h)
    assembly(f"V5_Marshal_{i}", (bp.x, bp.y, 0.0), h, [_hut, _lamp], size=2.0)
print("marshal posts:", 7)


# ---------------------------------------------------------------
# 12. 场地外围：机库 / 树线 / 灯柱（带严格赛道安全净距拒绝采样）
# ---------------------------------------------------------------
def _min_track_dist(x, y, step=6):
    return min(hypot(x - XY[k].x, y - XY[k].y) for k in range(0, N, step))


random.seed(23)
for i in range(6):
    w = random.uniform(42, 86)
    d = random.uniform(30, 58)
    hgt = random.uniform(9, 17)
    half_diag = 0.5 * hypot(w, d)
    # 拒绝采样直至建筑外边缘距任意赛道中心线点 >= 220 m（修复 Hangar_5 横穿赛道问题）
    for _try in range(200):
        a = random.uniform(0, 2 * pi)
        rad = random.uniform(1180, 1520)
        bx = _cx + cos(a) * rad
        by = _cy + sin(a) * rad
        if _min_track_dist(bx, by) - half_diag >= 220.0:
            break
    box(f"V5_Hangar_{i}", (bx, by, hgt / 2), (w, d, hgt), M_HANGAR, rot_z=random.uniform(0, pi))

# 场地边界：低矮灌篱（基底半径提升至 >=1520 m 并强制距赛道外侧 >=280 m，彻底杜绝横切赛道）
_tree_mat = new_mat("V5_Tree", (0.018, 0.034, 0.015), 0.9)
_tv, _tf = [], []
_hedge_v = []
for i in range(241):
    a = 2 * pi * (i % 240) / 240.0
    rad = 1540.0 + 150.0 * sin(a * 2.3 + 0.7) + 65.0 * sin(a * 5.1)
    bx = _cx + cos(a) * rad
    by = _cy + sin(a) * rad
    d_tr = _min_track_dist(bx, by)
    if d_tr < 280.0:
        rad += (285.0 - d_tr)
        bx = _cx + cos(a) * rad
        by = _cy + sin(a) * rad
    hgt = 2.4 + 1.6 * (0.5 + 0.5 * sin(a * 7.0))
    _hedge_v.append((bx, by, hgt))
for i in range(240):
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
    _lf += [(base + 0, base + 1, base + 5, base + 4), (base + 1, base + 2, base + 6, base + 5),
            (base + 2, base + 3, base + 7, base + 6), (base + 3, base + 0, base + 4, base + 7)]
    hb = len(_lv)
    _lv += [(px - 0.9, py - 0.25, 15.6), (px + 0.9, py - 0.25, 15.6),
            (px + 0.9, py + 0.25, 15.6), (px - 0.9, py + 0.25, 15.6)]
    _lf += [(hb, hb + 1, hb + 2, hb + 3)]
mesh_from("V5_FieldMasts", _lv, _lf, M_STEEL, up=False)

print("ENV BUILD DONE")
print("objects:", len(bpy.data.objects), "materials:", len(bpy.data.materials))


# ---------------------------------------------------------------
# 13. 工程整理：原点归位 + 组件 Empty 父子 + 集合分组 + 根集合与孤立块清理
# ---------------------------------------------------------------
_GROUPS = {
    "V5_01_Road": ("V5_Track", "V5_RacingLine", "V5_Skid", "V5_BrakeZone",
                   "V5_Line_", "V5_Kerb_", "V5_StartLine",
                   "V5_PitLane", "V5_PitLine", "V5_PitBoxLine"),
    "V5_02_Terrain": ("V5_Ground", "V5_Verge_", "V5_Gravel_", "V5_HedgeRing", "V5_SkyDome"),
    "V5_03_Barriers": ("V5_Barrier", "V5_FencePosts"),
    "V5_04_Stands": ("V5_Stand_",),
    "V5_05_Pit": ("V5_PitWall", "V5_PitExit", "V5_PitGarage", "V5_PitRoof", "V5_PitTop"),
    "V5_06_Props": ("V5_Ad_", "V5_Brake_", "V5_DRS_", "V5_ApexBollards",
                    "V5_Screen_", "V5_Bridge_", "V5_Marshal_", "V5_FieldMasts",
                    "V5_Hangar_", "V5_Gantry", "V5_StartLight"),
    "V5_07_Lighting": ("LGT_V5",),
}

# 13a. 原点归位：只处理"网格烘焙在世界坐标里"的对象
bpy.context.view_layer.update()
_moved = 0
_I4 = Matrix.Identity(4)
for _ob in list(bpy.data.objects):
    if _ob.type != 'MESH' or not _ob.name.startswith("V5_") or _ob.parent is not None:
        continue
    if not _ob.data.vertices:
        continue
    _mb = _ob.matrix_basis
    if any(abs(_mb[i][j] - _I4[i][j]) > 1e-9 for i in range(4) for j in range(4)):
        continue
    _xs = [_v.co.x for _v in _ob.data.vertices]
    _ys = [_v.co.y for _v in _ob.data.vertices]
    _zs = [_v.co.z for _v in _ob.data.vertices]
    _c = Vector(((min(_xs) + max(_xs)) / 2, (min(_ys) + max(_ys)) / 2, (min(_zs) + max(_zs)) / 2))
    _ob.data.transform(Matrix.Translation(-_c))
    _ob.data.update()
    _ob.location = _c
    _moved += 1
bpy.context.view_layer.update()

# 13b. 组件 Empty 父子（保持世界变换）
_parented = 0
for _em, _parts in ASSEMBLIES:
    _inv = _em.matrix_basis.inverted()
    for _ob in _parts:
        _mw = _ob.matrix_basis.copy()
        _ob.parent = _em
        _ob.matrix_parent_inverse = Matrix.Identity(4)
        _ob.matrix_basis = _inv @ _mw
        _parented += 1
bpy.context.view_layer.update()
print("assemblies: %d empties, %d parented parts" % (len(ASSEMBLIES), _parented))

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

# 把 RIG_F1_Race 归入 SCIFI_F1_2035，确保根 Scene Collection 零散落对象
_rig_ob = bpy.data.objects.get("RIG_F1_Race")
_scifi = bpy.data.collections.get("SCIFI_F1_2035")
if _rig_ob and _scifi:
    if _rig_ob.name not in _scifi.objects:
        _scifi.objects.link(_rig_ob)
    if _rig_ob.name in _root.objects:
        _root.objects.unlink(_rig_ob)

print("organize: origin_to_geometry=%d  regrouped=%d  root_objs=%d"
      % (_moved, _reg, len(_root.objects)))

# 13c. 清掉空的杂乱集合与全部孤立网格/材质/贴图数据块
_dropped = []
for _c in list(bpy.data.collections):
    if (_c.name == "09_Studio_Stage_Rig" or _c.name.startswith("WheelSpokes_")) \
            and len(_c.all_objects) == 0 and len(_c.children) == 0:
        _dropped.append(_c.name)
        bpy.data.collections.remove(_c)

try:
    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
except Exception:
    for _datablock in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.lights):
        for _item in list(_datablock):
            if _item.users == 0:
                _datablock.remove(_item)

print("removed empty collections:", _dropped)
print("FINAL objects:", len(bpy.data.objects),
      "| V5 meshes:", sum(1 for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith("V5_")),
      "| empties:", sum(1 for o in bpy.data.objects if o.type == 'EMPTY'),
      "| orphan_meshes:", sum(1 for m in bpy.data.meshes if m.users == 0),
      "| orphan_mats:", sum(1 for m in bpy.data.materials if m.users == 0))

bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("ENV SAVED:", OUT)
