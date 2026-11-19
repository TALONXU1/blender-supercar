# -*- coding: utf-8 -*-
"""
V6 SPIDER-VERSE STYLIZED EDITION — Lookdev, 3D Ink Outlines & Action FX Builder
Input (READ-ONLY): LATEST/v5_stage_anim.blend
Output           : v6_spiderverse/v6_stage_lookdev.blend
Optional flag    : --preview -> renders 4x 1080p Act I/II/III previews to renders_v6/preview/

严格与 V5 隔离：绝不修改任何 LATEST/v5_*、pipeline/v5_*、textures/* 或 renders_v5/*。
"""
import bpy
import bmesh
import math
import os
import sys
import time
from math import sin, cos, pi, radians
from mathutils import Vector, Matrix, Euler

PROJ = r"D:\项目session\blender-supercar"
SRC_BLEND = os.path.join(PROJ, "LATEST", "v5_stage_anim.blend")
OUT_DIR = os.path.join(PROJ, "v6_spiderverse")
TEX_SV = os.path.join(OUT_DIR, "textures")
OUT_BLEND = os.path.join(OUT_DIR, "v6_stage_lookdev.blend")
PREV_DIR = os.path.join(PROJ, "renders_v6", "preview")

os.makedirs(OUT_DIR, exist_ok=True)
ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

t_build_start = time.time()
bpy.ops.wm.open_mainfile(filepath=SRC_BLEND)
scene = bpy.context.scene
scene.frame_set(1)

# ---------------------------------------------------------------
# 0. EEVEE 非写实高速渲染配置 + 宇宙维度主控属性 scene["sv_dimension"]
#    0.0 = Act I  Earth-1610 (Miles: 经典美漫朱红/普鲁士靛蓝/电青/暖金)
#    1.0 = Act II Earth-65   (Gwen : 表现主义水彩青绿/品红/珊瑚桃粉)
#    2.0 = Act III Earth-928 (2099 : 赛博黑曜/紫外光/激光绯红)
# ---------------------------------------------------------------
scene["sv_dimension"] = 0.0
scene.eevee.use_raytracing = False
scene.eevee.taa_render_samples = 16
scene.render.motion_blur_shutter = 0.05
scene.view_settings.view_transform = 'Standard'
scene.view_settings.look = 'None'
# 更新曝光曲线基准（Standard 下 0.12 保持鲜明高饱和漫画色块，片尾保留淡出）
if scene.animation_data and scene.animation_data.action:
    def _iter_fcs(act):
        fcs = list(getattr(act, "fcurves", []) or [])
        if fcs:
            return fcs
        for lay in getattr(act, "layers", []) or []:
            for st in getattr(lay, "strips", []) or []:
                for cb in getattr(st, "channelbags", []) or []:
                    fcs.extend(cb.fcurves)
        return fcs
    for _fc in _iter_fcs(scene.animation_data.action):
        if "exposure" in _fc.data_path:
            for _kp in _fc.keyframe_points:
                _kp.co.y = 0.12 if _kp.co.x < 2140 else -5.0
scene.view_settings.exposure = 0.12


def add_dim_driver(id_block_or_node_socket, prop_name, expr, index=-1):
    """给任意属性或节点端口绑定读取 scene['sv_dimension'] (变量名 dim) 的表达式驱动器。"""
    if index >= 0:
        fc = id_block_or_node_socket.driver_add(prop_name, index)
    else:
        fc = id_block_or_node_socket.driver_add(prop_name)
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
    """由输入的 dim 端口计算 w2 (Act II Gwen 权重) 与 w3 (Act III 2099 权重)。"""
    sub1 = nt.nodes.new('ShaderNodeMath')
    sub1.operation = 'SUBTRACT'
    sub1.inputs[1].default_value = 1.0
    nt.links.new(dim_out, sub1.inputs[0])
    ab1 = nt.nodes.new('ShaderNodeMath')
    ab1.operation = 'ABSOLUTE'
    nt.links.new(sub1.outputs[0], ab1.inputs[0])
    w2 = nt.nodes.new('ShaderNodeMath')
    w2.operation = 'SUBTRACT'
    w2.use_clamp = True
    w2.inputs[0].default_value = 1.0
    nt.links.new(ab1.outputs[0], w2.inputs[1])

    w3 = nt.nodes.new('ShaderNodeMath')
    w3.operation = 'SUBTRACT'
    w3.use_clamp = True
    w3.inputs[1].default_value = 1.0
    nt.links.new(dim_out, w3.inputs[0])
    return w2.outputs[0], w3.outputs[0]


def add_act_weights(nt):
    """直接在 Math 节点的 INPUT 端口绑定 scene['sv_dimension'] 驱动器（避免 EEVEE 缓存 Value 输出端口常量！）。"""
    sub1 = nt.nodes.new('ShaderNodeMath')
    sub1.name = "SV_Dim_Sub1"
    sub1.operation = 'SUBTRACT'
    sub1.inputs[0].default_value = 0.0
    sub1.inputs[1].default_value = 1.0
    add_dim_driver(sub1.inputs[0], "default_value", "dim")
    ab1 = nt.nodes.new('ShaderNodeMath')
    ab1.operation = 'ABSOLUTE'
    nt.links.new(sub1.outputs[0], ab1.inputs[0])
    w2 = nt.nodes.new('ShaderNodeMath')
    w2.operation = 'SUBTRACT'
    w2.use_clamp = True
    w2.inputs[0].default_value = 1.0
    nt.links.new(ab1.outputs[0], w2.inputs[1])

    w3 = nt.nodes.new('ShaderNodeMath')
    w3.name = "SV_Dim_W3"
    w3.operation = 'SUBTRACT'
    w3.use_clamp = True
    w3.inputs[0].default_value = 0.0
    w3.inputs[1].default_value = 1.0
    add_dim_driver(w3.inputs[0], "default_value", "dim")
    return sub1, w2.outputs[0], w3.outputs[0]


def tri_color_mix(nt, c_act1, c_act2, c_act3, w2_out, w3_out):
    """按 Act I / II / III 插值三组色彩。"""
    m12 = nt.nodes.new('ShaderNodeMixRGB')
    m12.inputs['Color1'].default_value = (*c_act1, 1.0)
    m12.inputs['Color2'].default_value = (*c_act2, 1.0)
    nt.links.new(w2_out, m12.inputs['Factor'])
    m123 = nt.nodes.new('ShaderNodeMixRGB')
    m123.inputs['Color2'].default_value = (*c_act3, 1.0)
    nt.links.new(w3_out, m123.inputs['Factor'])
    nt.links.new(m12.outputs['Color'], m123.inputs['Color1'])
    return m123.outputs['Color']


# ---------------------------------------------------------------
# 1. 核心漫画节点组 NG_SV_ComicSurface
#    - 纯白 Diffuse BSDF -> ShaderToRGB 提取真实日照与投影辐照度
#    - 线性空间精确校准的深邃普鲁士靛蓝(1610) / 青紫水彩(65) / 黑曜紫外光(2099) 漫画阴影
#    - 16:9 屏幕空间 (Window) 14px 高对比双极本戴半调网点 + 45° 浓墨钢笔交叉排线
#    - 锐利阶梯双边缘光 (Dual Rim Kick: 电青 + 品红/激光绯红)
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
    s_ht.default_value = 72.0
    s_hts = ng.interface.new_socket(name="Halftone Strength", in_out='INPUT', socket_type='NodeSocketFloat')
    s_hts.default_value = 0.72
    s_hcs = ng.interface.new_socket(name="Hatch Strength", in_out='INPUT', socket_type='NodeSocketFloat')
    s_hcs.default_value = 0.75
    s_nrm = ng.interface.new_socket(name="Normal", in_out='INPUT', socket_type='NodeSocketVector')
    ng.interface.new_socket(name="Shader", in_out='OUTPUT', socket_type='NodeSocketShader')

    gi = ng.nodes.new('NodeGroupInput')
    go = ng.nodes.new('NodeGroupOutput')
    w2, w3 = act_weights_from_socket(ng, gi.outputs['SV Dimension'])

    # A) 提取纯光照亮度 irr
    diff = ng.nodes.new('ShaderNodeBsdfDiffuse')
    diff.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)
    ng.links.new(gi.outputs['Normal'], diff.inputs['Normal'])
    s2r = ng.nodes.new('ShaderNodeShaderToRGB')
    ng.links.new(diff.outputs['BSDF'], s2r.inputs['Shader'])
    rgb2bw = ng.nodes.new('ShaderNodeRGBToBW')
    ng.links.new(s2r.outputs['Color'], rgb2bw.inputs['Color'])
    irr = rgb2bw.outputs['Val']

    # B) 三阶硬边卡通明暗量化 (0.0=暗部, 0.5=中调, 1.0=高光块)
    band_ramp = ng.nodes.new('ShaderNodeValToRGB')
    band_ramp.color_ramp.interpolation = 'CONSTANT'
    band_ramp.color_ramp.elements[0].position = 0.0
    band_ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    e_mid = band_ramp.color_ramp.elements.new(0.28)
    e_mid.color = (0.5, 0.5, 0.5, 1.0)
    band_ramp.color_ramp.elements[-1].position = 0.68
    band_ramp.color_ramp.elements[-1].color = (1.0, 1.0, 1.0, 1.0)
    ng.links.new(irr, band_ramp.inputs[0])

    # 线性色值校准：深邃高饱和普鲁士靛蓝(Act1) / 水彩青梅紫(Act2) / 赛博深紫外(Act3)
    sh_tint = tri_color_mix(ng, (0.005, 0.003, 0.028), (0.006, 0.028, 0.048), (0.010, 0.002, 0.038), w2, w3)
    mid_tint = tri_color_mix(ng, (0.012, 0.004, 0.002), (0.018, 0.028, 0.036), (0.024, 0.004, 0.032), w2, w3)
    hi_tint = tri_color_mix(ng, (0.14, 0.07, 0.015), (0.16, 0.05, 0.14), (0.02, 0.14, 0.24), w2, w3)

    sh_mul = ng.nodes.new('ShaderNodeMixRGB')
    sh_mul.blend_type = 'MULTIPLY'
    sh_mul.inputs['Factor'].default_value = 1.0
    sh_mul.inputs['Color2'].default_value = (0.24, 0.22, 0.34, 1.0)
    ng.links.new(gi.outputs['Base Color'], sh_mul.inputs['Color1'])
    sh_col = ng.nodes.new('ShaderNodeMixRGB')
    sh_col.blend_type = 'ADD'
    sh_col.inputs['Factor'].default_value = 1.0
    ng.links.new(sh_mul.outputs['Color'], sh_col.inputs['Color1'])
    ng.links.new(sh_tint, sh_col.inputs['Color2'])

    mid_mul = ng.nodes.new('ShaderNodeMixRGB')
    mid_mul.blend_type = 'MULTIPLY'
    mid_mul.inputs['Factor'].default_value = 1.0
    mid_mul.inputs['Color2'].default_value = (1.22, 1.18, 1.20, 1.0)
    ng.links.new(gi.outputs['Base Color'], mid_mul.inputs['Color1'])
    mid_col = ng.nodes.new('ShaderNodeMixRGB')
    mid_col.blend_type = 'ADD'
    mid_col.inputs['Factor'].default_value = 1.0
    ng.links.new(mid_mul.outputs['Color'], mid_col.inputs['Color1'])
    ng.links.new(mid_tint, mid_col.inputs['Color2'])

    hi_mul = ng.nodes.new('ShaderNodeMixRGB')
    hi_mul.blend_type = 'MULTIPLY'
    hi_mul.inputs['Factor'].default_value = 1.0
    hi_mul.inputs['Color2'].default_value = (1.75, 1.65, 1.58, 1.0)
    ng.links.new(gi.outputs['Base Color'], hi_mul.inputs['Color1'])
    hi_col = ng.nodes.new('ShaderNodeMixRGB')
    hi_col.blend_type = 'ADD'
    hi_col.inputs['Factor'].default_value = 1.0
    ng.links.new(hi_mul.outputs['Color'], hi_col.inputs['Color1'])
    ng.links.new(hi_tint, hi_col.inputs['Color2'])

    is_mid = ng.nodes.new('ShaderNodeMath'); is_mid.operation = 'GREATER_THAN'; is_mid.inputs[1].default_value = 0.25
    ng.links.new(band_ramp.outputs[0], is_mid.inputs[0])
    is_hi = ng.nodes.new('ShaderNodeMath'); is_hi.operation = 'GREATER_THAN'; is_hi.inputs[1].default_value = 0.75
    ng.links.new(band_ramp.outputs[0], is_hi.inputs[0])

    mix_sm = ng.nodes.new('ShaderNodeMixRGB')
    ng.links.new(is_mid.outputs[0], mix_sm.inputs['Factor'])
    ng.links.new(sh_col.outputs['Color'], mix_sm.inputs['Color1'])
    ng.links.new(mid_col.outputs['Color'], mix_sm.inputs['Color2'])

    mix_smh = ng.nodes.new('ShaderNodeMixRGB')
    ng.links.new(is_hi.outputs[0], mix_smh.inputs['Factor'])
    ng.links.new(mix_sm.outputs['Color'], mix_smh.inputs['Color1'])
    ng.links.new(hi_col.outputs['Color'], mix_smh.inputs['Color2'])

    # C) 16:9 屏幕空间高对比双极本戴半调网点 (Ben-Day Halftone Dots, 1080p 清晰可见)
    tc = ng.nodes.new('ShaderNodeTexCoord')
    sep_w = ng.nodes.new('ShaderNodeSeparateXYZ')
    ng.links.new(tc.outputs['Window'], sep_w.inputs['Vector'])
    wx_asp = ng.nodes.new('ShaderNodeMath')
    wx_asp.operation = 'MULTIPLY'
    wx_asp.inputs[1].default_value = 16.0 / 9.0
    ng.links.new(sep_w.outputs['X'], wx_asp.inputs[0])

    c22, s22 = cos(radians(22.5)), sin(radians(22.5))
    ux1 = ng.nodes.new('ShaderNodeMath'); ux1.operation = 'MULTIPLY'; ux1.inputs[1].default_value = c22
    uy1 = ng.nodes.new('ShaderNodeMath'); uy1.operation = 'MULTIPLY'; uy1.inputs[1].default_value = s22
    ng.links.new(wx_asp.outputs[0], ux1.inputs[0]); ng.links.new(sep_w.outputs['Y'], uy1.inputs[0])
    u_rot = ng.nodes.new('ShaderNodeMath'); u_rot.operation = 'SUBTRACT'
    ng.links.new(ux1.outputs[0], u_rot.inputs[0]); ng.links.new(uy1.outputs[0], u_rot.inputs[1])

    vx1 = ng.nodes.new('ShaderNodeMath'); vx1.operation = 'MULTIPLY'; vx1.inputs[1].default_value = s22
    vy1 = ng.nodes.new('ShaderNodeMath'); vy1.operation = 'MULTIPLY'; vy1.inputs[1].default_value = c22
    ng.links.new(wx_asp.outputs[0], vx1.inputs[0]); ng.links.new(sep_w.outputs['Y'], vy1.inputs[0])
    v_rot = ng.nodes.new('ShaderNodeMath'); v_rot.operation = 'ADD'
    ng.links.new(vx1.outputs[0], v_rot.inputs[0]); ng.links.new(vy1.outputs[0], v_rot.inputs[1])

    u_sc = ng.nodes.new('ShaderNodeMath'); u_sc.operation = 'MULTIPLY'
    v_sc = ng.nodes.new('ShaderNodeMath'); v_sc.operation = 'MULTIPLY'
    ng.links.new(u_rot.outputs[0], u_sc.inputs[0]); ng.links.new(gi.outputs['Halftone Scale'], u_sc.inputs[1])
    ng.links.new(v_rot.outputs[0], v_sc.inputs[0]); ng.links.new(gi.outputs['Halftone Scale'], v_sc.inputs[1])

    u_fr = ng.nodes.new('ShaderNodeMath'); u_fr.operation = 'FRACT'; ng.links.new(u_sc.outputs[0], u_fr.inputs[0])
    v_fr = ng.nodes.new('ShaderNodeMath'); v_fr.operation = 'FRACT'; ng.links.new(v_sc.outputs[0], v_fr.inputs[0])
    du = ng.nodes.new('ShaderNodeMath'); du.operation = 'SUBTRACT'; du.inputs[1].default_value = 0.5; ng.links.new(u_fr.outputs[0], du.inputs[0])
    dv = ng.nodes.new('ShaderNodeMath'); dv.operation = 'SUBTRACT'; dv.inputs[1].default_value = 0.5; ng.links.new(v_fr.outputs[0], dv.inputs[0])
    du2 = ng.nodes.new('ShaderNodeMath'); du2.operation = 'MULTIPLY'; ng.links.new(du.outputs[0], du2.inputs[0]); ng.links.new(du.outputs[0], du2.inputs[1])
    dv2 = ng.nodes.new('ShaderNodeMath'); dv2.operation = 'MULTIPLY'; ng.links.new(dv.outputs[0], dv2.inputs[0]); ng.links.new(dv.outputs[0], dv2.inputs[1])
    dsum = ng.nodes.new('ShaderNodeMath'); dsum.operation = 'ADD'; ng.links.new(du2.outputs[0], dsum.inputs[0]); ng.links.new(dv2.outputs[0], dsum.inputs[1])
    drad = ng.nodes.new('ShaderNodeMath'); drad.operation = 'SQRT'; ng.links.new(dsum.outputs[0], drad.inputs[0])

    ht_zone = ng.nodes.new('ShaderNodeValToRGB')
    ht_zone.color_ramp.interpolation = 'LINEAR'
    ht_zone.color_ramp.elements[0].position = 0.14
    ht_zone.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    hz1 = ht_zone.color_ramp.elements.new(0.52)
    hz1.color = (0.48, 0.48, 0.48, 1.0)
    ht_zone.color_ramp.elements[-1].position = 0.92
    ht_zone.color_ramp.elements[-1].color = (0.0, 0.0, 0.0, 1.0)
    ng.links.new(irr, ht_zone.inputs[0])

    dot_hit = ng.nodes.new('ShaderNodeMath')
    dot_hit.operation = 'LESS_THAN'
    ng.links.new(drad.outputs[0], dot_hit.inputs[0])
    ng.links.new(ht_zone.outputs[0], dot_hit.inputs[1])

    ht_fac = ng.nodes.new('ShaderNodeMath')
    ht_fac.operation = 'MULTIPLY'
    ng.links.new(dot_hit.outputs[0], ht_fac.inputs[0])
    ng.links.new(gi.outputs['Halftone Strength'], ht_fac.inputs[1])

    # 亮区网点跳亮色（电青/洋红/激光红），暗中调网点跳深靛色，确保无论深浅表面网点对比度都拉满！
    ht_bright = tri_color_mix(ng, (0.0, 0.85, 1.0), (1.0, 0.22, 0.72), (1.0, 0.05, 0.26), w2, w3)
    ht_dark = tri_color_mix(ng, (0.004, 0.003, 0.025), (0.005, 0.024, 0.045), (0.012, 0.001, 0.032), w2, w3)
    is_upper = ng.nodes.new('ShaderNodeMath'); is_upper.operation = 'GREATER_THAN'; is_upper.inputs[1].default_value = 0.46
    ng.links.new(irr, is_upper.inputs[0])
    ht_target = ng.nodes.new('ShaderNodeMixRGB')
    ng.links.new(is_upper.outputs[0], ht_target.inputs['Factor'])
    ng.links.new(ht_dark, ht_target.inputs['Color1'])
    ng.links.new(ht_bright, ht_target.inputs['Color2'])

    after_ht = ng.nodes.new('ShaderNodeMixRGB')
    ng.links.new(ht_fac.outputs[0], after_ht.inputs['Factor'])
    ng.links.new(mix_smh.outputs['Color'], after_ht.inputs['Color1'])
    ng.links.new(ht_target.outputs['Color'], after_ht.inputs['Color2'])

    # D) 45° 浓墨钢笔交叉排线 (Pen Crosshatching: irr < 0.46 主排线, irr < 0.24 双向网格排线)
    h_sum = ng.nodes.new('ShaderNodeMath'); h_sum.operation = 'ADD'
    ng.links.new(wx_asp.outputs[0], h_sum.inputs[0]); ng.links.new(sep_w.outputs['Y'], h_sum.inputs[1])
    h_sc1 = ng.nodes.new('ShaderNodeMath'); h_sc1.operation = 'MULTIPLY'; h_sc1.inputs[1].default_value = 92.0
    ng.links.new(h_sum.outputs[0], h_sc1.inputs[0])
    h_fr1 = ng.nodes.new('ShaderNodeMath'); h_fr1.operation = 'FRACT'; ng.links.new(h_sc1.outputs[0], h_fr1.inputs[0])
    h_ln1 = ng.nodes.new('ShaderNodeMath'); h_ln1.operation = 'LESS_THAN'; h_ln1.inputs[1].default_value = 0.26
    ng.links.new(h_fr1.outputs[0], h_ln1.inputs[0])

    h_dif = ng.nodes.new('ShaderNodeMath'); h_dif.operation = 'SUBTRACT'
    ng.links.new(wx_asp.outputs[0], h_dif.inputs[0]); ng.links.new(sep_w.outputs['Y'], h_dif.inputs[1])
    h_sc2 = ng.nodes.new('ShaderNodeMath'); h_sc2.operation = 'MULTIPLY'; h_sc2.inputs[1].default_value = 92.0
    ng.links.new(h_dif.outputs[0], h_sc2.inputs[0])
    h_fr2 = ng.nodes.new('ShaderNodeMath'); h_fr2.operation = 'FRACT'; ng.links.new(h_sc2.outputs[0], h_fr2.inputs[0])
    h_ln2 = ng.nodes.new('ShaderNodeMath'); h_ln2.operation = 'LESS_THAN'; h_ln2.inputs[1].default_value = 0.24
    ng.links.new(h_fr2.outputs[0], h_ln2.inputs[0])

    sh_m1 = ng.nodes.new('ShaderNodeMath'); sh_m1.operation = 'LESS_THAN'; sh_m1.inputs[1].default_value = 0.46
    ng.links.new(irr, sh_m1.inputs[0])
    sh_m2 = ng.nodes.new('ShaderNodeMath'); sh_m2.operation = 'LESS_THAN'; sh_m2.inputs[1].default_value = 0.24
    ng.links.new(irr, sh_m2.inputs[0])

    hm1 = ng.nodes.new('ShaderNodeMath'); hm1.operation = 'MULTIPLY'
    ng.links.new(h_ln1.outputs[0], hm1.inputs[0]); ng.links.new(sh_m1.outputs[0], hm1.inputs[1])
    hm2 = ng.nodes.new('ShaderNodeMath'); hm2.operation = 'MULTIPLY'
    ng.links.new(h_ln2.outputs[0], hm2.inputs[0]); ng.links.new(sh_m2.outputs[0], hm2.inputs[1])
    h_any = ng.nodes.new('ShaderNodeMath'); h_any.operation = 'MAXIMUM'
    ng.links.new(hm1.outputs[0], h_any.inputs[0]); ng.links.new(hm2.outputs[0], h_any.inputs[1])
    h_fac = ng.nodes.new('ShaderNodeMath'); h_fac.operation = 'MULTIPLY'
    ng.links.new(h_any.outputs[0], h_fac.inputs[0]); ng.links.new(gi.outputs['Hatch Strength'], h_fac.inputs[1])

    ink_hatch_col = tri_color_mix(ng, (0.0012, 0.0008, 0.008), (0.0012, 0.006, 0.014), (0.0020, 0.0005, 0.010), w2, w3)
    after_hatch = ng.nodes.new('ShaderNodeMixRGB')
    ng.links.new(h_fac.outputs[0], after_hatch.inputs['Factor'])
    ng.links.new(after_ht.outputs['Color'], after_hatch.inputs['Color1'])
    ng.links.new(ink_hatch_col, after_hatch.inputs['Color2'])

    # E) 阶梯双色漫画边缘光 (Dual Rim Kick: 电青主轮廓光 + 品红/绯红对侧轮廓光)
    lw = ng.nodes.new('ShaderNodeLayerWeight')
    lw.inputs['Blend'].default_value = 0.32
    ng.links.new(gi.outputs['Normal'], lw.inputs['Normal'])
    rim_step = ng.nodes.new('ShaderNodeValToRGB')
    rim_step.color_ramp.interpolation = 'CONSTANT'
    rim_step.color_ramp.elements[0].position = 0.0
    rim_step.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    rim_step.color_ramp.elements[1].position = 0.66
    rim_step.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    ng.links.new(lw.outputs['Facing'], rim_step.inputs[0])

    # 用世界法线 X 分量区分左右双色边缘光（左电青/薄荷，右品红/绯红）
    geo = ng.nodes.new('ShaderNodeNewGeometry')
    sep_n = ng.nodes.new('ShaderNodeSeparateXYZ')
    ng.links.new(geo.outputs['Normal'], sep_n.inputs['Vector'])
    n_side = ng.nodes.new('ShaderNodeMapRange')
    n_side.inputs['From Min'].default_value = -0.25
    n_side.inputs['From Max'].default_value = 0.25
    ng.links.new(sep_n.outputs['X'], n_side.inputs['Value'])

    rim_c1 = tri_color_mix(ng, (0.0, 0.90, 1.0), (0.08, 0.98, 0.82), (0.0, 0.82, 1.0), w2, w3)
    rim_c2 = tri_color_mix(ng, (1.0, 0.12, 0.48), (1.0, 0.24, 0.72), (1.0, 0.04, 0.14), w2, w3)
    rim_dual = ng.nodes.new('ShaderNodeMixRGB')
    ng.links.new(n_side.outputs['Result'], rim_dual.inputs['Factor'])
    ng.links.new(rim_c1, rim_dual.inputs['Color1'])
    ng.links.new(rim_c2, rim_dual.inputs['Color2'])

    rim_amt = ng.nodes.new('ShaderNodeMath')
    rim_amt.operation = 'MULTIPLY'
    ng.links.new(rim_step.outputs[0], rim_amt.inputs[0])
    ng.links.new(gi.outputs['Rim Strength'], rim_amt.inputs[1])

    final_col = ng.nodes.new('ShaderNodeMixRGB')
    ng.links.new(rim_amt.outputs[0], final_col.inputs['Factor'])
    ng.links.new(after_hatch.outputs['Color'], final_col.inputs['Color1'])
    ng.links.new(rim_dual.outputs['Color'], final_col.inputs['Color2'])

    em = ng.nodes.new('ShaderNodeEmission')
    em.inputs['Strength'].default_value = 1.0
    ng.links.new(final_col.outputs['Color'], em.inputs['Color'])
    ng.links.new(em.outputs['Emission'], go.inputs['Shader'])
    return ng


NG_COMIC = build_comic_nodegroup()


# ---------------------------------------------------------------
# 2. 天空穹顶 V5_SkyDome + 太阳/补光/世界随 scene["sv_dimension"] 三幕变色
# ---------------------------------------------------------------
def upgrade_sky_and_lights():
    sun_ob = bpy.data.objects.get("LGT_V5Sun")
    sun_dir = (sun_ob.matrix_world.to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized() if sun_ob else Vector((-0.57, -0.74, 0.37))

    if sun_ob and sun_ob.data:
        # 太阳光强度与色彩随三幕切换：暖金(1610) -> 透亮珊瑚粉白(65) -> 赛博霓虹紫青(2099)
        add_dim_driver(sun_ob.data, "energy", "5.8 + 1.4*max(0.0, 1.0-abs(dim-1.0)) + 0.6*max(0.0, dim-1.0)")
        add_dim_driver(sun_ob.data, "color", "1.0 if dim < 1.0 else max(0.75, 1.0 - 0.25*(dim-1.0))", 0)
        add_dim_driver(sun_ob.data, "color", "0.86 - 0.08*max(0.0, 1.0-abs(dim-1.0)) - 0.25*max(0.0, dim-1.0)", 1)
        add_dim_driver(sun_ob.data, "color", "0.72 + 0.28*min(1.0, max(0.0, dim))", 2)

    fill_ob = bpy.data.objects.get("LGT_V5SkyFill")
    if fill_ob and fill_ob.data:
        add_dim_driver(fill_ob.data, "energy", "0.85 + 0.55*max(0.0, 1.0-abs(dim-1.0)) + 0.35*max(0.0, dim-1.0)")
        add_dim_driver(fill_ob.data, "color", "0.42 + 0.52*max(0.0, 1.0-abs(dim-1.0)) + 0.30*max(0.0, dim-1.0)", 0)
        add_dim_driver(fill_ob.data, "color", "0.72 + 0.24*max(0.0, 1.0-abs(dim-1.0)) - 0.35*max(0.0, dim-1.0)", 1)
        add_dim_driver(fill_ob.data, "color", "0.98", 2)

    sky_ob = bpy.data.objects.get("V5_SkyDome")
    if sky_ob and sky_ob.data.materials:
        sm = sky_ob.data.materials[0]
        snt = sm.node_tree
        snt.nodes.clear()
        sout = snt.nodes.new('ShaderNodeOutputMaterial')
        sem = snt.nodes.new('ShaderNodeEmission')
        sem.inputs['Strength'].default_value = 1.0
        _, sw2, sw3 = add_act_weights(snt)

        tc = snt.nodes.new('ShaderNodeTexCoord')
        nrm = snt.nodes.new('ShaderNodeVectorMath')
        nrm.operation = 'NORMALIZE'
        snt.links.new(tc.outputs['Object'], nrm.inputs[0])
        sep = snt.nodes.new('ShaderNodeSeparateXYZ')
        snt.links.new(nrm.outputs['Vector'], sep.inputs['Vector'])

        mz = snt.nodes.new('ShaderNodeMapRange')
        mz.inputs['From Min'].default_value = -0.03
        mz.inputs['From Max'].default_value = 0.85
        snt.links.new(sep.outputs['Z'], mz.inputs['Value'])
        pz = snt.nodes.new('ShaderNodeMath')
        pz.operation = 'POWER'
        pz.inputs[1].default_value = 0.58
        snt.links.new(mz.outputs['Result'], pz.inputs[0])

        def _make_sky_ramp(stops):
            r = snt.nodes.new('ShaderNodeValToRGB')
            r.color_ramp.interpolation = 'B_SPLINE'
            r.color_ramp.elements[0].position = stops[0][0]
            r.color_ramp.elements[0].color = (*stops[0][1], 1.0)
            r.color_ramp.elements[1].position = stops[-1][0]
            r.color_ramp.elements[1].color = (*stops[-1][1], 1.0)
            for p_s, c_s in stops[1:-1]:
                el = r.color_ramp.elements.new(p_s)
                el.color = (*c_s, 1.0)
            snt.links.new(pz.outputs[0], r.inputs[0])
            return r.outputs['Color']

        # Act I Earth-1610: 布鲁克林漫画赤红金橙地平线 -> 皇家紫 -> 普鲁士深蓝天顶
        sky1 = _make_sky_ramp([
            (0.00, (0.08, 0.04, 0.14)),
            (0.14, (0.95, 0.34, 0.18)),
            (0.30, (0.68, 0.14, 0.42)),
            (0.56, (0.16, 0.12, 0.44)),
            (1.00, (0.035, 0.045, 0.18)),
        ])
        # Act II Earth-65: 格温水彩珊瑚蜜桃 -> 霓虹洋红薰衣草 -> 绿松石青蓝天顶
        sky2 = _make_sky_ramp([
            (0.00, (0.12, 0.18, 0.26)),
            (0.15, (0.98, 0.56, 0.48)),
            (0.34, (0.92, 0.24, 0.62)),
            (0.60, (0.12, 0.68, 0.74)),
            (1.00, (0.04, 0.36, 0.52)),
        ])
        # Act III Earth-928: 2099 赛博激光绯红地平线 -> 电光紫外 -> 黑曜深蓝天顶
        sky3 = _make_sky_ramp([
            (0.00, (0.04, 0.01, 0.08)),
            (0.13, (0.96, 0.05, 0.22)),
            (0.28, (0.42, 0.06, 0.68)),
            (0.55, (0.07, 0.04, 0.26)),
            (1.00, (0.015, 0.018, 0.085)),
        ])

        m12 = snt.nodes.new('ShaderNodeMixRGB')
        snt.links.new(sw2, m12.inputs['Factor'])
        snt.links.new(sky1, m12.inputs['Color1'])
        snt.links.new(sky2, m12.inputs['Color2'])
        m123 = snt.nodes.new('ShaderNodeMixRGB')
        snt.links.new(sw3, m123.inputs['Factor'])
        snt.links.new(m12.outputs['Color'], m123.inputs['Color1'])
        snt.links.new(sky3, m123.inputs['Color2'])

        # 漫画阶梯太阳日冕光环 + 水彩笔触云带
        sdot = snt.nodes.new('ShaderNodeVectorMath')
        sdot.operation = 'DOT_PRODUCT'
        sdot.inputs[1].default_value = (sun_dir.x, sun_dir.y, sun_dir.z)
        snt.links.new(nrm.outputs['Vector'], sdot.inputs[0])
        sun_rings = snt.nodes.new('ShaderNodeValToRGB')
        sun_rings.color_ramp.interpolation = 'CONSTANT'
        sun_rings.color_ramp.elements[0].position = 0.0
        sun_rings.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
        sr1 = sun_rings.color_ramp.elements.new(0.92)
        sr1.color = (0.28, 0.14, 0.22, 1.0)
        sun_rings.color_ramp.elements[-1].position = 0.982
        sun_rings.color_ramp.elements[-1].color = (0.85, 0.56, 0.24, 1.0)
        snt.links.new(sdot.outputs['Value'], sun_rings.inputs[0])

        # 天空水彩笔触噪波（Act II 增强表现主义天幕笔刷感）
        c_scale = snt.nodes.new('ShaderNodeVectorMath')
        c_scale.operation = 'MULTIPLY'
        c_scale.inputs[1].default_value = (3.5, 3.5, 16.0)
        snt.links.new(nrm.outputs['Vector'], c_scale.inputs[0])
        c_noise = snt.nodes.new('ShaderNodeTexNoise')
        c_noise.inputs['Scale'].default_value = 2.8
        c_noise.inputs['Detail'].default_value = 5.0
        c_noise.inputs['Distortion'].default_value = 1.4
        snt.links.new(c_scale.outputs['Vector'], c_noise.inputs['Vector'])
        c_step = snt.nodes.new('ShaderNodeValToRGB')
        c_step.color_ramp.interpolation = 'CONSTANT'
        c_step.color_ramp.elements[0].position = 0.0
        c_step.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
        c_step.color_ramp.elements[1].position = 0.62
        c_step.color_ramp.elements[1].color = (0.16, 0.12, 0.20, 1.0)
        snt.links.new(c_noise.outputs['Fac'], c_step.inputs[0])

        add_sun = snt.nodes.new('ShaderNodeMixRGB')
        add_sun.blend_type = 'ADD'
        add_sun.inputs['Factor'].default_value = 0.75
        snt.links.new(m123.outputs['Color'], add_sun.inputs['Color1'])
        snt.links.new(sun_rings.outputs['Color'], add_sun.inputs['Color2'])

        add_cld = snt.nodes.new('ShaderNodeMixRGB')
        add_cld.blend_type = 'SCREEN'
        add_cld.inputs['Factor'].default_value = 0.45
        snt.links.new(add_sun.outputs['Color'], add_cld.inputs['Color1'])
        snt.links.new(c_step.outputs['Color'], add_cld.inputs['Color2'])

        snt.links.new(add_cld.outputs['Color'], sem.inputs['Color'])
        snt.links.new(sem.outputs['Emission'], sout.inputs['Surface'])


upgrade_sky_and_lights()


# ---------------------------------------------------------------
# 3. 赛车与赛道材质全面转化为蜘蛛侠漫画着色器（严格保留动态发光动画曲线！）
# ---------------------------------------------------------------
def apply_comic_to_mat(mat, base_rgb=None, rim=0.85, ht_scale=96.0, ht_str=0.52, hc_str=0.50, swap_img=None):
    if not mat or not mat.use_nodes:
        return
    nt = mat.node_tree
    # 若该材质本身带有动画曲线（刹车热辉光/雨灯/换挡灯/刹车盘/卡钳），专门处理以绝不丢失关键帧
    has_anim = bool(nt.animation_data and (nt.animation_data.action or nt.animation_data.drivers))
    if has_anim:
        return

    tex_node = next((n for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image), None)
    saved_img = tex_node.image if tex_node else None
    if swap_img:
        fp = os.path.join(TEX_SV, swap_img)
        if os.path.exists(fp):
            saved_img = bpy.data.images.load(fp, check_existing=True)

    old_bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if base_rgb is None:
        if old_bsdf:
            c = old_bsdf.inputs['Base Color'].default_value
            base_rgb = (c[0], c[1], c[2])
        else:
            base_rgb = (0.25, 0.25, 0.30)

    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    grp = nt.nodes.new('ShaderNodeGroup')
    grp.node_tree = NG_COMIC
    add_dim_driver(grp.inputs['SV Dimension'], "default_value", "dim")
    grp.inputs['Rim Strength'].default_value = rim
    grp.inputs['Halftone Scale'].default_value = ht_scale * 0.76
    grp.inputs['Halftone Strength'].default_value = min(0.88, ht_str * 1.32)
    grp.inputs['Hatch Strength'].default_value = min(0.88, hc_str * 1.35)

    if saved_img is not None:
        tn = nt.nodes.new('ShaderNodeTexImage')
        tn.image = saved_img
        tn.extension = 'REPEAT'
        nt.links.new(tn.outputs['Color'], grp.inputs['Base Color'])
        if 'Alpha' in tn.outputs and mat.name.startswith("Mat_DEC_"):
            try:
                mat.surface_render_method = 'DITHERED'
            except Exception:
                pass
            tr = nt.nodes.new('ShaderNodeBsdfTransparent')
            mx = nt.nodes.new('ShaderNodeMixShader')
            nt.links.new(tn.outputs['Alpha'], mx.inputs['Fac'])
            nt.links.new(tr.outputs['BSDF'], mx.inputs[1])
            nt.links.new(grp.outputs['Shader'], mx.inputs[2])
            nt.links.new(mx.outputs['Shader'], out.inputs['Surface'])
            return
    else:
        grp.inputs['Base Color'].default_value = (*base_rgb, 1.0)

    nt.links.new(grp.outputs['Shader'], out.inputs['Surface'])


# A) 替换赛道漫画贴图材质（维修车库 / 广告牌 / 大屏 / 刹车牌 / DRS 牌）
_TEX_SWAPS = {
    "V5_PitGarage": ("sv_pit_garage.png", 0.35),
    "V5_AdBoard": ("sv_ad_boards.png", 0.55),
    "V5_BigScreen": ("sv_bigscreen.png", 0.95),
    "V5_DRSBoard": ("sv_drs_board.png", 0.45),
    "V5_Brake150": ("sv_brake_150.png", 0.35),
    "V5_Brake100": ("sv_brake_100.png", 0.35),
    "V5_Brake50": ("sv_brake_50.png", 0.35),
}
for _mn, (_fn, _em_boost) in _TEX_SWAPS.items():
    _m = bpy.data.materials.get(_mn)
    _fp = os.path.join(TEX_SV, _fn)
    if _m and os.path.exists(_fp):
        _nt = _m.node_tree
        _nt.nodes.clear()
        _img = bpy.data.images.load(_fp, check_existing=True)
        _tn = _nt.nodes.new('ShaderNodeTexImage')
        _tn.image = _img
        _tn.extension = 'REPEAT'
        _grp = _nt.nodes.new('ShaderNodeGroup')
        _grp.node_tree = NG_COMIC
        add_dim_driver(_grp.inputs['SV Dimension'], "default_value", "dim")
        _grp.inputs['Rim Strength'].default_value = 0.08
        _grp.inputs['Halftone Strength'].default_value = 0.42
        _grp.inputs['Hatch Strength'].default_value = 0.35
        _nt.links.new(_tn.outputs['Color'], _grp.inputs['Base Color'])
        _em = _nt.nodes.new('ShaderNodeEmission')
        _em.inputs['Strength'].default_value = _em_boost
        _nt.links.new(_tn.outputs['Color'], _em.inputs['Color'])
        _add = _nt.nodes.new('ShaderNodeAddShader')
        _nt.links.new(_grp.outputs['Shader'], _add.inputs[0])
        _nt.links.new(_em.outputs['Emission'], _add.inputs[1])
        _out = _nt.nodes.new('ShaderNodeOutputMaterial')
        _nt.links.new(_add.outputs['Shader'], _out.inputs['Surface'])

# B) 赛道地面系漫画材质：手绘笔刷流线沥青、高饱和红白青漫画路肩、色块草坪（全部零高光防炫光！）
def style_track_surfaces():
    # 沥青：深蓝紫漫画底色 + 沿赛道高速手绘笔刷流线 + 本戴网点
    m_asp = bpy.data.materials.get("V5_Asphalt")
    if m_asp:
        nt = m_asp.node_tree
        nt.nodes.clear()
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        grp = nt.nodes.new('ShaderNodeGroup')
        grp.node_tree = NG_COMIC
        add_dim_driver(grp.inputs['SV Dimension'], "default_value", "dim")
        _, aw2, aw3 = add_act_weights(nt)
        grp.inputs['Rim Strength'].default_value = 0.0
        grp.inputs['Halftone Scale'].default_value = 66.0
        grp.inputs['Halftone Strength'].default_value = 0.68
        grp.inputs['Hatch Strength'].default_value = 0.72
        uv = nt.nodes.new('ShaderNodeUVMap'); uv.uv_map = "UVMap"
        sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(uv.outputs['UV'], sep.inputs['Vector'])
        comb = nt.nodes.new('ShaderNodeCombineXYZ')
        mx = nt.nodes.new('ShaderNodeMath'); mx.operation = 'MULTIPLY'; mx.inputs[1].default_value = 28.0
        my = nt.nodes.new('ShaderNodeMath'); my.operation = 'MULTIPLY'; my.inputs[1].default_value = 0.42
        nt.links.new(sep.outputs['X'], mx.inputs[0]); nt.links.new(sep.outputs['Y'], my.inputs[0])
        nt.links.new(mx.outputs['Value'], comb.inputs['X']); nt.links.new(my.outputs['Value'], comb.inputs['Y'])
        ns = nt.nodes.new('ShaderNodeTexNoise'); ns.inputs['Scale'].default_value = 3.2; ns.inputs['Detail'].default_value = 4.0
        nt.links.new(comb.outputs['Vector'], ns.inputs['Vector'])
        # 三幕赛道沥青色盘：Act1 靛蓝石墨 -> Act2 格温水彩青紫/玫瑰灰 -> Act3 2099 赛博黑曜紫外
        asp_lo = tri_color_mix(nt, (0.028, 0.026, 0.072), (0.065, 0.125, 0.195), (0.032, 0.012, 0.095), aw2, aw3)
        asp_hi = tri_color_mix(nt, (0.082, 0.092, 0.175), (0.245, 0.135, 0.245), (0.125, 0.025, 0.185), aw2, aw3)
        st_a = nt.nodes.new('ShaderNodeMath'); st_a.operation = 'GREATER_THAN'; st_a.inputs[1].default_value = 0.52
        nt.links.new(ns.outputs['Fac'], st_a.inputs[0])
        asp_mix = nt.nodes.new('ShaderNodeMixRGB')
        nt.links.new(st_a.outputs[0], asp_mix.inputs['Factor'])
        nt.links.new(asp_lo, asp_mix.inputs['Color1'])
        nt.links.new(asp_hi, asp_mix.inputs['Color2'])
        nt.links.new(asp_mix.outputs['Color'], grp.inputs['Base Color'])
        nt.links.new(grp.outputs['Shader'], out.inputs['Surface'])

    _flat_specs = {
        "V5_RubberLine": ((0.016, 0.015, 0.052), 0.0, 92.0, 0.52, 0.68),
        "V5_WhiteLine": ((0.94, 0.95, 0.98), 0.0, 92.0, 0.22, 0.18),
        "V5_CurbRed": ((0.96, 0.04, 0.24), 0.0, 88.0, 0.68, 0.52),
        "V5_CurbWhite": ((0.96, 0.94, 0.90), 0.0, 88.0, 0.42, 0.30),
        "V5_SausageYellow": ((1.00, 0.74, 0.02), 0.15, 92.0, 0.58, 0.45),
        "V5_SausageBlack": ((0.018, 0.015, 0.055), 0.15, 92.0, 0.45, 0.65),
        "V5_Gravel": ((0.48, 0.30, 0.26), 0.0, 76.0, 0.62, 0.52),
        "V5_Barrier": ((0.055, 0.068, 0.175), 0.35, 88.0, 0.58, 0.55),
        "V5_Concrete": ((0.28, 0.25, 0.38), 0.18, 88.0, 0.52, 0.52),
        "V5_Steel": ((0.12, 0.15, 0.30), 0.42, 92.0, 0.52, 0.52),
        "V5_Roof": ((0.10, 0.12, 0.28), 0.28, 88.0, 0.48, 0.50),
        "V5_Hangar": ((0.14, 0.12, 0.30), 0.18, 80.0, 0.45, 0.48),
        "V5_Tree": ((0.025, 0.105, 0.105), 0.0, 76.0, 0.52, 0.60),
    }
    for mn, (rgb, rm, hs, hts, hcs) in _flat_specs.items():
        apply_comic_to_mat(bpy.data.materials.get(mn), rgb, rim=rm, ht_scale=hs, ht_str=hts, hc_str=hcs)

    # 草地：三幕表现主义水彩色块（Act1 翠青绿 -> Act2 格温薄荷绿松石/洋红花影 -> Act3 2099 赛博深青紫）
    m_gr = bpy.data.materials.get("V5_Grass")
    if m_gr:
        nt = m_gr.node_tree
        nt.nodes.clear()
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        grp = nt.nodes.new('ShaderNodeGroup')
        grp.node_tree = NG_COMIC
        add_dim_driver(grp.inputs['SV Dimension'], "default_value", "dim")
        _, gw2, gw3 = add_act_weights(nt)
        grp.inputs['Rim Strength'].default_value = 0.0
        grp.inputs['Halftone Scale'].default_value = 62.0
        grp.inputs['Halftone Strength'].default_value = 0.66
        grp.inputs['Hatch Strength'].default_value = 0.60
        geo = nt.nodes.new('ShaderNodeNewGeometry')
        ns = nt.nodes.new('ShaderNodeTexNoise'); ns.inputs['Scale'].default_value = 0.045; ns.inputs['Detail'].default_value = 3.0
        nt.links.new(geo.outputs['Position'], ns.inputs['Vector'])
        gr_lo = tri_color_mix(nt, (0.032, 0.135, 0.105), (0.045, 0.265, 0.275), (0.025, 0.035, 0.125), gw2, gw3)
        gr_hi = tri_color_mix(nt, (0.095, 0.245, 0.135), (0.195, 0.385, 0.345), (0.095, 0.025, 0.185), gw2, gw3)
        st_g = nt.nodes.new('ShaderNodeMath'); st_g.operation = 'GREATER_THAN'; st_g.inputs[1].default_value = 0.50
        nt.links.new(ns.outputs['Fac'], st_g.inputs[0])
        gr_mix = nt.nodes.new('ShaderNodeMixRGB')
        nt.links.new(st_g.outputs[0], gr_mix.inputs['Factor'])
        nt.links.new(gr_lo, gr_mix.inputs['Color1'])
        nt.links.new(gr_hi, gr_mix.inputs['Color2'])
        nt.links.new(gr_mix.outputs['Color'], grp.inputs['Base Color'])
        nt.links.new(grp.outputs['Shader'], out.inputs['Surface'])


style_track_surfaces()

# C) 赛车英雄漫画材质：鲜明蜘蛛侠配色（深电光靛蓝车身、绯红/曜黄/青色高饱和色块、碳纤维醒目网点与双色轮廓光）
_CAR_SPECS = {
    "Mat_RedBull_MatteNavy": ((0.045, 0.065, 0.24), 0.95, 102.0, 0.62, 0.58),
    "Mat_RedBull_Crimson": ((0.96, 0.05, 0.22), 0.92, 102.0, 0.58, 0.48),
    "Mat_RedBull_SolarYellow": ((1.00, 0.78, 0.04), 0.88, 102.0, 0.55, 0.42),
    "Mat_Merc_Petronas": ((0.0, 0.88, 0.82), 0.92, 102.0, 0.55, 0.45),
    "Mat_Merc_Silver": ((0.76, 0.82, 0.94), 0.90, 102.0, 0.52, 0.42),
    "Mat_Forged_Carbon": ((0.065, 0.072, 0.155), 0.88, 108.0, 0.60, 0.56),
    "Mat_Carbon_Satin": ((0.075, 0.082, 0.175), 0.85, 108.0, 0.58, 0.54),
    "Mat_Carbon_Endplate_Matte": ((0.058, 0.065, 0.145), 0.90, 104.0, 0.60, 0.56),
    "Mat_Duct_Carbon": ((0.055, 0.060, 0.135), 0.80, 108.0, 0.55, 0.52),
    "Mat_Tire_Slick_Compound": ((0.048, 0.048, 0.095), 0.92, 98.0, 0.58, 0.60),
    "Mat_Rim_Forged_Dark": ((0.085, 0.098, 0.215), 0.90, 106.0, 0.56, 0.52),
    "Mat_Rim_Machined_Lip": ((0.85, 0.90, 0.98), 0.92, 106.0, 0.45, 0.35),
    "Mat_Liquid_Titanium": ((0.78, 0.84, 0.96), 0.95, 104.0, 0.52, 0.42),
    "Mat_Titanium_Hardware": ((0.72, 0.78, 0.92), 0.85, 108.0, 0.45, 0.40),
    "Mat_Anodized_Gold": ((1.00, 0.74, 0.08), 0.88, 108.0, 0.52, 0.42),
    "Mat_CenterLock_Cyan": ((0.0, 0.92, 0.98), 0.92, 108.0, 0.50, 0.40),
    "Mat_Inconel_GoldHeatShield": ((1.00, 0.72, 0.10), 0.88, 108.0, 0.52, 0.42),
    "Mat_Exhaust_Titanium": ((0.42, 0.48, 0.72), 0.90, 108.0, 0.52, 0.48),
    "Mat_Radiator_Mesh": ((0.14, 0.16, 0.28), 0.60, 112.0, 0.50, 0.55),
    "Mat_Seatbelt_Webbing": ((0.95, 0.08, 0.24), 0.75, 108.0, 0.50, 0.45),
    "Mat_PZero_White": ((0.94, 0.95, 0.98), 0.75, 108.0, 0.35, 0.30),
}
for _mn, (_rgb, _rm, _hs, _hts, _hcs) in _CAR_SPECS.items():
    apply_comic_to_mat(bpy.data.materials.get(_mn), _rgb, rim=_rm, ht_scale=_hs, ht_str=_hts, hc_str=_hcs)

# 贴花与轮胎侧壁贴图转为漫画渲染
for _mn in ("Mat_DEC_Engine_RedBull", "Mat_DEC_Halo_Oracle", "Mat_DEC_Nose_Livery",
            "Mat_DEC_Sidepod_Oracle", "Mat_PZero_Pirelli_Sidewall"):
    apply_comic_to_mat(bpy.data.materials.get(_mn), rim=0.65, ht_scale=102.0, ht_str=0.45, hc_str=0.40)

# 护栏发光灯带随三幕变色：Act1 电青 -> Act2 格温霓虹洋红 -> Act3 2099 激光绯红
_m_strip = bpy.data.materials.get("V5_LightStrip")
if _m_strip and _m_strip.node_tree:
    _snt2 = _m_strip.node_tree
    _snt2.nodes.clear()
    _so2 = _snt2.nodes.new('ShaderNodeOutputMaterial')
    _se2 = _snt2.nodes.new('ShaderNodeEmission')
    _se2.inputs['Strength'].default_value = 8.5
    _, _sw2b, _sw3b = add_act_weights(_snt2)
    _scol = tri_color_mix(_snt2, (0.0, 0.94, 1.0), (1.0, 0.18, 0.72), (1.0, 0.03, 0.14), _sw2b, _sw3b)
    _snt2.links.new(_scol, _se2.inputs['Color'])
    _snt2.links.new(_se2.outputs['Emission'], _so2.inputs['Surface'])

_m_cyan = bpy.data.materials.get("Mat_Neon_Cyan")
if _m_cyan and _m_cyan.node_tree:
    _cnt2 = _m_cyan.node_tree
    _cnt2.nodes.clear()
    _co2 = _cnt2.nodes.new('ShaderNodeOutputMaterial')
    _ce2 = _cnt2.nodes.new('ShaderNodeEmission')
    _ce2.inputs['Strength'].default_value = 7.0
    _, _cw2b, _cw3b = add_act_weights(_cnt2)
    _ccol = tri_color_mix(_cnt2, (0.0, 0.96, 1.0), (0.12, 1.0, 0.85), (1.0, 0.04, 0.18), _cw2b, _cw3b)
    _cnt2.links.new(_ccol, _ce2.inputs['Color'])
    _cnt2.links.new(_ce2.outputs['Emission'], _co2.inputs['Surface'])


# ---------------------------------------------------------------
# 4. 3D 可变线宽手绘墨线轮廓 (Solidify Inverted-Hull + 距离自适应防远景糊团)
# ---------------------------------------------------------------
def build_ink_outline_mat(name, max_dist=95.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    m.use_backface_culling = True
    try:
        m.use_backface_culling_shadow = True
        m.surface_render_method = 'DITHERED'
    except Exception:
        pass
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (0.0008, 0.0005, 0.0038, 1.0)
    em.inputs['Strength'].default_value = 1.0

    # 3D 干笔刷粗细断续微噪波 + 远摄距离平滑收敛（防止 S13/S20 长焦薄翼糊成黑团）
    tc = nt.nodes.new('ShaderNodeTexCoord')
    ns = nt.nodes.new('ShaderNodeTexNoise')
    ns.inputs['Scale'].default_value = 18.0
    ns.inputs['Detail'].default_value = 4.0
    nt.links.new(tc.outputs['Object'], ns.inputs['Vector'])
    brush = nt.nodes.new('ShaderNodeMapRange')
    brush.inputs['From Min'].default_value = 0.18
    brush.inputs['From Max'].default_value = 0.34
    brush.inputs['To Min'].default_value = 0.65
    brush.inputs['To Max'].default_value = 1.0
    nt.links.new(ns.outputs['Fac'], brush.inputs['Value'])

    camd = nt.nodes.new('ShaderNodeCameraData')
    dfade = nt.nodes.new('ShaderNodeMapRange')
    dfade.inputs['From Min'].default_value = max_dist * 0.45
    dfade.inputs['From Max'].default_value = max_dist
    dfade.inputs['To Min'].default_value = 1.0
    dfade.inputs['To Max'].default_value = 0.15
    nt.links.new(camd.outputs['View Z Depth'], dfade.inputs['Value'])

    fac = nt.nodes.new('ShaderNodeMath')
    fac.operation = 'MULTIPLY'
    fac.use_clamp = True
    nt.links.new(brush.outputs['Result'], fac.inputs[0])
    nt.links.new(dfade.outputs['Result'], fac.inputs[1])

    mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(fac.outputs[0], mx.inputs['Fac'])
    nt.links.new(tr.outputs['BSDF'], mx.inputs[1])
    nt.links.new(em.outputs['Emission'], mx.inputs[2])
    nt.links.new(mx.outputs['Shader'], out.inputs['Surface'])
    return m


MAT_INK_HERO = build_ink_outline_mat("MAT_SV_InkOutline", max_dist=130.0)
MAT_INK_THIN = build_ink_outline_mat("MAT_SV_InkOutline_Thin", max_dist=42.0)

# 仅对主车身、前后主翼、轮胎、轮毂、Halo 施加反向壳墨线（跳过细小螺栓/LED/贴花，use_rim=False 杜绝镜像中缝黑线）
_OUTLINE_PRIMARY = (
    "GEO_F1_Monocoque_Chassis", "GEO_F1_Nosecone", "GEO_F1_EngineCowl_Body",
    "GEO_F1_Underbody_Floor", "GEO_F1_Airbox_Scoop", "GEO_F1_Dorsal_SharkFin",
    "GEO_F1_Sidepod_IntakeLip_L", "GEO_F1_Sidepod_IntakeLip_R",
    "GEO_F1_Tire_FL", "GEO_F1_Tire_FR", "GEO_F1_Tire_RL", "GEO_F1_Tire_RR",
    "GEO_F1_Rim_FL", "GEO_F1_Rim_FR", "GEO_F1_Rim_RL", "GEO_F1_Rim_RR",
)
_OUTLINE_THIN = (
    "GEO_F1_FrontWing_Mainplane", "GEO_F1_FrontWing_Endplate_L", "GEO_F1_FrontWing_Endplate_R",
    "GEO_F1_RearWing_Mainplane", "GEO_F1_RearWing_DRSFlap",
    "GEO_F1_RearWing_Endplate_L", "GEO_F1_RearWing_Endplate_R", "GEO_F1_RearWing_Pylon",
    "GEO_F1_Halo_CenterPylon", "GEO_F1_Halo_Hoop", "GEO_F1_Cockpit_SteeringWheel",
    "GEO_F1_AeroMirror_L", "GEO_F1_AeroMirror_R", "GEO_F1_Diffuser_Ramp",
)

_outlined_cnt = 0
for _onm, _thick, _imat in (
    *[(n, 0.0085, MAT_INK_HERO) for n in _OUTLINE_PRIMARY],
    *[(n, 0.0042, MAT_INK_THIN) for n in _OUTLINE_THIN],
):
    _ob = bpy.data.objects.get(_onm)
    if not _ob or not hasattr(_ob.data, "materials"):
        continue
    # 非均匀缩放补偿（如 GEO_F1_FrontWing_Endplate_L scale.x=0.018）
    _min_sc = min(abs(_ob.scale.x), abs(_ob.scale.y), abs(_ob.scale.z))
    if _min_sc < 0.15:
        continue
    if _imat.name not in [m.name for m in _ob.data.materials if m]:
        _ob.data.materials.append(_imat)
    _slot_idx = [m.name if m else "" for m in _ob.data.materials].index(_imat.name)
    _mod = _ob.modifiers.get("SV_InkHull") or _ob.modifiers.new("SV_InkHull", 'SOLIDIFY')
    _mod.thickness = -_thick       # offset=1.0 + 负 thickness -> 沿法线向外膨胀 _thick 米
    _mod.offset = 1.0
    _mod.use_flip_normals = True
    _mod.use_rim = False           # 严禁在 Mirror 中轴线开口边缘生成黑墙
    _mod.material_offset = _slot_idx
    _outlined_cnt += 1
print("3D Ink Outlines applied to hero car parts:", _outlined_cnt)


# ---------------------------------------------------------------
# 5. 3D 漫画速度特效集合 V6_09_ComicFX（零文字、零遮挡相机视线）
#    - 尾翼/前翼涡流飘带 (V6_FX_AeroRibbon_RL/RR/FL/FR -> Bone_Body)
#    - 车轮高速旋转残影弧 (V6_FX_WheelSmear_FL/FR/RL/RR -> Bone_Wheel_*)
#    - 排气管换挡爆燃星锥 (V6_FX_ExhaustCone -> Bone_Body)
#    - 底板路肩擦地漫画火花斩 (V6_FX_KerbSparks_L/R -> Bone_Body)
# ---------------------------------------------------------------
fx_coll = bpy.data.collections.get("V6_09_ComicFX") or bpy.data.collections.new("V6_09_ComicFX")
if fx_coll.name not in scene.collection.children:
    scene.collection.children.link(fx_coll)

rig = bpy.data.objects["RIG_F1_Race"]
deps = bpy.context.evaluated_depsgraph_get()
rig_ev = rig.evaluated_get(deps)
m_car_f1 = rig_ev.matrix_world @ rig_ev.pose.bones["Bone_Heading"].matrix


def parent_to_bone_at_car_coords(ob, bone_name):
    """把以车身局部坐标 (Bone_Heading 系) 建模的对象挂接到指定骨骼，精确保持第 1 帧姿态。"""
    pb_mat = rig_ev.matrix_world @ rig_ev.pose.bones[bone_name].matrix
    ob.matrix_world = m_car_f1
    ob.parent = rig
    ob.parent_type = 'BONE'
    ob.parent_bone = bone_name
    ob.matrix_parent_inverse = pb_mat.inverted()
    ob.matrix_basis = pb_mat.inverted() @ m_car_f1
    # 原点保持在车坐标系，方便 anim 直接缩放 ob.scale 开关/跳帧抖动！
    try:
        ob.visible_shadow = False
    except Exception:
        pass


def make_fx_mat(name, c_core, c_edge, strength=3.8, wave_freq=6.0):
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
    em.name = "SV_FX_Emission"
    em.inputs['Strength'].default_value = strength

    uv = nt.nodes.new('ShaderNodeUVMap'); uv.uv_map = "UVMap"
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(uv.outputs['UV'], sep.inputs['Vector'])
    # 沿长度 U (0->1) 渐隐，沿宽度 V (0->1) 中心亮白/边缘霓虹 + 手绘锯齿切口
    v_phase = nt.nodes.new('ShaderNodeValue')
    v_phase.name = "SV_FlutterPhase"
    v_phase.outputs[0].default_value = 0.0

    u_off = nt.nodes.new('ShaderNodeMath'); u_off.operation = 'ADD'
    nt.links.new(sep.outputs['X'], u_off.inputs[0]); nt.links.new(v_phase.outputs[0], u_off.inputs[1])
    comb = nt.nodes.new('ShaderNodeCombineXYZ')
    nt.links.new(u_off.outputs[0], comb.inputs['X']); nt.links.new(sep.outputs['Y'], comb.inputs['Y'])
    ns = nt.nodes.new('ShaderNodeTexNoise'); ns.inputs['Scale'].default_value = wave_freq; ns.inputs['Detail'].default_value = 3.0
    nt.links.new(comb.outputs['Vector'], ns.inputs['Vector'])

    fade_u = nt.nodes.new('ShaderNodeMapRange')
    fade_u.inputs['From Min'].default_value = 0.0
    fade_u.inputs['From Max'].default_value = 1.0
    fade_u.inputs['To Min'].default_value = 0.92
    fade_u.inputs['To Max'].default_value = 0.0
    nt.links.new(sep.outputs['X'], fade_u.inputs['Value'])

    step_a = nt.nodes.new('ShaderNodeMath'); step_a.operation = 'GREATER_THAN'; step_a.inputs[1].default_value = 0.34
    mul_a = nt.nodes.new('ShaderNodeMath'); mul_a.operation = 'MULTIPLY'
    nt.links.new(fade_u.outputs['Result'], mul_a.inputs[0]); nt.links.new(ns.outputs['Fac'], mul_a.inputs[1])
    nt.links.new(mul_a.outputs[0], step_a.inputs[0])

    # 中心亮白芯 + 边缘电青/品红双色
    dv = nt.nodes.new('ShaderNodeMath'); dv.operation = 'SUBTRACT'; dv.inputs[1].default_value = 0.5
    nt.links.new(sep.outputs['Y'], dv.inputs[0])
    abv = nt.nodes.new('ShaderNodeMath'); abv.operation = 'ABSOLUTE'; nt.links.new(dv.outputs[0], abv.inputs[0])
    col_r = nt.nodes.new('ShaderNodeValToRGB'); col_r.color_ramp.interpolation = 'CONSTANT'
    col_r.color_ramp.elements[0].position = 0.0; col_r.color_ramp.elements[0].color = (*c_core, 1.0)
    col_r.color_ramp.elements[1].position = 0.24; col_r.color_ramp.elements[1].color = (*c_edge, 1.0)
    nt.links.new(abv.outputs[0], col_r.inputs[0])
    nt.links.new(col_r.outputs['Color'], em.inputs['Color'])

    mx = nt.nodes.new('ShaderNodeMixShader')
    mx.name = "SV_FX_AlphaMix"
    nt.links.new(step_a.outputs[0], mx.inputs['Fac'])
    nt.links.new(tr.outputs['BSDF'], mx.inputs[1])
    nt.links.new(em.outputs['Emission'], mx.inputs[2])
    nt.links.new(mx.outputs['Shader'], out.inputs['Surface'])
    return m


MAT_RIBBON_CYAN = make_fx_mat("MAT_SV_AeroRibbon_Cyan", (1.0, 1.0, 1.0), (0.0, 0.92, 1.0), strength=3.6, wave_freq=5.5)
MAT_RIBBON_MAG = make_fx_mat("MAT_SV_AeroRibbon_Mag", (1.0, 0.96, 1.0), (1.0, 0.14, 0.58), strength=3.6, wave_freq=6.5)
MAT_WHEEL_SMEAR = make_fx_mat("MAT_SV_WheelSmear", (1.0, 0.96, 0.85), (0.0, 0.88, 1.0), strength=2.8, wave_freq=8.0)
MAT_EXH_BURST = make_fx_mat("MAT_SV_ExhaustBurst", (1.0, 0.98, 0.82), (1.0, 0.18, 0.42), strength=5.2, wave_freq=9.0)
MAT_SPARK_SLASH = make_fx_mat("MAT_SV_SparkSlashes", (1.0, 1.0, 0.92), (1.0, 0.76, 0.06), strength=6.0, wave_freq=11.0)


def create_fx_mesh(name, verts, faces, uvs, mat):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    uvl = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            uvl.data[li].uv = uvs[me.loops[li].vertex_index]
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    fx_coll.objects.link(ob)
    return ob


# 5a) 尾翼端板双螺旋漫画涡流飘带 + 前翼外侧导流涡流带
def build_aero_ribbon(name, start_xyz, length, width0, side_sgn, mat, arch_z=0.14):
    segs = 18
    vs, fs, uvs = [], [], []
    sx, sy, sz = start_xyz
    for i in range(segs + 1):
        u = i / float(segs)
        cx = sx + side_sgn * (0.12 * (u ** 1.3) + 0.035 * sin(u * 9.0))
        cy = sy - length * u
        cz = sz + arch_z * (u ** 1.1) + 0.025 * cos(u * 9.0)
        w = width0 * (1.0 - 0.88 * u)
        twist = u * 2.4 * side_sgn
        dx, dz = w * cos(twist), w * sin(twist)
        vs.append((cx - dx, cy, cz - dz))
        vs.append((cx + dx, cy, cz + dz))
        uvs.append((u, 0.0))
        uvs.append((u, 1.0))
    for i in range(segs):
        a = i * 2
        fs.append((a, a + 1, a + 3, a + 2))
    ob = create_fx_mesh(name, vs, fs, uvs, mat)
    parent_to_bone_at_car_coords(ob, "Bone_Body")
    ob["fx_flutter"] = 1.0
    return ob


build_aero_ribbon("V6_FX_AeroRibbon_RL", (-0.51, -2.47, 1.03), 3.6, 0.055, -1.0, MAT_RIBBON_CYAN, arch_z=0.14)
build_aero_ribbon("V6_FX_AeroRibbon_RR", (0.51, -2.47, 1.03), 3.6, 0.055, 1.0, MAT_RIBBON_MAG, arch_z=0.14)
build_aero_ribbon("V6_FX_AeroRibbon_FL", (-1.04, 2.62, 0.28), 1.65, 0.038, -1.0, MAT_RIBBON_MAG, arch_z=0.08)
build_aero_ribbon("V6_FX_AeroRibbon_FR", (1.04, 2.62, 0.28), 1.65, 0.038, 1.0, MAT_RIBBON_CYAN, arch_z=0.08)

# 5b) 四轮外侧漫画旋转速度残影弧 (Wheel-Spin Comic Smear Arcs -> Bone_Wheel_*)
_WHEEL_SPECS = [
    ("V6_FX_WheelSmear_FL", "Bone_Wheel_FL", -1.084, 1.45, 0.351),
    ("V6_FX_WheelSmear_FR", "Bone_Wheel_FR", 1.084, 1.45, 0.351),
    ("V6_FX_WheelSmear_RL", "Bone_Wheel_RL", -1.080, -1.55, 0.336),
    ("V6_FX_WheelSmear_RR", "Bone_Wheel_RR", 1.080, -1.55, 0.336),
]
for _wnm, _wb, _wx, _wy, _wz in _WHEEL_SPECS:
    vs, fs, uvs = [], [], []
    # 两段不对称残影弧，旋转时产生强烈的 12fps 手绘动感残像
    for a0_deg, span_deg, r_in, r_out in ((18.0, 118.0, 0.215, 0.285), (195.0, 108.0, 0.245, 0.318)):
        base = len(vs)
        steps = 12
        for k in range(steps + 1):
            u = k / float(steps)
            ang = radians(a0_deg + span_deg * u)
            vs.append((_wx, _wy + cos(ang) * r_in, _wz + sin(ang) * r_in))
            vs.append((_wx, _wy + cos(ang) * r_out, _wz + sin(ang) * r_out))
            uvs.append((u, 0.0))
            uvs.append((u, 1.0))
        for k in range(steps):
            a = base + k * 2
            fs.append((a, a + 1, a + 3, a + 2))
    wob = create_fx_mesh(_wnm, vs, fs, uvs, MAT_WHEEL_SMEAR)
    parent_to_bone_at_car_coords(wob, _wb)

# 5c) 排气管星芒漫画爆燃锥 (V6_FX_ExhaustCone) + 底板路肩火花斩 (V6_FX_KerbSparks_L/R)
def build_exhaust_and_sparks():
    # 十字交叉锯齿爆燃锥
    vs, fs, uvs = [], [], []
    for plane in (0, 1):
        b = len(vs)
        for k in range(7):
            u = k / 6.0
            y = -2.38 - 0.88 * u
            w = 0.075 * (1.0 - 0.85 * u)
            if plane == 0:
                vs += [(-w, y, 0.436), (w, y, 0.436)]
            else:
                vs += [(0.0, y, 0.436 - w), (0.0, y, 0.436 + w)]
            uvs += [(u, 0.0), (u, 1.0)]
        for k in range(6):
            a = b + k * 2
            fs.append((a, a + 1, a + 3, a + 2))
    ex_ob = create_fx_mesh("V6_FX_ExhaustCone", vs, fs, uvs, MAT_EXH_BURST)
    parent_to_bone_at_car_coords(ex_ob, "Bone_Body")

    # 左右底板擦地漫画锐角火花斩（默认微缩待命，anim 在高速触底/压路肩时 12fps 爆发缩放！）
    for sgn, snm in ((-1.0, "V6_FX_KerbSparks_L"), (1.0, "V6_FX_KerbSparks_R")):
        sv, sf, suv = [], [], []
        for si, (dx, dz_end, ln) in enumerate(((-0.04, 0.22, 1.15), (0.03, 0.14, 0.92), (0.09, 0.28, 1.30))):
            b = len(sv)
            x0 = sgn * (0.66 + dx)
            y0, z0 = -1.72, 0.055
            x1 = x0 + sgn * 0.18
            y1, z1 = y0 - ln, z0 + dz_end
            sv += [(x0 - 0.018, y0, z0), (x0 + 0.018, y0, z0), (x1 + 0.004, y1, z1), (x1 - 0.004, y1, z1)]
            suv += [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0)]
            sf.append((b, b + 1, b + 2, b + 3))
        sp_ob = create_fx_mesh(snm, sv, sf, suv, MAT_SPARK_SLASH)
        parent_to_bone_at_car_coords(sp_ob, "Bone_Body")


build_exhaust_and_sparks()

# ---------------------------------------------------------------
# 6. 自检：确认根 Scene Collection 为 0 对象，且 V6_09_ComicFX 零遮挡相机到 V5_CamFocus 视线
# ---------------------------------------------------------------
deps = bpy.context.evaluated_depsgraph_get()
fx_names = {o.name for o in fx_coll.objects}
mks = sorted([(m.frame, m.camera) for m in scene.timeline_markers if m.camera], key=lambda x: x[0])
cam_focus = bpy.data.objects.get("V5_CamFocus")
fx_hits = []
for f_chk in range(1, 2162, 8):
    scene.frame_set(f_chk)
    deps.update()
    cam = scene.camera
    for mf, mc in mks:
        if f_chk >= mf:
            cam = mc
    cpos = cam.evaluated_get(deps).matrix_world.translation
    tpos = cam_focus.evaluated_get(deps).matrix_world.translation if cam_focus else Vector((0, 0, 0.5))
    dv = tpos - cpos
    if dv.length > 1.2:
        ok, _, _, _, hob, _ = scene.ray_cast(deps, cpos + dv.normalized() * 0.5, dv.normalized(), distance=dv.length - 0.8)
        if ok and hob and hob.name in fx_names:
            fx_hits.append((f_chk, cam.name, hob.name))

scene.frame_set(1)
scene["sv_dimension"] = 0.0
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
# 清理可能生成的 .blend1
if os.path.exists(OUT_BLEND + "1"):
    try:
        os.remove(OUT_BLEND + "1")
    except Exception:
        pass

print("=== V6 SPIDER-VERSE LOOKDEV BUILD SUMMARY ===")
print(f"Saved: {OUT_BLEND} in {time.time() - t_build_start:.2f} s")
print("Total objects:", len(bpy.data.objects), "| Root objs:", [o.name for o in scene.collection.objects])
print("V6_09_ComicFX objects:", sorted(fx_names))
print("FX camera-to-focus raycast hits:", len(fx_hits), fx_hits[:5])

# ---------------------------------------------------------------
# 7. 可选 4 帧三幕预览渲染 (--preview) -> renders_v6/preview/
# ---------------------------------------------------------------
if "--preview" in ARGV:
    os.makedirs(PREV_DIR, exist_ok=True)
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.image_settings.file_format = 'JPEG'
    scene.render.image_settings.quality = 95
    # 临时关闭旧版 V5 泛光合成器以便纯粹检验三幕 3D 蜘蛛侠着色与墨线速度（anim 将在 v6_sv_comp.py 挂载完整多通道合成器）
    scene.use_nodes = False

    preview_specs = [
        ("sv_prev_01_act1_chase_f0068", 68, 0.0),
        ("sv_prev_02_act1_onboard_f0145", 145, 0.0),
        ("sv_prev_03_act2_gwen_f1320", 1320, 1.0),
        ("sv_prev_04_act3_2099_f1715", 1715, 2.0),
    ]
    for p_name, p_frame, p_dim in preview_specs:
        scene["sv_dimension"] = float(p_dim)
        scene.keyframe_insert('["sv_dimension"]', frame=p_frame)
    for p_name, p_frame, p_dim in preview_specs:
        scene.frame_set(p_frame)
        bpy.context.view_layer.update()
        # 切换当前拍点对应激活相机
        act_cam = scene.camera
        for mf, mc in mks:
            if p_frame >= mf:
                act_cam = mc
        scene.camera = act_cam
        scene.render.filepath = os.path.join(PREV_DIR, p_name + ".jpg")
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"RENDERED {p_name} (frame={p_frame}, cam={act_cam.name}, dim={p_dim}): {time.time() - t0:.2f} s")
    scene["sv_dimension"] = 0.0
