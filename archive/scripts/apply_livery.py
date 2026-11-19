# -*- coding: utf-8 -*-
"""
Script to inject Oracle Red Bull Racing Livery, Materials and Sponsor Decals into build_scifi_f1.py
"""
import re

with open(r"D:\项目session\blender-supercar\build_scifi_f1_pre_livery.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. 替换集合结构 (增加 08_Sponsor_Decals，原 08_Studio 改为 09_Studio)
old_col = """    col_lights = get_or_create_col("07_Telemetry_LED_Lights", col_root)
    col_studio = get_or_create_col("08_Studio_Stage_Rig")"""

new_col = """    col_lights = get_or_create_col("07_Telemetry_LED_Lights", col_root)
    col_decals = get_or_create_col("08_Sponsor_Decals", col_root)
    col_studio = get_or_create_col("09_Studio_Stage_Rig")"""

assert old_col in code, "Failed to find old collection block"
code = code.replace(old_col, new_col)

# 2. 注入红牛专属涂装材质与 Decal 材质加载器
old_mat = """    mat_titanium = create_pbr_mat("Mat_Liquid_Titanium", color=(0.82, 0.84, 0.88, 1.0), metallic=0.98, roughness=0.12, clearcoat=1.0)"""

new_mat = """    # Oracle Red Bull Racing 官方色彩规范
    mat_navy = create_pbr_mat("Mat_RedBull_MatteNavy", color=(0.015, 0.030, 0.075, 1.0), metallic=0.18, roughness=0.40, clearcoat=0.0)
    mat_rb_red = create_pbr_mat("Mat_RedBull_Crimson", color=(0.88, 0.02, 0.0, 1.0), metallic=0.15, roughness=0.35)
    mat_rb_yellow = create_pbr_mat("Mat_RedBull_SolarYellow", color=(1.0, 0.80, 0.0, 1.0), metallic=0.15, roughness=0.35)
    mat_pzero_red = create_pbr_mat("Mat_PZero_Red", color=(0.88, 0.02, 0.0, 1.0), metallic=0.0, roughness=0.45)
    
    # 贴纸材质生成函数 (Alpha通道透明映射)
    tex_base_dir = r"D:\\项目session\\blender-supercar\\textures"
    def create_decal_mat(mat_name, filename):
        mat = bpy.data.materials.get(mat_name)
        if not mat:
            mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()
        
        out_node = nodes.new(type='ShaderNodeOutputMaterial')
        sh_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
        tex_node = nodes.new(type='ShaderNodeTexImage')
        
        img_path = os.path.join(tex_base_dir, filename)
        if os.path.exists(img_path):
            tex_node.image = bpy.data.images.load(img_path, check_existing=True)
            
        sh_bsdf.inputs['Roughness'].default_value = 0.38
        if 'Specular IOR Level' in sh_bsdf.inputs:
            sh_bsdf.inputs['Specular IOR Level'].default_value = 0.5
        elif 'Specular' in sh_bsdf.inputs:
            sh_bsdf.inputs['Specular'].default_value = 0.5
            
        links.new(tex_node.outputs['Color'], sh_bsdf.inputs['Base Color'])
        links.new(tex_node.outputs['Alpha'], sh_bsdf.inputs['Alpha'])
        links.new(sh_bsdf.outputs['BSDF'], out_node.inputs['Surface'])
        
        if hasattr(mat, 'blend_method'):
            mat.blend_method = 'BLEND'
        if hasattr(mat, 'shadow_method'):
            mat.shadow_method = 'NONE'
        return mat

    mat_dec_side_oracle = create_decal_mat("Mat_DEC_Sidepod_Oracle", "decal_sidepod_oracle.png")
    mat_dec_eng_redbull = create_decal_mat("Mat_DEC_Engine_RedBull", "decal_engine_redbull_bull.png")
    mat_dec_nose_livery = create_decal_mat("Mat_DEC_Nose_Livery", "decal_nose_livery.png")
    mat_dec_rw_front = create_decal_mat("Mat_DEC_RearWing_Front", "decal_rearwing_front.png")
    mat_dec_rw_bybit = create_decal_mat("Mat_DEC_RearWing_Bybit", "decal_rearwing_bybit.png")
    mat_dec_rw_back = create_decal_mat("Mat_DEC_RearWing_Back", "decal_rearwing_back.png")
    mat_dec_halo = create_decal_mat("Mat_DEC_Halo_Oracle", "decal_halo_oracle.png")
    mat_dec_endplate = create_decal_mat("Mat_DEC_Endplate_Mobil1", "decal_endplate_mobil1.png")

    # 四边形贴纸独立网格生成器 (高精度四个三维角点与非破坏性UV)
    def create_quad_decal(name, p_bl, p_br, p_tr, p_tl, mat=None, target_col=col_decals, uv_mode='normal'):
        bm = bmesh.new()
        v1 = bm.verts.new(p_bl)
        v2 = bm.verts.new(p_br)
        v3 = bm.verts.new(p_tr)
        v4 = bm.verts.new(p_tl)
        f = bm.faces.new([v1, v2, v3, v4])
        uv_layer = bm.loops.layers.uv.new("UVMap")
        bm.verts.ensure_lookup_table()
        
        if uv_mode == 'normal':
            uvs = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        elif uv_mode == 'flip_x':
            uvs = [(1.0, 0.0), (0.0, 0.0), (0.0, 1.0), (1.0, 1.0)]
        elif uv_mode == 'flip_y':
            uvs = [(0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)]
        else:
            uvs = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
            
        for idx, loop in enumerate(f.loops):
            loop[uv_layer].uv = uvs[idx]
            
        me = bpy.data.meshes.new(f"ME_{name}")
        bm.to_mesh(me)
        bm.free()
        
        obj = bpy.data.objects.new(name, me)
        if target_col:
            link_to_col(obj, target_col)
        if mat:
            obj.data.materials.append(mat)
        return obj

    mat_titanium = create_pbr_mat("Mat_Liquid_Titanium", color=(0.82, 0.84, 0.88, 1.0), metallic=0.98, roughness=0.12, clearcoat=1.0)"""

assert old_mat in code, "Failed to find old material block"
code = code.replace(old_mat, new_mat)

# 3. 替换车身核心覆盖件材质为 mat_navy
code = code.replace("obj_nose.data.materials.append(mat_titanium)", "obj_nose.data.materials.append(mat_navy)")
code = code.replace("obj_chassis.data.materials.append(mat_titanium)", "obj_chassis.data.materials.append(mat_navy)")
code = code.replace("obj_engine.data.materials.append(mat_titanium)", "obj_engine.data.materials.append(mat_navy)")
code = code.replace("obj_ab.data.materials.append(mat_titanium)", "obj_ab.data.materials.append(mat_navy)")
code = code.replace("intake_box.data.materials.append(mat_carbon)", "intake_box.data.materials.append(mat_navy)")
code = code.replace("mirror.data.materials.append(mat_titanium)", "mirror.data.materials.append(mat_navy)")
code = code.replace("pzero_ring.data.materials.append(mat_white)", "pzero_ring.data.materials.append(mat_pzero_red)")
code = code.replace("nose_stripe.data.materials.append(mat_neon_cyan)", "nose_stripe.data.materials.append(mat_rb_yellow)")

# 4. 在摄影棚灯光之前插入全套 10 块赞助商独立贴纸对象
old_studio = """    # =========================================================================
    # 15."""

old_studio_end = """(Professional Automotive Studio Stage)
    # ========================================================================="""

new_decals_and_studio = """    # =========================================================================
    # 15. 红牛官方赞助商全套独立贴纸系统 (Oracle Red Bull Racing Decal Mesh System)
    # 100% 独立网格浮雕片，非破坏性挂载于 08_Sponsor_Decals 集合，完全可点击编辑
    # =========================================================================
    # A. 机鼻流线涂装与维斯塔潘车号 1 贴纸 (贴合鼻锥 13.8° 俯冲斜坡)
    create_quad_decal(
        "DEC_Nose_Livery",
        p_bl=Vector((-0.13, 1.70, 0.493)),
        p_br=Vector((0.13, 1.70, 0.493)),
        p_tr=Vector((0.088, 2.70, 0.248)),
        p_tl=Vector((-0.088, 2.70, 0.248)),
        mat=mat_dec_nose_livery,
        target_col=col_decals,
        uv_mode='normal'
    )

    # B. 侧箱外壁巨幅 ORACLE + 赛车速度拉花 + Mobil 1 (左右两侧完全正向可读)
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
    # 右侧侧箱
    create_quad_decal(
        "DEC_Sidepod_Oracle_R",
        p_bl=Vector((0.638, -0.25, 0.22)),
        p_br=Vector((0.638, -1.35, 0.22)),
        p_tr=Vector((0.638, -1.35, 0.52)),
        p_tl=Vector((0.638, -0.25, 0.52)),
        mat=mat_dec_side_oracle,
        target_col=col_decals,
        uv_mode='normal'
    )

    # C. 发动机罩两侧双牛撞日 + Red Bull RACING + HONDA (左右两侧公牛均朝前冲刺)
    # 左侧发动机罩
    create_quad_decal(
        "DEC_Engine_RedBull_L",
        p_bl=Vector((-0.292, -1.65, 0.55)),
        p_br=Vector((-0.292, -0.50, 0.65)),
        p_tr=Vector((-0.262, -0.50, 0.98)),
        p_tl=Vector((-0.262, -1.65, 0.88)),
        mat=mat_dec_eng_redbull,
        target_col=col_decals,
        uv_mode='flip_x'
    )
    # 右侧发动机罩
    create_quad_decal(
        "DEC_Engine_RedBull_R",
        p_bl=Vector((0.292, -0.50, 0.65)),
        p_br=Vector((0.292, -1.65, 0.55)),
        p_tr=Vector((0.262, -1.65, 0.88)),
        p_tl=Vector((0.262, -0.50, 0.98)),
        mat=mat_dec_eng_redbull,
        target_col=col_decals,
        uv_mode='normal'
    )

    # D. 尾翼主翼面迎风正面巨幅 ORACLE
    create_quad_decal(
        "DEC_RearWing_Front_Oracle",
        p_bl=Vector((-0.67, -2.26, 0.83)),
        p_br=Vector((0.67, -2.26, 0.83)),
        p_tr=Vector((0.67, -2.29, 1.02)),
        p_tl=Vector((-0.67, -2.29, 1.02)),
        mat=mat_dec_rw_front,
        target_col=col_decals,
        uv_mode='normal'
    )

    # E. 尾翼 DRS 活跃副翼金黄 BYBIT 标
    create_quad_decal(
        "DEC_RearWing_Top_Bybit",
        p_bl=Vector((-0.66, -2.34, 1.03)),
        p_br=Vector((0.66, -2.34, 1.03)),
        p_tr=Vector((0.66, -2.37, 1.15)),
        p_tl=Vector((-0.66, -2.37, 1.15)),
        mat=mat_dec_rw_bybit,
        target_col=col_decals,
        uv_mode='normal'
    )

    # F. 尾翼后车直视背面 Red Bull 撞日标
    create_quad_decal(
        "DEC_RearWing_Back_RedBull",
        p_bl=Vector((0.67, -2.39, 0.83)),
        p_br=Vector((-0.67, -2.39, 0.83)),
        p_tr=Vector((-0.67, -2.42, 1.02)),
        p_tl=Vector((0.67, -2.42, 1.02)),
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

    # H. 前翼外洗端板 Mobil 1 + Pirelli 贴纸 (左右两侧)
    create_quad_decal(
        "DEC_Endplate_Front_L",
        p_bl=Vector((-1.042, 3.15, 0.10)),
        p_br=Vector((-1.042, 2.75, 0.10)),
        p_tr=Vector((-1.042, 2.75, 0.36)),
        p_tl=Vector((-1.042, 3.15, 0.36)),
        mat=mat_dec_endplate,
        target_col=col_decals,
        uv_mode='flip_x'
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

    # I. 尾翼外侧端板 Mobil 1 + Pirelli 贴纸 (左右两侧)
    create_quad_decal(
        "DEC_Endplate_Rear_L",
        p_bl=Vector((-0.728, -2.10, 0.74)),
        p_br=Vector((-0.728, -2.52, 0.74)),
        p_tr=Vector((-0.728, -2.52, 1.14)),
        p_tl=Vector((-0.728, -2.10, 1.14)),
        mat=mat_dec_endplate,
        target_col=col_decals,
        uv_mode='flip_x'
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
    )

    # =========================================================================
    # 16. 专业赛车摄影棚高对比度布光 (Dark Studio Automotive Lighting)
    # ========================================================================="""

pattern_studio = r"(\s+# =========================================================================\s+# 15\..*?\(Professional Automotive Studio Stage\)\s+# =========================================================================)"
m = re.search(pattern_studio, code)
assert m, "Failed to find regex studio block"
code = code[:m.start()] + "\n" + new_decals_and_studio + "\n" + code[m.end():]

# 5. 更新章节编号与全部可选择状态
code = code.replace("16. 四机位工业级摄影机阵列", "17. 四机位工业级摄影机阵列")
code = code.replace("17. 渲染输出：4 视角美图", "18. 渲染输出：4 视角美图")

# 确保 DEC_* 贴纸也完全可选择
old_select = """    for obj in bpy.data.objects:
        if obj.name.startswith("GEO_F1_"):
            obj.hide_select = False
            obj.select_set(False)"""

new_select = """    for obj in bpy.data.objects:
        if obj.name.startswith("GEO_F1_") or obj.name.startswith("DEC_"):
            obj.hide_select = False
            obj.select_set(False)"""

assert old_select in code, "Failed to find old select block"
code = code.replace(old_select, new_select)

with open(r"D:\项目session\blender-supercar\build_scifi_f1.py", "w", encoding="utf-8") as f:
    f.write(code)

print("build_scifi_f1.py successfully updated with Oracle Red Bull Racing Livery & Decals!")
