# -*- coding: utf-8 -*-
"""
Fine-tuning script for build_scifi_f1.py
Fixes UV orientations, decal visibility on rear wing, nose stripe overlap, and enhances decal luminescence
"""
import re

with open(r"D:\项目session\blender-supercar\build_scifi_f1.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. 贴纸材质增加真实微光对比度
old_decal_mat_core = """        links.new(tex_node.outputs['Color'], sh_bsdf.inputs['Base Color'])
        links.new(tex_node.outputs['Alpha'], sh_bsdf.inputs['Alpha'])
        links.new(sh_bsdf.outputs['BSDF'], out_node.inputs['Surface'])"""

new_decal_mat_core = """        links.new(tex_node.outputs['Color'], sh_bsdf.inputs['Base Color'])
        links.new(tex_node.outputs['Alpha'], sh_bsdf.inputs['Alpha'])
        
        # 赋予贴纸 0.25 微弱环境漫射光感，确保赛车贴纸在暗光赛道下具备高可读性
        if 'Emission Color' in sh_bsdf.inputs:
            links.new(tex_node.outputs['Color'], sh_bsdf.inputs['Emission Color'])
            if 'Emission Strength' in sh_bsdf.inputs:
                sh_bsdf.inputs['Emission Strength'].default_value = 0.25
        elif 'Emission' in sh_bsdf.inputs:
            links.new(tex_node.outputs['Color'], sh_bsdf.inputs['Emission'])
            
        links.new(sh_bsdf.outputs['BSDF'], out_node.inputs['Surface'])"""

assert old_decal_mat_core in code, "Failed to find old decal mat core"
code = code.replace(old_decal_mat_core, new_decal_mat_core)

# 2. 机鼻实体中轴线后移缩短，不再压在贴纸上方
old_stripe = """    nose_stripe.scale = (0.016, 1.60, 0.012)
    nose_stripe.location = (0.0, 2.30, 0.38)
    nose_stripe.rotation_euler = (math.radians(-11.5), 0, 0)"""

new_stripe = """    nose_stripe.scale = (0.012, 0.35, 0.010)
    nose_stripe.location = (0.0, 1.45, 0.55)
    nose_stripe.rotation_euler = (math.radians(-14.0), 0, 0)"""

assert old_stripe in code, "Failed to find old stripe"
code = code.replace(old_stripe, new_stripe)

# 3. 替换全套贴纸的精确顶点与 UV 映射
pattern_decals = r"(    # A\. 机鼻流线涂装与维斯塔潘车号 1 贴纸.*?mat=mat_dec_endplate,\s+target_col=col_decals,\s+uv_mode='normal'\s+\))"

new_decals_block = """    # A. 机鼻流线涂装与维斯塔潘车号 1 贴纸 (贴合鼻锥 13.8° 俯冲斜坡，前置加宽)
    create_quad_decal(
        "DEC_Nose_Livery",
        p_bl=Vector((-0.145, 1.70, 0.495)),
        p_br=Vector((0.145, 1.70, 0.495)),
        p_tr=Vector((0.098, 2.78, 0.232)),
        p_tl=Vector((-0.098, 2.78, 0.232)),
        mat=mat_dec_nose_livery,
        target_col=col_decals,
        uv_mode='normal'
    )

    # B. 侧箱外壁巨幅 ORACLE + 赛车速度拉花 + Mobil 1 (左右两侧完全正向可读，彻底解决镜像反字)
    # 左侧侧箱
    create_quad_decal(
        "DEC_Sidepod_Oracle_L",
        p_bl=Vector((-0.638, -1.35, 0.22)),
        p_br=Vector((-0.638, -0.25, 0.22)),
        p_tr=Vector((-0.638, -0.25, 0.52)),
        p_tl=Vector((-0.638, -1.35, 0.52)),
        mat=mat_dec_side_oracle,
        target_col=col_decals,
        uv_mode='flip_x'
    )
    # 右侧侧箱 (修正为 flip_x 使得文字正向自然排布)
    create_quad_decal(
        "DEC_Sidepod_Oracle_R",
        p_bl=Vector((0.638, -0.25, 0.22)),
        p_br=Vector((0.638, -1.35, 0.22)),
        p_tr=Vector((0.638, -1.35, 0.52)),
        p_tl=Vector((0.638, -0.25, 0.52)),
        mat=mat_dec_side_oracle,
        target_col=col_decals,
        uv_mode='flip_x'
    )

    # C. 发动机罩两侧双牛撞日 + Red Bull RACING + HONDA (左右两侧公牛均朝前冲刺，文字全部正向)
    # 左侧发动机罩
    create_quad_decal(
        "DEC_Engine_RedBull_L",
        p_bl=Vector((-0.300, -1.55, 0.58)),
        p_br=Vector((-0.300, -0.45, 0.68)),
        p_tr=Vector((-0.260, -0.45, 1.02)),
        p_tl=Vector((-0.260, -1.55, 0.92)),
        mat=mat_dec_eng_redbull,
        target_col=col_decals,
        uv_mode='flip_x'
    )
    # 右侧发动机罩 (公牛朝前冲刺，文字正向)
    create_quad_decal(
        "DEC_Engine_RedBull_R",
        p_bl=Vector((0.300, -0.45, 0.68)),
        p_br=Vector((0.300, -1.55, 0.58)),
        p_tr=Vector((0.260, -1.55, 0.92)),
        p_tl=Vector((0.260, -0.45, 1.02)),
        mat=mat_dec_eng_redbull,
        target_col=col_decals,
        uv_mode='flip_x'
    )

    # D. 尾翼主翼面迎风正面巨幅 ORACLE (贴合主片前缘弧面，消除网格遮挡)
    create_quad_decal(
        "DEC_RearWing_Front_Oracle",
        p_bl=Vector((-0.67, -2.14, 0.88)),
        p_br=Vector((0.67, -2.14, 0.88)),
        p_tr=Vector((0.67, -2.22, 1.04)),
        p_tl=Vector((-0.67, -2.22, 1.04)),
        mat=mat_dec_rw_front,
        target_col=col_decals,
        uv_mode='normal'
    )

    # E. 尾翼 DRS 活跃副翼金黄 BYBIT 标
    create_quad_decal(
        "DEC_RearWing_Top_Bybit",
        p_bl=Vector((-0.66, -2.28, 1.05)),
        p_br=Vector((0.66, -2.28, 1.05)),
        p_tr=Vector((0.66, -2.36, 1.16)),
        p_tl=Vector((-0.66, -2.36, 1.16)),
        mat=mat_dec_rw_bybit,
        target_col=col_decals,
        uv_mode='normal'
    )

    # F. 尾翼后车直视背面 Red Bull 撞日标 (贴合后缘表面)
    create_quad_decal(
        "DEC_RearWing_Back_RedBull",
        p_bl=Vector((0.67, -2.46, 0.88)),
        p_br=Vector((-0.67, -2.46, 0.88)),
        p_tr=Vector((-0.67, -2.46, 1.04)),
        p_tl=Vector((0.67, -2.46, 1.04)),
        mat=mat_dec_rw_back,
        target_col=col_decals,
        uv_mode='normal'
    )

    # G. Halo 前弧顶部 ORACLE 品牌标
    create_quad_decal(
        "DEC_Halo_Top_Oracle",
        p_bl=Vector((-0.16, 0.20, 0.898)),
        p_br=Vector((0.16, 0.20, 0.898)),
        p_tr=Vector((0.16, 0.38, 0.878)),
        p_tl=Vector((-0.16, 0.38, 0.878)),
        mat=mat_dec_halo,
        target_col=col_decals,
        uv_mode='normal'
    )

    # H. 前翼外洗端板 Mobil 1 + Pirelli 贴纸 (左右两侧完全正向)
    create_quad_decal(
        "DEC_Endplate_Front_L",
        p_bl=Vector((-1.042, 3.15, 0.10)),
        p_br=Vector((-1.042, 2.75, 0.10)),
        p_tr=Vector((-1.042, 2.75, 0.36)),
        p_tl=Vector((-1.042, 3.15, 0.36)),
        mat=mat_dec_endplate,
        target_col=col_decals,
        uv_mode='normal'
    )
    create_quad_decal(
        "DEC_Endplate_Front_R",
        p_bl=Vector((1.042, 2.75, 0.10)),
        p_br=Vector((1.042, 3.15, 0.10)),
        p_tr=Vector((1.042, 3.15, 0.36)),
        p_tl=Vector((1.042, 2.75, 0.36)),
        mat=mat_dec_endplate,
        target_col=col_decals,
        uv_mode='normal'
    )

    # I. 尾翼外侧端板 Mobil 1 + Pirelli 贴纸 (左右两侧完全正向)
    create_quad_decal(
        "DEC_Endplate_Rear_L",
        p_bl=Vector((-0.728, -2.10, 0.74)),
        p_br=Vector((-0.728, -2.52, 0.74)),
        p_tr=Vector((-0.728, -2.52, 1.14)),
        p_tl=Vector((-0.728, -2.10, 1.14)),
        mat=mat_dec_endplate,
        target_col=col_decals,
        uv_mode='normal'
    )
    create_quad_decal(
        "DEC_Endplate_Rear_R",
        p_bl=Vector((0.728, -2.52, 0.74)),
        p_br=Vector((0.728, -2.10, 0.74)),
        p_tr=Vector((0.728, -2.10, 1.14)),
        p_tl=Vector((0.728, -2.52, 1.14)),
        mat=mat_dec_endplate,
        target_col=col_decals,
        uv_mode='normal'
    )"""

m = re.search(pattern_decals, code, re.DOTALL)
assert m, "Failed to match decals block"
code = code[:m.start()] + new_decals_block + code[m.end():]

with open(r"D:\项目session\blender-supercar\build_scifi_f1.py", "w", encoding="utf-8") as f:
    f.write(code)

print("build_scifi_f1.py successfully refined with flawless decal alignment and luminescence!")
