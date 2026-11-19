# -*- coding: utf-8 -*-
"""
V4 MODEL PASS — 车轮重建 + 表面/材质优化 + 贴花投影
输入: pipeline/base_v4.blend
输出: pipeline/v4_stage_model.blend
"""
import bpy, bmesh, math, os, sys
from mathutils import Vector, Matrix, Euler
from math import cos, sin, pi, radians

BASE = r"D:\项目session\blender-supercar\pipeline\base_v4.blend"
OUT = r"D:\项目session\blender-supercar\pipeline\v4_stage_model.blend"

bpy.ops.wm.open_mainfile(filepath=BASE)
scene = bpy.context.scene


# ============================================================
# 0. 工具
# ============================================================
def col(name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


def mesh_obj(name, verts, faces, collection, mat=None, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate(verbose=False)
    me.update()
    ob = bpy.data.objects.new(name, me)
    collection.objects.link(ob)
    if mat is not None:
        me.materials.append(mat)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    return ob


def recalc_normals(ob):
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()


def revolve(profile, segs, close_loop=True):
    n = len(profile)
    verts = []
    for s in range(segs):
        a = 2 * pi * s / segs
        ca, sa = cos(a), sin(a)
        for (u, r) in profile:
            verts.append((u, r * ca, r * sa))
    faces = []
    m = n if close_loop else n - 1
    for s in range(segs):
        s2 = (s + 1) % segs
        for k in range(m):
            k2 = (k + 1) % n
            faces.append((s * n + k, s * n + k2, s2 * n + k2, s2 * n + k))
    return verts, faces


def revolve_band(profile, segs, r_ref):
    n = len(profile)
    verts, uvs = [], []
    for s in range(segs):
        a = 2 * pi * s / segs
        ca, sa = cos(a), sin(a)
        for (u, r) in profile:
            verts.append((u, r * ca, r * sa))
            rn = min(1.0, r / r_ref)
            uvs.append((0.5 + 0.5 * rn * ca, 0.5 + 0.5 * rn * sa))
    faces = []
    for s in range(segs):
        s2 = (s + 1) % segs
        for k in range(n - 1):
            faces.append((s * n + k, s * n + k + 1, s2 * n + k + 1, s2 * n + k))
    return verts, faces, uvs


def add_uv(ob, uvs, name="UVMap"):
    me = ob.data
    uv = me.uv_layers.new(name=name)
    for poly in me.polygons:
        for li in poly.loop_indices:
            uv.data[li].uv = uvs[me.loops[li].vertex_index]


def principled(mat):
    if not mat.use_nodes:
        mat.use_nodes = True
    for n in mat.node_tree.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            return n
    return None


def ensure_mat(name, base=(0.2, 0.2, 0.2), metallic=0.0, roughness=0.5, coat=0.0):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = principled(m)
    if b:
        b.inputs['Base Color'].default_value = (*base, 1.0)
        b.inputs['Metallic'].default_value = metallic
        b.inputs['Roughness'].default_value = roughness
        for key in ('Coat Weight', 'Clearcoat'):
            if key in b.inputs:
                b.inputs[key].default_value = coat
                break
    return m


# ============================================================
# 1. 材质升级
# ============================================================
def build_materials():
    M = {}

    m = ensure_mat("Mat_Tire_Slick_Compound", (0.014, 0.014, 0.016), 0.0, 0.62)
    b = principled(m)
    nt = m.node_tree
    tc = nt.nodes.new('ShaderNodeTexCoord')
    n1 = nt.nodes.new('ShaderNodeTexNoise')
    n1.inputs['Scale'].default_value = 900.0
    n1.inputs['Detail'].default_value = 8.0
    n1.inputs['Roughness'].default_value = 0.75
    nt.links.new(tc.outputs['Object'], n1.inputs['Vector'])
    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.22
    bump.inputs['Distance'].default_value = 0.0015
    nt.links.new(n1.outputs['Fac'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    if 'Sheen Weight' in b.inputs:
        b.inputs['Sheen Weight'].default_value = 0.12
        b.inputs['Sheen Roughness'].default_value = 0.5
    M['tire'] = m

    m = ensure_mat("Mat_Rim_Forged_Dark", (0.048, 0.050, 0.058), 0.94, 0.24)
    b = principled(m)
    if 'Anisotropic' in b.inputs:
        b.inputs['Anisotropic'].default_value = 0.7
    if 'Coat Weight' in b.inputs:
        b.inputs['Coat Weight'].default_value = 0.4
        b.inputs['Coat Roughness'].default_value = 0.07
    M['rim'] = m

    M['lip'] = ensure_mat("Mat_Rim_Machined_Lip", (0.74, 0.75, 0.78), 1.0, 0.10)
    M['gold'] = ensure_mat("Mat_CenterLock_Gold", (0.78, 0.55, 0.11), 1.0, 0.20)

    m = ensure_mat("Mat_BrakeDisc_CarbonCeramic", (0.075, 0.070, 0.066), 0.4, 0.52)
    b = principled(m)
    nt = m.node_tree
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 420.0
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.3
    nt.links.new(nz.outputs['Fac'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    M['disc'] = m

    # 刹车过热发光环（动画可驱动）
    glow = bpy.data.materials.get("Mat_Brake_HeatGlow")
    if glow is None:
        glow = bpy.data.materials.new("Mat_Brake_HeatGlow")
    glow.use_nodes = True
    gnodes = glow.node_tree.nodes
    gnodes.clear()
    em = gnodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (1.0, 0.28, 0.05, 1)
    em.inputs['Strength'].default_value = 0.0
    go = gnodes.new('ShaderNodeOutputMaterial')
    glow.node_tree.links.new(em.outputs['Emission'], go.inputs['Surface'])
    glow.surface_render_method = 'BLENDED'
    M['glow'] = glow

    M['caliper'] = ensure_mat("Mat_Caliper_Anodized", (0.55, 0.012, 0.01), 0.6, 0.28)

    # 翼端板专用哑光碳纤（避免边缘掠射时反射天空成"白板"）
    cm = ensure_mat("Mat_Carbon_Endplate_Matte", (0.020, 0.021, 0.024), 0.0, 0.78)
    cb = principled(cm)
    if cb:
        if 'Specular IOR Level' in cb.inputs:
            cb.inputs['Specular IOR Level'].default_value = 0.18
        if 'Specular' in cb.inputs:
            cb.inputs['Specular'].default_value = 0.18
    M['endplate'] = cm
    M['duct'] = ensure_mat("Mat_Duct_Carbon", (0.020, 0.021, 0.024), 0.25, 0.42)

    old = bpy.data.materials.get("Mat_PZero_Pirelli_Sidewall")
    if old:
        b = principled(old)
        if b:
            b.inputs['Roughness'].default_value = 0.55
            if 'Emission Strength' in b.inputs:
                b.inputs['Emission Strength'].default_value = 0.0
        old.surface_render_method = 'DITHERED'
        old.use_transparent_shadow = True
        M['sidewall'] = old

    # 碳纤编织
    for cname in ("Mat_Forged_Carbon", "Mat_Carbon_Satin", "Mat_Carbon_Fiber"):
        m = bpy.data.materials.get(cname)
        if not m or not m.node_tree or m.node_tree.nodes.get("V4_CarbonWeave"):
            continue
        b = principled(m)
        if not b:
            continue
        nt = m.node_tree
        tc = nt.nodes.new('ShaderNodeTexCoord'); tc.name = "V4_CarbonWeave"
        w1 = nt.nodes.new('ShaderNodeTexWave'); w1.name = "V4_CarbonWeave"
        w1.wave_type = 'BANDS'
        w1.bands_direction = 'DIAGONAL'
        w1.inputs['Scale'].default_value = 320.0
        w1.inputs['Distortion'].default_value = 1.2
        nz = nt.nodes.new('ShaderNodeTexNoise'); nz.name = "V4_CarbonWeave"
        nz.inputs['Scale'].default_value = 40.0
        nt.links.new(tc.outputs['Object'], w1.inputs['Vector'])
        mix = nt.nodes.new('ShaderNodeMixRGB'); mix.name = "V4_CarbonWeave"
        mix.blend_type = 'MULTIPLY'
        mix.inputs['Fac'].default_value = 0.5
        nt.links.new(w1.outputs['Fac'], mix.inputs['Color1'])
        nt.links.new(nz.outputs['Fac'], mix.inputs['Color2'])
        bump = nt.nodes.new('ShaderNodeBump'); bump.name = "V4_CarbonWeave"
        bump.inputs['Strength'].default_value = 0.16
        bump.inputs['Distance'].default_value = 0.0012
        nt.links.new(mix.outputs['Color'], bump.inputs['Height'])
        nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
        b.inputs['Roughness'].default_value = max(0.50, b.inputs['Roughness'].default_value)
        if 'Metallic' in b.inputs:
            b.inputs['Metallic'].default_value = min(0.08, b.inputs['Metallic'].default_value)
        if 'Coat Weight' in b.inputs:
            b.inputs['Coat Weight'].default_value = 0.05
            b.inputs['Coat Roughness'].default_value = 0.30

    m = bpy.data.materials.get("Mat_RedBull_MatteNavy")
    if m and m.node_tree:
        b = principled(m)
        if b:
            b.inputs['Base Color'].default_value = (0.022, 0.042, 0.115, 1.0)
            b.inputs['Metallic'].default_value = 0.05
            b.inputs['Roughness'].default_value = 0.44
            if 'Coat Weight' in b.inputs:
                b.inputs['Coat Weight'].default_value = 0.14
                b.inputs['Coat Roughness'].default_value = 0.06

    # 贴花发光收敛（避免出现"发光白卡片"）
    for m in bpy.data.materials:
        if m.name.startswith("Mat_DEC_") and m.node_tree:
            b = principled(m)
            if b and 'Emission Strength' in b.inputs:
                b.inputs['Emission Strength'].default_value = 0.05
            m.use_transparent_shadow = False

    # ===== Mercedes-AMG PETRONAS 配色 =====
    # 车身：裸碳黑
    m = bpy.data.materials.get("Mat_RedBull_MatteNavy")
    if m and m.node_tree:
        b = principled(m)
        if b:
            b.inputs['Base Color'].default_value = (0.011, 0.012, 0.014, 1.0)
            b.inputs['Metallic'].default_value = 0.16
            b.inputs['Roughness'].default_value = 0.36
            if 'Coat Weight' in b.inputs:
                b.inputs['Coat Weight'].default_value = 0.30
                b.inputs['Coat Roughness'].default_value = 0.10
    # Petronas 青绿（车体饰条）
    pm = ensure_mat("Mat_Merc_Petronas", (0.0, 0.62, 0.55), 0.25, 0.30)
    pb = principled(pm)
    if pb and 'Coat Weight' in pb.inputs:
        pb.inputs['Coat Weight'].default_value = 0.45
        pb.inputs['Coat Roughness'].default_value = 0.08
    M['petronas'] = pm
    # 银色（顶部渐变装饰）
    sm = ensure_mat("Mat_Merc_Silver", (0.62, 0.65, 0.69), 0.85, 0.22)
    M['silver'] = sm
    # 轮毂中心锁：青色
    cm2 = ensure_mat("Mat_CenterLock_Cyan", (0.0, 0.55, 0.50), 0.95, 0.18)
    M['gold'] = cm2
    # 刹车卡钳：Mercedes 深色卡钳
    cal = bpy.data.materials.get("Mat_Caliper_Anodized")
    if cal and cal.node_tree:
        cb = principled(cal)
        if cb:
            cb.inputs['Base Color'].default_value = (0.05, 0.05, 0.06, 1.0)
            cb.inputs['Metallic'].default_value = 0.4
            cb.inputs['Roughness'].default_value = 0.35

    # 贴花贴图 -> Mercedes 素材
    import os as _os
    texmap = {
        "Mat_DEC_Sidepod_Oracle": "merc_sidepod.png",
        "Mat_DEC_Engine_RedBull": "merc_engine.png",
        "Mat_DEC_Nose_Livery": "merc_nose.png",
        "Mat_DEC_Halo_Oracle": "merc_halo.png",
        "Mat_DEC_RearWing_Front": "merc_rearwing.png",
        "Mat_DEC_RearWing_Bybit": "merc_rearwing.png",
        "Mat_DEC_RearWing_Back": "merc_rearwing.png",
        "Mat_DEC_Endplate_Mobil1": "merc_endplate.png",
    }
    for mname, fname in texmap.items():
        mm = bpy.data.materials.get(mname)
        if not mm or not mm.node_tree:
            continue
        path = _os.path.join("D:/项目session/blender-supercar/textures", fname)
        if not _os.path.exists(path):
            continue
        img = bpy.data.images.load(path, check_existing=True)
        for n in mm.node_tree.nodes:
            if n.type == 'TEX_IMAGE':
                n.image = img
                n.image.colorspace_settings.name = 'sRGB'

    for nm, strength in (("Mat_Neon_Cyan", 6.0), ("Mat_Neon_Orange", 5.0), ("Mat_HUD_Green", 2.5)):
        m = bpy.data.materials.get(nm)
        if m and m.node_tree:
            for n in m.node_tree.nodes:
                if n.type == 'EMISSION':
                    n.inputs['Strength'].default_value = strength
                elif n.type == 'BSDF_PRINCIPLED' and 'Emission Strength' in n.inputs:
                    n.inputs['Emission Strength'].default_value = strength
    return M


MATS = build_materials()


# ============================================================
# 2. 车轮重建
# ============================================================
WHEEL_SPEC = {
    'FL': dict(center=Vector((-0.900, 1.450, 0.355)), width=0.345, out=-1),
    'FR': dict(center=Vector(( 0.900, 1.450, 0.355)), width=0.345, out= 1),
    'RL': dict(center=Vector((-0.860, -1.550, 0.355)), width=0.425, out=-1),
    'RR': dict(center=Vector(( 0.860, -1.550, 0.355)), width=0.425, out= 1),
}
R_TIRE = 0.357
R_RIM = 0.2286
SEGS = 96
WHEEL_COLS = {'FL': "Wheel_FL", 'FR': "Wheel_FR", 'RL': "Wheel_RL", 'RR': "Wheel_RR"}


def wipe_old_wheel(side):
    doomed = []
    c = bpy.data.collections.get(WHEEL_COLS[side])
    if c:
        doomed += list(c.objects)
    lr = 'L' if side.endswith('L') else 'R'
    names = [f"GEO_F1_Tire_{side}", f"GEO_F1_WheelCover_{side}", f"GEO_F1_Wheel_CenterNut_{side}",
             f"GEO_F1_BrakeDisc_{side}", f"GEO_F1_BrakeBell_{side}", f"DEC_Tire_Sidewall_{side}",
             f"GEO_F1_ValveStem_{side}", f"GEO_F1_BrakeCaliper_{side}",
             f"GEO_F1_Front_BrakeDrum_{lr}", f"GEO_F1_Front_BrakeDuctScoop_{lr}",
             f"GEO_F1_Wheel_AeroDeflector_{side}", f"GEO_F1_Wheel_DeflectorLight_{side}",
             f"GEO_F1_BrakeHose_{side}"]
    for nm in names:
        o = bpy.data.objects.get(nm)
        if o:
            doomed.append(o)
    for o in bpy.data.objects:
        if o.name.startswith((f"GEO_F1_Blade_{side}_", f"GEO_F1_MagSpoke_{side}_",
                              f"GEO_F1_Tire_WearIndicator_{side}_")):
            doomed.append(o)
    for o in set(doomed):
        try:
            bpy.data.objects.remove(o, do_unlink=True)
        except Exception:
            pass


def tire_profile(half_w, R=R_TIRE, Rr=R_RIM):
    outer = [
        (half_w * 0.94, Rr + 0.004),
        (half_w * 1.00, Rr + 0.040),
        (half_w * 1.012, Rr + 0.085),
        (half_w * 1.005, R - 0.070),
        (half_w * 0.972, R - 0.032),
        (half_w * 0.900, R - 0.006),
        (half_w * 0.780, R + 0.0015),
        (half_w * 0.500, R + 0.0035),
        (0.0, R + 0.004),
    ]
    prof = list(outer)
    prof += [(-u, r) for (u, r) in reversed(outer[:-1])]
    prof += [
        (-half_w * 0.92, Rr - 0.002),
        (-half_w * 0.55, Rr - 0.006),
        (0.0, Rr - 0.008),
        (half_w * 0.55, Rr - 0.006),
        (half_w * 0.92, Rr - 0.002),
    ]
    return prof


def tire_u_at(r, half):
    prof = tire_profile(half)
    for i in range(len(prof) - 1):
        (u0, r0), (u1, r1) = prof[i], prof[i + 1]
        if (r0 - r <= 0 <= r1 - r) or (r1 - r <= 0 <= r0 - r):
            if abs(r1 - r0) < 1e-9:
                continue
            return u0 + (u1 - u0) * (r - r0) / (r1 - r0)
    return prof[0][0]


def build_tire(side, spec, collection):
    half = spec['width'] / 2
    verts, faces = revolve(tire_profile(half), SEGS, close_loop=True)
    ob = mesh_obj(f"GEO_F1_Tire_{side}", verts, faces, collection, MATS['tire'], smooth=True)
    recalc_normals(ob)
    ob.location = spec['center']
    if spec['out'] < 0:
        ob.rotation_euler = (0, 0, pi)
    return ob


def build_rim(side, spec, collection):
    half = spec['width'] / 2
    u_out = half * 0.94
    u_in = -half * 0.98

    # 轮辋筒身
    prof = [
        (u_in, R_RIM - 0.004),
        (u_in - 0.004, R_RIM + 0.012),
        (u_in + 0.010, R_RIM + 0.016),
        (u_out - 0.030, R_RIM + 0.014),
        (u_out - 0.010, R_RIM + 0.015),
        (u_out, R_RIM + 0.019),
        (u_out + 0.003, R_RIM + 0.007),
        (u_out - 0.008, R_RIM - 0.002),
        (u_out - 0.008, R_RIM - 0.013),
        (u_in + 0.02, R_RIM - 0.015),
        (u_in + 0.004, R_RIM - 0.008),
    ]
    verts, faces = revolve(prof, SEGS, close_loop=True)
    rim = mesh_obj(f"GEO_F1_Rim_{side}", verts, faces, collection, MATS['rim'], smooth=True)
    recalc_normals(rim)

    # 外唇抛光
    lip_prof = [
        (u_out - 0.006, R_RIM + 0.0185),
        (u_out + 0.0028, R_RIM + 0.0100),
        (u_out + 0.0028, R_RIM + 0.0020),
        (u_out - 0.0085, R_RIM + 0.0005),
    ]
    v2, f2 = revolve(lip_prof, SEGS, close_loop=False)
    lip = mesh_obj(f"GEO_F1_RimLip_{side}", v2, f2, collection, MATS['lip'], smooth=True)
    recalc_normals(lip)

    # 轮毂盘（中心区域）
    plate_prof = [
        (u_out - 0.086, 0.030),
        (u_out - 0.086, 0.078),
        (u_out - 0.072, 0.086),
        (u_out - 0.068, 0.030),
    ]
    vp, fp = revolve(plate_prof, 64, close_loop=True)
    plate = mesh_obj(f"GEO_F1_RimHubPlate_{side}", vp, fp, collection, MATS['rim'], smooth=True)
    recalc_normals(plate)

    # 10 根细锻造辐条
    verts_all, faces_all = [], []
    n_steps = 12
    r0, r1 = 0.062, R_RIM + 0.002
    for k in range(10):
        a0 = 2 * pi * k / 10
        prev = None
        for i in range(n_steps + 1):
            t = i / n_steps
            r = r0 + (r1 - r0) * t
            half_t = 0.0145 * (1 - t) + 0.0085
            u_face = u_out - 0.020 - 0.062 * (1 - t) ** 1.6
            thick = 0.030 * (1 - t) + 0.010
            a = a0 + 0.035 * t * t
            ca, sa = cos(a), sin(a)
            ta, tb = -sa, ca
            ring = []
            for (du, dt) in ((0.0, -1.0), (0.0, 1.0), (-thick, 1.0), (-thick, -1.0)):
                ring.append((u_face + du,
                             r * ca + ta * half_t * dt,
                             r * sa + tb * half_t * dt))
            base = len(verts_all)
            verts_all.extend(ring)
            cur = [base, base + 1, base + 2, base + 3]
            if prev:
                faces_all.append((prev[0], prev[1], cur[1], cur[0]))
                faces_all.append((prev[1], prev[3], cur[3], cur[1]))
                faces_all.append((prev[3], prev[2], cur[2], cur[3]))
                faces_all.append((prev[2], prev[0], cur[0], cur[2]))
            prev = cur
        faces_all.append(tuple(prev))
    spokes = mesh_obj(f"GEO_F1_RimSpokes_{side}", verts_all, faces_all, collection, MATS['rim'], smooth=True)
    recalc_normals(spokes)
    bev = spokes.modifiers.new("V4_SpokeBevel", 'BEVEL')
    bev.width = 0.0018
    bev.segments = 2
    bev.limit_method = 'ANGLE'
    bev.angle_limit = radians(35)
    bev.harden_normals = True

    # 中央锁止螺母（带三槽）
    nut_r = 0.040
    nut_prof = [
        (u_out - 0.040, 0.001),
        (u_out - 0.038, nut_r * 0.6),
        (u_out - 0.030, nut_r),
        (u_out - 0.012, nut_r * 0.95),
        (u_out - 0.008, nut_r * 0.62),
        (u_out - 0.008, 0.001),
    ]
    v3, f3 = revolve(nut_prof, 6, close_loop=False)
    nut = mesh_obj(f"GEO_F1_CenterLock_{side}", v3, f3, collection, MATS['gold'], smooth=False)
    recalc_normals(nut)

    for ob in (rim, lip, plate, spokes, nut):
        ob.location = spec['center']
        if spec['out'] < 0:
            ob.rotation_euler = (0, 0, pi)
    return rim, spokes, nut


def build_brake(side, spec, collection):
    half = spec['width'] / 2
    u_disc = -half * 0.20
    r_in, r_out = 0.098, 0.188
    t = 0.020

    verts, faces = [], []
    n_seg = 72
    for i in range(n_seg):
        a = 2 * pi * i / n_seg
        ca, sa = cos(a), sin(a)
        for u in (u_disc - t / 2, u_disc + t / 2):
            verts.append((u, r_in * ca, r_in * sa))
            verts.append((u, r_out * ca, r_out * sa))
    idx = lambda i, k, s: ((i % n_seg) * 4) + k * 2 + s
    for i in range(n_seg):
        faces.append((idx(i, 1, 0), idx(i, 1, 1), idx(i + 1, 1, 1), idx(i + 1, 1, 0)))
        faces.append((idx(i + 1, 0, 0), idx(i + 1, 0, 1), idx(i, 0, 1), idx(i, 0, 0)))
        faces.append((idx(i, 0, 1), idx(i, 1, 1), idx(i + 1, 1, 1), idx(i + 1, 0, 1)))
        faces.append((idx(i + 1, 0, 0), idx(i + 1, 1, 0), idx(i, 1, 0), idx(i, 0, 0)))
    disc = mesh_obj(f"GEO_F1_BrakeDisc_{side}", verts, faces, collection, MATS['disc'], smooth=False)
    recalc_normals(disc)

    # 打孔阵列
    hole_verts, hole_faces = [], []
    nh = 22
    rad = 0.0058
    u_hole = u_disc + t / 2 + 0.0012
    for ri, ring_r in enumerate((0.120, 0.155)):
        for i in range(nh):
            a = 2 * pi * i / nh + ri * pi / nh
            cy, cz = ring_r * cos(a), ring_r * sin(a)
            base = len(hole_verts)
            for k in range(14):
                aa = 2 * pi * k / 14
                hole_verts.append((u_hole, cy + rad * cos(aa), cz + rad * sin(aa)))
            hole_faces.append(tuple(range(base, base + 14)))
    holes = mesh_obj(f"GEO_F1_BrakeHoles_{side}", hole_verts, hole_faces, collection,
                     ensure_mat("Mat_BrakeHole_Shadow", (0.002, 0.002, 0.002), 0.0, 0.9), smooth=False)

    # 刹车过热发光环
    glow_prof = [(u_disc + t / 2 + 0.0016, r_in + 0.004), (u_disc + t / 2 + 0.0016, r_out - 0.004)]
    vg, fg = revolve(glow_prof, 64, close_loop=False)
    glow = mesh_obj(f"GEO_F1_BrakeGlow_{side}", vg, fg, collection, MATS['glow'], smooth=True)

    # 卡钳
    cal_verts, cal_faces = [], []
    a0, a1 = radians(112), radians(178)
    ncs = 12
    r_a, r_b = 0.133, 0.207
    u_a, u_b = u_disc - 0.060, u_disc + 0.032
    rings = []
    for i in range(ncs + 1):
        a = a0 + (a1 - a0) * i / ncs
        ca, sa = cos(a), sin(a)
        ring = [(u_a, r_a * ca, r_a * sa), (u_a, r_b * ca, r_b * sa),
                (u_b, r_b * ca, r_b * sa), (u_b, r_a * ca, r_a * sa)]
        base = len(cal_verts)
        cal_verts.extend(ring)
        cur = [base, base + 1, base + 2, base + 3]
        if rings:
            p = rings[-1]
            for j in range(4):
                j2 = (j + 1) % 4
                cal_faces.append((p[j], p[j2], cur[j2], cur[j]))
        rings.append(cur)
    cal_faces.append(tuple(rings[0]))
    cal_faces.append(tuple(reversed(rings[-1])))
    caliper = mesh_obj(f"GEO_F1_BrakeCaliper_{side}", cal_verts, cal_faces, collection, MATS['caliper'], smooth=True)
    recalc_normals(caliper)

    # 导风罩
    duct_prof = [
        (-half * 0.98, R_RIM - 0.030),
        (-half * 0.86, R_RIM - 0.006),
        (-half * 0.55, R_RIM - 0.010),
        (-half * 0.40, R_RIM - 0.026),
        (-half * 0.40, R_RIM - 0.060),
        (-half * 0.80, R_RIM - 0.070),
        (-half * 0.98, R_RIM - 0.055),
    ]
    v4, f4 = revolve(duct_prof, 64, close_loop=True)
    duct = mesh_obj(f"GEO_F1_BrakeDuct_{side}", v4, f4, collection, MATS['duct'], smooth=True)
    recalc_normals(duct)

    for ob in (disc, holes, glow, caliper, duct):
        ob.location = spec['center']
        if spec['out'] < 0:
            ob.rotation_euler = (0, 0, pi)
    return disc, caliper, duct


def build_sidewall_decal(side, spec, collection):
    half = spec['width'] / 2
    radii = [0.2450, 0.2750, 0.3050, 0.3300, 0.3440]
    prof = [(tire_u_at(r, half) + 0.0035, r) for r in radii]
    verts, faces, uvs = revolve_band(prof, 128, R_TIRE)
    ob = mesh_obj(f"DEC_Tire_Sidewall_{side}", verts, faces, collection, MATS['sidewall'], smooth=True)
    add_uv(ob, uvs)
    recalc_normals(ob)
    ob.location = spec['center']
    if spec['out'] < 0:
        ob.rotation_euler = (0, 0, pi)
    return ob


def rebuild_wheels():
    for side, spec in WHEEL_SPEC.items():
        wipe_old_wheel(side)
        c = col(WHEEL_COLS[side])
        build_tire(side, spec, c)
        build_rim(side, spec, c)
        build_brake(side, spec, c)
        build_sidewall_decal(side, spec, c)
        print("WHEEL REBUILT:", side)


# ============================================================
# 3. 表面优化
# ============================================================
def is_decal(o):
    return o.name.startswith("DEC_")


def surface_pass():
    meshes = [o for o in bpy.data.objects
              if o.type == 'MESH' and not is_decal(o) and not o.name.startswith("PROXY_")]
    for o in meshes:
        if o.name.startswith(("GEO_F1_Tire_", "GEO_F1_BrakeDisc_", "GEO_F1_BrakeHoles_", "GEO_F1_BrakeGlow_")):
            continue
        try:
            bm = bmesh.new()
            bm.from_mesh(o.data)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            bm.to_mesh(o.data)
            bm.free()
        except Exception:
            pass
    bpy.context.view_layer.update()

    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0] if meshes else None
    try:
        bpy.ops.object.shade_smooth_by_angle(angle=radians(34.0), keep_sharp_edges=True)
        print("SMOOTH BY ANGLE OK:", len(meshes))
    except Exception as e:
        print("SMOOTH FAIL", e)
    bpy.ops.object.select_all(action='DESELECT')


# ============================================================
# 4. 贴花：射线投影到车体曲面（无悬浮、无拉伸）
# ============================================================
def decal_frame(d):
    """从原贴花四边形的 UV 推导局部坐标系"""
    me = d.data
    uv = me.uv_layers[0]
    mw = d.matrix_world
    pts = {}
    for poly in me.polygons:
        for li in poly.loop_indices:
            u = uv.data[li].uv
            vi = me.loops[li].vertex_index
            key = (round(u.x, 3), round(u.y, 3))
            pts[key] = mw @ me.vertices[vi].co
    if (0.0, 0.0) not in pts:
        return None
    p00 = pts[(0.0, 0.0)].copy()
    cand_u = [k for k in pts if abs(k[1]) < 1e-3 and k[0] > 0.5]
    cand_v = [k for k in pts if abs(k[0]) < 1e-3 and k[1] > 0.5]
    if not cand_u or not cand_v:
        return None
    pu = pts[cand_u[0]]
    pv = pts[cand_v[0]]
    U = pu - p00
    V = pv - p00
    w, h = U.length, V.length
    if w < 1e-6 or h < 1e-6:
        return None
    U.normalize()
    V.normalize()
    N = U.cross(V).normalized()
    return p00, U, V, N, w, h


def build_car_bvh():
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    verts, faces = [], []
    for o in bpy.data.objects:
        if o.type not in ('MESH', 'CURVE'):
            continue
        n = o.name
        if not (n.startswith("GEO_F1_") or n.startswith("DEC_")):
            continue
        if n.startswith("DEC_Tire"):
            continue
        try:
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
        except Exception:
            continue
        if me is None:
            continue
        base = len(verts)
        mw = o.matrix_world
        for v in me.vertices:
            verts.append(tuple(mw @ v.co))
        for poly in me.polygons:
            faces.append(tuple(base + i for i in poly.vertices))
        ev.to_mesh_clear()
    return BVHTree.FromPolygons(verts, faces, all_triangles=False)


def project_decals():
    DROP = ("DEC_Endplate_", "DEC_RearWing_")
    for o in list(bpy.data.objects):
        if o.type == 'MESH' and is_decal(o) and o.name.startswith(DROP):
            bpy.data.objects.remove(o, do_unlink=True)
    decals = [o for o in bpy.data.objects
              if o.type == 'MESH' and is_decal(o) and not o.name.startswith("DEC_Tire")]
    bvh = build_car_bvh()
    made = 0
    for d in decals:
        fr = decal_frame(d)
        if not fr:
            continue
        p00, U, V, N, w, h = fr
        # 判断法线朝外：从贴花外侧 0.35m 处向里打射线应命中
        probe_o = p00 + N * 0.4 + U * w * 0.5 + V * h * 0.5
        hit = bvh.ray_cast(probe_o, -N, 0.8)
        if hit[0] is None:
            N = -N
            probe_o = p00 + N * 0.4 + U * w * 0.5 + V * h * 0.5
            hit = bvh.ray_cast(probe_o, -N, 0.8)
            if hit[0] is None:
                print("DECAL SKIP (no surface):", d.name)
                bpy.data.objects.remove(d, do_unlink=True)
                continue

        nu = max(24, int(w / 0.006))
        nv = max(12, int(h / 0.006))
        verts, uvs, grid = [], [], {}
        for j in range(nv + 1):
            for i in range(nu + 1):
                uu, vv = i / nu, j / nv
                target = p00 + U * (w * uu) + V * (h * vv)
                org = target + N * 0.14
                hit = bvh.ray_cast(org, -N, 0.22)
                loc, nor = hit[0], hit[1]
                if loc is None:
                    continue
                if nor is not None and abs(nor.dot(N)) < 0.15:
                    continue
                off = (nor.normalized() if nor is not None else N)
                if off.dot(N) < 0:
                    off = -off
                pos = loc + off * 0.0018
                grid[(i, j)] = len(verts)
                verts.append(tuple(pos))
                uvs.append((uu, vv))
        faces = []
        for j in range(nv):
            for i in range(nu):
                a, b, c, dd = grid.get((i, j)), grid.get((i + 1, j)), grid.get((i + 1, j + 1)), grid.get((i, j + 1))
                if None in (a, b, c, dd):
                    continue
                faces.append((a, b, c, dd))
        if not faces:
            print("DECAL SKIP (empty):", d.name)
            bpy.data.objects.remove(d, do_unlink=True)
            continue
        mat = d.data.materials[0] if d.data.materials else None
        c = col("08_Sponsor_Decals")
        ob = mesh_obj(d.name + "_PATCH", verts, faces, c, mat, smooth=True)
        add_uv(ob, uvs)
        recalc_normals(ob)
        ob["v4_decal_source"] = d.name
        bpy.data.objects.remove(d, do_unlink=True)
        made += 1
    print("DECALS PROJECTED:", made)
    bpy.ops.object.select_all(action='DESELECT')


# ============================================================
# 5. 气动细节修正（仅保留可靠件）
# ============================================================
def _plate(name, sections, mat, c, smooth=True):
    """sections: list of list[(x,y,z)] 环形截面 -> 放样"""
    verts, faces = [], []
    n = len(sections[0])
    for sec in sections:
        verts.extend(sec)
    for i in range(len(sections) - 1):
        a = i * n
        b = (i + 1) * n
        for k in range(n):
            k2 = (k + 1) % n
            faces.append((a + k, a + k2, b + k2, b + k))
    faces.append(tuple(range(n)))
    faces.append(tuple(range(len(verts) - n, len(verts)))[::-1])
    ob = mesh_obj(name, verts, faces, c, mat, smooth=smooth)
    recalc_normals(ob)
    return ob


def add_merc_livery():
    """Mercedes 风格：侧箱/引擎盖青绿饰条 + 鼻锥黄条改青"""
    c = col("08_Sponsor_Decals")
    pet = MATS['petronas']
    sil = MATS['silver']

    def ribbon(name, x0, x1, y0, y1, z0, z1, mat):
        v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z1), (x0, y1, z1)]
        ob = mesh_obj(name, v, [(0, 1, 2, 3)], c, mat, smooth=False)
        return ob

    # 侧箱外侧青绿斜条（左右各一）
    for s_, side in ((-1, 'L'), (1, 'R')):
        ribbon(f"GEO_MERC_Stripe_Sidepod_{side}",
               s_ * 0.648, s_ * 0.638, -1.85, -0.55, 0.44, 0.52, pet)
        ribbon(f"GEO_MERC_Stripe_Sidepod2_{side}",
               s_ * 0.646, s_ * 0.636, -1.70, -0.70, 0.58, 0.63, sil)
        # 引擎盖两侧银色细线
        ribbon(f"GEO_MERC_Stripe_Cowl_{side}",
               s_ * 0.315, s_ * 0.305, -1.55, -0.35, 0.80, 0.84, sil)
        # halo 支臂青条
        ribbon(f"GEO_MERC_Stripe_Halo_{side}",
               s_ * 0.30, s_ * 0.28, 0.30, 0.42, 0.72, 0.75, pet)

    # 鼻锥黄色饰条 -> Petronas 青
    for nm in ("GEO_F1_Nose_NeonStripe",):
        o = bpy.data.objects.get(nm)
        if o and o.data.materials:
            o.data.materials.clear()
            o.data.materials.append(pet)
    # 尾部雨灯区域改青（原 Mat_Neon_Orange 的排气内发光保留暖色）
    print("MERC LIVERY ADDED")


def rebuild_rear_wing():
    c = col("04_Wings_Aerodynamics")
    carbon = bpy.data.materials.get("Mat_Forged_Carbon")
    for n in ("GEO_F1_RearWing_Mainplane", "GEO_F1_RearWing_DRSFlap", "GEO_F1_RearWing_Endplate_L",
              "GEO_F1_RearWing_Endplate_R", "GEO_F1_RearWing_SwanPylon_L", "GEO_F1_RearWing_SwanPylon_R",
              "GEO_F1_BeamWing_Lower", "GEO_F1_BeamWing_Upper", "GEO_F1_RearWing_DRS_Actuator",
              "GEO_F1_RearWing_DRS_Piston", "GEO_F1_RearWing_Louvre_L_0", "GEO_F1_RearWing_Louvre_L_1",
              "GEO_F1_RearWing_Louvre_L_2", "GEO_F1_RearWing_Louvre_R_0", "GEO_F1_RearWing_Louvre_R_1",
              "GEO_F1_RearWing_Louvre_R_2"):
        o = bpy.data.objects.get(n)
        if o:
            bpy.data.objects.remove(o, do_unlink=True)

    HALF = 0.50

    def wing_element(name, y0, y1, z0, z1, camber, thick, chord_pts=9):
        # 弦向截面 (y, z)：前缘 -> 后缘，带弯度
        prof = []
        for i in range(chord_pts):
            t = i / (chord_pts - 1)
            y = y0 + (y1 - y0) * t
            z = z0 + (z1 - z0) * t + camber * math.sin(math.pi * t)
            prof.append((y, z))
        sections = []
        for x in (-HALF, -HALF * 0.5, 0.0, HALF * 0.5, HALF):
            sec = []
            for (y, z) in prof:
                sec.append((x, y, z + thick / 2))
            for (y, z) in reversed(prof):
                sec.append((x, y, z - thick / 2))
            sections.append(sec)
        return _plate(name, sections, carbon, c, smooth=True)

    # 主翼（弦长 0.30m，前缘 y=-2.34，后缘 y=-2.04）
    wing_element("GEO_F1_RearWing_Mainplane", -2.34, -2.04, 0.930, 0.905, 0.035, 0.022)
    # DRS 副翼（前缘 y=-2.20，后缘 y=-2.42，抬高 0.095）
    wing_element("GEO_F1_RearWing_DRSFlap", -2.20, -2.42, 1.035, 1.060, 0.022, 0.018)

    # 端板
    for s, side in ((-1, 'L'), (1, 'R')):
        outline = [(-2.40, 0.885), (-2.02, 0.885), (-2.02, 1.075), (-2.20, 1.095),
                   (-2.40, 1.070), (-2.46, 0.985)]
        x0, x1 = s * (HALF - 0.006), s * (HALF + 0.008)
        bm = bmesh.new()
        top = [bm.verts.new((x0, y, z)) for (y, z) in outline]
        bot = [bm.verts.new((x1, y, z)) for (y, z) in outline]
        bm.faces.new(top)
        bm.faces.new(list(reversed(bot)))
        nseg = len(outline)
        for i in range(nseg):
            j = (i + 1) % nseg
            bm.faces.new((top[i], top[j], bot[j], bot[i]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(f"GEO_F1_RearWing_Endplate_{side}")
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(f"GEO_F1_RearWing_Endplate_{side}", me)
        c.objects.link(ob)
        me.materials.append(carbon)
        for p in me.polygons:
            p.use_smooth = False
        bv = ob.modifiers.new("V4_Bevel", 'BEVEL')
        bv.width = 0.005
        bv.segments = 2
        bv.limit_method = 'ANGLE'
        # 端板灯条
        lp = bpy.data.objects.get(f"GEO_F1_RearWing_Endplate_Light_{side}")
        if lp:
            lp.location = (s * (HALF + 0.011), -2.414, 0.985)
            lp.dimensions = (0.008, 0.008, 0.150)
            bpy.context.view_layer.update()

    # 中央吊架
    verts, faces = [], []
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(0.055, 0.075, 0.11), verts=bm.verts)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, -2.09, 0.83))
    me = bpy.data.meshes.new("GEO_F1_RearWing_Pylon")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("GEO_F1_RearWing_Pylon", me)
    c.objects.link(ob)
    me.materials.append(carbon)

    # DRS 作动器
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(0.020, 0.045, 0.020), verts=bm.verts)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, -2.14, 1.012))
    me = bpy.data.meshes.new("GEO_F1_RearWing_DRS_Actuator")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("GEO_F1_RearWing_DRS_Actuator", me)
    c.objects.link(ob)
    me.materials.append(carbon)
    print("REAR WING REBUILT")


def rebuild_diffuser():
    c = col("04_Wings_Aerodynamics")
    carbon = bpy.data.materials.get("Mat_Forged_Carbon")
    for o in list(bpy.data.objects):
        if o.name.startswith("GEO_F1_Diffuser_Strake_"):
            bpy.data.objects.remove(o, do_unlink=True)
    HALF = 0.62
    # 弧形扩散器底板
    prof_yz = [(-1.62, 0.030), (-1.86, 0.075), (-2.06, 0.140), (-2.24, 0.215), (-2.38, 0.300)]
    sections = []
    for x in (-HALF, -HALF * 0.5, 0, HALF * 0.5, HALF):
        sec = [(x, y, z) for (y, z) in prof_yz]
        sec += [(x, y, z - 0.018) for (y, z) in reversed(prof_yz)]
        sections.append(sec)
    _plate("GEO_F1_Diffuser_Ramp", sections, carbon, c, smooth=True)
    # 导流栅
    for i, x in enumerate((-0.46, -0.28, -0.10, 0.10, 0.28, 0.46)):
        sec = []
        for (y, z) in prof_yz:
            sec.append((x - 0.006, y, z + 0.002))
        for (y, z) in reversed(prof_yz):
            sec.append((x + 0.006, y, z + 0.100))
        _plate(f"GEO_F1_Diffuser_Strake_{i}", [sec], carbon, c, smooth=False)
    print("DIFFUSER REBUILT")




rebuild_wheels()
surface_pass()
rebuild_rear_wing()
rebuild_diffuser()
add_merc_livery()
for _n in ("GEO_F1_FrontWing_Endplate_L", "GEO_F1_FrontWing_Endplate_R",
           "GEO_F1_RearWing_Endplate_L", "GEO_F1_RearWing_Endplate_R"):
    _o = bpy.data.objects.get(_n)
    if _o and _o.data.materials:
        _o.data.materials[0] = MATS['endplate']
project_decals()

scene.render.engine = 'BLENDER_EEVEE'
scene.eevee.taa_render_samples = 48
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.view_settings.view_transform = 'AgX'
try:
    scene.view_settings.look = 'High Contrast'
except Exception:
    pass
scene.view_settings.exposure = 0.2

bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("MODEL STAGE SAVED:", OUT)
