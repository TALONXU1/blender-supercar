# -*- coding: utf-8 -*-
"""
V6 SPIDER-VERSE 3D MEGA-CIRCUIT ENVIRONMENT, LOOKDEV & 3D ACTION FX BUILDER
Circuit : Neo-Monaco x Nueva York 2099 Sky-Harbor (track_data/spiderverse_circuit.json)
Input   : pipeline/v4_stage_rig.blend (READ-ONLY, 100% V5-isolated)
Output  : v6_spiderverse/v6_stage_lookdev.blend
Preview : blender -b -P pipeline/v6_sv_env.py -- --preview
"""
import bpy
import bmesh
import json
import math
import os
import random
import sys
import time
from math import sin, cos, pi, radians, hypot
from mathutils import Vector, Matrix, Euler

PROJ = r"D:\项目session\blender-supercar"
IN_RIG = os.path.join(PROJ, "pipeline", "v4_stage_rig.blend")
TRACK_JSON = os.path.join(PROJ, "track_data", "spiderverse_circuit.json")
OUT_DIR = os.path.join(PROJ, "v6_spiderverse")
TEX_SV = os.path.join(OUT_DIR, "textures")
OUT_BLEND = os.path.join(OUT_DIR, "v6_stage_lookdev.blend")
PREV_DIR = os.path.join(PROJ, "renders_v6", "preview")

os.makedirs(OUT_DIR, exist_ok=True)
ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

t_start = time.time()
bpy.ops.wm.open_mainfile(filepath=IN_RIG)
scene = bpy.context.scene

# ---------------------------------------------------------------
# 0. 读取 3D 赛道数据包 & 构建精确向心倾角正交标架 (right, fwd, up)
# ---------------------------------------------------------------
tdata = json.load(open(TRACK_JSON, encoding="utf-8"))
META = tdata["meta"]
PTS = tdata["points"]
N = len(PTS)
HALF_W = float(META.get("track_half_width_m", 7.0))
STEP_M = float(META.get("sample_step_m", 2.0))
LAP_LEN = float(PTS[-1]["s"]) + STEP_M

# 严格对齐 @track (#32) 的 3D 倾角丝带正交基 (T, R, U)：
# P_race_3d == C_3d - racing_offset_m * R，确保与 @anim 轮胎接触零误差 (0.000 m)！
FRAMES = []
_max_race_err = 0.0
for i, pt in enumerate(PTS):
    pos = Vector((pt["xy"][0], pt["xy"][1], pt["z"]))
    rpos = Vector((pt["racing_xy"][0], pt["racing_xy"][1], pt.get("racing_z", pt["z"])))
    h = radians(pt["heading_deg"])
    p = radians(pt.get("pitch_deg", 0.0))
    bk = radians(pt.get("bank_deg", 0.0))
    curv = float(pt.get("curv_1pm", 0.0))
    roff = float(pt.get("racing_offset_m", 0.0))

    fwd = Vector((cos(p) * cos(h), cos(p) * sin(h), sin(p))).normalized()
    right0 = Vector((sin(h), -cos(h), 0.0)).normalized()
    up0 = Vector((-sin(p) * cos(h), -sin(p) * sin(h), cos(p))).normalized()
    right = (cos(bk) * right0 - sin(bk) * up0).normalized()
    up = (sin(bk) * right0 + cos(bk) * up0).normalized()

    p_check = pos - right * roff
    _max_race_err = max(_max_race_err, (p_check - rpos).length)

    FRAMES.append(dict(
        s=float(pt["s"]), pos=pos, rpos=rpos, roff=roff,
        h=h, p=p, b_eff=bk, curv=curv, v=float(pt["v_mps"]), t=float(pt["t"]),
        zone=pt.get("zone", ""), tunnel=bool(pt.get("tunnel", False)), bridge=bool(pt.get("bridge", False)),
        fwd=fwd, right=right, up=up,
    ))
_peak_i = max(range(N), key=lambda k: abs(FRAMES[k]["b_eff"]))
print(f"Loaded {N} 3D circuit pts ({LAP_LEN:.1f} m) | max |P_race - rpos| = {_max_race_err * 1000.0:.4f} mm | peak bank idx={_peak_i} ({math.degrees(FRAMES[_peak_i]['b_eff']):.2f} deg)")


def frame_at(idx):
    return FRAMES[idx % N]


def frame_at_s(s_val):
    s_val %= LAP_LEN
    lo, hi = 0, N - 1
    while hi - lo > 1:
        m = (lo + hi) // 2
        if FRAMES[m]["s"] <= s_val:
            lo = m
        else:
            hi = m
    return FRAMES[lo]


# ---------------------------------------------------------------
# 1. 集合结构与网格合并工具（0 根集合散落对象）
# ---------------------------------------------------------------
COLLS = {}
for cname in (
    "V6_01_Track3D",
    "V6_02_Megacity",
    "V6_03_SkyBridge_Bowl",
    "V6_04_StrobeTunnel_Harbor",
    "V6_05_Atmosphere_GodRays",
    "V6_07_Lighting",
    "V6_09_ComicFX",
):
    c = bpy.data.collections.get(cname) or bpy.data.collections.new(cname)
    if c.name not in scene.collection.children:
        scene.collection.children.link(c)
    COLLS[cname] = c

# 整理 V4 遗留空集合并将 RIG_F1_Race 收入 SCIFI_F1_2035
for _c in list(bpy.data.collections):
    if (_c.name == "09_Studio_Stage_Rig" or _c.name.startswith("WheelSpokes_")) and len(_c.all_objects) == 0 and len(_c.children) == 0:
        bpy.data.collections.remove(_c)
rig = bpy.data.objects["RIG_F1_Race"]
_scifi = bpy.data.collections.get("SCIFI_F1_2035")
if _scifi:
    if rig.name not in _scifi.objects:
        _scifi.objects.link(rig)
    if rig.name in scene.collection.objects:
        scene.collection.objects.unlink(rig)

_CUBE_FACES = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
_QUAD_UVS = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]


class BatchMesh:
    """高密度场景合批器：把成百上千座摩天楼/斜拉索/隧道灯肋烘焙为极少量多材质带 UV 网格，保持渲染极速！"""
    def __init__(self, name, coll_name):
        self.name = name
        self.coll = COLLS[coll_name]
        self.v, self.f, self.fm, self.fuv, self.mats = [], [], [], [], []

    def _mi(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def add_oriented_box(self, center, ax_x, ax_y, ax_z, sx, sy, sz, mat, uv_tile=(1.0, 1.0), uv_off=(0.0, 0.0)):
        mi = self._mi(mat)
        base = len(self.v)
        hx, hy, hz = sx * 0.5, sy * 0.5, sz * 0.5
        for s_z in (-1.0, 1.0):
            for s_x, s_y in ((-1.0, -1.0), (1.0, -1.0), (1.0, 1.0), (-1.0, 1.0)):
                p = center + ax_x * (s_x * hx) + ax_y * (s_y * hy) + ax_z * (s_z * hz)
                self.v.append((p.x, p.y, p.z))
        u0, v0 = uv_off
        tu, tv = uv_tile
        side_uv = [(u0, v0), (u0 + tu, v0), (u0 + tu, v0 + tv), (u0, v0 + tv)]
        for fi, fc in enumerate(_CUBE_FACES):
            self.f.append(tuple(base + k for k in fc))
            self.fm.append(mi)
            self.fuv.append(side_uv if fi >= 2 else _QUAD_UVS)

    def add_beam(self, p0, p1, radius, mat):
        d = p1 - p0
        ln = d.length
        if ln < 1e-4:
            return
        ax_z = d / ln
        ref = Vector((0.0, 0.0, 1.0)) if abs(ax_z.z) < 0.92 else Vector((1.0, 0.0, 0.0))
        ax_x = ref.cross(ax_z).normalized()
        ax_y = ax_z.cross(ax_x).normalized()
        self.add_oriented_box((p0 + p1) * 0.5, ax_x, ax_y, ax_z, radius * 2.0, radius * 2.0, ln, mat)

    def add_quad(self, p0, p1, p2, p3, mat, uvs=None):
        mi = self._mi(mat)
        b = len(self.v)
        self.v.extend([(p0.x, p0.y, p0.z), (p1.x, p1.y, p1.z), (p2.x, p2.y, p2.z), (p3.x, p3.y, p3.z)])
        self.f.append((b, b + 1, b + 2, b + 3))
        self.fm.append(mi)
        self.fuv.append(uvs or _QUAD_UVS)

    def build(self, smooth=False, cast_shadow=True):
        if not self.f:
            return None
        me = bpy.data.meshes.new(self.name)
        me.from_pydata(self.v, [], self.f)
        me.validate()
        me.update()
        for m in self.mats:
            me.materials.append(m)
        uvl = me.uv_layers.new(name="UVMap")
        for pi, poly in enumerate(me.polygons):
            poly.material_index = self.fm[pi]
            poly.use_smooth = smooth
            uvs = self.fuv[pi]
            for k, li in enumerate(poly.loop_indices):
                uvl.data[li].uv = uvs[k % len(uvs)]
        # 将原点移至包围盒中心以便手工编辑
        xs = [v.co.x for v in me.vertices]
        ys = [v.co.y for v in me.vertices]
        zs = [v.co.z for v in me.vertices]
        ctr = Vector(((min(xs) + max(xs)) * 0.5, (min(ys) + max(ys)) * 0.5, (min(zs) + max(zs)) * 0.5))
        me.transform(Matrix.Translation(-ctr))
        me.update()
        ob = bpy.data.objects.new(self.name, me)
        ob.location = ctr
        ob.visible_shadow = cast_shadow
        self.coll.objects.link(ob)
        return ob


# ---------------------------------------------------------------
# 2. EEVEE 湿滑镜面光追设置 + scene["sv_dimension"] 宇宙主控驱动器
# ---------------------------------------------------------------
scene["sv_dimension"] = 0.0
scene.render.engine = 'BLENDER_EEVEE'
scene.eevee.use_raytracing = True
try:
    scene.eevee.ray_tracing_method = 'SCREEN'
except Exception:
    pass
try:
    scene.eevee.shadow_pool_size = '1024'
except Exception:
    pass
scene.eevee.taa_render_samples = 24
scene.render.fps = int(META.get("fps", 24))
scene.frame_start = 1
scene.frame_end = int(META.get("frame_end", 1281))
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.use_motion_blur = True
scene.render.motion_blur_shutter = 0.06
scene.view_settings.view_transform = 'AgX'
for _lk in ('High Contrast', 'AgX - High Contrast', 'Medium High Contrast'):
    try:
        scene.view_settings.look = _lk
        break
    except Exception:
        continue
scene.view_settings.exposure = 0.25


def add_dim_driver(target_obj, prop_name, expr, index=-1):
    fc = target_obj.driver_add(prop_name, index) if index >= 0 else target_obj.driver_add(prop_name)
    d = fc.driver
    d.type = 'SCRIPTED'
    while d.variables:
        d.variables.remove(d.variables[0])
    v = d.variables.new()
    v.name = "dim"
    v.type = 'SINGLE_PROP'
    v.targets[0].id_type = 'SCENE'
    v.targets[0].id = scene
    v.targets[0].data_path = '["sv_dimension"]'
    d.expression = expr
    return fc


def act_weights_from_socket(nt, dim_out):
    sub1 = nt.nodes.new('ShaderNodeMath'); sub1.operation = 'SUBTRACT'; sub1.inputs[1].default_value = 1.0
    nt.links.new(dim_out, sub1.inputs[0])
    ab1 = nt.nodes.new('ShaderNodeMath'); ab1.operation = 'ABSOLUTE'
    nt.links.new(sub1.outputs[0], ab1.inputs[0])
    w2 = nt.nodes.new('ShaderNodeMath'); w2.operation = 'SUBTRACT'; w2.use_clamp = True; w2.inputs[0].default_value = 1.0
    nt.links.new(ab1.outputs[0], w2.inputs[1])
    w3 = nt.nodes.new('ShaderNodeMath'); w3.operation = 'SUBTRACT'; w3.use_clamp = True; w3.inputs[1].default_value = 1.0
    nt.links.new(dim_out, w3.inputs[0])
    return w2.outputs[0], w3.outputs[0]


def add_act_weights(nt):
    sub1 = nt.nodes.new('ShaderNodeMath'); sub1.operation = 'SUBTRACT'; sub1.inputs[0].default_value = 0.0; sub1.inputs[1].default_value = 1.0
    add_dim_driver(sub1.inputs[0], "default_value", "dim")
    ab1 = nt.nodes.new('ShaderNodeMath'); ab1.operation = 'ABSOLUTE'
    nt.links.new(sub1.outputs[0], ab1.inputs[0])
    w2 = nt.nodes.new('ShaderNodeMath'); w2.operation = 'SUBTRACT'; w2.use_clamp = True; w2.inputs[0].default_value = 1.0
    nt.links.new(ab1.outputs[0], w2.inputs[1])
    w3 = nt.nodes.new('ShaderNodeMath'); w3.operation = 'SUBTRACT'; w3.use_clamp = True; w3.inputs[0].default_value = 0.0; w3.inputs[1].default_value = 1.0
    add_dim_driver(w3.inputs[0], "default_value", "dim")
    return w2.outputs[0], w3.outputs[0]


def tri_color_mix(nt, c1, c2, c3, w2_o, w3_o):
    m12 = nt.nodes.new('ShaderNodeMixRGB')
    m12.inputs['Color1'].default_value = (*c1, 1.0)
    m12.inputs['Color2'].default_value = (*c2, 1.0)
    nt.links.new(w2_o, m12.inputs['Factor'])
    m123 = nt.nodes.new('ShaderNodeMixRGB')
    m123.inputs['Color2'].default_value = (*c3, 1.0)
    nt.links.new(w3_o, m123.inputs['Factor'])
    nt.links.new(m12.outputs['Color'], m123.inputs['Color1'])
    return m123.outputs['Color']


# ---------------------------------------------------------------
# 3. 核心漫画着色组 NG_SV_ComicSurface（支持可选清漆流光反射，隧道激光条纹在车漆流动！）
# ---------------------------------------------------------------
def build_comic_nodegroup():
    old = bpy.data.node_groups.get("NG_SV_ComicSurface")
    if old:
        bpy.data.node_groups.remove(old)
    ng = bpy.data.node_groups.new("NG_SV_ComicSurface", 'ShaderNodeTree')

    s_col = ng.interface.new_socket(name="Base Color", in_out='INPUT', socket_type='NodeSocketColor')
    s_col.default_value = (0.5, 0.5, 0.5, 1.0)
    s_dim = ng.interface.new_socket(name="SV Dimension", in_out='INPUT', socket_type='NodeSocketFloat')
    s_dim.default_value = 0.0
    s_rim = ng.interface.new_socket(name="Rim Strength", in_out='INPUT', socket_type='NodeSocketFloat')
    s_rim.default_value = 0.85
    s_ht = ng.interface.new_socket(name="Halftone Scale", in_out='INPUT', socket_type='NodeSocketFloat')
    s_ht.default_value = 78.0
    s_hts = ng.interface.new_socket(name="Halftone Strength", in_out='INPUT', socket_type='NodeSocketFloat')
    s_hts.default_value = 0.72
    s_hcs = ng.interface.new_socket(name="Hatch Strength", in_out='INPUT', socket_type='NodeSocketFloat')
    s_hcs.default_value = 0.72
    s_coat = ng.interface.new_socket(name="Neon Coat", in_out='INPUT', socket_type='NodeSocketFloat')
    s_coat.default_value = 0.0
    s_nrm = ng.interface.new_socket(name="Normal", in_out='INPUT', socket_type='NodeSocketVector')
    ng.interface.new_socket(name="Shader", in_out='OUTPUT', socket_type='NodeSocketShader')

    gi = ng.nodes.new('NodeGroupInput')
    go = ng.nodes.new('NodeGroupOutput')
    w2, w3 = act_weights_from_socket(ng, gi.outputs['SV Dimension'])

    diff = ng.nodes.new('ShaderNodeBsdfDiffuse')
    diff.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)
    ng.links.new(gi.outputs['Normal'], diff.inputs['Normal'])
    s2r = ng.nodes.new('ShaderNodeShaderToRGB')
    ng.links.new(diff.outputs['BSDF'], s2r.inputs['Shader'])
    rgb2bw = ng.nodes.new('ShaderNodeRGBToBW')
    ng.links.new(s2r.outputs['Color'], rgb2bw.inputs['Color'])
    irr = rgb2bw.outputs['Val']

    band_ramp = ng.nodes.new('ShaderNodeValToRGB')
    band_ramp.color_ramp.interpolation = 'CONSTANT'
    band_ramp.color_ramp.elements[0].position = 0.0; band_ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    e_mid = band_ramp.color_ramp.elements.new(0.26); e_mid.color = (0.5, 0.5, 0.5, 1.0)
    band_ramp.color_ramp.elements[-1].position = 0.66; band_ramp.color_ramp.elements[-1].color = (1.0, 1.0, 1.0, 1.0)
    ng.links.new(irr, band_ramp.inputs[0])

    sh_tint = tri_color_mix(ng, (0.010, 0.005, 0.032), (0.014, 0.058, 0.058), (0.028, 0.001, 0.024), w2, w3)
    hi_tint = tri_color_mix(ng, (0.34, 0.12, 0.02), (0.14, 0.30, 0.24), (0.40, 0.01, 0.05), w2, w3)

    sh_mul = ng.nodes.new('ShaderNodeMixRGB'); sh_mul.blend_type = 'MULTIPLY'; sh_mul.inputs['Factor'].default_value = 1.0
    sh_mul.inputs['Color2'].default_value = (0.34, 0.30, 0.44, 1.0); ng.links.new(gi.outputs['Base Color'], sh_mul.inputs['Color1'])
    sh_col = ng.nodes.new('ShaderNodeMixRGB'); sh_col.blend_type = 'ADD'; sh_col.inputs['Factor'].default_value = 1.0
    ng.links.new(sh_mul.outputs['Color'], sh_col.inputs['Color1']); ng.links.new(sh_tint, sh_col.inputs['Color2'])

    mid_col = ng.nodes.new('ShaderNodeMixRGB'); mid_col.blend_type = 'MULTIPLY'; mid_col.inputs['Factor'].default_value = 1.0
    mid_col.inputs['Color2'].default_value = (1.30, 1.24, 1.26, 1.0); ng.links.new(gi.outputs['Base Color'], mid_col.inputs['Color1'])

    hi_mul = ng.nodes.new('ShaderNodeMixRGB'); hi_mul.blend_type = 'MULTIPLY'; hi_mul.inputs['Factor'].default_value = 1.0
    hi_mul.inputs['Color2'].default_value = (1.85, 1.74, 1.68, 1.0); ng.links.new(gi.outputs['Base Color'], hi_mul.inputs['Color1'])
    hi_col = ng.nodes.new('ShaderNodeMixRGB'); hi_col.blend_type = 'ADD'; hi_col.inputs['Factor'].default_value = 1.0
    ng.links.new(hi_mul.outputs['Color'], hi_col.inputs['Color1']); ng.links.new(hi_tint, hi_col.inputs['Color2'])

    is_mid = ng.nodes.new('ShaderNodeMath'); is_mid.operation = 'GREATER_THAN'; is_mid.inputs[1].default_value = 0.25; ng.links.new(band_ramp.outputs[0], is_mid.inputs[0])
    is_hi = ng.nodes.new('ShaderNodeMath'); is_hi.operation = 'GREATER_THAN'; is_hi.inputs[1].default_value = 0.75; ng.links.new(band_ramp.outputs[0], is_hi.inputs[0])
    mix_sm = ng.nodes.new('ShaderNodeMixRGB'); ng.links.new(is_mid.outputs[0], mix_sm.inputs['Factor']); ng.links.new(sh_col.outputs['Color'], mix_sm.inputs['Color1']); ng.links.new(mid_col.outputs['Color'], mix_sm.inputs['Color2'])
    mix_smh = ng.nodes.new('ShaderNodeMixRGB'); ng.links.new(is_hi.outputs[0], mix_smh.inputs['Factor']); ng.links.new(mix_sm.outputs['Color'], mix_smh.inputs['Color1']); ng.links.new(hi_col.outputs['Color'], mix_smh.inputs['Color2'])

    # 16:9 屏幕空间高对比双极本戴网点 + 双极 45° 钢笔交叉排线 (Bipolar Crosshatching)
    tc = ng.nodes.new('ShaderNodeTexCoord')
    sep_w = ng.nodes.new('ShaderNodeSeparateXYZ'); ng.links.new(tc.outputs['Window'], sep_w.inputs['Vector'])
    wx_asp = ng.nodes.new('ShaderNodeMath'); wx_asp.operation = 'MULTIPLY'; wx_asp.inputs[1].default_value = 16.0 / 9.0; ng.links.new(sep_w.outputs['X'], wx_asp.inputs[0])

    c22, s22 = cos(radians(22.5)), sin(radians(22.5))
    ux1 = ng.nodes.new('ShaderNodeMath'); ux1.operation = 'MULTIPLY'; ux1.inputs[1].default_value = c22; ng.links.new(wx_asp.outputs[0], ux1.inputs[0])
    uy1 = ng.nodes.new('ShaderNodeMath'); uy1.operation = 'MULTIPLY'; uy1.inputs[1].default_value = s22; ng.links.new(sep_w.outputs['Y'], uy1.inputs[0])
    u_rot = ng.nodes.new('ShaderNodeMath'); u_rot.operation = 'SUBTRACT'; ng.links.new(ux1.outputs[0], u_rot.inputs[0]); ng.links.new(uy1.outputs[0], u_rot.inputs[1])
    vx1 = ng.nodes.new('ShaderNodeMath'); vx1.operation = 'MULTIPLY'; vx1.inputs[1].default_value = s22; ng.links.new(wx_asp.outputs[0], vx1.inputs[0])
    vy1 = ng.nodes.new('ShaderNodeMath'); vy1.operation = 'MULTIPLY'; vy1.inputs[1].default_value = c22; ng.links.new(sep_w.outputs['Y'], vy1.inputs[0])
    v_rot = ng.nodes.new('ShaderNodeMath'); v_rot.operation = 'ADD'; ng.links.new(vx1.outputs[0], v_rot.inputs[0]); ng.links.new(vy1.outputs[0], v_rot.inputs[1])

    u_sc = ng.nodes.new('ShaderNodeMath'); u_sc.operation = 'MULTIPLY'; ng.links.new(u_rot.outputs[0], u_sc.inputs[0]); ng.links.new(gi.outputs['Halftone Scale'], u_sc.inputs[1])
    v_sc = ng.nodes.new('ShaderNodeMath'); v_sc.operation = 'MULTIPLY'; ng.links.new(v_rot.outputs[0], v_sc.inputs[0]); ng.links.new(gi.outputs['Halftone Scale'], v_sc.inputs[1])
    u_fr = ng.nodes.new('ShaderNodeMath'); u_fr.operation = 'FRACT'; ng.links.new(u_sc.outputs[0], u_fr.inputs[0])
    v_fr = ng.nodes.new('ShaderNodeMath'); v_fr.operation = 'FRACT'; ng.links.new(v_sc.outputs[0], v_fr.inputs[0])
    du = ng.nodes.new('ShaderNodeMath'); du.operation = 'SUBTRACT'; du.inputs[1].default_value = 0.5; ng.links.new(u_fr.outputs[0], du.inputs[0])
    dv = ng.nodes.new('ShaderNodeMath'); dv.operation = 'SUBTRACT'; dv.inputs[1].default_value = 0.5; ng.links.new(v_fr.outputs[0], dv.inputs[0])
    du2 = ng.nodes.new('ShaderNodeMath'); du2.operation = 'MULTIPLY'; ng.links.new(du.outputs[0], du2.inputs[0]); ng.links.new(du.outputs[0], du2.inputs[1])
    dv2 = ng.nodes.new('ShaderNodeMath'); dv2.operation = 'MULTIPLY'; ng.links.new(dv.outputs[0], dv2.inputs[0]); ng.links.new(dv.outputs[0], dv2.inputs[1])
    dsum = ng.nodes.new('ShaderNodeMath'); dsum.operation = 'ADD'; ng.links.new(du2.outputs[0], dsum.inputs[0]); ng.links.new(dv2.outputs[0], dsum.inputs[1])
    drad = ng.nodes.new('ShaderNodeMath'); drad.operation = 'SQRT'; ng.links.new(dsum.outputs[0], drad.inputs[0])

    ht_zone = ng.nodes.new('ShaderNodeValToRGB')
    ht_zone.color_ramp.elements[0].position = 0.14; ht_zone.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    hz1 = ht_zone.color_ramp.elements.new(0.50); hz1.color = (0.48, 0.48, 0.48, 1.0)
    ht_zone.color_ramp.elements[-1].position = 0.92; ht_zone.color_ramp.elements[-1].color = (0.0, 0.0, 0.0, 1.0)
    ng.links.new(irr, ht_zone.inputs[0])
    dot_hit = ng.nodes.new('ShaderNodeMath'); dot_hit.operation = 'LESS_THAN'; ng.links.new(drad.outputs[0], dot_hit.inputs[0]); ng.links.new(ht_zone.outputs[0], dot_hit.inputs[1])
    ht_fac = ng.nodes.new('ShaderNodeMath'); ht_fac.operation = 'MULTIPLY'; ng.links.new(dot_hit.outputs[0], ht_fac.inputs[0]); ng.links.new(gi.outputs['Halftone Strength'], ht_fac.inputs[1])

    ht_bright = tri_color_mix(ng, (1.0, 0.46, 0.08), (0.08, 1.0, 0.82), (1.0, 0.03, 0.08), w2, w3)
    ht_dark = tri_color_mix(ng, (0.003, 0.002, 0.022), (0.006, 0.032, 0.042), (0.012, 0.001, 0.022), w2, w3)
    is_upper = ng.nodes.new('ShaderNodeMath'); is_upper.operation = 'GREATER_THAN'; is_upper.inputs[1].default_value = 0.45; ng.links.new(irr, is_upper.inputs[0])
    ht_target = ng.nodes.new('ShaderNodeMixRGB'); ng.links.new(is_upper.outputs[0], ht_target.inputs['Factor']); ng.links.new(ht_dark, ht_target.inputs['Color1']); ng.links.new(ht_bright, ht_target.inputs['Color2'])
    after_ht = ng.nodes.new('ShaderNodeMixRGB'); ng.links.new(ht_fac.outputs[0], after_ht.inputs['Factor']); ng.links.new(mix_smh.outputs['Color'], after_ht.inputs['Color1']); ng.links.new(ht_target.outputs['Color'], after_ht.inputs['Color2'])

    # 双极 45° 钢笔交叉排线：中暗部 (0.22 < irr < 0.52) 绘深靛墨线，极暗部 (irr <= 0.22) 叠加亮色荧光交叉网纹！
    h_sum = ng.nodes.new('ShaderNodeMath'); h_sum.operation = 'ADD'; ng.links.new(wx_asp.outputs[0], h_sum.inputs[0]); ng.links.new(sep_w.outputs['Y'], h_sum.inputs[1])
    h_sc1 = ng.nodes.new('ShaderNodeMath'); h_sc1.operation = 'MULTIPLY'; h_sc1.inputs[1].default_value = 96.0; ng.links.new(h_sum.outputs[0], h_sc1.inputs[0])
    h_fr1 = ng.nodes.new('ShaderNodeMath'); h_fr1.operation = 'FRACT'; ng.links.new(h_sc1.outputs[0], h_fr1.inputs[0])
    h_ln1 = ng.nodes.new('ShaderNodeMath'); h_ln1.operation = 'LESS_THAN'; h_ln1.inputs[1].default_value = 0.26; ng.links.new(h_fr1.outputs[0], h_ln1.inputs[0])

    h_dif = ng.nodes.new('ShaderNodeMath'); h_dif.operation = 'SUBTRACT'; h_dif.inputs[1].default_value = -10.0
    h_dif_raw = ng.nodes.new('ShaderNodeMath'); h_dif_raw.operation = 'SUBTRACT'; ng.links.new(wx_asp.outputs[0], h_dif_raw.inputs[0]); ng.links.new(sep_w.outputs['Y'], h_dif_raw.inputs[1])
    ng.links.new(h_dif_raw.outputs[0], h_dif.inputs[0])
    h_sc2 = ng.nodes.new('ShaderNodeMath'); h_sc2.operation = 'MULTIPLY'; h_sc2.inputs[1].default_value = 96.0; ng.links.new(h_dif.outputs[0], h_sc2.inputs[0])
    h_fr2 = ng.nodes.new('ShaderNodeMath'); h_fr2.operation = 'FRACT'; ng.links.new(h_sc2.outputs[0], h_fr2.inputs[0])
    h_ln2 = ng.nodes.new('ShaderNodeMath'); h_ln2.operation = 'LESS_THAN'; h_ln2.inputs[1].default_value = 0.22; ng.links.new(h_fr2.outputs[0], h_ln2.inputs[0])

    is_deep = ng.nodes.new('ShaderNodeMath'); is_deep.operation = 'LESS_THAN'; is_deep.inputs[1].default_value = 0.22; ng.links.new(irr, is_deep.inputs[0])
    sh_m1 = ng.nodes.new('ShaderNodeMath'); sh_m1.operation = 'LESS_THAN'; sh_m1.inputs[1].default_value = 0.52; ng.links.new(irr, sh_m1.inputs[0])
    h_ln2_deep = ng.nodes.new('ShaderNodeMath'); h_ln2_deep.operation = 'MULTIPLY'; ng.links.new(h_ln2.outputs[0], h_ln2_deep.inputs[0]); ng.links.new(is_deep.outputs[0], h_ln2_deep.inputs[1])
    h_cross = ng.nodes.new('ShaderNodeMath'); h_cross.operation = 'MAXIMUM'; ng.links.new(h_ln1.outputs[0], h_cross.inputs[0]); ng.links.new(h_ln2_deep.outputs[0], h_cross.inputs[1])
    hm1 = ng.nodes.new('ShaderNodeMath'); hm1.operation = 'MULTIPLY'; ng.links.new(h_cross.outputs[0], hm1.inputs[0]); ng.links.new(sh_m1.outputs[0], hm1.inputs[1])
    h_fac = ng.nodes.new('ShaderNodeMath'); h_fac.operation = 'MULTIPLY'; ng.links.new(hm1.outputs[0], h_fac.inputs[0]); ng.links.new(gi.outputs['Hatch Strength'], h_fac.inputs[1])

    ink_dark = tri_color_mix(ng, (0.001, 0.0008, 0.008), (0.002, 0.014, 0.022), (0.003, 0.0004, 0.008), w2, w3)
    ink_lumi = tri_color_mix(ng, (0.76, 0.24, 0.12), (0.12, 0.68, 0.72), (0.68, 0.05, 0.18), w2, w3)
    ink_col = ng.nodes.new('ShaderNodeMixRGB'); ng.links.new(is_deep.outputs[0], ink_col.inputs['Factor']); ng.links.new(ink_dark, ink_col.inputs['Color1']); ng.links.new(ink_lumi, ink_col.inputs['Color2'])
    after_hatch = ng.nodes.new('ShaderNodeMixRGB'); ng.links.new(h_fac.outputs[0], after_hatch.inputs['Factor']); ng.links.new(after_ht.outputs['Color'], after_hatch.inputs['Color1']); ng.links.new(ink_col.outputs['Color'], after_hatch.inputs['Color2'])

    # 摄影机空间阶梯双色轮廓光 (Camera-Space Dual Rim Kick: 左永远电青/薄荷绿，右永远绯红/品红，全航向生效！)
    lw = ng.nodes.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.36; ng.links.new(gi.outputs['Normal'], lw.inputs['Normal'])
    rim_step = ng.nodes.new('ShaderNodeValToRGB'); rim_step.color_ramp.interpolation = 'CONSTANT'
    rim_step.color_ramp.elements[0].position = 0.0; rim_step.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    rim_step.color_ramp.elements[1].position = 0.62; rim_step.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    ng.links.new(lw.outputs['Facing'], rim_step.inputs[0])

    geo = ng.nodes.new('ShaderNodeNewGeometry')
    vt_cam = ng.nodes.new('ShaderNodeVectorTransform')
    vt_cam.vector_type = 'NORMAL'
    vt_cam.convert_from = 'WORLD'
    vt_cam.convert_to = 'CAMERA'
    ng.links.new(geo.outputs['Normal'], vt_cam.inputs['Vector'])
    sep_n = ng.nodes.new('ShaderNodeSeparateXYZ'); ng.links.new(vt_cam.outputs['Vector'], sep_n.inputs['Vector'])
    n_side = ng.nodes.new('ShaderNodeMapRange'); n_side.inputs['From Min'].default_value = -0.22; n_side.inputs['From Max'].default_value = 0.22; ng.links.new(sep_n.outputs['X'], n_side.inputs['Value'])
    rim_c1 = tri_color_mix(ng, (0.0, 0.92, 1.0), (0.04, 1.0, 0.82), (0.0, 0.82, 1.0), w2, w3)
    rim_c2 = tri_color_mix(ng, (1.0, 0.22, 0.08), (1.0, 0.16, 0.64), (1.0, 0.02, 0.06), w2, w3)
    rim_dual = ng.nodes.new('ShaderNodeMixRGB'); ng.links.new(n_side.outputs['Result'], rim_dual.inputs['Factor']); ng.links.new(rim_c1, rim_dual.inputs['Color1']); ng.links.new(rim_c2, rim_dual.inputs['Color2'])
    rim_amt = ng.nodes.new('ShaderNodeMath'); rim_amt.operation = 'MULTIPLY'; ng.links.new(rim_step.outputs[0], rim_amt.inputs[0]); ng.links.new(gi.outputs['Rim Strength'], rim_amt.inputs[1])
    final_col = ng.nodes.new('ShaderNodeMixRGB'); ng.links.new(rim_amt.outputs[0], final_col.inputs['Factor']); ng.links.new(after_hatch.outputs['Color'], final_col.inputs['Color1']); ng.links.new(rim_dual.outputs['Color'], final_col.inputs['Color2'])

    em = ng.nodes.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = 1.0
    ng.links.new(final_col.outputs['Color'], em.inputs['Color'])

    # 可选清漆镜面流光层（捕捉摩天楼霓虹窗与隧道激光肋反射）
    coat_bsdf = ng.nodes.new('ShaderNodeBsdfPrincipled')
    coat_bsdf.inputs['Base Color'].default_value = (0.0, 0.0, 0.0, 1.0)
    coat_bsdf.inputs['Metallic'].default_value = 0.0
    coat_bsdf.inputs['Roughness'].default_value = 0.075
    ng.links.new(gi.outputs['Neon Coat'], coat_bsdf.inputs['Specular IOR Level'])
    add_sh = ng.nodes.new('ShaderNodeAddShader')
    ng.links.new(em.outputs['Emission'], add_sh.inputs[0])
    ng.links.new(coat_bsdf.outputs['BSDF'], add_sh.inputs[1])
    ng.links.new(add_sh.outputs['Shader'], go.inputs['Shader'])
    return ng


NG_COMIC = build_comic_nodegroup()


def make_comic_mat(name, rgb, rim=0.5, ht_sc=78.0, ht_s=0.65, hc_s=0.65, coat=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    grp = nt.nodes.new('ShaderNodeGroup'); grp.node_tree = NG_COMIC
    add_dim_driver(grp.inputs['SV Dimension'], "default_value", "dim")
    grp.inputs['Base Color'].default_value = (*rgb, 1.0)
    grp.inputs['Rim Strength'].default_value = rim
    grp.inputs['Halftone Scale'].default_value = ht_sc
    grp.inputs['Halftone Strength'].default_value = ht_s
    grp.inputs['Hatch Strength'].default_value = hc_s
    grp.inputs['Neon Coat'].default_value = coat
    nt.links.new(grp.outputs['Shader'], out.inputs['Surface'])
    return m


def make_neon_mat(name, c1, c2, c3, strength=12.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Strength'].default_value = strength
    w2, w3 = add_act_weights(nt)
    col = tri_color_mix(nt, c1, c2, c3, w2, w3)
    nt.links.new(col, em.inputs['Color'])
    nt.links.new(em.outputs['Emission'], out.inputs['Surface'])
    return m


def make_tex_emit_mat(name, img_file, emit_strength=1.8, rough=0.35, spec=0.15):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Specular IOR Level'].default_value = spec
    tn = nt.nodes.new('ShaderNodeTexImage')
    tn.image = bpy.data.images.load(os.path.join(TEX_SV, img_file), check_existing=True)
    tn.extension = 'REPEAT'
    w2, w3 = add_act_weights(nt)
    act_mul = tri_color_mix(nt, (1.42, 0.76, 0.58), (0.86, 1.24, 1.16), (1.45, 0.52, 0.76), w2, w3)
    tmul = nt.nodes.new('ShaderNodeMixRGB'); tmul.blend_type = 'MULTIPLY'; tmul.inputs['Factor'].default_value = 1.0
    nt.links.new(tn.outputs['Color'], tmul.inputs['Color1'])
    nt.links.new(act_mul, tmul.inputs['Color2'])
    nt.links.new(tmul.outputs['Color'], bsdf.inputs['Base Color'])
    nt.links.new(tmul.outputs['Color'], bsdf.inputs['Emission Color'])
    bsdf.inputs['Emission Strength'].default_value = emit_strength
    nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return m


# ---------------------------------------------------------------
# 4. 湿滑镜面黑曜霓虹沥青 + 港湾反光水面 + 伪体积丁达尔神光片 + 天空与零镜面太阳
# ---------------------------------------------------------------
def build_wet_asphalt_mat():
    m = bpy.data.materials.get("MAT_V6_WetAsphalt") or bpy.data.materials.new("MAT_V6_WetAsphalt")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Metallic'].default_value = 0.08
    bsdf.inputs['Specular IOR Level'].default_value = 0.68
    w2, w3 = add_act_weights(nt)

    geo = nt.nodes.new('ShaderNodeNewGeometry')
    uv = nt.nodes.new('ShaderNodeUVMap'); uv.uv_map = "UVMap"
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(uv.outputs['UV'], sep.inputs['Vector'])

    # 积水镜面掩膜：世界尺度水洼噪波 -> Roughness 0.065 (镜面水洼) .. 0.25 (潮湿赛车线)
    ns_pud = nt.nodes.new('ShaderNodeTexNoise')
    ns_pud.inputs['Scale'].default_value = 0.085
    ns_pud.inputs['Detail'].default_value = 6.0
    ns_pud.inputs['Roughness'].default_value = 0.65
    nt.links.new(geo.outputs['Position'], ns_pud.inputs['Vector'])

    r_ramp = nt.nodes.new('ShaderNodeValToRGB')
    r_ramp.color_ramp.elements[0].position = 0.45; r_ramp.color_ramp.elements[0].color = (0.036, 0.036, 0.036, 1.0)
    r_ramp.color_ramp.elements[1].position = 0.58; r_ramp.color_ramp.elements[1].color = (0.165, 0.165, 0.165, 1.0)
    nt.links.new(ns_pud.outputs['Fac'], r_ramp.inputs[0])
    nt.links.new(r_ramp.outputs['Color'], bsdf.inputs['Roughness'])

    # 细微雨夜水波纹凹凸（让倒映的摩天楼霓虹与斜拉索呈现清晰拉丝流光）
    ns_rip = nt.nodes.new('ShaderNodeTexNoise')
    ns_rip.inputs['Scale'].default_value = 42.0
    ns_rip.inputs['Detail'].default_value = 8.0
    nt.links.new(geo.outputs['Position'], ns_rip.inputs['Vector'])
    bmp = nt.nodes.new('ShaderNodeBump')
    bmp.inputs['Strength'].default_value = 0.022
    bmp.inputs['Distance'].default_value = 0.008
    nt.links.new(ns_rip.outputs['Fac'], bmp.inputs['Height'])
    nt.links.new(bmp.outputs['Normal'], bsdf.inputs['Normal'])

    # 深邃黑曜靛蓝漫画底色 + 纵向高速笔刷流线
    comb = nt.nodes.new('ShaderNodeCombineXYZ')
    mx = nt.nodes.new('ShaderNodeMath'); mx.operation = 'MULTIPLY'; mx.inputs[1].default_value = 24.0; ng_u = sep.outputs['X']
    my = nt.nodes.new('ShaderNodeMath'); my.operation = 'MULTIPLY'; my.inputs[1].default_value = 0.35
    nt.links.new(ng_u, mx.inputs[0]); nt.links.new(sep.outputs['Y'], my.inputs[0])
    nt.links.new(mx.outputs['Value'], comb.inputs['X']); nt.links.new(my.outputs['Value'], comb.inputs['Y'])
    ns_str = nt.nodes.new('ShaderNodeTexNoise'); ns_str.inputs['Scale'].default_value = 3.5; nt.links.new(comb.outputs['Vector'], ns_str.inputs['Vector'])
    c_lo = tri_color_mix(nt, (0.002, 0.003, 0.011), (0.003, 0.008, 0.016), (0.003, 0.001, 0.012), w2, w3)
    c_hi = tri_color_mix(nt, (0.009, 0.012, 0.032), (0.016, 0.008, 0.030), (0.014, 0.003, 0.028), w2, w3)
    st_s = nt.nodes.new('ShaderNodeMath'); st_s.operation = 'GREATER_THAN'; st_s.inputs[1].default_value = 0.56; nt.links.new(ns_str.outputs['Fac'], st_s.inputs[0])
    cmix = nt.nodes.new('ShaderNodeMixRGB'); ng_f = st_s.outputs[0]
    nt.links.new(ng_f, cmix.inputs['Factor']); nt.links.new(c_lo, cmix.inputs['Color1']); nt.links.new(c_hi, cmix.inputs['Color2'])
    nt.links.new(cmix.outputs['Color'], bsdf.inputs['Base Color'])
    nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return m


def build_harbor_water_mat():
    m = bpy.data.materials.get("MAT_V6_HarborWater") or bpy.data.materials.new("MAT_V6_HarborWater")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (0.004, 0.012, 0.028, 1.0)
    bsdf.inputs['Metallic'].default_value = 0.15
    bsdf.inputs['Roughness'].default_value = 0.085
    bsdf.inputs['Specular IOR Level'].default_value = 0.75
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    wv = nt.nodes.new('ShaderNodeTexNoise')
    wv.inputs['Scale'].default_value = 0.28
    wv.inputs['Detail'].default_value = 7.0
    wv.inputs['Distortion'].default_value = 0.8
    nt.links.new(geo.outputs['Position'], wv.inputs['Vector'])
    bmp = nt.nodes.new('ShaderNodeBump')
    bmp.inputs['Strength'].default_value = 0.14
    nt.links.new(wv.outputs['Fac'], bmp.inputs['Height'])
    nt.links.new(bmp.outputs['Normal'], bsdf.inputs['Normal'])
    nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return m


def build_godray_mat(name, c1, c2, c3, strength=1.35):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    try:
        m.surface_render_method = 'BLENDED'
    except Exception:
        pass
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Strength'].default_value = strength
    w2, w3 = add_act_weights(nt)
    col = tri_color_mix(nt, c1, c2, c3, w2, w3)
    nt.links.new(col, em.inputs['Color'])

    # UV 边缘柔和衰减 + 视角边缘消隐（绝不出现硬多边形穿帮线！）
    uv = nt.nodes.new('ShaderNodeUVMap'); uv.uv_map = "UVMap"
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(uv.outputs['UV'], sep.inputs['Vector'])
    # 横向 sin(pi*u) 边缘消隐，纵向 (1 - v)^1.5 从高空向路面散射衰减
    u_center = nt.nodes.new('ShaderNodeMath'); u_center.operation = 'SUBTRACT'; u_center.inputs[1].default_value = 0.5; nt.links.new(sep.outputs['X'], u_center.inputs[0])
    u_abs = nt.nodes.new('ShaderNodeMath'); u_abs.operation = 'ABSOLUTE'; ng_ua = u_abs; nt.links.new(u_center.outputs[0], ng_ua.inputs[0])
    u_fade = ng_uf = nt.nodes.new('ShaderNodeMapRange'); ng_uf.inputs['From Min'].default_value = 0.0; ng_uf.inputs['From Max'].default_value = 0.5; ng_uf.inputs['To Min'].default_value = 1.0; ng_uf.inputs['To Max'].default_value = 0.0
    nt.links.new(u_abs.outputs[0], u_fade.inputs['Value'])

    v_fade = nt.nodes.new('ShaderNodeMapRange'); v_fade.inputs['From Min'].default_value = 0.0; v_fade.inputs['From Max'].default_value = 1.0; v_fade.inputs['To Min'].default_value = 0.06; v_fade.inputs['To Max'].default_value = 0.32
    nt.links.new(sep.outputs['Y'], v_fade.inputs['Value'])

    lw = nt.nodes.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.5
    f_inv = nt.nodes.new('ShaderNodeMath'); f_inv.operation = 'SUBTRACT'; f_inv.inputs[0].default_value = 1.0; nt.links.new(lw.outputs['Facing'], f_inv.inputs[1])
    f_pow = nt.nodes.new('ShaderNodeMath'); f_pow.operation = 'POWER'; f_pow.inputs[1].default_value = 1.8; nt.links.new(f_inv.outputs[0], f_pow.inputs[0])

    m1 = nt.nodes.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'; nt.links.new(u_fade.outputs['Result'], m1.inputs[0]); nt.links.new(v_fade.outputs['Result'], m1.inputs[1])
    m2 = nt.nodes.new('ShaderNodeMath'); m2.operation = 'MULTIPLY'; m2.use_clamp = True; nt.links.new(m1.outputs[0], m2.inputs[0]); nt.links.new(f_pow.outputs[0], m2.inputs[1])

    mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(m2.outputs[0], mx.inputs['Fac'])
    nt.links.new(tr.outputs['BSDF'], mx.inputs[1])
    nt.links.new(em.outputs['Emission'], mx.inputs[2])
    nt.links.new(mx.outputs['Shader'], out.inputs['Surface'])
    return m


MAT_WET_ROAD = build_wet_asphalt_mat()
MAT_WATER = build_harbor_water_mat()
MAT_WHITE_LINE = make_neon_mat("MAT_V6_WhiteLine", (0.75, 0.92, 1.0), (0.95, 0.78, 1.0), (0.65, 0.90, 1.0), strength=1.8)
MAT_KERB_A = make_neon_mat("MAT_V6_KerbPrimary", (1.0, 0.06, 0.28), (1.0, 0.16, 0.72), (1.0, 0.03, 0.16), strength=3.2)
MAT_KERB_B = make_comic_mat("MAT_V6_KerbSecondary", (0.92, 0.94, 0.98), rim=0.2, ht_s=0.35, hc_s=0.25)
MAT_BARRIER = make_comic_mat("MAT_V6_Barrier", (0.045, 0.055, 0.145), rim=0.45, ht_s=0.55, hc_s=0.55, coat=0.35)
MAT_CONCRETE = make_comic_mat("MAT_V6_Concrete", (0.14, 0.14, 0.24), rim=0.25, ht_s=0.50, hc_s=0.52)
MAT_STEEL = make_comic_mat("MAT_V6_Steel", (0.08, 0.10, 0.22), rim=0.50, ht_s=0.52, hc_s=0.50, coat=0.30)
MAT_TUNNEL_WALL = make_comic_mat("MAT_V6_TunnelVault", (0.025, 0.028, 0.075), rim=0.35, ht_s=0.45, hc_s=0.60, coat=0.45)

MAT_NEON_CYAN = make_neon_mat("MAT_V6_NeonCyan", (0.0, 0.88, 1.0), (0.06, 1.0, 0.82), (0.96, 0.04, 0.12), strength=6.0)
MAT_NEON_MAG = make_neon_mat("MAT_V6_NeonMag", (1.0, 0.20, 0.05), (1.0, 0.18, 0.62), (1.0, 0.01, 0.04), strength=6.8)
MAT_NEON_GOLD = make_neon_mat("MAT_V6_NeonGold", (1.0, 0.54, 0.02), (0.20, 1.0, 0.78), (0.88, 0.02, 0.18), strength=5.8)

MAT_FACADE = make_tex_emit_mat("MAT_V6_SkyscraperFacade", "sv_skyscraper_facade.png", emit_strength=1.75, rough=0.22, spec=0.35)
MAT_SIGNS = make_tex_emit_mat("MAT_V6_NeonSigns", "sv_neon_signs.png", emit_strength=3.6, rough=0.20, spec=0.20)
MAT_AD = make_tex_emit_mat("MAT_V6_AdBoard", "sv_ad_boards.png", emit_strength=2.1, rough=0.30)
MAT_SCREEN = make_tex_emit_mat("MAT_V6_BigScreen", "sv_bigscreen.png", emit_strength=2.6, rough=0.25)
MAT_GARAGE = make_tex_emit_mat("MAT_V6_PitGarage", "sv_pit_garage.png", emit_strength=1.6, rough=0.35)
MAT_DRS = make_tex_emit_mat("MAT_V6_DRSBoard", "sv_drs_board.png", emit_strength=2.0, rough=0.30)
MAT_BRAKE = {n: make_tex_emit_mat(f"MAT_V6_Brake{n}", f"sv_brake_{n}.png", emit_strength=1.85, rough=0.30) for n in ("150", "100", "50")}
MAT_GODRAY_A = build_godray_mat("MAT_V6_GodRayCyan", (1.0, 0.42, 0.10), (0.06, 1.0, 0.84), (1.0, 0.03, 0.10), strength=1.18)
MAT_GODRAY_B = build_godray_mat("MAT_V6_GodRayWarm", (1.0, 0.22, 0.08), (1.0, 0.28, 0.64), (1.0, 0.01, 0.06), strength=1.28)


# ---------------------------------------------------------------
# 5. 世界环境、零镜面太阳光（彻底杜绝路面太阳白楔！）与三幕漫画天穹 + 巨型地平线次元月门
# ---------------------------------------------------------------
_cx = sum(f["pos"].x for f in FRAMES) / N
_cy = sum(f["pos"].y for f in FRAMES) / N

world = bpy.data.worlds.get("World_V6_SpiderVerse") or bpy.data.worlds.new("World_V6_SpiderVerse")
scene.world = world
world.use_nodes = True
_wnt = world.node_tree
_wnt.nodes.clear()
_wbg = _wnt.nodes.new('ShaderNodeBackground')
_wbg.inputs['Strength'].default_value = 0.28
_ww2, _ww3 = add_act_weights(_wnt)
_wcol = tri_color_mix(_wnt, (0.022, 0.012, 0.038), (0.024, 0.072, 0.068), (0.028, 0.003, 0.026), _ww2, _ww3)
_wnt.links.new(_wcol, _wbg.inputs['Color'])
_wout = _wnt.nodes.new('ShaderNodeOutputWorld')
_wnt.links.new(_wbg.outputs[0], _wout.inputs[0])

# 精确锁定 Eau-Rouge +42m 盲坡顶点地标 (idx=599)，将太阳与巨型蜘蛛侠次元月门对准盲坡与斜拉桥双塔中轴！
_crest_landmarks = [lm["idx"] for lm in META.get("landmarks", []) if lm.get("event") == "eau_rouge_42m_blind_crest"]
_crest_idx = int(_crest_landmarks[0]) if _crest_landmarks else max(
    range(N), key=lambda k: FRAMES[k]["pos"].z if FRAMES[k]["zone"] == "eau_rouge_climb" else -999.0
)
_crest_f = FRAMES[_crest_idx]
_crest_fwd_xy = Vector((_crest_f["fwd"].x, _crest_f["fwd"].y, 0.0)).normalized()
_crest_rgt_xy = Vector((_crest_f["fwd"].y, -_crest_f["fwd"].x, 0.0)).normalized()
_sun_az = math.atan2(_crest_f["fwd"].y, _crest_f["fwd"].x)

_sl = bpy.data.lights.new("LGT_V6Sun", 'SUN')
_sl.energy = 5.4
_sl.angle = radians(2.2)
_sl.use_shadow = True
try:
    _sl.shadow_maximum_resolution = 0.012
except Exception:
    pass
_sl.specular_factor = 0.0        # 核心关键：压零太阳镜面分量，湿滑沥青只反射建筑霓虹/斜拉索/车灯，零太阳白楔！
add_dim_driver(_sl, "energy", "5.4 + 0.8*max(0.0, 1.0-abs(dim-1.0)) + 0.5*max(0.0, dim-1.0)")
add_dim_driver(_sl, "color", "1.0", 0)
add_dim_driver(_sl, "color", "0.72 + 0.22*max(0.0, 1.0-abs(dim-1.0)) - 0.42*max(0.0, dim-1.0)", 1)
add_dim_driver(_sl, "color", "0.48 + 0.44*max(0.0, 1.0-abs(dim-1.0)) - 0.12*max(0.0, dim-1.0)", 2)
_sun_ob = bpy.data.objects.new("LGT_V6Sun", _sl)
COLLS["V6_07_Lighting"].objects.link(_sun_ob)
_sun_ob.rotation_euler = Euler((radians(90.0 - 20.0), 0.0, _sun_az - pi / 2.0), 'XYZ')

_fl = bpy.data.lights.new("LGT_V6SkyFill", 'SUN')
_fl.energy = 0.42
_fl.angle = radians(35.0)
_fl.use_shadow = False
_fl.specular_factor = 0.0
add_dim_driver(_fl, "color", "0.62 - 0.30*max(0.0, 1.0-abs(dim-1.0)) + 0.32*max(0.0, dim-1.0)", 0)
add_dim_driver(_fl, "color", "0.36 + 0.62*max(0.0, 1.0-abs(dim-1.0)) - 0.26*max(0.0, dim-1.0)", 1)
add_dim_driver(_fl, "color", "0.72 + 0.22*max(0.0, 1.0-abs(dim-1.0)) - 0.24*max(0.0, dim-1.0)", 2)
_fill_ob = bpy.data.objects.new("LGT_V6SkyFill", _fl)
COLLS["V6_07_Lighting"].objects.link(_fill_ob)
_fill_ob.rotation_euler = Euler((radians(48.0), 0.0, _sun_az + pi / 2.0), 'XYZ')

# 天空穹顶 V5_SkyDome（三幕鲜明宇宙分色：Act1 布鲁克林暖琥珀绯红 / Act2 格温水彩薄荷青与蜜桃粉 / Act3 2099 激光朱红与暗紫）
def build_skydome_and_moon():
    sky_mat = bpy.data.materials.new("V5_SkyDome")
    sky_mat.use_nodes = True
    snt = sky_mat.node_tree
    snt.nodes.clear()
    sout = snt.nodes.new('ShaderNodeOutputMaterial')
    sem = snt.nodes.new('ShaderNodeEmission'); sem.inputs['Strength'].default_value = 0.90
    sw2, sw3 = add_act_weights(snt)

    tc = snt.nodes.new('ShaderNodeTexCoord')
    nrm = snt.nodes.new('ShaderNodeVectorMath'); nrm.operation = 'NORMALIZE'; snt.links.new(tc.outputs['Object'], nrm.inputs[0])
    sep = snt.nodes.new('ShaderNodeSeparateXYZ'); snt.links.new(nrm.outputs['Vector'], sep.inputs['Vector'])
    mz = snt.nodes.new('ShaderNodeMapRange'); mz.inputs['From Min'].default_value = -0.04; mz.inputs['From Max'].default_value = 0.80; snt.links.new(sep.outputs['Z'], mz.inputs['Value'])
    pz = snt.nodes.new('ShaderNodeMath'); pz.operation = 'POWER'; pz.inputs[1].default_value = 0.58; snt.links.new(mz.outputs['Result'], pz.inputs[0])

    def _sramp(stops):
        r = snt.nodes.new('ShaderNodeValToRGB'); r.color_ramp.interpolation = 'B_SPLINE'
        r.color_ramp.elements[0].position = stops[0][0]; r.color_ramp.elements[0].color = (*stops[0][1], 1.0)
        r.color_ramp.elements[1].position = stops[-1][0]; r.color_ramp.elements[1].color = (*stops[-1][1], 1.0)
        for ps, cs in stops[1:-1]:
            e = r.color_ramp.elements.new(ps); e.color = (*cs, 1.0)
        snt.links.new(pz.outputs[0], r.inputs[0])
        return r.outputs['Color']

    s1 = _sramp([(0.0, (0.045, 0.012, 0.032)), (0.12, (0.95, 0.28, 0.07)), (0.30, (0.64, 0.10, 0.18)), (0.58, (0.10, 0.045, 0.22)), (1.0, (0.016, 0.012, 0.062))])
    s2 = _sramp([(0.0, (0.08, 0.30, 0.30)), (0.14, (0.94, 0.38, 0.54)), (0.34, (0.60, 0.34, 0.56)), (0.60, (0.10, 0.68, 0.60)), (1.0, (0.05, 0.46, 0.48))])
    s3 = _sramp([(0.0, (0.042, 0.002, 0.020)), (0.13, (0.96, 0.02, 0.05)), (0.30, (0.54, 0.01, 0.16)), (0.56, (0.08, 0.006, 0.15)), (1.0, (0.012, 0.003, 0.030))])
    m12 = snt.nodes.new('ShaderNodeMixRGB'); snt.links.new(sw2, m12.inputs['Factor']); snt.links.new(s1, m12.inputs['Color1']); snt.links.new(s2, m12.inputs['Color2'])
    m123 = snt.nodes.new('ShaderNodeMixRGB'); snt.links.new(sw3, m123.inputs['Factor']); snt.links.new(m12.outputs['Color'], m123.inputs['Color1']); snt.links.new(s3, m123.inputs['Color2'])
    snt.links.new(m123.outputs['Color'], sem.inputs['Color'])
    snt.links.new(sem.outputs['Emission'], sout.inputs['Surface'])

    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=80, v_segments=48, radius=1.0)
    me = bpy.data.meshes.new("V5_SkyDome")
    bm.to_mesh(me); bm.free()
    for p_s in me.polygons:
        p_s.use_smooth = True
    me.materials.append(sky_mat)
    ob = bpy.data.objects.new("V5_SkyDome", me)
    ob.location = (_cx, _cy, 0.0)
    ob.scale = (4200.0, 4200.0, 4200.0)
    ob.visible_shadow = False
    COLLS["V6_05_Atmosphere_GodRays"].objects.link(ob)

    # 巨型蜘蛛侠高饱和次元传送光轮/本戴巨月（AgX 防泛白校准：高纯度双色同心光环 + 边缘暗角消隐）
    moon_mat = bpy.data.materials.new("MAT_V6_HorizonMoonPortal")
    moon_mat.use_nodes = True
    try:
        moon_mat.surface_render_method = 'BLENDED'
    except Exception:
        pass
    mnt = moon_mat.node_tree; mnt.nodes.clear()
    mout = mnt.nodes.new('ShaderNodeOutputMaterial')
    mtr = mnt.nodes.new('ShaderNodeBsdfTransparent')
    mem = mnt.nodes.new('ShaderNodeEmission'); mem.inputs['Strength'].default_value = 1.42
    mw2, mw3 = add_act_weights(mnt)
    mtc = mnt.nodes.new('ShaderNodeTexCoord')
    mlen = mnt.nodes.new('ShaderNodeVectorMath'); mlen.operation = 'LENGTH'; mnt.links.new(mtc.outputs['Object'], mlen.inputs[0])
    # 同心次元脉冲光环
    mring = mnt.nodes.new('ShaderNodeMath'); mring.operation = 'MULTIPLY'; mring.inputs[1].default_value = 22.0; mnt.links.new(mlen.outputs['Value'], mring.inputs[0])
    mfr = mnt.nodes.new('ShaderNodeMath'); mfr.operation = 'SINE'; mnt.links.new(mring.outputs[0], mfr.inputs[0])
    mst = mnt.nodes.new('ShaderNodeMath'); mst.operation = 'GREATER_THAN'; mst.inputs[1].default_value = 0.15; mnt.links.new(mfr.outputs[0], mst.inputs[0])
    mc_a = tri_color_mix(mnt, (1.0, 0.34, 0.02), (1.0, 0.04, 0.52), (1.0, 0.01, 0.18), mw2, mw3)
    mc_b = tri_color_mix(mnt, (0.0, 0.78, 1.0), (0.0, 0.92, 0.78), (0.36, 0.02, 1.0), mw2, mw3)
    mmx = mnt.nodes.new('ShaderNodeMixRGB'); mnt.links.new(mst.outputs[0], mmx.inputs['Factor']); mnt.links.new(mc_a, mmx.inputs['Color1']); mnt.links.new(mc_b, mmx.inputs['Color2'])
    mnt.links.new(mmx.outputs['Color'], mem.inputs['Color'])
    medg = mnt.nodes.new('ShaderNodeMapRange'); medg.inputs['From Min'].default_value = 0.62; medg.inputs['From Max'].default_value = 0.99; medg.inputs['To Min'].default_value = 0.95; medg.inputs['To Max'].default_value = 0.0
    mnt.links.new(mlen.outputs['Value'], medg.inputs['Value'])
    msh = mnt.nodes.new('ShaderNodeMixShader')
    mnt.links.new(medg.outputs['Result'], msh.inputs['Fac']); mnt.links.new(mtr.outputs['BSDF'], msh.inputs[1]); mnt.links.new(mem.outputs['Emission'], msh.inputs[2])
    mnt.links.new(msh.outputs['Shader'], mout.inputs['Surface'])

    mbm = bmesh.new()
    bmesh.ops.create_circle(mbm, cap_ends=True, cap_tris=False, segments=64, radius=1.0)
    mme = bpy.data.meshes.new("V6_HorizonMoonPortal")
    mbm.to_mesh(mme); mbm.free()
    mme.materials.append(moon_mat)
    mob = bpy.data.objects.new("V6_HorizonMoonPortal", mme)
    moon_pos = _crest_f["pos"] + _crest_fwd_xy * 1650.0 + Vector((0.0, 0.0, 126.0))
    mob.location = moon_pos
    mob.rotation_euler = (-_crest_fwd_xy).to_track_quat('Z', 'Y').to_euler()
    mob.scale = (255.0, 255.0, 255.0)
    mob.visible_shadow = False
    COLLS["V6_05_Atmosphere_GodRays"].objects.link(mob)

    # Z = -5.0 m 巨型暗黑海港反光水面
    w_sz = 2800.0
    w_me = bpy.data.meshes.new("V6_HarborWater")
    w_me.from_pydata([
        (_cx - w_sz, _cy - w_sz, -5.0), (_cx + w_sz, _cy - w_sz, -5.0),
        (_cx + w_sz, _cy + w_sz, -5.0), (_cx - w_sz, _cy + w_sz, -5.0),
    ], [], [(0, 1, 2, 3)])
    w_me.update()
    w_me.materials.append(MAT_WATER)
    w_ob = bpy.data.objects.new("V6_HarborWater", w_me)
    COLLS["V6_03_SkyBridge_Bowl"].objects.link(w_ob)


build_skydome_and_moon()


# ---------------------------------------------------------------
# 6. 3D 倾角赛道主体 + 贴身 ±8.2m 赛博护栏 + 霓虹路肩（彻底告别 33m 空旷草坪！）
# ---------------------------------------------------------------
BARRIER_OFF = HALF_W + 1.2     # ±8.2 m 紧贴赛道，强烈摩纳哥街道/2099 速度压迫感！
BARRIER_H = 1.18


def build_3d_track_and_barriers():
    # A) 主路面厚板（上表面 5 段湿滑镜面沥青 + 下腹板钢箱梁包边，仰拍/航拍绝不穿帮薄片！）
    cols = (-HALF_W - 1.25, -HALF_W, -3.5, 0.0, 3.5, HALF_W, HALF_W + 1.25)
    nc = len(cols)
    tv, tfc, tuv, tmat = [], [], [], []
    idxs = list(range(N)) + [0]
    for k_i, idx in enumerate(idxs):
        fr = FRAMES[idx]
        p, r, u = fr["pos"], fr["right"], fr["up"]
        s_uv = (fr["s"] if k_i < N else LAP_LEN) / 10.0
        for ci, off in enumerate(cols):
            pt3 = p + r * off
            tv.append((pt3.x, pt3.y, pt3.z))
            tuv.append((ci / float(nc - 1), s_uv))
        # 下腹板底边两列（厚 0.95 m）
        b_l = p - r * (HALF_W + 1.25) - u * 0.95
        b_r = p + r * (HALF_W + 1.25) - u * 0.95
        tv.append((b_l.x, b_l.y, b_l.z)); tuv.append((0.0, s_uv))
        tv.append((b_r.x, b_r.y, b_r.z)); tuv.append((1.0, s_uv))

    stride = nc + 2
    for j in range(len(idxs) - 1):
        b0 = j * stride
        b1 = (j + 1) * stride
        for ci in range(nc - 1):
            tfc.append((b0 + ci, b0 + ci + 1, b1 + ci + 1, b1 + ci))
            tmat.append(0)
        # 左侧壁、右侧壁、底面（材质槽 1: MAT_STEEL）
        tfc.append((b0 + nc, b0 + 0, b1 + 0, b1 + nc)); tmat.append(1)
        tfc.append((b0 + nc - 1, b0 + nc + 1, b1 + nc + 1, b1 + nc - 1)); tmat.append(1)
        tfc.append((b0 + nc + 1, b0 + nc, b1 + nc, b1 + nc + 1)); tmat.append(1)

    me_tr = bpy.data.meshes.new("V6_TrackDeck")
    me_tr.from_pydata(tv, [], tfc)
    me_tr.validate(); me_tr.update()
    me_tr.materials.append(MAT_WET_ROAD)
    me_tr.materials.append(MAT_STEEL)
    uvl = me_tr.uv_layers.new(name="UVMap")
    for pi, poly in enumerate(me_tr.polygons):
        poly.material_index = tmat[pi]
        poly.use_smooth = (tmat[pi] == 0)
        for li in poly.loop_indices:
            uvl.data[li].uv = tuv[me_tr.loops[li].vertex_index]
    ob_tr = bpy.data.objects.new("V6_TrackDeck", me_tr)
    COLLS["V6_01_Track3D"].objects.link(ob_tr)

    # B) 赛道两侧发光边界白线 & 3D 弯道红白霓虹路肩 & ±8.2m 赛博混凝土护栏 + 顶部霓虹光带
    lines_bm = BatchMesh("V6_TrackLines_3D", "V6_01_Track3D")
    kerbs_bm = BatchMesh("V6_Kerbs_3D", "V6_01_Track3D")
    barr_bm = BatchMesh("V6_Barriers_3D", "V6_01_Track3D")

    for i in range(N):
        f0 = FRAMES[i]
        f1 = FRAMES[(i + 1) % N]
        for sgn in (-1.0, 1.0):
            # 发光边线 (+8mm 紧贴 0.000m 湿滑沥青表面，零闪烁零埋胎)
            la0 = f0["pos"] + f0["right"] * (sgn * (HALF_W - 0.22)) + f0["up"] * 0.008
            lb0 = f0["pos"] + f0["right"] * (sgn * (HALF_W - 0.06)) + f0["up"] * 0.008
            la1 = f1["pos"] + f1["right"] * (sgn * (HALF_W - 0.22)) + f1["up"] * 0.008
            lb1 = f1["pos"] + f1["right"] * (sgn * (HALF_W - 0.06)) + f1["up"] * 0.008
            lines_bm.add_quad(la0, lb0, lb1, la1, MAT_WHITE_LINE)

            # 弯道路肩 (|curv| > 0.0038)
            if abs(f0["curv"]) > 0.0038:
                km = MAT_KERB_A if (int(f0["s"] / 2.8) % 2 == 0) else MAT_KERB_B
                ka0 = f0["pos"] + f0["right"] * (sgn * HALF_W) + f0["up"] * 0.006
                kb0 = f0["pos"] + f0["right"] * (sgn * (HALF_W + 1.05)) + f0["up"] * 0.065
                ka1 = f1["pos"] + f1["right"] * (sgn * HALF_W) + f1["up"] * 0.006
                kb1 = f1["pos"] + f1["right"] * (sgn * (HALF_W + 1.05)) + f1["up"] * 0.065
                kerbs_bm.add_quad(ka0, kb0, kb1, ka1, km)

            # ±8.2m 紧贴护栏内表面 + 顶面 + 顶部连续霓虹灯带
            wa0 = f0["pos"] + f0["right"] * (sgn * BARRIER_OFF)
            wt0 = wa0 + f0["up"] * BARRIER_H
            wa1 = f1["pos"] + f1["right"] * (sgn * BARRIER_OFF)
            wt1 = wa1 + f1["up"] * BARRIER_H
            wo0 = wt0 + f0["right"] * (sgn * 0.36)
            wo1 = wt1 + f1["right"] * (sgn * 0.36)
            if sgn < 0:
                barr_bm.add_quad(wa0, wa1, wt1, wt0, MAT_BARRIER)
                barr_bm.add_quad(wt0, wt1, wo1, wo0, MAT_CONCRETE)
            else:
                barr_bm.add_quad(wa1, wa0, wt0, wt1, MAT_BARRIER)
                barr_bm.add_quad(wt1, wt0, wo0, wo1, MAT_CONCRETE)
            # 护栏内上沿双色霓虹光带（在湿滑沥青边缘拉出一条连续流光倒影！）
            ns0 = f0["pos"] + f0["right"] * (sgn * (BARRIER_OFF - 0.04)) + f0["up"] * (BARRIER_H - 0.14)
            nt0 = ns0 + f0["up"] * 0.11
            ns1 = f1["pos"] + f1["right"] * (sgn * (BARRIER_OFF - 0.04)) + f1["up"] * (BARRIER_H - 0.14)
            nt1 = ns1 + f1["up"] * 0.11
            nmat = MAT_NEON_CYAN if sgn < 0 else MAT_NEON_MAG
            barr_bm.add_quad(ns0, ns1, nt1, nt0, nmat)

        # 每 14m 一对倾斜赛博防撞网立柱（隧道段跳过，由隧道激光肋接管）
        if i % 7 == 0 and not f0["tunnel"]:
            for sgn in (-1.0, 1.0):
                p_post = f0["pos"] + f0["right"] * (sgn * (BARRIER_OFF + 0.18)) + f0["up"] * (BARRIER_H + 1.4)
                barr_bm.add_oriented_box(p_post, f0["fwd"], f0["right"], f0["up"], 0.16, 0.16, 2.8, MAT_STEEL)

    lines_bm.build(cast_shadow=False)
    kerbs_bm.build(cast_shadow=False)
    barr_bm.build(cast_shadow=True)


build_3d_track_and_barriers()


# ---------------------------------------------------------------
# 7. 五大蜘蛛侠史诗级奇观场景 (5 Monumental Spider-Verse Set-Pieces)
# ---------------------------------------------------------------
def min_xy_dist_to_track(x, y, step=3):
    return min(hypot(x - FRAMES[k]["pos"].x, y - FRAMES[k]["pos"].y) for k in range(0, N, step))


def build_five_setpieces():
    city_bm = BatchMesh("V6_Megacity_Skyscrapers", "V6_02_Megacity")
    far_city_bm = BatchMesh("V6_Megacity_FarSkyline", "V6_02_Megacity")
    sign_bm = BatchMesh("V6_Megacity_NeonSigns", "V6_02_Megacity")
    arch_bm = BatchMesh("V6_Canyon_ViaductArches", "V6_02_Megacity")
    brdg_bm = BatchMesh("V6_SkyBridge_Structure", "V6_03_SkyBridge_Bowl")
    cabl_bm = BatchMesh("V6_SkyBridge_StayCables", "V6_03_SkyBridge_Bowl")
    bowl_bm = BatchMesh("V6_BankedBowl_NeonWall", "V6_03_SkyBridge_Bowl")
    tunn_bm = BatchMesh("V6_StrobeTunnel_Vault", "V6_04_StrobeTunnel_Harbor")
    ribs_bm = BatchMesh("V6_StrobeTunnel_LaserRibs", "V6_04_StrobeTunnel_Harbor")
    harb_bm = BatchMesh("V6_Harbor_PropsGantries", "V6_04_StrobeTunnel_Harbor")
    gray_bm = BatchMesh("V6_FauxVolumetric_GodRays", "V6_05_Atmosphere_GodRays")

    rng = random.Random(2099)

    # ① 起终点赛博龙门架 (s ~ 24m) + Neo-Monaco 赛博维修区车库长廊 (s = 36..228m, 右侧外立面)
    f_sf = frame_at_s(24.0)
    for sgn in (-1.0, 1.0):
        c_leg = f_sf["pos"] + f_sf["right"] * (sgn * (BARRIER_OFF + 0.8)) + f_sf["up"] * 4.2
        arch_bm.add_oriented_box(c_leg, f_sf["fwd"], f_sf["right"], f_sf["up"], 0.7, 0.7, 8.4, MAT_STEEL)
    c_beam = f_sf["pos"] + f_sf["up"] * 8.2
    arch_bm.add_oriented_box(c_beam, f_sf["right"], f_sf["fwd"], f_sf["up"], (BARRIER_OFF + 1.2) * 2.0, 0.9, 1.2, MAT_STEEL)
    arch_bm.add_oriented_box(c_beam - f_sf["fwd"] * 0.52, f_sf["right"], f_sf["fwd"], f_sf["up"], HALF_W * 2.0, 0.10, 0.95, MAT_AD)

    for k_pit in range(6):
        fp = frame_at_s(52.0 + k_pit * 30.0)
        cp = fp["pos"] + fp["right"] * (BARRIER_OFF + 5.8) + fp["up"] * 3.8
        arch_bm.add_oriented_box(cp, fp["fwd"], fp["right"], fp["up"], 28.5, 6.2, 7.6, MAT_GARAGE, uv_tile=(1.0, 1.0))
        arch_bm.add_oriented_box(cp + fp["up"] * 3.95 - fp["right"] * 3.15, fp["fwd"], fp["right"], fp["up"], 28.5, 0.22, 0.22, MAT_NEON_CYAN)

    def _in_moon_sightline(bx, by):
        dx = bx - _crest_f["pos"].x
        dy = by - _crest_f["pos"].y
        along = dx * _crest_fwd_xy.x + dy * _crest_fwd_xy.y
        lat = abs(dx * _crest_rgt_xy.x + dy * _crest_rgt_xy.y)
        return (-40.0 < along < 1750.0) and (lat < 165.0)

    # ② 峡谷摩天楼群 & Eau-Rouge 爬坡天际线（紧贴护栏外 14..46m，高 55..225m，严格验证绝不侵入任何赛段与次元月走廊！）
    placed_towers = []
    for idx in range(0, N, 14):   # 每 28 m 沿线两侧尝试生成紧贴峡谷的摩天楼
        fr = FRAMES[idx]
        if fr["bridge"]:
            continue
        for sgn in (-1.0, 1.0):
            w = rng.uniform(18.0, 30.0)
            d = rng.uniform(18.0, 30.0)
            half_diag = 0.5 * hypot(w, d)
            pit_pad = 9.5 if (sgn > 0 and 30.0 <= fr["s"] <= 245.0) else 0.0
            dist_out = BARRIER_OFF + half_diag + pit_pad + rng.uniform(4.5, 18.0)
            bx = fr["pos"].x + fr["right"].x * (sgn * dist_out)
            by = fr["pos"].y + fr["right"].y * (sgn * dist_out)
            if _in_moon_sightline(bx, by):
                continue
            # 安全净距检查：距全圈任意赛道中心线 XY >= BARRIER_OFF + half_diag + 3.0m，且不与已放塔楼重叠
            if min_xy_dist_to_track(bx, by, step=2) < (BARRIER_OFF + half_diag + 3.0):
                continue
            if any(hypot(bx - ox, by - oy) < (half_diag + odiag - 2.0) for ox, oy, odiag in placed_towers):
                continue
            placed_towers.append((bx, by, half_diag))

            hgt = rng.uniform(75.0, 225.0) if fr["zone"] in ("canyon_grid", "eau_rouge_climb") else rng.uniform(55.0, 165.0)
            base_z = -5.0
            total_h = (fr["pos"].z + hgt) - base_z
            center_b = Vector((bx, by, base_z + total_h * 0.5))
            ax_f = Vector((cos(fr["h"]), sin(fr["h"]), 0.0))
            ax_r = Vector((sin(fr["h"]), -cos(fr["h"]), 0.0))
            ax_u = Vector((0.0, 0.0, 1.0))

            city_bm.add_oriented_box(center_b, ax_f, ax_r, ax_u, w, d, total_h, MAT_FACADE,
                                     uv_tile=(max(1.0, round(w / 18.0)), max(1.0, round(total_h / 55.0))))
            # 塔冠退台霓虹边框
            crown_c = Vector((bx, by, base_z + total_h + 1.2))
            n_mat = MAT_NEON_CYAN if (len(placed_towers) % 3 == 0) else (MAT_NEON_MAG if len(placed_towers) % 3 == 1 else MAT_NEON_GOLD)
            city_bm.add_oriented_box(crown_c, ax_f, ax_r, ax_u, w * 0.92, d * 0.92, 0.65, n_mat)

            # 面向赛道的巨幅竖向赛博漫画霓虹招牌
            sign_h = min(46.0, hgt * 0.52)
            sign_c = Vector((
                bx - fr["right"].x * (sgn * (d * 0.5 + 0.45)),
                by - fr["right"].y * (sgn * (d * 0.5 + 0.45)),
                fr["pos"].z + 8.0 + sign_h * 0.5,
            ))
            slot = len(placed_towers) % 4
            sign_bm.add_oriented_box(sign_c, ax_f, ax_r, ax_u, 4.4, 0.35, sign_h, MAT_SIGNS,
                                     uv_tile=(0.24, 0.96), uv_off=(slot * 0.25 + 0.005, 0.02))

    # 外围远景天际线环（填满 360° 视野，同时留空次元巨月视线走廊！）
    for k_ring in range(44):
        ang = 2.0 * pi * k_ring / 44.0 + rng.uniform(-0.04, 0.04)
        rad = rng.uniform(520.0, 880.0)
        rx = _cx + cos(ang) * rad
        ry = _cy + sin(ang) * rad
        if _in_moon_sightline(rx, ry) or min_xy_dist_to_track(rx, ry, step=4) < 95.0:
            continue
        rw, rd = rng.uniform(36.0, 68.0), rng.uniform(36.0, 68.0)
        rh = rng.uniform(95.0, 260.0)
        ax_f = Vector((-sin(ang), cos(ang), 0.0))
        ax_r = Vector((cos(ang), sin(ang), 0.0))
        far_city_bm.add_oriented_box(Vector((rx, ry, -5.0 + rh * 0.5)), ax_f, ax_r, Vector((0, 0, 1)),
                                     rw, rd, rh, MAT_FACADE, uv_tile=(2.0, max(1.0, round(rh / 65.0))))

    # 城市峡谷段跨街赛博过街天桥拱门（净高 8.8 m，绝不挡任何镜头）
    canyon_idxs = [i for i, f in enumerate(FRAMES) if f["zone"] == "canyon_grid"]
    for step_a in canyon_idxs[::55][:3]:
        fa = FRAMES[step_a]
        for sgn in (-1.0, 1.0):
            pl = fa["pos"] + fa["right"] * (sgn * (BARRIER_OFF + 1.1)) + fa["up"] * 4.6
            arch_bm.add_oriented_box(pl, fa["fwd"], fa["right"], fa["up"], 1.8, 0.9, 9.2, MAT_CONCRETE)
        top_a = fa["pos"] + fa["up"] * 9.0
        arch_bm.add_oriented_box(top_a, fa["right"], fa["fwd"], fa["up"], (BARRIER_OFF + 1.6) * 2.0, 2.2, 1.1, MAT_STEEL)
        arch_bm.add_oriented_box(top_a - fa["up"] * 0.62, fa["right"], fa["fwd"], fa["up"], HALF_W * 2.1, 0.25, 0.16, MAT_NEON_CYAN)

    # ③ 跨海斜拉天空大桥 (sky_bridge)：双 115m 巨型 H 型索塔 + 发光青/金扇形斜拉索网 + 桥下钢箱梁桥墩
    bridge_idxs = [i for i, f in enumerate(FRAMES) if f["bridge"] or f["zone"] == "sky_bridge"]
    for idx in range(0, N, 20):
        fb = FRAMES[idx]
        if fb["pos"].z > 6.5 and not fb["tunnel"]:
            # 高架混凝土双柱桥墩直插海面 Z=-5m
            pier_top = fb["pos"] - fb["up"] * 1.1
            pier_h = pier_top.z - (-5.0)
            if pier_h > 2.0:
                for sgn in (-1.0, 1.0):
                    pxy = pier_top + fb["right"] * (sgn * 4.8)
                    brdg_bm.add_oriented_box(Vector((pxy.x, pxy.y, -5.0 + pier_h * 0.5)),
                                             Vector((cos(fb["h"]), sin(fb["h"]), 0.0)),
                                             Vector((sin(fb["h"]), -cos(fb["h"]), 0.0)),
                                             Vector((0, 0, 1)), 1.6, 1.6, pier_h, MAT_CONCRETE)

    if len(bridge_idxs) >= 20:
        t1_i = bridge_idxs[int(len(bridge_idxs) * 0.28)]
        t2_i = bridge_idxs[int(len(bridge_idxs) * 0.72)]
        for t_ord, ti in enumerate((t1_i, t2_i)):
            ft = FRAMES[ti]
            tower_off = BARRIER_OFF + 4.8     # ±13.0 m 巨型双立柱
            tower_top_z = ft["pos"].z + 115.0
            tower_h = tower_top_z - (-5.0)
            ax_f = Vector((cos(ft["h"]), sin(ft["h"]), 0.0))
            ax_r = Vector((sin(ft["h"]), -cos(ft["h"]), 0.0))
            ax_u = Vector((0.0, 0.0, 1.0))
            for sgn in (-1.0, 1.0):
                leg_xy = ft["pos"] + ax_r * (sgn * tower_off)
                brdg_bm.add_oriented_box(Vector((leg_xy.x, leg_xy.y, -5.0 + tower_h * 0.5)),
                                         ax_f, ax_r, ax_u, 3.8, 3.2, tower_h, MAT_STEEL)
                # 索塔竖向发光导光槽
                brdg_bm.add_oriented_box(Vector((leg_xy.x, leg_xy.y, ft["pos"].z + 56.0)),
                                         ax_f, ax_r, ax_u, 0.45, 3.45, 108.0,
                                         MAT_NEON_CYAN if t_ord == 0 else MAT_NEON_GOLD)
            # H 型索塔三道高空横梁（净高 +38m / +76m / +110m）
            for hz_rel in (38.0, 76.0, 110.0):
                cb_p = Vector((ft["pos"].x, ft["pos"].y, ft["pos"].z + hz_rel))
                brdg_bm.add_oriented_box(cb_p, ax_r, ax_f, ax_u, tower_off * 2.0 + 3.2, 3.0, 3.4, MAT_STEEL)
                brdg_bm.add_oriented_box(cb_p - Vector((0, 0, 1.85)), ax_r, ax_f, ax_u, tower_off * 1.9, 0.5, 0.35, MAT_NEON_MAG)

            # 扇形发光斜拉索阵列（每座塔前后各 7 对斜拉索，直连桥面护栏外侧！）
            for step_c in range(-42, 49, 12):
                if abs(step_c) < 8:
                    continue
                fc_anch = frame_at(ti + step_c)
                h_anchor = ft["pos"].z + 62.0 + abs(step_c) * 1.05
                c_mat = MAT_NEON_CYAN if (abs(step_c) // 12) % 2 == 0 else MAT_NEON_GOLD
                for sgn in (-1.0, 1.0):
                    p_top = Vector((ft["pos"].x, ft["pos"].y, h_anchor)) + ax_r * (sgn * tower_off)
                    p_bot = fc_anch["pos"] + fc_anch["right"] * (sgn * (BARRIER_OFF + 0.65)) + fc_anch["up"] * 1.15
                    cabl_bm.add_beam(p_top, p_bot, 0.085, c_mat)

    # ④ 17.4° 倾角巨碗弯外侧弧形霓虹防护高墙 (banked_bowl_plunge: 置于抬高外缘，为贴墙轨道机位提供极致参照物！)
    for i in range(N - 1):
        fb0, fb1 = FRAMES[i], FRAMES[(i + 1) % N]
        if abs(math.degrees(fb0["b_eff"])) > 6.5:
            # 弯外侧即抬高(+Z)的一侧：按 @track 正交基 R = cos(bk)*R0 - sin(bk)*U0，直接取 (right*sgn).z > 0 的高侧！
            out_sgn = 1.0 if fb0["right"].z >= 0.0 else -1.0
            w0_b = fb0["pos"] + fb0["right"] * (out_sgn * (BARRIER_OFF + 0.25)) + fb0["up"] * BARRIER_H
            w0_t = w0_b + fb0["up"] * 4.2
            w1_b = fb1["pos"] + fb1["right"] * (out_sgn * (BARRIER_OFF + 0.25)) + fb1["up"] * BARRIER_H
            w1_t = w1_b + fb1["up"] * 4.2
            wmat = MAT_BARRIER if (i % 4 == 0) else MAT_STEEL
            bowl_bm.add_quad(w0_b, w1_b, w1_t, w0_t, wmat)
            bowl_bm.add_quad(w1_b, w0_b, w0_t, w1_t, wmat)
            inw = -out_sgn * 0.05
            for h_str, smat in ((1.4, MAT_NEON_CYAN), (2.8, MAT_NEON_MAG), (4.1, MAT_NEON_GOLD)):
                s0a = w0_b + fb0["right"] * inw + fb0["up"] * h_str
                s0b = s0a + fb0["up"] * 0.18
                s1a = w1_b + fb1["right"] * inw + fb1["up"] * h_str
                s1b = s1a + fb1["up"] * 0.18
                bowl_bm.add_quad(s0a, s1a, s1b, s0b, smat)
                bowl_bm.add_quad(s1a, s0a, s0b, s1b, smat)

    # ⑤ 450m 封闭式赛博激光频闪隧道 (tunnel == True)：暗黑六角拱顶 + 每 12m 一道高能绯红/电青激光肋拱！
    tunnel_idxs = [i for i, f in enumerate(FRAMES) if f["tunnel"]]
    vault_pts = [
        (-BARRIER_OFF - 0.3, 0.0),
        (-BARRIER_OFF - 0.9, 4.2),
        (-5.2, 8.2),
        (5.2, 8.2),
        (BARRIER_OFF + 0.9, 4.2),
        (BARRIER_OFF + 0.3, 0.0),
    ]
    for i in range(N):
        ft0 = FRAMES[i]
        ft1 = FRAMES[(i + 1) % N]
        if not ft0["tunnel"]:
            continue
        for vi in range(len(vault_pts) - 1):
            ox0, oz0 = vault_pts[vi]
            ox1, oz1 = vault_pts[vi + 1]
            q0 = ft0["pos"] + ft0["right"] * ox0 + ft0["up"] * oz0
            q1 = ft0["pos"] + ft0["right"] * ox1 + ft0["up"] * oz1
            q2 = ft1["pos"] + ft1["right"] * ox1 + ft1["up"] * oz1
            q3 = ft1["pos"] + ft1["right"] * ox0 + ft1["up"] * oz0
            # 内壁朝向隧道中心 + 外壳封闭阻挡日光
            tunn_bm.add_quad(q1, q0, q3, q2, MAT_TUNNEL_WALL)
            tunn_bm.add_quad(q0, q1, q2, q3, MAT_TUNNEL_WALL)

        # 隧道穹顶纵向双道引导灯带
        for sgn in (-1.0, 1.0):
            ca0 = ft0["pos"] + ft0["right"] * (sgn * 2.6) + ft0["up"] * 8.05
            cb0 = ft0["pos"] + ft0["right"] * (sgn * 2.9) + ft0["up"] * 8.05
            ca1 = ft1["pos"] + ft1["right"] * (sgn * 2.6) + ft1["up"] * 8.05
            cb1 = ft1["pos"] + ft1["right"] * (sgn * 2.9) + ft1["up"] * 8.05
            ribs_bm.add_quad(ca0, cb0, cb1, ca1, MAT_NEON_CYAN if sgn < 0 else MAT_NEON_MAG)

        # 每 12 m (i % 6 == 0) 一座高能六角激光灯肋拱架，让 340km/h 车身与湿滑地面产生炸裂频闪流光！
        if i % 6 == 0:
            rmat = MAT_NEON_MAG if ((i // 6) % 2 == 0) else MAT_NEON_CYAN
            for vi in range(len(vault_pts) - 1):
                ox0, oz0 = vault_pts[vi]
                ox1, oz1 = vault_pts[vi + 1]
                p_a = ft0["pos"] + ft0["right"] * (ox0 * 0.96) + ft0["up"] * (oz0 * 0.97)
                p_b = ft0["pos"] + ft0["right"] * (ox1 * 0.96) + ft0["up"] * (oz1 * 0.97)
                ribs_bm.add_beam(p_a, p_b, 0.16, rmat)

    # 隧道出口耀眼门廊 + 海港重刹发夹弯 150/100/50m 刹车牌与巨幕
    if tunnel_idxs:
        t_exit_i = tunnel_idxs[-1]
        fe = FRAMES[t_exit_i]
        # 隧道出口爆发丁达尔光束片（置于赛道两侧护栏外斜照高空，零阻挡视线！）
        for k_g in range(4):
            fg = frame_at(t_exit_i + 4 + k_g * 5)
            for sgn in (-1.0, 1.0):
                b0 = fg["pos"] + fg["right"] * (sgn * (BARRIER_OFF + 1.5))
                b1 = b0 + fg["fwd"] * 9.0
                t1 = b1 + Vector((0, 0, 48.0)) - fg["right"] * (sgn * 6.0)
                t0 = b0 + Vector((0, 0, 48.0)) - fg["right"] * (sgn * 6.0)
                gray_bm.add_quad(b0, b1, t1, t0, MAT_GODRAY_B if k_g % 2 == 0 else MAT_GODRAY_A)

    # 城市峡谷丁达尔斜射神光片（摩天楼缝隙斜切而下）
    for idx_g in range(18, N, max(1, N // 10)):
        fg = FRAMES[idx_g]
        if fg["tunnel"]:
            continue
        sgn = 1.0 if (idx_g % 2 == 0) else -1.0
        b0 = fg["pos"] + fg["right"] * (sgn * (BARRIER_OFF + 3.5))
        b1 = b0 + fg["fwd"] * 14.0
        t1 = b1 + Vector((0, 0, 75.0)) + fg["right"] * (sgn * 12.0)
        t0 = b0 + Vector((0, 0, 75.0)) + fg["right"] * (sgn * 12.0)
        gray_bm.add_quad(b0, b1, t1, t0, MAT_GODRAY_A if sgn > 0 else MAT_GODRAY_B)

    # 自动寻找全圈最重刹车发夹弯（Harbor Hairpin 等），在弯前 150/100/50 m 护栏外布置正对来车的漫画刹车牌 + 大屏
    min_v_i = min(range(N), key=lambda k: FRAMES[k]["v"])
    s_hairpin = FRAMES[min_v_i]["s"]
    out_hp = -1.0 if FRAMES[min_v_i]["curv"] > 0 else 1.0
    for d_m, lbl in ((150.0, "150"), (100.0, "100"), (50.0, "50")):
        fbk = frame_at_s(s_hairpin - d_m)
        cbk = fbk["pos"] + fbk["right"] * (out_hp * (BARRIER_OFF + 1.1)) + fbk["up"] * 2.1
        harb_bm.add_oriented_box(cbk, fbk["right"], fbk["fwd"], fbk["up"], 1.5, 0.12, 1.0, MAT_BRAKE[lbl])
    # 发夹弯外侧巨型霓虹直播大屏 + 维修区直道侧翼漫画车库外立面
    f_scr = frame_at_s(s_hairpin + 18.0)
    c_scr = f_scr["pos"] + f_scr["right"] * (out_hp * (BARRIER_OFF + 7.5)) + f_scr["up"] * 8.5
    harb_bm.add_oriented_box(c_scr, f_scr["fwd"], f_scr["right"], f_scr["up"], 22.0, 0.6, 12.4, MAT_SCREEN)

    # 沿全圈非隧道段护栏外侧布置漫画广告灯箱与 DRS 标志牌
    for idx_ad in range(12, N, 32):
        fad = FRAMES[idx_ad]
        if fad["tunnel"]:
            continue
        sgn = 1.0 if ((idx_ad // 32) % 2 == 0) else -1.0
        cad = fad["pos"] + fad["right"] * (sgn * (BARRIER_OFF + 0.55)) + fad["up"] * (BARRIER_H + 0.85)
        slot = (idx_ad // 32) % 4
        harb_bm.add_oriented_box(cad, fad["fwd"], fad["right"], fad["up"], 9.5, 0.18, 1.65, MAT_AD,
                                 uv_tile=(0.24, 0.96), uv_off=(slot * 0.25 + 0.005, 0.02))
    for s_drs in (LAP_LEN * 0.34, LAP_LEN * 0.72):
        fd = frame_at_s(s_drs)
        cd = fd["pos"] + fd["right"] * (BARRIER_OFF + 1.0) + fd["up"] * 2.2
        harb_bm.add_oriented_box(cd, fd["right"], fd["fwd"], fd["up"], 1.5, 0.12, 1.0, MAT_DRS)

    city_bm.build(cast_shadow=True)
    far_city_bm.build(cast_shadow=False)
    sign_bm.build(cast_shadow=False)
    arch_bm.build(cast_shadow=True)
    brdg_bm.build(cast_shadow=True)
    cabl_bm.build(cast_shadow=False)
    bowl_bm.build(cast_shadow=True)
    tunn_bm.build(cast_shadow=False)    # 关键：隧道拱顶不挡日光阴影，避免隧道内 ShaderToRGB 漫反射辐照度坍缩为 0！
    ribs_bm.build(cast_shadow=False)
    harb_bm.build(cast_shadow=False)
    gray_bm.build(cast_shadow=False)
    print(f"Megacity towers placed: {len(placed_towers)} | Tunnel samples: {len(tunnel_idxs)} | Bridge samples: {len(bridge_idxs)}")


build_five_setpieces()


# ---------------------------------------------------------------
# 8. 英雄赛车漫画着色器 + 3D 可变线宽手绘墨线 + 炸裂级 V6_09_ComicFX 特效组
#    (马赫激波环双尾焰 + 金白钛合金底板火花长束 + 尾翼螺旋涡流带 + 雨胎霓虹水雾鸡尾酒喷流 + 轮毂残影弧)
# ---------------------------------------------------------------
def style_car_and_outlines():
    car_specs = {
        "Mat_RedBull_MatteNavy": ((0.055, 0.072, 0.30), 0.96, 92.0, 0.68, 0.72, 0.38),
        "Mat_RedBull_Crimson": ((0.98, 0.04, 0.22), 0.94, 92.0, 0.62, 0.52, 0.32),
        "Mat_RedBull_SolarYellow": ((1.00, 0.78, 0.03), 0.90, 92.0, 0.58, 0.45, 0.30),
        "Mat_Merc_Petronas": ((0.0, 0.90, 0.84), 0.92, 92.0, 0.58, 0.48, 0.30),
        "Mat_Merc_Silver": ((0.78, 0.84, 0.96), 0.92, 92.0, 0.52, 0.45, 0.38),
        "Mat_Forged_Carbon": ((0.072, 0.085, 0.21), 0.90, 98.0, 0.64, 0.66, 0.26),
        "Mat_Carbon_Satin": ((0.082, 0.096, 0.23), 0.88, 98.0, 0.60, 0.62, 0.24),
        "Mat_Carbon_Endplate_Matte": ((0.068, 0.078, 0.19), 0.92, 96.0, 0.62, 0.64, 0.24),
        "Mat_Duct_Carbon": ((0.060, 0.070, 0.17), 0.82, 98.0, 0.58, 0.58, 0.18),
        "Mat_Tire_Slick_Compound": ((0.045, 0.048, 0.105), 0.92, 90.0, 0.60, 0.65, 0.28),
        "Mat_Rim_Forged_Dark": ((0.088, 0.102, 0.245), 0.92, 98.0, 0.58, 0.58, 0.30),
        "Mat_Rim_Machined_Lip": ((0.86, 0.90, 0.98), 0.92, 98.0, 0.45, 0.35, 0.40),
        "Mat_Liquid_Titanium": ((0.80, 0.86, 0.98), 0.95, 96.0, 0.52, 0.42, 0.42),
        "Mat_Titanium_Hardware": ((0.74, 0.80, 0.94), 0.85, 98.0, 0.45, 0.40, 0.35),
        "Mat_Anodized_Gold": ((1.00, 0.74, 0.06), 0.88, 98.0, 0.52, 0.42, 0.35),
        "Mat_CenterLock_Cyan": ((0.0, 0.92, 0.98), 0.92, 98.0, 0.50, 0.40, 0.35),
        "Mat_Inconel_GoldHeatShield": ((1.00, 0.72, 0.08), 0.88, 98.0, 0.52, 0.42, 0.35),
        "Mat_Exhaust_Titanium": ((0.42, 0.48, 0.74), 0.90, 98.0, 0.52, 0.48, 0.35),
        "Mat_Radiator_Mesh": ((0.12, 0.14, 0.26), 0.60, 102.0, 0.50, 0.55, 0.10),
        "Mat_Seatbelt_Webbing": ((0.96, 0.06, 0.24), 0.75, 98.0, 0.50, 0.45, 0.05),
        "Mat_PZero_White": ((0.94, 0.95, 0.98), 0.75, 98.0, 0.35, 0.30, 0.10),
    }
    for mn, (rgb, rm, hs, hts, hcs, ct) in car_specs.items():
        if bpy.data.materials.get(mn):
            make_comic_mat(mn, rgb, rim=rm, ht_sc=hs, ht_s=hts, hc_s=hcs, coat=ct)

    # 保留贴花 Alpha 与轮胎侧壁贴图的漫画转化
    for mn in ("Mat_DEC_Engine_RedBull", "Mat_DEC_Halo_Oracle", "Mat_DEC_Nose_Livery",
               "Mat_DEC_Sidepod_Oracle", "Mat_PZero_Pirelli_Sidewall"):
        m = bpy.data.materials.get(mn)
        if m and m.node_tree:
            tn_old = next((n for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image), None)
            if tn_old:
                img = tn_old.image
                nt = m.node_tree; nt.nodes.clear()
                out = nt.nodes.new('ShaderNodeOutputMaterial')
                tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = img
                grp = nt.nodes.new('ShaderNodeGroup'); grp.node_tree = NG_COMIC
                add_dim_driver(grp.inputs['SV Dimension'], "default_value", "dim")
                grp.inputs['Rim Strength'].default_value = 0.65
                grp.inputs['Neon Coat'].default_value = 0.25
                nt.links.new(tn.outputs['Color'], grp.inputs['Base Color'])
                if mn.startswith("Mat_DEC_"):
                    try:
                        m.surface_render_method = 'DITHERED'
                    except Exception:
                        pass
                    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
                    mx = nt.nodes.new('ShaderNodeMixShader')
                    nt.links.new(tn.outputs['Alpha'], mx.inputs['Fac'])
                    nt.links.new(tr.outputs['BSDF'], mx.inputs[1])
                    nt.links.new(grp.outputs['Shader'], mx.inputs[2])
                    nt.links.new(mx.outputs['Shader'], out.inputs['Surface'])
                else:
                    nt.links.new(grp.outputs['Shader'], out.inputs['Surface'])

    # 车身自带青色 LED 灯带随三幕变色增强（倒映在湿滑路面上！）
    m_nc = bpy.data.materials.get("Mat_Neon_Cyan")
    if m_nc:
        make_neon_mat("Mat_Neon_Cyan", (0.0, 0.96, 1.0), (0.12, 1.0, 0.86), (1.0, 0.03, 0.18), strength=10.5)

    # 独立 FIA 尾部雨灯 Mat_FIA_RainLight + 径向热辐射碳陶刹车盘 Mat_BrakeDisc_CarbonCeramic + 卡钳
    rl_ob = bpy.data.objects.get("GEO_F1_FIA_RainLight")
    if rl_ob and hasattr(rl_ob.data, "materials"):
        m_fia = bpy.data.materials.get("Mat_FIA_RainLight") or bpy.data.materials.new("Mat_FIA_RainLight")
        m_fia.use_nodes = True
        fnt = m_fia.node_tree; fnt.nodes.clear()
        fb = fnt.nodes.new("ShaderNodeBsdfPrincipled")
        fb.inputs['Base Color'].default_value = (0.12, 0.005, 0.01, 1.0)
        fb.inputs['Roughness'].default_value = 0.18
        fb.inputs['Emission Color'].default_value = (1.0, 0.02, 0.04, 1.0)
        fb.inputs['Emission Strength'].default_value = 4.5
        fout = fnt.nodes.new("ShaderNodeOutputMaterial")
        fnt.links.new(fb.outputs['BSDF'], fout.inputs['Surface'])
        if rl_ob.data.materials:
            rl_ob.data.materials[0] = m_fia
        else:
            rl_ob.data.materials.append(m_fia)

    mdisc = bpy.data.materials.get("Mat_BrakeDisc_CarbonCeramic")
    if mdisc and mdisc.node_tree:
        dnt = mdisc.node_tree
        db = next((n for n in dnt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if db:
            dtc = next((n for n in dnt.nodes if n.type == 'TEX_COORD'), None) or dnt.nodes.new('ShaderNodeTexCoord')
            dsub = dnt.nodes.new('ShaderNodeVectorMath'); dsub.operation = 'MULTIPLY'; dsub.inputs[1].default_value = (0.0, 1.0, 1.0)
            dlen = dnt.nodes.new('ShaderNodeVectorMath'); dlen.operation = 'LENGTH'
            drmp = dnt.nodes.new('ShaderNodeValToRGB')
            drmp.color_ramp.elements[0].position = 0.085; drmp.color_ramp.elements[0].color = (0.02, 0.0, 0.01, 1.0)
            de1 = drmp.color_ramp.elements.new(0.138); de1.color = (1.0, 0.24, 0.03, 1.0)
            drmp.color_ramp.elements[-1].position = 0.186; drmp.color_ramp.elements[-1].color = (0.65, 0.04, 0.08, 1.0)
            dnt.links.new(dtc.outputs['Object'], dsub.inputs[0])
            dnt.links.new(dsub.outputs['Vector'], dlen.inputs[0])
            dnt.links.new(dlen.outputs['Value'], drmp.inputs['Fac'])
            dnt.links.new(drmp.outputs['Color'], db.inputs['Emission Color'])
            db.inputs['Emission Strength'].default_value = 0.0

    # 3D 可变线宽手绘墨线轮廓 (Solidify Inverted-Hull, use_rim=False, 距离自适应收敛)
    def _ink_mat(nm, max_d):
        m = bpy.data.materials.get(nm) or bpy.data.materials.new(nm)
        m.use_nodes = True
        m.use_backface_culling = True
        try:
            m.use_backface_culling_shadow = True
            m.surface_render_method = 'DITHERED'
        except Exception:
            pass
        nt = m.node_tree; nt.nodes.clear()
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        tr = nt.nodes.new('ShaderNodeBsdfTransparent')
        em = nt.nodes.new('ShaderNodeEmission')
        em.inputs['Color'].default_value = (0.0008, 0.0005, 0.0038, 1.0)
        em.inputs['Strength'].default_value = 1.0
        camd = nt.nodes.new('ShaderNodeCameraData')
        df = nt.nodes.new('ShaderNodeMapRange')
        df.inputs['From Min'].default_value = max_d * 0.45
        df.inputs['From Max'].default_value = max_d
        df.inputs['To Min'].default_value = 1.0
        df.inputs['To Max'].default_value = 0.12
        nt.links.new(camd.outputs['View Z Depth'], df.inputs['Value'])
        mx = nt.nodes.new('ShaderNodeMixShader')
        nt.links.new(df.outputs['Result'], mx.inputs['Fac'])
        nt.links.new(tr.outputs['BSDF'], mx.inputs[1])
        nt.links.new(em.outputs['Emission'], mx.inputs[2])
        nt.links.new(mx.outputs['Shader'], out.inputs['Surface'])
        return m

    ink_hero = _ink_mat("MAT_SV_InkOutline", 135.0)
    ink_thin = _ink_mat("MAT_SV_InkOutline_Thin", 42.0)
    pri = (
        "GEO_F1_Monocoque_Chassis", "GEO_F1_Nosecone", "GEO_F1_EngineCowl_Body",
        "GEO_F1_Underbody_Floor", "GEO_F1_Airbox_Scoop", "GEO_F1_Dorsal_SharkFin",
        "GEO_F1_Sidepod_IntakeLip_L", "GEO_F1_Sidepod_IntakeLip_R",
        "GEO_F1_Tire_FL", "GEO_F1_Tire_FR", "GEO_F1_Tire_RL", "GEO_F1_Tire_RR",
        "GEO_F1_Rim_FL", "GEO_F1_Rim_FR", "GEO_F1_Rim_RL", "GEO_F1_Rim_RR",
    )
    thn = (
        "GEO_F1_FrontWing_Mainplane", "GEO_F1_RearWing_Mainplane", "GEO_F1_RearWing_DRSFlap",
        "GEO_F1_RearWing_Endplate_L", "GEO_F1_RearWing_Endplate_R", "GEO_F1_RearWing_Pylon",
        "GEO_F1_Halo_CenterPylon", "GEO_F1_Halo_Hoop", "GEO_F1_Cockpit_SteeringWheel",
        "GEO_F1_AeroMirror_L", "GEO_F1_AeroMirror_R", "GEO_F1_Diffuser_Ramp",
    )
    for onm, thk, imat in (*[(n, 0.0085, ink_hero) for n in pri], *[(n, 0.0042, ink_thin) for n in thn]):
        ob = bpy.data.objects.get(onm)
        if not ob or not hasattr(ob.data, "materials"):
            continue
        if min(abs(ob.scale.x), abs(ob.scale.y), abs(ob.scale.z)) < 0.15:
            continue
        if imat.name not in [m.name for m in ob.data.materials if m]:
            ob.data.materials.append(imat)
        idx_s = [m.name if m else "" for m in ob.data.materials].index(imat.name)
        mod = ob.modifiers.get("SV_InkHull") or ob.modifiers.new("SV_InkHull", 'SOLIDIFY')
        mod.thickness = -thk; mod.offset = 1.0; mod.use_flip_normals = True; mod.use_rim = False; mod.material_offset = idx_s


style_car_and_outlines()


def build_high_impact_car_fx():
    fx_coll = COLLS["V6_09_ComicFX"]
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    rig_ev = rig.evaluated_get(deps)
    m_car0 = rig_ev.matrix_world @ rig_ev.pose.bones["Bone_Heading"].matrix

    def _bind_bone(ob, bname):
        pb_m = rig_ev.matrix_world @ rig_ev.pose.bones[bname].matrix
        ob.matrix_world = m_car0
        ob.parent = rig
        ob.parent_type = 'BONE'
        ob.parent_bone = bname
        ob.matrix_parent_inverse = pb_m.inverted()
        ob.matrix_basis = pb_m.inverted() @ m_car0
        ob.visible_shadow = False

    def _fx_mat(name, c_core, c_edge, strength=5.0, freq=6.5, cut_thresh=0.30):
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m.use_nodes = True
        try:
            m.surface_render_method = 'BLENDED'
        except Exception:
            pass
        nt = m.node_tree; nt.nodes.clear()
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        tr = nt.nodes.new('ShaderNodeBsdfTransparent')
        em = nt.nodes.new('ShaderNodeEmission'); em.name = "SV_FX_Emission"; em.inputs['Strength'].default_value = strength
        uv = nt.nodes.new('ShaderNodeUVMap'); uv.uv_map = "UVMap"
        sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(uv.outputs['UV'], sep.inputs['Vector'])
        uo = nt.nodes.new('ShaderNodeMath'); uo.name = "SV_FlutterAdd"; uo.operation = 'ADD'
        nt.links.new(sep.outputs['X'], uo.inputs[0])
        fc_fl = uo.inputs[1].driver_add("default_value")
        fc_fl.driver.type = 'SCRIPTED'
        fc_fl.driver.expression = "floor(frame / 2.0) * 0.37"
        cb = nt.nodes.new('ShaderNodeCombineXYZ'); nt.links.new(uo.outputs[0], cb.inputs['X']); nt.links.new(sep.outputs['Y'], cb.inputs['Y'])
        ns = nt.nodes.new('ShaderNodeTexNoise'); ns.inputs['Scale'].default_value = freq; ns.inputs['Detail'].default_value = 3.0; nt.links.new(cb.outputs['Vector'], ns.inputs['Vector'])
        fu = nt.nodes.new('ShaderNodeMapRange'); fu.inputs['To Min'].default_value = 0.96; fu.inputs['To Max'].default_value = 0.0; nt.links.new(sep.outputs['X'], fu.inputs['Value'])
        ma = nt.nodes.new('ShaderNodeMath'); ma.operation = 'MULTIPLY'; nt.links.new(fu.outputs['Result'], ma.inputs[0]); nt.links.new(ns.outputs['Fac'], ma.inputs[1])
        st = nt.nodes.new('ShaderNodeMath'); st.operation = 'GREATER_THAN'; st.inputs[1].default_value = cut_thresh; nt.links.new(ma.outputs[0], st.inputs[0])
        dv = nt.nodes.new('ShaderNodeMath'); dv.operation = 'SUBTRACT'; dv.inputs[1].default_value = 0.5; nt.links.new(sep.outputs['Y'], dv.inputs[0])
        ab = nt.nodes.new('ShaderNodeMath'); ab.operation = 'ABSOLUTE'; nt.links.new(dv.outputs[0], ab.inputs[0])
        cr = nt.nodes.new('ShaderNodeValToRGB'); cr.color_ramp.interpolation = 'CONSTANT'
        cr.color_ramp.elements[0].position = 0.0; cr.color_ramp.elements[0].color = (*c_core, 1.0)
        cr.color_ramp.elements[1].position = 0.25; cr.color_ramp.elements[1].color = (*c_edge, 1.0)
        nt.links.new(ab.outputs[0], cr.inputs[0]); nt.links.new(cr.outputs['Color'], em.inputs['Color'])
        mx = nt.nodes.new('ShaderNodeMixShader'); mx.name = "SV_FX_AlphaMix"
        nt.links.new(st.outputs[0], mx.inputs['Fac']); nt.links.new(tr.outputs['BSDF'], mx.inputs[1]); nt.links.new(em.outputs['Emission'], mx.inputs[2])
        nt.links.new(mx.outputs['Shader'], out.inputs['Surface'])
        return m

    def _new_fx(nm, vs, fs, uvs, mat, bone):
        me = bpy.data.meshes.new(nm)
        me.from_pydata(vs, [], fs); me.update()
        uvl = me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            for li in poly.loop_indices:
                uvl.data[li].uv = uvs[me.loops[li].vertex_index]
        me.materials.append(mat)
        ob = bpy.data.objects.new(nm, me)
        fx_coll.objects.link(ob)
        _bind_bone(ob, bone)
        return ob

    m_rib_c = _fx_mat("MAT_SV_AeroRibbon_Cyan", (1.0, 1.0, 1.0), (0.0, 0.94, 1.0), strength=5.2, freq=5.5)
    m_rib_m = _fx_mat("MAT_SV_AeroRibbon_Mag", (1.0, 0.96, 1.0), (1.0, 0.10, 0.56), strength=5.2, freq=6.5)
    m_exh = _fx_mat("MAT_SV_ExhaustBurst", (0.85, 0.98, 1.0), (1.0, 0.16, 0.48), strength=12.5, freq=10.0, cut_thresh=0.20)
    m_spk = _fx_mat("MAT_SV_SparkSlashes", (1.0, 1.0, 0.94), (1.0, 0.68, 0.04), strength=14.0, freq=12.0, cut_thresh=0.22)
    m_spr = _fx_mat("MAT_SV_RoosterSpray", (0.78, 0.95, 1.0), (1.0, 0.12, 0.52), strength=3.6, freq=7.5, cut_thresh=0.32)
    m_smr = _fx_mat("MAT_SV_WheelSmear", (1.0, 0.96, 0.85), (0.0, 0.90, 1.0), strength=4.2, freq=8.0)

    # 1) 尾翼螺旋涡流带 & 前翼导流涡流带 (V6_FX_AeroRibbon_RL/RR/FL/FR)
    for nm, sxyz, ln, w0, sgn, mt, az in (
        ("V6_FX_AeroRibbon_RL", (-0.51, -2.47, 1.03), 4.2, 0.062, -1.0, m_rib_c, 0.16),
        ("V6_FX_AeroRibbon_RR", (0.51, -2.47, 1.03), 4.2, 0.062, 1.0, m_rib_m, 0.16),
        ("V6_FX_AeroRibbon_FL", (-1.04, 2.62, 0.28), 1.85, 0.042, -1.0, m_rib_m, 0.09),
        ("V6_FX_AeroRibbon_FR", (1.04, 2.62, 0.28), 1.85, 0.042, 1.0, m_rib_c, 0.09),
    ):
        vs, fs, uvs = [], [], []
        for k in range(21):
            u = k / 20.0
            cx = sxyz[0] + sgn * (0.14 * (u ** 1.2) + 0.048 * sin(u * 11.0))
            cy = sxyz[1] - ln * u
            cz = sxyz[2] + az * u + 0.042 * cos(u * 11.0)
            w = w0 * (1.0 - 0.88 * u)
            tw = u * 3.2 * sgn
            vs += [(cx - w * cos(tw), cy, cz - w * sin(tw)), (cx + w * cos(tw), cy, cz + w * sin(tw))]
            uvs += [(u, 0.0), (u, 1.0)]
        for k in range(20):
            a = k * 2; fs.append((a, a + 1, a + 3, a + 2))
        _new_fx(nm, vs, fs, uvs, mt, "Bone_Body")

    # 2) 双通道加力燃烧室马赫激波环尾焰 (V6_FX_ExhaustCone: 中央主尾管 + 扩散器双侧激波菱形环！)
    evs, efs, euv = [], [], []
    for ox, oy, oz, r_scale in ((0.0, -2.38, 0.436, 1.0), (-0.22, -2.32, 0.26, 0.65), (0.22, -2.32, 0.26, 0.65)):
        for pl in (0, 1):
            b = len(evs)
            for k in range(9):
                u = k / 8.0
                # 马赫激波菱形膨胀-收缩节律
                shock = 1.0 + 0.42 * abs(sin(u * pi * 3.0))
                w = 0.088 * r_scale * (1.0 - 0.82 * u) * shock
                yy = oy - 1.35 * r_scale * u
                evs += ([(-w + ox, yy, oz), (w + ox, yy, oz)] if pl == 0 else [(ox, yy, oz - w), (ox, yy, oz + w)])
                euv += [(u, 0.0), (u, 1.0)]
            for k in range(8):
                a = b + k * 2; efs.append((a, a + 1, a + 3, a + 2))
    _new_fx("V6_FX_ExhaustCone", evs, efs, euv, m_exh, "Bone_Body")

    # 3) 金白钛合金底板擦地火花长束 (V6_FX_KerbSparks_L/R: 专供 Eau-Rouge +14° 压缩触底与 >300km/h 坡顶飞溅！)
    for sgn, snm in ((-1.0, "V6_FX_KerbSparks_L"), (1.0, "V6_FX_KerbSparks_R")):
        sv, sf, suv = [], [], []
        for dx, dz_e, ln, w_s in ((-0.18, 0.42, 2.75, 0.026), (-0.04, 0.26, 2.15, 0.022),
                                  (0.08, 0.55, 3.10, 0.024), (0.16, 0.18, 1.75, 0.018), (-0.28, 0.34, 2.40, 0.020)):
            b = len(sv)
            x0, y0, z0 = sgn * (0.58 + dx), -1.68, 0.045
            x1, y1, z1 = x0 + sgn * 0.36, y0 - ln, z0 + dz_e
            sv += [(x0 - w_s, y0, z0), (x0 + w_s, y0, z0), (x1 + 0.004, y1, z1), (x1 - 0.004, y1, z1)]
            suv += [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0)]
            sf.append((b, b + 1, b + 2, b + 3))
        _new_fx(snm, sv, sf, suv, m_spk, "Bone_Body")

    # 4) 雨夜后轮霓虹水雾鸡尾酒喷流弧 (V6_FX_RoosterSpray_RL/RR)
    for sgn, rnm in ((-1.0, "V6_FX_RoosterSpray_RL"), (1.0, "V6_FX_RoosterSpray_RR")):
        rv, rf, ruv = [], [], []
        for k in range(13):
            u = k / 12.0
            cx = sgn * (0.86 + 0.18 * u)
            cy = -1.92 - 2.65 * u
            cz = 0.14 + 0.92 * (u ** 0.78)
            w = 0.08 + 0.28 * u
            rv += [(cx - w * 0.35, cy, max(0.03, cz - w)), (cx + w * 0.35, cy, cz + w * 0.65)]
            ruv += [(u, 0.0), (u, 1.0)]
        for k in range(12):
            a = k * 2; rf.append((a, a + 1, a + 3, a + 2))
        _new_fx(rnm, rv, rf, ruv, m_spr, "Bone_Body")

    # 5) 四轮外侧 12fps 手绘旋转速度残影弧 (V6_FX_WheelSmear_FL/FR/RL/RR)
    for wnm, wb, wx, wy, wz in (
        ("V6_FX_WheelSmear_FL", "Bone_Wheel_FL", -1.084, 1.45, 0.351),
        ("V6_FX_WheelSmear_FR", "Bone_Wheel_FR", 1.084, 1.45, 0.351),
        ("V6_FX_WheelSmear_RL", "Bone_Wheel_RL", -1.080, -1.55, 0.336),
        ("V6_FX_WheelSmear_RR", "Bone_Wheel_RR", 1.080, -1.55, 0.336),
    ):
        vs, fs, uvs = [], [], []
        for a0, spn, ri, ro in ((18.0, 122.0, 0.215, 0.288), (195.0, 112.0, 0.245, 0.320)):
            b = len(vs)
            for k in range(13):
                u = k / 12.0; ang = radians(a0 + spn * u)
                vs += [(wx, wy + cos(ang) * ri, wz + sin(ang) * ri), (wx, wy + cos(ang) * ro, wz + sin(ang) * ro)]
                uvs += [(u, 0.0), (u, 1.0)]
            for k in range(12):
                a = b + k * 2; fs.append((a, a + 1, a + 3, a + 2))
        _new_fx(wnm, vs, fs, uvs, m_smr, wb)


build_high_impact_car_fx()

# 清理孤立数据块并保存 v6_stage_lookdev.blend
try:
    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
except Exception:
    pass

scene["sv_dimension"] = 0.0
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
if os.path.exists(OUT_BLEND + "1"):
    try:
        os.remove(OUT_BLEND + "1")
    except Exception:
        pass

print("=== V6 3D MEGA-CIRCUIT LOOKDEV SUMMARY ===")
print(f"Saved: {OUT_BLEND} in {time.time() - t_start:.2f} s")
print("Total objects:", len(bpy.data.objects), "| Root objs:", [o.name for o in scene.collection.objects])
print("Collections:", {c.name: len(c.all_objects) for c in scene.collection.children})

# ---------------------------------------------------------------
# 9. 五大奇观定妆预览渲染 (--preview -> renders_v6/preview/)
# ---------------------------------------------------------------
if "--preview" in ARGV:
    os.makedirs(PREV_DIR, exist_ok=True)
    scene.render.image_settings.file_format = 'JPEG'
    scene.render.image_settings.quality = 95
    for _old in os.listdir(PREV_DIR):
        if _old.endswith((".jpg", ".png")):
            try:
                os.remove(os.path.join(PREV_DIR, _old))
            except Exception:
                pass

    cd = bpy.data.cameras.new("CAM_V6_PREV")
    cd.clip_start = 0.25
    cd.clip_end = 6000.0
    cam_p = bpy.data.objects.new("CAM_V6_PREV", cd)
    COLLS["V6_07_Lighting"].objects.link(cam_p)
    scene.camera = cam_p
    pb_root = rig.pose.bones["Bone_Root"]
    pb_head = rig.pose.bones["Bone_Heading"]

    # 选出六大代表奇观地标点（对齐 #32 @track 地标：1 峡谷摩天楼与赛博维修区; 2 +13.5° 爬坡火花; 3 +42m 盲坡斜拉桥与次元巨月; 4 +17.4° 巨碗霓虹高墙; 5 341km/h 激光频闪隧道; 6 海港发夹弯重刹区）
    shots_prev = [
        ("v6_01_canyon_15mm_wet", 95, 0.0, 15.0, (-5.8, -1.6, 0.28), (2.2, 0.2, 1.45), 10.0),
        ("v6_02_raidillon_climb_sparks", 437, 0.0, 24.0, (-6.2, 1.8, 0.42), (3.5, -0.3, 1.15), -8.0),
        ("v6_03_crest_skybridge_moon", _crest_idx, 1.0, 85.0, (-18.5, 0.6, 0.62), (12.0, 0.0, 2.35), 0.0),
        ("v6_04_banked_bowl_17deg", _peak_i, 1.0, 20.0, (-6.2, 2.5, 0.85), (4.5, -2.0, 0.95), -14.0),
        ("v6_05_laser_strobe_tunnel_2099", 1440, 2.0, 16.0, (-6.0, -1.3, 0.36), (5.0, 0.0, 0.78), 8.0),
        ("v6_06_harbor_hairpin_brake_2099", 1640, 2.0, 28.0, (-7.2, -2.2, 0.65), (6.0, 1.2, 1.25), 6.0),
    ]

    mw_inv = rig.matrix_world.inverted()
    pb_root.rotation_mode = 'QUATERNION'
    pb_head.rotation_mode = 'QUATERNION'
    for idx_shot, (sname, fi, sdim, flens, cam_rel, tgt_rel, roll_d) in enumerate(shots_prev, start=1):
        fr = FRAMES[fi % N]
        scene["sv_dimension"] = float(sdim)
        scene.keyframe_insert('["sv_dimension"]', frame=idx_shot)
        # 严格零误差轮胎贴地定位：car_pos == fr["rpos"] (0.000 m Z 偏差)
        car_pos = fr["rpos"].copy()
        rot_m = Matrix((
            (fr["right"].x, fr["fwd"].x, fr["up"].x),
            (fr["right"].y, fr["fwd"].y, fr["up"].y),
            (fr["right"].z, fr["fwd"].z, fr["up"].z),
        )).to_4x4()
        pb_root.matrix = mw_inv @ Matrix.Translation(car_pos)
        bpy.context.view_layer.update()
        pb_head.matrix = mw_inv @ (Matrix.Translation(car_pos) @ rot_m)
        bpy.context.view_layer.update()
        pb_root.keyframe_insert("location", frame=idx_shot)
        pb_root.keyframe_insert("rotation_quaternion", frame=idx_shot)
        pb_head.keyframe_insert("location", frame=idx_shot)
        pb_head.keyframe_insert("rotation_quaternion", frame=idx_shot)

        scene.frame_set(idx_shot)
        bpy.context.view_layer.update()
        c_loc = car_pos + fr["fwd"] * cam_rel[0] + fr["right"] * cam_rel[1] + fr["up"] * cam_rel[2]
        c_tgt = car_pos + fr["fwd"] * tgt_rel[0] + fr["right"] * tgt_rel[1] + fr["up"] * tgt_rel[2]
        q = (c_tgt - c_loc).to_track_quat('-Z', 'Y')
        m_cam = q.to_matrix().to_4x4() @ Matrix.Rotation(radians(roll_d), 4, 'Z')
        cam_p.matrix_world = Matrix.Translation(c_loc) @ m_cam
        cd.lens = flens
        scene.render.filepath = os.path.join(PREV_DIR, sname + ".jpg")
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"PREVIEW {sname} (dim={sdim}, z={fr['pos'].z:.1f}m, pitch={math.degrees(fr['p']):.1f}deg, bank={math.degrees(fr['b_eff']):.1f}deg): {time.time() - t0:.2f} s")
