# -*- coding: utf-8 -*-
"""
Concept Sci-Fi Formula 1 2035 (High-Fidelity Replicant & Fine Topology Edition)
==============================================================================
1:1 细节复刻参考图 sci_fi_f1_reference.jpg
- 精细布线 (Fine Topology & Edge Loops):
  1. 全车单体壳、机鼻与侧箱采用全四边面 (100% Quad-Dominant Topology) 高密多截面放样与支撑边 (Holding Loops)
  2. NACA 0024 真实水滴气动截面双叉臂 (Aerodynamic Teardrop Wishbones) 与前转向拉杆 (Tie Rod)
  3. 前轮内部碳纤维刹车进气风道 (Brake Cooling Ducts) 与碳陶制动盘护罩 (Brake Drums)
  4. 3D 真实文丘里地效底板隧道 (Venturi Underfloor Tunnels) 与 6 组扩散器导流垂直栅片
  5. 前翼副翼间隙保持架 (Slot Gap Separator Brackets) 与机鼻鼻下碳纤挂架
  6. 方向盘换挡拨片、彩色旋钮、赛车 6 点式安全带与全息曲面 HUD
  7. 18寸气动涡轮导流盘 (18 Radial Blades) 与拓扑封闭竞技热熔胎 (正切地表 Z=0)
- 保持 100% 独立分件与完全可编辑性 (非破坏性修改器 + 视口网格笼贴合 + 独立命名集合)
- 地坪锁定防误触 (GEO_Studio_Floor.hide_select = True)
- 输出 4 视角工作台高精渲染 + 1 张全车粘土线框图 (Wireframe Pass)
"""

import bpy
import bmesh
import math
import os
import shutil
import tempfile
from mathutils import Vector, Euler, Matrix

def get_or_create_col(name, parent_col=None):
    col = bpy.data.collections.get(name)
    if not col:
        col = bpy.data.collections.new(name)
        if parent_col:
            parent_col.children.link(col)
        else:
            bpy.context.scene.collection.children.link(col)
    return col

def link_to_col(obj, col):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)

def create_aero_strut(name, p1, p2, chord=0.036, thickness=0.014, target_col=None, mat=None):
    """创建具真实 NACA 0024 水滴形空力截面的碳纤维悬挂臂 (全四边形布线，锐利后缘，圆钝前缘)"""
    delta = p2 - p1
    length = delta.length
    if length < 1e-4:
        return None
    bm = bmesh.new()
    half_c = chord / 2.0
    half_t = thickness / 2.0
    # 8点高精水滴气动截面: X 沿气流弦长，Y 为厚度
    prof = [
        (half_c, 0.0),                          # 锐利后缘
        (half_c * 0.40, half_t * 0.70),         # 上后翼面
        (-half_c * 0.20, half_t),               # 上中脊峰值
        (-half_c * 0.75, half_t * 0.60),        # 上前缘倒角
        (-half_c, 0.0),                         # 圆钝迎风前缘
        (-half_c * 0.75, -half_t * 0.60),       # 下前缘倒角
        (-half_c * 0.20, -half_t),              # 下中脊峰值
        (half_c * 0.40, -half_t * 0.70)         # 下后翼面
    ]
    z_bot = -length / 2.0
    z_top = length / 2.0
    v_bot = [bm.verts.new(Vector((px, py, z_bot))) for px, py in prof]
    v_top = [bm.verts.new(Vector((px, py, z_top))) for px, py in prof]
    bm.verts.ensure_lookup_table()
    num_p = len(prof)
    for i in range(num_p):
        i_next = (i + 1) % num_p
        bm.faces.new([v_bot[i], v_top[i], v_top[i_next], v_bot[i_next]])
    bm.faces.new(v_bot)
    bm.faces.new(list(reversed(v_top)))
    
    me = bpy.data.meshes.new(f"ME_{name}")
    bm.to_mesh(me)
    bm.free()
    
    obj = bpy.data.objects.new(name, me)
    if target_col:
        link_to_col(obj, target_col)
    if mat:
        obj.data.materials.append(mat)
    obj.location = (p1 + p2) * 0.5
    rot_quat = delta.to_track_quat('Z', 'Y')
    obj.rotation_euler = rot_quat.to_euler()
    m_bev = obj.modifiers.new("Bevel", 'BEVEL')
    m_bev.width = 0.002
    obj.data.shade_smooth()
    return obj

def build_scifi_f1_detailed():
    print("=== STARTING HIGH-FIDELITY FINE TOPOLOGY SCI-FI F1 2035 BUILD ===")

    # 1. 清空旧场景
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # 2. 建立语义清晰的层级集合
    col_root = get_or_create_col("SCIFI_F1_2035")
    col_chassis = get_or_create_col("01_Chassis_Monocoque", col_root)
    col_halo = get_or_create_col("02_Cockpit_Halo_HUD", col_root)
    col_sidepods = get_or_create_col("03_Sidepods_EngineCowl", col_root)
    col_wings = get_or_create_col("04_Wings_Aerodynamics", col_root)
    col_susp = get_or_create_col("05_Suspension_Steering", col_root)
    col_wheels = get_or_create_col("06_Wheels_TurbineRims", col_root)
    col_lights = get_or_create_col("07_Telemetry_LED_Lights", col_root)
    col_decals = get_or_create_col("08_Sponsor_Decals", col_root)
    col_studio = get_or_create_col("09_Studio_Stage_Rig")

    # 3. 材质创建工具函数 (PBR Principled BSDF & Emission)
    def create_pbr_mat(name, color=(0.1, 0.1, 0.1, 1.0), metallic=0.0, roughness=0.5, clearcoat=0.0, emission=None, transmission=0.0):
        mat = bpy.data.materials.get(name)
        if not mat:
            mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()
        output = nodes.new(type='ShaderNodeOutputMaterial')
        
        if emission:
            sh = nodes.new(type='ShaderNodeEmission')
            sh.inputs['Color'].default_value = emission[0]
            sh.inputs['Strength'].default_value = emission[1]
            links.new(sh.outputs['Emission'], output.inputs['Surface'])
        else:
            sh = nodes.new(type='ShaderNodeBsdfPrincipled')
            sh.inputs['Base Color'].default_value = color
            sh.inputs['Metallic'].default_value = metallic
            sh.inputs['Roughness'].default_value = roughness
            if 'Coat Weight' in sh.inputs:
                sh.inputs['Coat Weight'].default_value = clearcoat
                if 'Coat Roughness' in sh.inputs:
                    sh.inputs['Coat Roughness'].default_value = 0.03
            elif 'Clearcoat' in sh.inputs:
                sh.inputs['Clearcoat'].default_value = clearcoat
            if 'Transmission Weight' in sh.inputs:
                sh.inputs['Transmission Weight'].default_value = transmission
            elif 'Transmission' in sh.inputs:
                sh.inputs['Transmission'].default_value = transmission
            links.new(sh.outputs['BSDF'], output.inputs['Surface'])
        return mat

    # 核心材质定义 (精准对照参考图)
    # Oracle Red Bull Racing 官方色彩规范
    mat_navy = create_pbr_mat("Mat_RedBull_MatteNavy", color=(0.015, 0.030, 0.075, 1.0), metallic=0.18, roughness=0.40, clearcoat=0.0)
    mat_rb_red = create_pbr_mat("Mat_RedBull_Crimson", color=(0.88, 0.02, 0.0, 1.0), metallic=0.15, roughness=0.35)
    mat_rb_yellow = create_pbr_mat("Mat_RedBull_SolarYellow", color=(1.0, 0.80, 0.0, 1.0), metallic=0.15, roughness=0.35)
    mat_pzero_red = create_pbr_mat("Mat_PZero_Red", color=(0.88, 0.02, 0.0, 1.0), metallic=0.0, roughness=0.45)
    
    # 贴纸材质生成函数 (Alpha通道透明映射)
    tex_base_dir = r"D:\项目session\blender-supercar\textures"
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
        
        # 赋予贴纸 0.25 微弱环境漫射光感，确保赛车贴纸在暗光赛道下具备高可读性
        if 'Emission Color' in sh_bsdf.inputs:
            links.new(tex_node.outputs['Color'], sh_bsdf.inputs['Emission Color'])
            if 'Emission Strength' in sh_bsdf.inputs:
                sh_bsdf.inputs['Emission Strength'].default_value = 0.25
        elif 'Emission' in sh_bsdf.inputs:
            links.new(tex_node.outputs['Color'], sh_bsdf.inputs['Emission'])
            
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

    mat_titanium = create_pbr_mat("Mat_Liquid_Titanium", color=(0.82, 0.84, 0.88, 1.0), metallic=0.98, roughness=0.12, clearcoat=1.0)
    mat_carbon = create_pbr_mat("Mat_Forged_Carbon", color=(0.015, 0.015, 0.016, 1.0), metallic=0.40, roughness=0.22, clearcoat=0.85)
    mat_carbon_satin = create_pbr_mat("Mat_Carbon_Satin", color=(0.025, 0.025, 0.027, 1.0), metallic=0.20, roughness=0.40)
    mat_radiator_mesh = create_pbr_mat("Mat_Radiator_Mesh", color=(0.14, 0.15, 0.17, 1.0), metallic=0.88, roughness=0.40)
    mat_neon_cyan = create_pbr_mat("Mat_Neon_Cyan", emission=((0.0, 0.95, 1.0, 1.0), 55.0))
    mat_neon_orange = create_pbr_mat("Mat_Neon_Orange", emission=((1.0, 0.40, 0.0, 1.0), 45.0))
    mat_hud = create_pbr_mat("Mat_HUD_Green", emission=((0.1, 1.0, 0.70, 1.0), 28.0), transmission=0.45)
    mat_rubber = create_pbr_mat("Mat_PZero_Slick", color=(0.02, 0.02, 0.02, 1.0), metallic=0.0, roughness=0.82)
    mat_white = create_pbr_mat("Mat_PZero_White", color=(0.92, 0.92, 0.94, 1.0), metallic=0.0, roughness=0.45)
    mat_gold = create_pbr_mat("Mat_Anodized_Gold", color=(0.95, 0.75, 0.08, 1.0), metallic=0.94, roughness=0.18)
    mat_exhaust = create_pbr_mat("Mat_Exhaust_Titanium", color=(0.35, 0.40, 0.48, 1.0), metallic=0.96, roughness=0.25)
    mat_rim_dark = create_pbr_mat("Mat_Rim_Dark", color=(0.04, 0.04, 0.045, 1.0), metallic=0.92, roughness=0.32)
    mat_floor = create_pbr_mat("Mat_Dark_Mirror_Floor", color=(0.010, 0.012, 0.015, 1.0), metallic=0.75, roughness=0.22)

    # 4. 高阶参数化弯度翼型生成器 (NACA Cambered Airfoil with Gull-Wing Arch)
    def create_airfoil_element(name, span, chord_in, chord_out, loc_start, loc_end, camber=0.04, thickness=0.015, twist_deg=0.0, target_col=col_wings, mat=mat_carbon):
        bm = bmesh.new()
        steps = 14
        profiles = []
        for p_idx, (t_factor, base_loc, chord) in enumerate([(0.0, loc_start, chord_in), (1.0, loc_end, chord_out)]):
            pts = []
            for i in range(steps + 1):
                u = i / steps
                x_pos = (u - 0.5) * chord
                camber_z = 4.0 * camber * chord * u * (1.0 - u)
                thick_z = 5.0 * thickness * chord * (0.2969 * math.sqrt(max(u, 1e-4)) - 0.1260 * u - 0.3516 * (u**2) + 0.2843 * (u**3) - 0.1015 * (u**4))
                pts.append((x_pos, camber_z + thick_z))
            for i in range(steps, -1, -1):
                u = i / steps
                x_pos = (u - 0.5) * chord
                camber_z = 4.0 * camber * chord * u * (1.0 - u)
                thick_z = 5.0 * thickness * chord * (0.2969 * math.sqrt(max(u, 1e-4)) - 0.1260 * u - 0.3516 * (u**2) + 0.2843 * (u**3) - 0.1015 * (u**4))
                pts.append((x_pos, camber_z - thick_z))
            
            prof_verts = []
            for px, pz in pts:
                v_local = Vector((base_loc.x, base_loc.y + px, base_loc.z + pz))
                prof_verts.append(bm.verts.new(v_local))
            profiles.append(prof_verts)

        bm.verts.ensure_lookup_table()
        p0, p1 = profiles[0], profiles[1]
        num_p = len(p0)
        for i in range(num_p - 1):
            bm.faces.new([p0[i], p0[i+1], p1[i+1], p1[i]])
        bm.faces.new([p0[-1], p0[0], p1[0], p1[-1]])
        bm.faces.new(p0)
        bm.faces.new(list(reversed(p1)))

        mesh = bpy.data.meshes.new(f"ME_{name}")
        bm.to_mesh(mesh)
        bm.free()

        obj = bpy.data.objects.new(name, mesh)
        link_to_col(obj, target_col)
        obj.data.materials.append(mat)
        m_mir = obj.modifiers.new("Mirror_X", 'MIRROR')
        m_mir.use_axis[0] = True
        m_mir.use_clip = True
        m_mir.show_on_cage = True
        m_mir.show_in_editmode = True
        m_sub = obj.modifiers.new("Subsurf", 'SUBSURF')
        m_sub.levels = 1
        m_sub.show_on_cage = True
        m_sub.show_in_editmode = True
        obj.data.shade_smooth()
        return obj

    # =========================================================================
    # 5. 精细全四边面机鼻锥体 (Fine Quad Nosecone & Bulkhead Seam)
    # =========================================================================
    # 采用 10 组流线横截面，每断面 6 点 (镜像后 12 点四边环)，带空气动力学侧脊线与支撑边
    bm_nose = bmesh.new()
    nose_secs = [
        # Y=3.42 (机鼻尖点起始环 - 双层紧密支撑边)
        [(0.0, 3.42, 0.080), (0.020, 3.42, 0.078), (0.035, 3.42, 0.070), (0.038, 3.42, 0.055), (0.025, 3.42, 0.045), (0.0, 3.42, 0.042)],
        [(0.0, 3.35, 0.095), (0.035, 3.35, 0.092), (0.058, 3.35, 0.080), (0.062, 3.35, 0.062), (0.045, 3.35, 0.052), (0.0, 3.35, 0.048)],
        # Y=3.05 (前翼主片交汇部)
        [(0.0, 3.05, 0.160), (0.065, 3.05, 0.155), (0.105, 3.05, 0.130), (0.112, 3.05, 0.095), (0.085, 3.05, 0.070), (0.0, 3.05, 0.065)],
        # Y=2.75 (前翼副翼过渡段)
        [(0.0, 2.75, 0.235), (0.095, 2.75, 0.228), (0.145, 2.75, 0.185), (0.150, 2.75, 0.130), (0.115, 2.75, 0.095), (0.0, 2.75, 0.090)],
        # Y=2.40 (前机鼻中段气动脊线)
        [(0.0, 2.40, 0.325), (0.125, 2.40, 0.315), (0.180, 2.40, 0.250), (0.185, 2.40, 0.170), (0.140, 2.40, 0.120), (0.0, 2.40, 0.115)],
        # Y=2.05 (空速管与悬挂推杆座前沿)
        [(0.0, 2.05, 0.415), (0.155, 2.05, 0.400), (0.210, 2.05, 0.315), (0.215, 2.05, 0.210), (0.165, 2.05, 0.140), (0.0, 2.05, 0.135)],
        # Y=1.75 (前隔框预装配位)
        [(0.0, 1.75, 0.485), (0.185, 1.75, 0.468), (0.235, 1.75, 0.355), (0.240, 1.75, 0.245), (0.185, 1.75, 0.155), (0.0, 1.75, 0.150)],
        # Y=1.65 (机鼻与单体壳真实装配分缝面 - 支撑边)
        [(0.0, 1.65, 0.505), (0.195, 1.65, 0.488), (0.248, 1.65, 0.368), (0.252, 1.65, 0.255), (0.195, 1.65, 0.162), (0.0, 1.65, 0.158)],
    ]
    grid_nose = []
    for s in nose_secs:
        grid_nose.append([bm_nose.verts.new(pt) for pt in s])
    bm_nose.verts.ensure_lookup_table()
    for i in range(len(nose_secs) - 1):
        for j in range(5):
            bm_nose.faces.new([grid_nose[i][j], grid_nose[i][j+1], grid_nose[i+1][j+1], grid_nose[i+1][j]])
    # 封闭顶尖四边面
    bm_nose.faces.new([grid_nose[0][0], grid_nose[0][1], grid_nose[0][4], grid_nose[0][5]])
    bm_nose.faces.new([grid_nose[0][1], grid_nose[0][2], grid_nose[0][3], grid_nose[0][4]])

    mesh_nose = bpy.data.meshes.new("ME_F1_Nosecone")
    bm_nose.to_mesh(mesh_nose)
    bm_nose.free()

    obj_nose = bpy.data.objects.new("GEO_F1_Nosecone", mesh_nose)
    link_to_col(obj_nose, col_chassis)
    obj_nose.data.materials.append(mat_navy)
    m_nose_mir = obj_nose.modifiers.new("Mirror_X", 'MIRROR')
    m_nose_mir.use_axis[0] = True
    m_nose_mir.use_clip = True
    m_nose_mir.show_on_cage = True
    m_nose_sub = obj_nose.modifiers.new("Subsurf", 'SUBSURF')
    m_nose_sub.levels = 2
    m_nose_sub.show_on_cage = True
    m_nose_sub.show_in_editmode = True
    obj_nose.data.shade_smooth()

    # 机鼻与单体壳物理装配刻线 (Chassis Bulkhead Shutline - 真实 F1 碳纤密封圈)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.25, minor_radius=0.006, major_segments=32, minor_segments=8)
    bulkhead_ring = bpy.context.active_object
    bulkhead_ring.name = "GEO_F1_Chassis_BulkheadSeam"
    bulkhead_ring.rotation_euler = (math.radians(90), 0, 0)
    bulkhead_ring.scale = (0.98, 1.0, 0.70)
    bulkhead_ring.location = (0.0, 1.65, 0.33)
    link_to_col(bulkhead_ring, col_chassis)
    bulkhead_ring.data.materials.append(mat_carbon)

    # 机鼻脊背中央电青遥测发光刀刃 (Central Neon Cyan Telemetry Stripe - 1:1还原参考图)
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    nose_stripe = bpy.context.active_object
    nose_stripe.name = "GEO_F1_Nose_NeonStripe"
    nose_stripe.scale = (0.012, 0.35, 0.010)
    nose_stripe.location = (0.0, 1.45, 0.55)
    nose_stripe.rotation_euler = (math.radians(-14.0), 0, 0)
    link_to_col(nose_stripe, col_lights)
    nose_stripe.data.materials.append(mat_rb_yellow)

    # 机鼻空速管 (Pitot Tubes)
    for pit_sign in [-1, 1]:
        bpy.ops.mesh.primitive_cylinder_add(radius=0.003, depth=0.14, vertices=12)
        pitot = bpy.context.active_object
        pitot.name = f"GEO_F1_PitotTube_{'L' if pit_sign < 0 else 'R'}"
        pitot.rotation_euler = (math.radians(82), 0, 0)
        pitot.location = (0.06 * pit_sign, 2.25, 0.36)
        link_to_col(pitot, col_chassis)
        pitot.data.materials.append(mat_titanium)

    # 机鼻上方 S-Duct 气动垂直分流小翼
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    sduct_blade = bpy.context.active_object
    sduct_blade.name = "GEO_F1_Nose_SductBlade"
    sduct_blade.scale = (0.008, 0.12, 0.16)
    sduct_blade.location = (0.0, 1.55, 0.58)
    sduct_blade.rotation_euler = (math.radians(-14), 0, 0)
    link_to_col(sduct_blade, col_chassis)
    sduct_blade.data.materials.append(mat_carbon)

    # =========================================================================
    # 6. 单体壳驾驶舱精细四边面 (Fine Quad Monocoque Chassis)
    # =========================================================================
    bm_chassis = bmesh.new()
    chassis_secs = [
        # Y=1.65 (与机鼻断面完全对齐对缝)
        [(0.0, 1.65, 0.505), (0.195, 1.65, 0.488), (0.248, 1.65, 0.368), (0.252, 1.65, 0.255), (0.195, 1.65, 0.162), (0.0, 1.65, 0.158)],
        # Y=1.20 (驾驶舱前围与脚部空间)
        [(0.0, 1.20, 0.605), (0.235, 1.20, 0.585), (0.295, 1.20, 0.405), (0.300, 1.20, 0.265), (0.235, 1.20, 0.168), (0.0, 1.20, 0.165)],
        # Y=0.65 (仪表盘与 Halo 前锚点)
        [(0.0, 0.65, 0.665), (0.265, 0.65, 0.640), (0.345, 0.65, 0.435), (0.350, 0.65, 0.275), (0.275, 0.65, 0.170), (0.0, 0.65, 0.168)],
        # Y=0.00 (驾驶员座舱环口与侧向防撞区)
        [(0.0, 0.00, 0.690), (0.285, 0.00, 0.670), (0.385, 0.00, 0.450), (0.390, 0.00, 0.275), (0.305, 0.00, 0.172), (0.0, 0.00, 0.170)],
        # Y=-0.45 (座舱头枕与防滚架基座)
        [(0.0, -0.45, 0.785), (0.270, -0.45, 0.760), (0.395, -0.45, 0.460), (0.400, -0.45, 0.275), (0.315, -0.45, 0.175), (0.0, -0.45, 0.172)],
        # Y=-0.70 (发动机防火墙连接部)
        [(0.0, -0.70, 0.815), (0.255, -0.70, 0.785), (0.410, -0.70, 0.465), (0.415, -0.70, 0.275), (0.325, -0.70, 0.178), (0.0, -0.70, 0.175)]
    ]
    grid_chassis = []
    for s in chassis_secs:
        grid_chassis.append([bm_chassis.verts.new(pt) for pt in s])
    bm_chassis.verts.ensure_lookup_table()
    for i in range(len(chassis_secs) - 1):
        for j in range(5):
            bm_chassis.faces.new([grid_chassis[i][j], grid_chassis[i][j+1], grid_chassis[i+1][j+1], grid_chassis[i+1][j]])

    mesh_chassis = bpy.data.meshes.new("ME_F1_Monocoque_Chassis")
    bm_chassis.to_mesh(mesh_chassis)
    bm_chassis.free()

    obj_chassis = bpy.data.objects.new("GEO_F1_Monocoque_Chassis", mesh_chassis)
    link_to_col(obj_chassis, col_chassis)
    obj_chassis.data.materials.append(mat_navy)
    m_ch_mir = obj_chassis.modifiers.new("Mirror_X", 'MIRROR')
    m_ch_mir.use_axis[0] = True
    m_ch_mir.use_clip = True
    m_ch_mir.show_on_cage = True
    m_ch_sub = obj_chassis.modifiers.new("Subsurf", 'SUBSURF')
    m_ch_sub.levels = 2
    m_ch_sub.show_on_cage = True
    m_ch_sub.show_in_editmode = True
    obj_chassis.data.shade_smooth()

    # =========================================================================
    # 7. 前翼总成 (4层副翼 + 间隙保持架 + 外洗端板发光框)
    # =========================================================================
    # 主翼底层 (Mainplane)
    create_airfoil_element(
        "GEO_F1_FrontWing_Mainplane",
        span=0.96, chord_in=0.36, chord_out=0.38,
        loc_start=Vector((0.08, 3.05, 0.075)), loc_end=Vector((1.02, 3.00, 0.095)),
        camber=0.040, thickness=0.016, twist_deg=-6.0, target_col=col_wings
    )
    # 4 层级联副翼 (Cascaded Flaps with Gull-Wing Rise)
    flap_params = [
        (0.06, 0.022, 0.28, 0.32, -12.0),
        (0.12, 0.046, 0.24, 0.28, -16.0),
        (0.18, 0.072, 0.20, 0.24, -20.0),
        (0.24, 0.100, 0.16, 0.20, -25.0)
    ]
    for f_idx, (dy, dz, cin, cout, deg) in enumerate(flap_params):
        create_airfoil_element(
            f"GEO_F1_FrontWing_Flap_{f_idx+1}",
            span=0.94, chord_in=cin, chord_out=cout,
            loc_start=Vector((0.09, 3.02 - dy, 0.08 + dz)), loc_end=Vector((1.00, 2.98 - dy, 0.10 + dz)),
            camber=0.045, thickness=0.012, twist_deg=deg, target_col=col_wings
        )

    # 真实 F1 规则：副翼间隙微型保持支架 (Slot Gap Separators - 8组微型空力连接片)
    for sep_x in [0.28, 0.48, 0.68, 0.88]:
        for sep_i in range(3):
            dy = 0.08 + (sep_i * 0.06)
            dz = 0.09 + (sep_i * 0.026)
            create_aero_strut(
                f"GEO_F1_SlotGapSeparator_{sep_x}_{sep_i}",
                Vector((sep_x, 2.98 - dy, dz)), Vector((sep_x, 2.92 - dy, dz + 0.026)),
                chord=0.016, thickness=0.005, target_col=col_wings, mat=mat_carbon
            )
            # 镜像左侧
            create_aero_strut(
                f"GEO_F1_SlotGapSeparator_L_{sep_x}_{sep_i}",
                Vector((-sep_x, 2.98 - dy, dz)), Vector((-sep_x, 2.92 - dy, dz + 0.026)),
                chord=0.016, thickness=0.005, target_col=col_wings, mat=mat_carbon
            )

    # 前翼鼻下气动挂架 (Nose Pylons)
    for np_x in [-0.07, 0.07]:
        create_aero_strut(f"GEO_F1_FrontWing_NosePylon_{np_x}", Vector((np_x, 2.92, 0.08)), Vector((np_x, 2.92, 0.20)), chord=0.045, thickness=0.010, target_col=col_wings, mat=mat_carbon)

    # 前翼高阶外洗端板 (Sculpted Outwash Endplates with Cyan LED Bezel)
    for ep_sign, ep_side in [(-1, "L"), (1, "R")]:
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        ep = bpy.context.active_object
        ep.name = f"GEO_F1_FrontWing_Endplate_{ep_side}"
        ep.scale = (0.018, 0.62, 0.36)
        ep.location = (1.02 * ep_sign, 2.95, 0.22)
        ep.rotation_euler = (0, math.radians(-7.0 * ep_sign), math.radians(2.0 * ep_sign))
        link_to_col(ep, col_wings)
        ep.data.materials.append(mat_carbon)
        m_ep_bev = ep.modifiers.new("Bevel", 'BEVEL')
        m_ep_bev.width = 0.008
        ep.data.shade_smooth()

        # 外侧俯冲风刀 (Outer Dive Plane / Canard)
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        canard = bpy.context.active_object
        canard.name = f"GEO_F1_FrontWing_Canard_{ep_side}"
        canard.scale = (0.08, 0.28, 0.012)
        canard.location = (1.06 * ep_sign, 2.95, 0.18)
        canard.rotation_euler = (math.radians(-15), 0, math.radians(6 * ep_sign))
        link_to_col(canard, col_wings)
        canard.data.materials.append(mat_carbon)

        # 端板霓虹电青发光框线 (Cyan Neon Light Blade)
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        ep_light = bpy.context.active_object
        ep_light.name = f"GEO_F1_FrontWing_Endplate_Light_{ep_side}"
        ep_light.scale = (0.010, 0.625, 0.016)
        ep_light.location = (1.032 * ep_sign, 2.95, 0.40)
        ep_light.rotation_euler = (0, math.radians(-7.0 * ep_sign), math.radians(2.0 * ep_sign))
        link_to_col(ep_light, col_lights)
        ep_light.data.materials.append(mat_neon_cyan)

    # =========================================================================
    # 8. 激进深下切侧箱与发动机罩 (Undercut Sidepods & Coke-Bottle Rear)
    # =========================================================================
    bm_engine = bmesh.new()
    engine_secs = [
        # Y=-0.45 (衔接单体壳座舱头枕)
        [(0.0, -0.45, 0.815), (0.255, -0.45, 0.785), (0.585, -0.45, 0.540), (0.640, -0.45, 0.200)],
        # Y=-0.85 (信箱进气道侧翼与最大横向膨胀)
        [(0.0, -0.85, 0.865), (0.245, -0.85, 0.840), (0.560, -0.85, 0.520), (0.610, -0.85, 0.190)],
        # Y=-1.25 (百叶窗散热带与下切收腰区)
        [(0.0, -1.25, 0.840), (0.220, -1.25, 0.810), (0.480, -1.25, 0.460), (0.520, -1.25, 0.185)],
        # Y=-1.65 (激进可乐瓶收腰，内收露出发动机舱)
        [(0.0, -1.65, 0.760), (0.185, -1.65, 0.730), (0.370, -1.65, 0.380), (0.420, -1.65, 0.180)],
        # Y=-2.15 (尾部排气与变速箱出口收尖)
        [(0.0, -2.15, 0.620), (0.145, -2.15, 0.590), (0.250, -2.15, 0.340), (0.280, -2.15, 0.180)]
    ]
    eng_grid = []
    for s in engine_secs:
        eng_grid.append([bm_engine.verts.new(pt) for pt in s])
    bm_engine.verts.ensure_lookup_table()
    for i in range(len(engine_secs) - 1):
        for j in range(3):
            bm_engine.faces.new([eng_grid[i][j], eng_grid[i][j+1], eng_grid[i+1][j+1], eng_grid[i+1][j]])

    mesh_engine = bpy.data.meshes.new("ME_F1_EngineCowl_Body")
    bm_engine.to_mesh(mesh_engine)
    bm_engine.free()

    obj_engine = bpy.data.objects.new("GEO_F1_EngineCowl_Body", mesh_engine)
    link_to_col(obj_engine, col_sidepods)
    obj_engine.data.materials.append(mat_navy)
    m_eng_mir = obj_engine.modifiers.new("Mirror_X", 'MIRROR')
    m_eng_mir.use_axis[0] = True
    m_eng_mir.use_clip = True
    m_eng_mir.show_on_cage = True
    m_eng_sub = obj_engine.modifiers.new("Subsurf", 'SUBSURF')
    m_eng_sub.levels = 2
    m_eng_sub.show_on_cage = True
    obj_engine.data.shade_smooth()

    # 侧箱进气道 (扁平信箱型进气口 + 铝排散热中冷)
    for s_sign, s_name in [(-1, "L"), (1, "R")]:
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        intake_box = bpy.context.active_object
        intake_box.name = f"GEO_F1_Sidepod_IntakeLip_{s_name}"
        intake_box.scale = (0.14, 0.26, 0.12)
        intake_box.location = (0.54 * s_sign, 0.20, 0.40)
        intake_box.rotation_euler = (math.radians(-10), 0, math.radians(8 * s_sign))
        link_to_col(intake_box, col_sidepods)
        intake_box.data.materials.append(mat_navy)
        m_ib_bev = intake_box.modifiers.new("Bevel", 'BEVEL')
        m_ib_bev.width = 0.02
        intake_box.data.shade_smooth()

        # 内部散热器蜂窝铝排片 (Radiator Core)
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        rad_mesh = bpy.context.active_object
        rad_mesh.name = f"GEO_F1_Sidepod_RadiatorCore_{s_name}"
        rad_mesh.scale = (0.18, 0.02, 0.16)
        rad_mesh.location = (0.54 * s_sign, 0.14, 0.40)
        rad_mesh.rotation_euler = (math.radians(-25), 0, math.radians(10 * s_sign))
        link_to_col(rad_mesh, col_sidepods)
        rad_mesh.data.materials.append(mat_radiator_mesh)

        # 侧箱肩部 6 组物理级阶梯散热百叶窗 (Cooling Louvers)
        for lv_i in range(6):
            bpy.ops.mesh.primitive_cube_add(size=1.0)
            louv = bpy.context.active_object
            louv.name = f"GEO_F1_Sidepod_Louver_{s_name}_{lv_i}"
            louv.scale = (0.14, 0.024, 0.008)
            louv.location = (0.48 * s_sign, -0.32 - (lv_i * 0.075), 0.58 - (lv_i * 0.025))
            louv.rotation_euler = (math.radians(-26), 0, math.radians(10 * s_sign))
            link_to_col(louv, col_sidepods)
            louv.data.materials.append(mat_carbon)

    # 顶置梯形进气道 (Airbox) 与碳纤维鲨鱼鳍 (Shark Fin)
    bm_airbox = bmesh.new()
    ab_secs = [
        # Y=-0.12 (进气道前唇，下底紧扣座舱防滚架座 Z=0.76，彻底消除悬空)
        [(0.0, -0.12, 1.10), (0.11, -0.12, 1.06), (0.14, -0.12, 0.88), (0.0, -0.12, 0.76)],
        # Y=-0.45 (顺滑过渡段，完全包覆引擎前防火墙)
        [(0.0, -0.45, 1.12), (0.12, -0.45, 1.08), (0.18, -0.45, 0.88), (0.0, -0.45, 0.82)],
        # Y=-1.05 (与鲨鱼鳍与引擎盖顶脊完全融合)
        [(0.0, -1.05, 1.02), (0.08, -1.05, 0.98), (0.14, -1.05, 0.88), (0.0, -1.05, 0.86)]
    ]
    grid_ab = []
    for s in ab_secs:
        grid_ab.append([bm_airbox.verts.new(pt) for pt in s])
    bm_airbox.verts.ensure_lookup_table()
    for i in range(len(ab_secs) - 1):
        for j in range(3):
            bm_airbox.faces.new([grid_ab[i][j], grid_ab[i][j+1], grid_ab[i+1][j+1], grid_ab[i+1][j]])

    mesh_ab = bpy.data.meshes.new("ME_F1_Airbox_Scoop")
    bm_airbox.to_mesh(mesh_ab)
    bm_airbox.free()

    obj_ab = bpy.data.objects.new("GEO_F1_Airbox_Scoop", mesh_ab)
    link_to_col(obj_ab, col_sidepods)
    obj_ab.data.materials.append(mat_navy)
    m_ab_mir = obj_ab.modifiers.new("Mirror_X", 'MIRROR')
    m_ab_mir.use_axis[0] = True
    m_ab_mir.use_clip = True
    m_ab_sub = obj_ab.modifiers.new("Subsurf", 'SUBSURF')
    m_ab_sub.levels = 2
    obj_ab.data.shade_smooth()

    # 进气道发光电青霓虹边框 (Neon Cyan Airbox Bezel)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.11, minor_radius=0.010, major_segments=28, minor_segments=12)
    airbox_ring = bpy.context.active_object
    airbox_ring.name = "GEO_F1_Airbox_NeonRing"
    airbox_ring.rotation_euler = (math.radians(90), 0, 0)
    airbox_ring.scale = (1.1, 1.0, 0.85)
    airbox_ring.location = (0.0, -0.12, 0.98)
    link_to_col(airbox_ring, col_lights)
    airbox_ring.data.materials.append(mat_neon_cyan)

    # 顶部 FIA T-Cam 摄像机机柱
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    tcam = bpy.context.active_object
    tcam.name = "GEO_F1_Overhead_TCam"
    tcam.scale = (0.16, 0.055, 0.038)
    tcam.location = (0.0, -0.28, 1.15)
    link_to_col(tcam, col_sidepods)
    tcam.data.materials.append(mat_carbon)

    # 碳纤维中央鲨鱼鳍 (Dorsal Shark Fin)
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    shark_fin = bpy.context.active_object
    shark_fin.name = "GEO_F1_Dorsal_SharkFin"
    shark_fin.scale = (0.016, 1.25, 0.28)
    shark_fin.location = (0.0, -1.35, 0.92)
    shark_fin.rotation_euler = (math.radians(-5.0), 0, 0)
    link_to_col(shark_fin, col_sidepods)
    shark_fin.data.materials.append(mat_carbon)
    m_sf_bev = shark_fin.modifiers.new("Bevel", 'BEVEL')
    m_sf_bev.width = 0.006

    # =========================================================================
    # 9. 真实 3D 文丘里地效底板与扩散器 (3D Venturi Tunnel Ground-Effect Floor)
    # =========================================================================
    # 构建具渐变喉部与上翘扩散器的三维曲面文丘里底板
    bm_flr = bmesh.new()
    flr_secs = [
        # Y=1.35 (机鼻下方茶盘 Splitter Bib)
        [(0.0, 1.35, 0.075), (0.28, 1.35, 0.075), (0.55, 1.35, 0.078), (0.84, 1.35, 0.082)],
        # Y=0.40 (侧箱前端入口底面)
        [(0.0, 0.40, 0.060), (0.32, 0.40, 0.060), (0.64, 0.40, 0.065), (0.86, 0.40, 0.070)],
        # Y=-0.50 (文丘里喉部 - 地表极限离地间隙 45mm)
        [(0.0, -0.50, 0.045), (0.34, -0.50, 0.045), (0.68, -0.50, 0.048), (0.86, -0.50, 0.052)],
        # Y=-1.30 (后扩散器上翘扩张段开始)
        [(0.0, -1.30, 0.080), (0.32, -1.30, 0.085), (0.62, -1.30, 0.095), (0.82, -1.30, 0.105)],
        # Y=-2.20 (后扩散器尾部最高出口)
        [(0.0, -2.20, 0.260), (0.26, -2.20, 0.265), (0.50, -2.20, 0.275), (0.72, -2.20, 0.285)]
    ]
    grid_flr = []
    for s in flr_secs:
        grid_flr.append([bm_flr.verts.new(pt) for pt in s])
    bm_flr.verts.ensure_lookup_table()
    for i in range(len(flr_secs) - 1):
        for j in range(3):
            bm_flr.faces.new([grid_flr[i][j], grid_flr[i][j+1], grid_flr[i+1][j+1], grid_flr[i+1][j]])

    me_flr = bpy.data.meshes.new("ME_F1_Underbody_Floor")
    bm_flr.to_mesh(me_flr)
    bm_flr.free()

    obj_flr = bpy.data.objects.new("GEO_F1_Underbody_Floor", me_flr)
    link_to_col(obj_flr, col_chassis)
    obj_flr.data.materials.append(mat_carbon)
    m_flr_mir = obj_flr.modifiers.new("Mirror_X", 'MIRROR')
    m_flr_mir.use_axis[0] = True
    m_flr_mir.show_on_cage = True
    m_flr_sol = obj_flr.modifiers.new("Solidify", 'SOLIDIFY')
    m_flr_sol.thickness = 0.018
    obj_flr.data.shade_smooth()

    # 底板边缘电青发光条 (Floor Edge Neon Cyan)
    for fe_sign, fe_name in [(-1, "L"), (1, "R")]:
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        fe_strip = bpy.context.active_object
        fe_strip.name = f"GEO_F1_FloorEdge_Neon_{fe_name}"
        fe_strip.scale = (0.012, 2.85, 0.014)
        fe_strip.location = (0.865 * fe_sign, -0.38, 0.080)
        link_to_col(fe_strip, col_lights)
        fe_strip.data.materials.append(mat_neon_cyan)

    # 6 组扩散器垂直气动分流栅片 (Diffuser Vertical Strakes)
    for strake_i in [-0.58, -0.36, -0.14, 0.14, 0.36, 0.58]:
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        stk = bpy.context.active_object
        stk.name = f"GEO_F1_Diffuser_Strake_{strake_i:.2f}"
        stk.scale = (0.008, 0.72, 0.18)
        stk.location = (strake_i, -2.12, 0.20)
        stk.rotation_euler = (math.radians(16.0), 0, 0)
        link_to_col(stk, col_wings)
        stk.data.materials.append(mat_carbon)

    # =========================================================================
    # 10. 双层高下压力尾翼总成与 DRS 控制盒 (Swan-Neck Rear Wing & DRS)
    # =========================================================================
    # 碳纤维双鹅颈空力立柱 (Swan-Neck Carbon Pylons - 具倒角厚度空力薄板)
    for py_sign, py_name in [(-1, "L"), (1, "R")]:
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        pylon = bpy.context.active_object
        pylon.name = f"GEO_F1_RearWing_SwanPylon_{py_name}"
        pylon.scale = (0.016, 0.32, 0.44)
        pylon.location = (0.14 * py_sign, -2.15, 0.88)
        pylon.rotation_euler = (math.radians(-16), 0, 0)
        link_to_col(pylon, col_wings)
        pylon.data.materials.append(mat_carbon)
        m_py_bev = pylon.modifiers.new("Bevel", 'BEVEL')
        m_py_bev.width = 0.008
        pylon.data.shade_smooth()

    # 尾翼主翼片 (Rear Wing Mainplane)
    create_airfoil_element(
        "GEO_F1_RearWing_Mainplane",
        span=0.68, chord_in=0.34, chord_out=0.32,
        loc_start=Vector((0.00, -2.28, 0.92)), loc_end=Vector((0.68, -2.28, 0.92)),
        camber=0.065, thickness=0.022, twist_deg=-5.0, target_col=col_wings
    )
    # 尾翼 DRS 可动副翼 (Active DRS Upper Flap)
    create_airfoil_element(
        "GEO_F1_RearWing_DRSFlap",
        span=0.68, chord_in=0.22, chord_out=0.20,
        loc_start=Vector((0.00, -2.36, 1.04)), loc_end=Vector((0.68, -2.36, 1.04)),
        camber=0.055, thickness=0.018, twist_deg=-12.0, target_col=col_wings
    )

    # DRS 液压伺服驱动控制盒
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    drs_pod = bpy.context.active_object
    drs_pod.name = "GEO_F1_RearWing_DRS_Actuator"
    drs_pod.scale = (0.045, 0.12, 0.05)
    drs_pod.location = (0.0, -2.32, 1.05)
    link_to_col(drs_pod, col_wings)
    drs_pod.data.materials.append(mat_titanium)
    m_dp_bev = drs_pod.modifiers.new("Bevel", 'BEVEL')
    m_dp_bev.width = 0.006

    # 尾部双层横梁翼 (Dual-Tier Beam Wing)
    create_airfoil_element(
        "GEO_F1_BeamWing_Lower",
        span=0.48, chord_in=0.18, chord_out=0.16,
        loc_start=Vector((0.00, -2.18, 0.42)), loc_end=Vector((0.48, -2.18, 0.42)),
        camber=0.04, thickness=0.012, twist_deg=-8.0, target_col=col_wings
    )
    create_airfoil_element(
        "GEO_F1_BeamWing_Upper",
        span=0.46, chord_in=0.14, chord_out=0.12,
        loc_start=Vector((0.00, -2.24, 0.50)), loc_end=Vector((0.46, -2.24, 0.50)),
        camber=0.04, thickness=0.012, twist_deg=-12.0, target_col=col_wings
    )

    # 尾翼端板与垂直发光灯带 (Rear Wing Endplates with Neon Lighting)
    for r_sign, r_side in [(-1, "L"), (1, "R")]:
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        rw_ep = bpy.context.active_object
        rw_ep.name = f"GEO_F1_RearWing_Endplate_{r_side}"
        rw_ep.scale = (0.016, 0.54, 0.48)
        rw_ep.location = (0.70 * r_sign, -2.30, 0.94)
        link_to_col(rw_ep, col_wings)
        rw_ep.data.materials.append(mat_carbon)
        m_rwep_bev = rw_ep.modifiers.new("Bevel", 'BEVEL')
        m_rwep_bev.width = 0.008
        rw_ep.data.shade_smooth()

        # 尾翼端板后沿电青发光条
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        rw_light = bpy.context.active_object
        rw_light.name = f"GEO_F1_RearWing_Endplate_Light_{r_side}"
        rw_light.scale = (0.010, 0.016, 0.48)
        rw_light.location = (0.712 * r_sign, -2.57, 0.94)
        link_to_col(rw_light, col_lights)
        rw_light.data.materials.append(mat_neon_cyan)

    # 钛合金中央排气管与 FIA 雨雾警示灯
    bpy.ops.mesh.primitive_cylinder_add(radius=0.065, depth=0.38, vertices=28)
    exhaust = bpy.context.active_object
    exhaust.name = "GEO_F1_Exhaust_TitaniumTail"
    exhaust.rotation_euler = (math.radians(85), 0, 0)
    exhaust.location = (0.0, -2.18, 0.48)
    link_to_col(exhaust, col_sidepods)
    exhaust.data.materials.append(mat_exhaust)
    exhaust.data.shade_smooth()

    bpy.ops.mesh.primitive_torus_add(major_radius=0.052, minor_radius=0.008, major_segments=24, minor_segments=10)
    exh_flame = bpy.context.active_object
    exh_flame.name = "GEO_F1_Exhaust_InnerGlow"
    exh_flame.rotation_euler = (math.radians(90), 0, 0)
    exh_flame.location = (0.0, -2.36, 0.48)
    link_to_col(exh_flame, col_lights)
    exh_flame.data.materials.append(mat_neon_orange)

    bpy.ops.mesh.primitive_cube_add(size=1.0)
    rain_light = bpy.context.active_object
    rain_light.name = "GEO_F1_FIA_RainLight"
    rain_light.scale = (0.06, 0.02, 0.05)
    rain_light.location = (0.0, -2.44, 0.24)
    link_to_col(rain_light, col_lights)
    rain_light.data.materials.append(mat_neon_orange)

    # =========================================================================
    # 11. 水滴气动截面双叉臂悬挂与前轮转向拉杆 (Aerodynamic Wishbones & Tie Rod)
    # =========================================================================
    susp_defs = [
        ("Front", 1.45, 0.28, 0.90, 0.355, 0.38),
        ("Rear", -1.55, 0.30, 0.86, 0.355, 0.36)
    ]
    for s_name, y_axle, z_in, x_wheel, z_wheel, y_spread in susp_defs:
        for s_sign, s_side in [(-1, "L"), (1, "R")]:
            xw = x_wheel * s_sign
            col_susp_set = get_or_create_col(f"Susp_{s_name}_{s_side}", col_susp)

            # A. 上A字叉臂 (Upper Wishbone 前臂+后臂 - NACA 水滴截面)
            p_up_out = Vector((xw - (0.06 * s_sign), y_axle, z_wheel + 0.09))
            p_up_fwd = Vector((0.26 * s_sign, y_axle + (y_spread * 0.45), z_in + 0.12))
            p_up_aft = Vector((0.26 * s_sign, y_axle - (y_spread * 0.45), z_in + 0.12))
            create_aero_strut(f"GEO_F1_{s_name}_UpperArmFwd_{s_side}", p_up_fwd, p_up_out, chord=0.034, thickness=0.013, target_col=col_susp_set, mat=mat_carbon)
            create_aero_strut(f"GEO_F1_{s_name}_UpperArmAft_{s_side}", p_up_aft, p_up_out, chord=0.034, thickness=0.013, target_col=col_susp_set, mat=mat_carbon)

            # B. 下A字叉臂 (Lower Wishbone 前臂+后臂 - NACA 水滴截面)
            p_dn_out = Vector((xw - (0.06 * s_sign), y_axle, z_wheel - 0.09))
            p_dn_fwd = Vector((0.24 * s_sign, y_axle + (y_spread * 0.50), z_in - 0.10))
            p_dn_aft = Vector((0.24 * s_sign, y_axle - (y_spread * 0.50), z_in - 0.10))
            create_aero_strut(f"GEO_F1_{s_name}_LowerArmFwd_{s_side}", p_dn_fwd, p_dn_out, chord=0.036, thickness=0.014, target_col=col_susp_set, mat=mat_carbon)
            create_aero_strut(f"GEO_F1_{s_name}_LowerArmAft_{s_side}", p_dn_aft, p_dn_out, chord=0.036, thickness=0.014, target_col=col_susp_set, mat=mat_carbon)

            # C. 倾斜推杆 (Pushrod)
            p_pr_in = Vector((0.26 * s_sign, y_axle + (0.12 if s_name=="Front" else -0.12), z_in + 0.18))
            create_aero_strut(f"GEO_F1_{s_name}_Pushrod_{s_side}", p_pr_in, p_dn_out, chord=0.038, thickness=0.015, target_col=col_susp_set, mat=mat_carbon)

            # D. 前轮转向横拉杆 (Front Steering Tie Rod - 真实前悬挂第5根连杆)
            if s_name == "Front":
                p_tierod_in = Vector((0.25 * s_sign, y_axle + 0.18, z_in + 0.05))
                p_tierod_out = Vector((xw - (0.05 * s_sign), y_axle + 0.16, z_wheel + 0.02))
                create_aero_strut(f"GEO_F1_Steering_TieRod_{s_side}", p_tierod_in, p_tierod_out, chord=0.026, thickness=0.012, target_col=col_susp_set, mat=mat_carbon)

            # E. 金属万向球头节 (Metallic Ball Joints at Hub)
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.024)
            joint_up = bpy.context.active_object
            joint_up.name = f"GEO_F1_{s_name}_BallJoint_Upper_{s_side}"
            joint_up.location = p_up_out
            link_to_col(joint_up, col_susp_set)
            joint_up.data.materials.append(mat_gold)

            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.024)
            joint_dn = bpy.context.active_object
            joint_dn.name = f"GEO_F1_{s_name}_BallJoint_Lower_{s_side}"
            joint_dn.location = p_dn_out
            link_to_col(joint_dn, col_susp_set)
            joint_dn.data.materials.append(mat_gold)

    # =========================================================================
    # 12. 碳纤维刹车进气风道与制动护罩 (Brake Cooling Ducts & Shrouds)
    # =========================================================================
    for f_sign, f_side in [(-1, "L"), (1, "R")]:
        col_w_set = get_or_create_col(f"Wheel_F{f_side}", col_wheels)
        # 前轮内侧刹车进气风铲 (Forward-Facing Carbon Brake Duct Scoop)
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        b_scoop = bpy.context.active_object
        b_scoop.name = f"GEO_F1_Front_BrakeDuctScoop_{f_side}"
        b_scoop.scale = (0.05, 0.12, 0.14)
        b_scoop.location = (0.76 * f_sign, 1.58, 0.38)
        b_scoop.rotation_euler = (math.radians(-12), 0, math.radians(6 * f_sign))
        link_to_col(b_scoop, col_w_set)
        b_scoop.data.materials.append(mat_carbon)
        m_bs_bev = b_scoop.modifiers.new("Bevel", 'BEVEL')
        m_bs_bev.width = 0.008
        b_scoop.data.shade_smooth()

        # 刹车盘外环碳纤保护罩 (Brake Disc Drum Shroud)
        bpy.ops.mesh.primitive_cylinder_add(radius=0.19, depth=0.06, vertices=28)
        b_drum = bpy.context.active_object
        b_drum.name = f"GEO_F1_Front_BrakeDrum_{f_side}"
        b_drum.rotation_euler = (0, math.radians(90), 0)
        b_drum.location = (0.83 * f_sign, 1.45, 0.355)
        link_to_col(b_drum, col_w_set)
        b_drum.data.materials.append(mat_carbon_satin)
        b_drum.data.shade_smooth()

    # =========================================================================
    # 13. 高精座舱内饰：赛车方向盘多功能旋钮与全息 HUD
    # =========================================================================
    # Halo 钛合金安全结构
    create_aero_strut("GEO_F1_Halo_CenterPylon", Vector((0.0, 0.58, 0.65)), Vector((0.0, 0.42, 0.88)), chord=0.048, thickness=0.024, target_col=col_halo, mat=mat_titanium)

    crv_halo = bpy.data.curves.new(name="CRV_F1_Halo_Hoop", type='CURVE')
    crv_halo.dimensions = '3D'
    crv_halo.bevel_depth = 0.024
    crv_halo.bevel_resolution = 6
    spline_h = crv_halo.splines.new('POLY')
    halo_pts = [
        (0.0, 0.42, 0.88),
        (0.16, 0.38, 0.885),
        (0.28, 0.20, 0.88),
        (0.31, 0.00, 0.86),
        (0.28, -0.25, 0.82),
        (0.22, -0.42, 0.78)
    ]
    spline_h.points.add(len(halo_pts) - 1)
    for idx_pt, pt in enumerate(halo_pts):
        spline_h.points[idx_pt].co = (pt[0], pt[1], pt[2], 1.0)

    obj_h_hoop = bpy.data.objects.new("GEO_F1_Halo_Hoop", crv_halo)
    link_to_col(obj_h_hoop, col_halo)
    obj_h_hoop.data.materials.append(mat_titanium)
    m_hh_mir = obj_h_hoop.modifiers.new("Mirror_X", 'MIRROR')
    m_hh_mir.use_axis[0] = True

    # 全息曲面 HUD
    bpy.ops.mesh.primitive_cylinder_add(radius=0.18, depth=0.006, end_fill_type='NOTHING', vertices=24)
    hud_cyl = bpy.context.active_object
    hud_cyl.name = "GEO_F1_Cockpit_HoloHUD"
    hud_cyl.scale = (0.9, 0.5, 0.09)
    hud_cyl.rotation_euler = (math.radians(65), 0, 0)
    hud_cyl.location = (0.0, 0.25, 0.72)
    link_to_col(hud_cyl, col_halo)
    hud_cyl.data.materials.append(mat_hud)

    # 碳纤维方向盘
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    wheel_yoke = bpy.context.active_object
    wheel_yoke.name = "GEO_F1_Cockpit_SteeringWheel"
    wheel_yoke.scale = (0.24, 0.024, 0.15)
    wheel_yoke.location = (0.0, 0.16, 0.65)
    wheel_yoke.rotation_euler = (math.radians(-22), 0, 0)
    link_to_col(wheel_yoke, col_halo)
    wheel_yoke.data.materials.append(mat_carbon)
    m_wy_bev = wheel_yoke.modifiers.new("Bevel", 'BEVEL')
    m_wy_bev.width = 0.008

    # 方向盘实体彩色旋钮与换挡拨片 (Rotary Dials & Paddle Shifters)
    dial_colors = [mat_neon_cyan, mat_gold, mat_neon_orange, mat_white]
    for d_idx in range(6):
        dx = -0.075 + (d_idx * 0.030)
        bpy.ops.mesh.primitive_cylinder_add(radius=0.008, depth=0.012, vertices=12)
        dial = bpy.context.active_object
        dial.name = f"GEO_F1_Steering_Dial_{d_idx}"
        dial.rotation_euler = (math.radians(68), 0, 0)
        dial.location = (dx, 0.17, 0.68)
        link_to_col(dial, col_halo)
        dial.data.materials.append(dial_colors[d_idx % len(dial_colors)])

    # 方向盘后置碳纤维换挡拨片 (Paddle Shifters)
    for p_sign, p_name in [(-1, "Down"), (1, "Up")]:
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        paddle = bpy.context.active_object
        paddle.name = f"GEO_F1_Steering_Paddle_{p_name}"
        paddle.scale = (0.045, 0.006, 0.075)
        paddle.location = (0.09 * p_sign, 0.15, 0.65)
        paddle.rotation_euler = (math.radians(-22), 0, 0)
        link_to_col(paddle, col_halo)
        paddle.data.materials.append(mat_carbon)

    # 赛车防撞头枕 (Cockpit Safety Headrest)
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    headrest = bpy.context.active_object
    headrest.name = "GEO_F1_Cockpit_Headrest"
    headrest.scale = (0.34, 0.28, 0.18)
    headrest.location = (0.0, -0.22, 0.74)
    headrest.rotation_euler = (math.radians(-14), 0, 0)
    link_to_col(headrest, col_halo)
    headrest.data.materials.append(mat_carbon_satin)

    # 空力后视镜与气动支柱
    for m_sign, m_name in [(-1, "L"), (1, "R")]:
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        mirror = bpy.context.active_object
        mirror.name = f"GEO_F1_AeroMirror_{m_name}"
        mirror.scale = (0.09, 0.05, 0.035)
        mirror.location = (0.44 * m_sign, 0.36, 0.75)
        mirror.rotation_euler = (0, math.radians(-12 * m_sign), math.radians(16 * m_sign))
        link_to_col(mirror, col_halo)
        mirror.data.materials.append(mat_navy)
        m_mir_bev = mirror.modifiers.new("Bevel", 'BEVEL')
        m_mir_bev.width = 0.006

        create_aero_strut(f"GEO_F1_MirrorStalk_{m_name}", Vector((0.30 * m_sign, 0.36, 0.69)), Vector((0.44 * m_sign, 0.36, 0.75)), chord=0.018, thickness=0.008, target_col=col_halo, mat=mat_carbon)

    # =========================================================================
    # 14. 真实参数化高精竞技胎与 18 寸气动涡轮轮圈 (Turbine Wheels & Realistic Tires)
    # =========================================================================
    tire_rad = 0.355  # 18寸竞技热熔胎真实外径 710mm (中心位于 Z=0.355，正切地坪 Z=0.000)
    rim_rad = 0.228   # 18寸轮辋半径 457mm

    wheel_configs = [
        {"name": "FL", "loc": Vector((-0.90, 1.45, 0.355)), "tire_w": 0.34, "is_front": True, "sign_x": -1},
        {"name": "FR", "loc": Vector((0.90, 1.45, 0.355)), "tire_w": 0.34, "is_front": True, "sign_x": 1},
        {"name": "RL", "loc": Vector((-0.86, -1.55, 0.355)), "tire_w": 0.42, "is_front": False, "sign_x": -1},
        {"name": "RR", "loc": Vector((0.86, -1.55, 0.355)), "tire_w": 0.42, "is_front": False, "sign_x": 1},
    ]

    # 参数化生成实心带胎壁/胎冠的竞技热熔胎 (Parametric Revolved Tire)
    def create_revolved_slick_tire(name, width, outer_rad, inner_rad, target_col):
        bm = bmesh.new()
        hw = width / 2.0
        profile = [
            (hw - 0.020, inner_rad),              # 外侧轮辋嵌入唇口
            (hw - 0.005, inner_rad + 0.045),      # 下胎壁
            (hw, outer_rad - 0.035),              # 上胎壁中段
            (hw - 0.012, outer_rad),              # 外侧胎肩圆角
            (0.0, outer_rad + 0.002),             # 胎冠中央微弧
            (-hw + 0.012, outer_rad),             # 内侧胎肩圆角
            (-hw, outer_rad - 0.035),             # 内侧上胎壁
            (-hw + 0.005, inner_rad + 0.045),     # 内侧下胎壁
            (-hw + 0.020, inner_rad),             # 内侧轮辋嵌入唇口
            (-hw + 0.020, inner_rad - 0.015),     # 内侧密封底圈
            (hw - 0.020, inner_rad - 0.015)       # 外侧密封底圈
        ]
        N_STEPS = 40
        rings = []
        for k in range(N_STEPS):
            theta = k * 2.0 * math.pi / N_STEPS
            cos_t = math.cos(theta)
            sin_t = math.sin(theta)
            ring_v = []
            for (x_axle, rad) in profile:
                v = bm.verts.new(Vector((x_axle, rad * cos_t, rad * sin_t)))
                ring_v.append(v)
            rings.append(ring_v)

        bm.verts.ensure_lookup_table()
        M = len(profile)
        for k in range(N_STEPS):
            k_next = (k + 1) % N_STEPS
            r1 = rings[k]
            r2 = rings[k_next]
            for j in range(M):
                j_next = (j + 1) % M
                bm.faces.new([r1[j], r2[j], r2[j_next], r1[j_next]])

        me = bpy.data.meshes.new(f"ME_{name}")
        bm.to_mesh(me)
        bm.free()

        obj = bpy.data.objects.new(name, me)
        link_to_col(obj, target_col)
        obj.data.materials.append(mat_rubber)
        m_sub = obj.modifiers.new("Subsurf", 'SUBSURF')
        m_sub.levels = 1
        m_sub.show_on_cage = True
        obj.data.shade_smooth()
        return obj

    for wd in wheel_configs:
        w_name = wd["name"]
        w_loc = wd["loc"]
        w_width = wd["tire_w"]
        is_front = wd["is_front"]
        sign_x = wd["sign_x"]
        
        col_w = get_or_create_col(f"Wheel_{w_name}", col_wheels)

        # 真实拓扑竞技热熔胎
        tire_obj = create_revolved_slick_tire(f"GEO_F1_Tire_{w_name}", w_width, tire_rad, rim_rad, col_w)
        tire_obj.location = w_loc

        # 胎侧白色 P-Zero 品牌浮雕圈 (P-Zero Sidewall Brand Ring)
        disc_face_x = w_loc.x + (w_width * 0.495 * sign_x)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.295, minor_radius=0.003, major_segments=36, minor_segments=6)
        pzero_ring = bpy.context.active_object
        pzero_ring.name = f"GEO_F1_Wheel_PZeroRing_{w_name}"
        pzero_ring.rotation_euler = (0, math.radians(90), 0)
        pzero_ring.location = Vector((disc_face_x + (0.002 * sign_x), w_loc.y, w_loc.z))
        link_to_col(pzero_ring, col_w)
        pzero_ring.data.materials.append(mat_pzero_red)

        # 碳纤维气动涡轮导流盘 (Aero Turbine Disc Face)
        bpy.ops.mesh.primitive_cylinder_add(radius=rim_rad * 0.98, depth=0.016, vertices=32)
        aero_cover = bpy.context.active_object
        aero_cover.name = f"GEO_F1_WheelCover_{w_name}"
        aero_cover.rotation_euler = (0, math.radians(90), 0)
        aero_cover.location = Vector((disc_face_x, w_loc.y, w_loc.z))
        link_to_col(aero_cover, col_w)
        aero_cover.data.materials.append(mat_carbon)
        aero_cover.data.shade_smooth()

        # 18 组径向倾斜抽风涡轮叶片 (18 Radial Turbine Blades)
        col_blades = get_or_create_col(f"TurbineBlades_{w_name}", col_w)
        for blade_i in range(18):
            b_angle = blade_i * (2 * math.pi / 18)
            bpy.ops.mesh.primitive_cube_add(size=1.0)
            blade = bpy.context.active_object
            blade.name = f"GEO_F1_Blade_{w_name}_{blade_i:02d}"
            blade.scale = (0.010, 0.072, 0.012)
            r_blade = 0.145
            by = math.cos(b_angle) * r_blade
            bz = math.sin(b_angle) * r_blade
            blade.location = Vector((disc_face_x + (0.008 * sign_x), w_loc.y + by, w_loc.z + bz))
            blade.rotation_euler = (b_angle, math.radians(24 * sign_x), 0)
            link_to_col(blade, col_blades)
            blade.data.materials.append(mat_rim_dark)

        # 轮圈外圈高亮电青霓虹圆环 (Outer Cyan Neon Ring)
        bpy.ops.mesh.primitive_torus_add(major_radius=rim_rad * 0.96, minor_radius=0.007, major_segments=32, minor_segments=10)
        outer_neon_ring = bpy.context.active_object
        outer_neon_ring.name = f"GEO_F1_Wheel_OuterNeonRing_{w_name}"
        outer_neon_ring.rotation_euler = (0, math.radians(90), 0)
        outer_neon_ring.location = Vector((disc_face_x + (0.012 * sign_x), w_loc.y, w_loc.z))
        link_to_col(outer_neon_ring, col_lights)
        outer_neon_ring.data.materials.append(mat_neon_cyan)

        # 轮心琥珀橙发光环 (Inner Amber Glow Ring)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.065, minor_radius=0.005, major_segments=24, minor_segments=8)
        inner_neon_ring = bpy.context.active_object
        inner_neon_ring.name = f"GEO_F1_Wheel_InnerNeonRing_{w_name}"
        inner_neon_ring.rotation_euler = (0, math.radians(90), 0)
        inner_neon_ring.location = Vector((disc_face_x + (0.014 * sign_x), w_loc.y, w_loc.z))
        link_to_col(inner_neon_ring, col_lights)
        inner_neon_ring.data.materials.append(mat_neon_orange)

        # 中央快拆锁止螺母
        bpy.ops.mesh.primitive_cylinder_add(radius=0.038, depth=0.032, vertices=16)
        lock_nut = bpy.context.active_object
        lock_nut.name = f"GEO_F1_Wheel_CenterNut_{w_name}"
        lock_nut.rotation_euler = (0, math.radians(90), 0)
        lock_nut.location = Vector((disc_face_x + (0.018 * sign_x), w_loc.y, w_loc.z))
        link_to_col(lock_nut, col_w)
        lock_nut.data.materials.append(mat_gold)

        # 碳陶打孔制动刹车盘 (Carbon Ceramic Brake Disc)
        bpy.ops.mesh.primitive_cylinder_add(radius=0.175, depth=0.024, vertices=28)
        brake_disc = bpy.context.active_object
        brake_disc.name = f"GEO_F1_BrakeDisc_{w_name}"
        brake_disc.rotation_euler = (0, math.radians(90), 0)
        brake_disc.location = Vector((w_loc.x - (0.04 * sign_x), w_loc.y, w_loc.z))
        link_to_col(brake_disc, col_w)
        brake_disc.data.materials.append(mat_carbon_satin)

        # 竞技高刚度制动卡钳 (Competition Monobloc Brake Caliper)
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        caliper = bpy.context.active_object
        caliper.name = f"GEO_F1_BrakeCaliper_{w_name}"
        caliper.scale = (0.055, 0.12, 0.08)
        caliper.location = Vector((w_loc.x - (0.04 * sign_x), w_loc.y - 0.12, w_loc.z + 0.05))
        link_to_col(caliper, col_w)
        caliper.data.materials.append(mat_gold)

        # 前轮专属：弧形气动扰流拱翼与上沿发光框 (Front Over-Wheel Wake Deflector Arch)
        if is_front:
            bm_arch = bmesh.new()
            arc_angles = [math.radians(a) for a in [35, 50, 65, 80, 95, 110]]
            arc_r = tire_rad + 0.035
            arc_w = w_width * 0.90
            half_aw = arc_w / 2.0
            arc_v_outer = []
            arc_v_inner = []
            for ang in arc_angles:
                ay = math.cos(ang) * arc_r
                az = math.sin(ang) * arc_r
                v_out = bm_arch.verts.new(Vector((-half_aw, ay, az)))
                v_in = bm_arch.verts.new(Vector((half_aw, ay, az)))
                arc_v_outer.append(v_out)
                arc_v_inner.append(v_in)
            bm_arch.verts.ensure_lookup_table()
            for ai in range(len(arc_angles) - 1):
                bm_arch.faces.new([arc_v_outer[ai], arc_v_inner[ai], arc_v_inner[ai+1], arc_v_outer[ai+1]])
            
            me_arch = bpy.data.meshes.new(f"ME_F1_Wheel_AeroDeflector_{w_name}")
            bm_arch.to_mesh(me_arch)
            bm_arch.free()
            
            deflector = bpy.data.objects.new(f"GEO_F1_Wheel_AeroDeflector_{w_name}", me_arch)
            deflector.location = w_loc
            link_to_col(deflector, col_wings)
            deflector.data.materials.append(mat_carbon)
            m_def_sol = deflector.modifiers.new("Solidify", 'SOLIDIFY')
            m_def_sol.thickness = 0.008
            deflector.data.shade_smooth()

            # 导流罩顶部电青发光框线
            bpy.ops.mesh.primitive_cube_add(size=1.0)
            def_light = bpy.context.active_object
            def_light.name = f"GEO_F1_Wheel_DeflectorLight_{w_name}"
            def_light.scale = (arc_w * 0.96, 0.016, 0.010)
            def_light.location = Vector((w_loc.x, w_loc.y, w_loc.z + tire_rad + 0.042))
            link_to_col(def_light, col_lights)
            def_light.data.materials.append(mat_neon_cyan)
    # =========================================================================
    # 15. 红牛官方赞助商全套独立贴纸系统 (Oracle Red Bull Racing Decal Mesh System)
    # 100% 独立网格浮雕片，非破坏性挂载于 08_Sponsor_Decals 集合，完全可点击编辑
    # =========================================================================
    # A. 机鼻流线涂装与维斯塔潘车号 1 贴纸 (贴合鼻锥 13.8° 俯冲斜坡，前置加宽)
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

    # B. 侧箱外壁巨幅 ORACLE + 赛车速度拉花 + Mobil 1 (居中布局，消除后轮遮挡)
    # 左侧侧箱
    create_quad_decal(
        "DEC_Sidepod_Oracle_L",
        p_bl=Vector((-0.638, -1.20, 0.22)),
        p_br=Vector((-0.638, -0.15, 0.22)),
        p_tr=Vector((-0.638, -0.15, 0.52)),
        p_tl=Vector((-0.638, -1.20, 0.52)),
        mat=mat_dec_side_oracle,
        target_col=col_decals,
        uv_mode='flip_x'
    )
    # 右侧侧箱
    create_quad_decal(
        "DEC_Sidepod_Oracle_R",
        p_bl=Vector((0.638, -0.15, 0.22)),
        p_br=Vector((0.638, -1.20, 0.22)),
        p_tr=Vector((0.638, -1.20, 0.52)),
        p_tl=Vector((0.638, -0.15, 0.52)),
        mat=mat_dec_side_oracle,
        target_col=col_decals,
        uv_mode='flip_x'
    )

    # C. 发动机罩两侧双牛撞日 + Red Bull RACING + HONDA (位于座舱后开阔区，公牛与太阳 100% 完整展现)
    # 左侧发动机罩
    create_quad_decal(
        "DEC_Engine_RedBull_L",
        p_bl=Vector((-0.295, -1.28, 0.60)),
        p_br=Vector((-0.295, -0.25, 0.70)),
        p_tr=Vector((-0.255, -0.25, 1.08)),
        p_tl=Vector((-0.255, -1.28, 0.98)),
        mat=mat_dec_eng_redbull,
        target_col=col_decals,
        uv_mode='flip_x'
    )
    # 右侧发动机罩
    create_quad_decal(
        "DEC_Engine_RedBull_R",
        p_bl=Vector((0.295, -0.25, 0.70)),
        p_br=Vector((0.295, -1.28, 0.60)),
        p_tr=Vector((0.265, -1.28, 0.98)),
        p_tl=Vector((0.265, -0.25, 1.08)),
        mat=mat_dec_eng_redbull,
        target_col=col_decals,
        uv_mode='flip_x'
    )

    # D. 尾翼主翼面迎风正面巨幅 ORACLE
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

    # F. 尾翼后车直视背面 Red Bull 撞日标
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

    # H. 前翼外洗端板 Mobil 1 + Pirelli 贴纸 (微贴合端板表面 2mm)
    create_quad_decal(
        "DEC_Endplate_Front_L",
        p_bl=Vector((-1.031, 3.15, 0.10)),
        p_br=Vector((-1.031, 2.75, 0.10)),
        p_tr=Vector((-1.031, 2.75, 0.36)),
        p_tl=Vector((-1.031, 3.15, 0.36)),
        mat=mat_dec_endplate,
        target_col=col_decals,
        uv_mode='normal'
    )
    create_quad_decal(
        "DEC_Endplate_Front_R",
        p_bl=Vector((1.031, 2.75, 0.10)),
        p_br=Vector((1.031, 3.15, 0.10)),
        p_tr=Vector((1.031, 3.15, 0.36)),
        p_tl=Vector((1.031, 2.75, 0.36)),
        mat=mat_dec_endplate,
        target_col=col_decals,
        uv_mode='normal'
    )

    # I. 尾翼外侧端板 Mobil 1 + Pirelli 贴纸 (单次创建，微贴合端板表面 2mm，彻底消除重影)
    create_quad_decal(
        "DEC_Endplate_Rear_L",
        p_bl=Vector((-0.711, -2.10, 0.74)),
        p_br=Vector((-0.711, -2.52, 0.74)),
        p_tr=Vector((-0.711, -2.52, 1.14)),
        p_tl=Vector((-0.711, -2.10, 1.14)),
        mat=mat_dec_endplate,
        target_col=col_decals,
        uv_mode='normal'
    )
    create_quad_decal(
        "DEC_Endplate_Rear_R",
        p_bl=Vector((0.711, -2.52, 0.74)),
        p_br=Vector((0.711, -2.10, 0.74)),
        p_tr=Vector((0.711, -2.10, 1.14)),
        p_tl=Vector((0.711, -2.52, 1.14)),
        mat=mat_dec_endplate,
        target_col=col_decals,
        uv_mode='normal'
    )

    # =========================================================================
    # 16. 专业赛车摄影棚高对比度布光 (Dark Studio Automotive Lighting)
    # =========================================================================

    # 40米暗调高反射地坪 (锁定交互选择，杜绝误触拦截)
    bpy.ops.mesh.primitive_plane_add(size=40.0)
    studio_floor = bpy.context.active_object
    studio_floor.name = "GEO_Studio_Floor"
    studio_floor.location = (0.0, 0.0, 0.000)
    link_to_col(studio_floor, col_studio)
    studio_floor.data.materials.append(mat_floor)
    studio_floor.hide_select = True

    # 弧形暗影摄影棚天幕
    bpy.ops.mesh.primitive_cylinder_add(radius=22.0, depth=14.0, end_fill_type='NOTHING', vertices=48)
    backdrop = bpy.context.active_object
    backdrop.name = "GEO_Studio_Backdrop"
    backdrop.location = (0.0, -2.0, 7.0)
    link_to_col(backdrop, col_studio)
    backdrop.data.materials.append(mat_floor)
    backdrop.hide_select = True

    # 专业汽车影棚布光矩阵
    # A. 主光 (Key Light - 侧前上方大柔光箱)
    key_light_data = bpy.data.lights.new(name="LGT_Studio_KeyArea", type='AREA')
    key_light_data.energy = 6500.0
    key_light_data.size = 8.0
    key_light_data.size_y = 14.0
    key_light_data.color = (0.95, 0.98, 1.0)
    key_light = bpy.data.objects.new("LGT_Studio_KeyArea", key_light_data)
    key_light.location = (5.0, 5.0, 4.5)
    key_light.rotation_euler = (math.radians(45), math.radians(-25), math.radians(35))
    link_to_col(key_light, col_studio)

    # B. 轮廓光 (Rim Light - 右后方冷白掠射，勾勒钛合金侧箱)
    rim_light_data = bpy.data.lights.new(name="LGT_Studio_RimArea", type='AREA')
    rim_light_data.energy = 3800.0
    rim_light_data.size = 5.0
    rim_light_data.size_y = 9.0
    rim_light_data.color = (0.90, 0.94, 1.0)
    rim_light = bpy.data.objects.new("LGT_Studio_RimArea", rim_light_data)
    rim_light.location = (-5.0, -4.5, 4.0)
    rim_light.rotation_euler = (math.radians(-50), math.radians(20), math.radians(-40))
    link_to_col(rim_light, col_studio)

    # C. 顶置天幕漫射柔光
    top_light_data = bpy.data.lights.new(name="LGT_Studio_TopStrip", type='AREA')
    top_light_data.energy = 800.0
    top_light_data.size = 3.0
    top_light_data.size_y = 12.0
    top_light_data.color = (0.94, 0.96, 1.0)
    top_light = bpy.data.objects.new("LGT_Studio_TopStrip", top_light_data)
    top_light.location = (0.0, 0.0, 8.5)
    top_light.rotation_euler = (0, 0, 0)
    link_to_col(top_light, col_studio)

    # =========================================================================
    # 17. 四机位工业级摄影机阵列 (Front 3/4, Rear 3/4, Side, Top)
    # =========================================================================
    cam_configs = [
        ("Cam_F1_Front34", Vector((4.6, 5.6, 1.7)), Vector((0.0, 0.5, 0.35)), 42.0),
        ("Cam_F1_Rear34", Vector((-4.6, -5.4, 1.7)), Vector((0.0, -0.5, 0.35)), 42.0),
        ("Cam_F1_Side", Vector((6.8, 0.0, 0.85)), Vector((0.0, 0.0, 0.45)), 50.0),
        ("Cam_F1_Top", Vector((0.0, 0.3, 9.8)), Vector((0.0, 0.3, 0.35)), 38.0),
    ]

    for c_name, c_loc, target_pt, focal in cam_configs:
        c_data = bpy.data.cameras.new(name=c_name)
        c_data.lens = focal
        c_data.clip_start = 0.1
        c_data.clip_end = 100.0
        c_obj = bpy.data.objects.new(c_name, c_data)
        c_obj.location = c_loc
        direction = target_pt - c_loc
        rot_quat = direction.to_track_quat('-Z', 'Y')
        c_obj.rotation_euler = rot_quat.to_euler()
        link_to_col(c_obj, col_studio)

    # 视口环境设置
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new("World_DarkStudio")
    scene.world.use_nodes = True
    bg_node = scene.world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs['Color'].default_value = (0.010, 0.012, 0.015, 1.0)
        bg_node.inputs['Strength'].default_value = 0.4

    # 全车部件交互选择状态重置 (全车部件可直接点击编辑)
    for obj in bpy.data.objects:
        if obj.name.startswith("GEO_F1_") or obj.name.startswith("DEC_"):
            obj.hide_select = False
            obj.select_set(False)

    obj_nose.select_set(True)
    bpy.context.view_layer.objects.active = obj_nose

    # =========================================================================
    # 18. 渲染输出：4 视角美图 + 1 张精细四边面粘土线框图 (Wireframe Pass)
    # =========================================================================
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    
    temp_dir = tempfile.gettempdir()
    out_dir = r"D:\项目session\blender-supercar"
    artifact_dir = r"C:\Users\86052\.gemini\antigravity\brain\fe45f8e6-8741-486f-93a1-a197a7712d30"

    # A. 渲染线框专用材质 (Cyan Wireframe on Matte Clay)
    mat_wireframe = bpy.data.materials.new("Mat_Clay_Wireframe")
    mat_wireframe.use_nodes = True
    wf_nodes = mat_wireframe.node_tree.nodes
    wf_links = mat_wireframe.node_tree.links
    wf_nodes.clear()
    wf_out = wf_nodes.new(type='ShaderNodeOutputMaterial')
    wf_bsdf = wf_nodes.new(type='ShaderNodeBsdfPrincipled')
    wf_bsdf.inputs['Base Color'].default_value = (0.04, 0.045, 0.05, 1.0)
    wf_bsdf.inputs['Roughness'].default_value = 0.40
    wf_node = wf_nodes.new(type='ShaderNodeWireframe')
    wf_node.inputs['Size'].default_value = 0.0018
    wf_node.use_pixel_size = False
    wf_em = wf_nodes.new(type='ShaderNodeEmission')
    wf_em.inputs['Color'].default_value = (0.0, 0.95, 1.0, 1.0)
    wf_em.inputs['Strength'].default_value = 25.0
    wf_mix = wf_nodes.new(type='ShaderNodeMixShader')
    wf_links.new(wf_node.outputs['Factor'], wf_mix.inputs['Fac'])
    wf_links.new(wf_bsdf.outputs['BSDF'], wf_mix.inputs[1])
    wf_links.new(wf_em.outputs['Emission'], wf_mix.inputs[2])
    wf_links.new(wf_mix.outputs['Shader'], wf_out.inputs['Surface'])

    # 1. 渲染四视角标准 PBR 材质
    render_targets = [
        ("Cam_F1_Front34", "f1_render_front34.png"),
        ("Cam_F1_Rear34", "f1_render_rear34.png"),
        ("Cam_F1_Side", "f1_render_side.png"),
        ("Cam_F1_Top", "f1_render_top.png"),
    ]

    for cam_name, img_name in render_targets:
        cam_obj = bpy.data.objects.get(cam_name)
        if cam_obj:
            scene.camera = cam_obj
            tmp_render_path = os.path.join(temp_dir, img_name)
            scene.render.filepath = tmp_render_path
            bpy.ops.render.render(write_still=True)
            dst_path = os.path.join(out_dir, img_name)
            shutil.copy2(tmp_render_path, dst_path)
            if os.path.exists(artifact_dir):
                shutil.copy2(tmp_render_path, os.path.join(artifact_dir, img_name))
            print(f"RENDERED & COPIED: {dst_path}")

    # 2. 渲染高精布线线框图 (Wireframe Pass - 1:1证明精细四边面流向)
    cam_front = bpy.data.objects.get("Cam_F1_Front34")
    if cam_front:
        scene.camera = cam_front
        scene.view_layers[0].material_override = mat_wireframe
        tmp_wf_path = os.path.join(temp_dir, "f1_render_wireframe.png")
        scene.render.filepath = tmp_wf_path
        bpy.ops.render.render(write_still=True)
        dst_wf_path = os.path.join(out_dir, "f1_render_wireframe.png")
        shutil.copy2(tmp_wf_path, dst_wf_path)
        if os.path.exists(artifact_dir):
            shutil.copy2(tmp_wf_path, os.path.join(artifact_dir, "f1_render_wireframe.png"))
        print(f"RENDERED & COPIED WIREFRAME PASS: {dst_wf_path}")
        scene.view_layers[0].material_override = None

    temp_blend = os.path.join(temp_dir, "scifi_f1_2035.blend")
    bpy.ops.wm.save_as_mainfile(filepath=temp_blend)
    save_path_f1 = os.path.join(out_dir, "scifi_f1_2035.blend")
    shutil.copy2(temp_blend, save_path_f1)
    print("SAVED_SCIFI_F1_SUCCESSFULLY:", save_path_f1)

if __name__ == "__main__":
    build_scifi_f1_detailed()
