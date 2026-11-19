import bpy
import bmesh
import math
from mathutils import Vector, Matrix
import os

def build_supercar_v3_perfect():
    # 1. 彻底清空现有场景
    bpy.ops.object.select_all(action='SELECT')
    for obj in bpy.context.scene.objects:
        if obj.type in ('MESH', 'CURVE', 'LIGHT', 'CAMERA'):
            bpy.data.objects.remove(obj, do_unlink=True)
            
    # 2. 顶层集合架构
    def get_or_create_col(name, parent=None):
        col = bpy.data.collections.get(name)
        if not col:
            col = bpy.data.collections.new(name)
            (parent or bpy.context.scene.collection).children.link(col)
        return col

    def link_to_col(obj, target_col):
        for c in list(obj.users_collection):
            c.objects.unlink(obj)
        target_col.objects.link(obj)

    root_col = get_or_create_col("SUPERCAR_GT_V3")
    col_body = get_or_create_col("01_Body_Panels", root_col)
    col_glass = get_or_create_col("02_Glass_Canopy", root_col)
    col_aero = get_or_create_col("03_Aero_Kit", root_col)
    col_wheels = get_or_create_col("04_Wheels_Brakes", root_col)
    col_lights = get_or_create_col("05_Lighting", root_col)
    col_interior = get_or_create_col("06_Interior", root_col)
    col_studio = get_or_create_col("07_Studio_Rig", root_col)

    # 3. 材质库
    def create_pbr_material(name, color, metallic=0.0, roughness=0.5, transmission=0.0, emission=None, clearcoat=0.0):
        mat = bpy.data.materials.get(name)
        if not mat:
            mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()
        
        output = nodes.new(type='ShaderNodeOutputMaterial')
        output.location = (300, 0)
        
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
            if 'Transmission Weight' in sh.inputs:
                sh.inputs['Transmission Weight'].default_value = transmission
            elif 'Transmission' in sh.inputs:
                sh.inputs['Transmission'].default_value = transmission
            if 'Coat Weight' in sh.inputs:
                sh.inputs['Coat Weight'].default_value = clearcoat
                if 'Coat Roughness' in sh.inputs:
                    sh.inputs['Coat Roughness'].default_value = 0.05
            elif 'Clearcoat' in sh.inputs:
                sh.inputs['Clearcoat'].default_value = clearcoat
            sh.inputs['IOR'].default_value = 1.5
            links.new(sh.outputs['BSDF'], output.inputs['Surface'])
        return mat

    mat_paint = create_pbr_material("Mat_Liquid_Titanium", (0.08, 0.09, 0.11, 1.0), metallic=0.96, roughness=0.18, clearcoat=1.0)
    mat_carbon = create_pbr_material("Mat_Gloss_Carbon", (0.015, 0.015, 0.015, 1.0), metallic=0.4, roughness=0.22, clearcoat=0.9)
    mat_glass = create_pbr_material("Mat_Smoked_Canopy", (0.03, 0.04, 0.06, 1.0), metallic=0.1, roughness=0.03, transmission=0.92)
    mat_tire = create_pbr_material("Mat_Tire_Rubber", (0.02, 0.02, 0.02, 1.0), metallic=0.0, roughness=0.85)
    mat_rim = create_pbr_material("Mat_Forged_Silver", (0.85, 0.86, 0.88, 1.0), metallic=0.98, roughness=0.12)
    mat_caliper = create_pbr_material("Mat_Brembo_Gold", (0.95, 0.72, 0.05, 1.0), metallic=0.9, roughness=0.2)
    mat_disc = create_pbr_material("Mat_Ceramic_Disc", (0.38, 0.38, 0.40, 1.0), metallic=0.85, roughness=0.32)
    mat_exhaust = create_pbr_material("Mat_Titanium_Exhaust", (0.32, 0.38, 0.45, 1.0), metallic=0.95, roughness=0.28)
    mat_headlight = create_pbr_material("Mat_LED_Blade_IceBlue", None, emission=((0.65, 0.88, 1.0, 1.0), 30.0))
    mat_taillight = create_pbr_material("Mat_OLED_Strip_Crimson", None, emission=((1.0, 0.03, 0.015, 1.0), 35.0))
    mat_interior = create_pbr_material("Mat_Dark_Alcantara", (0.025, 0.025, 0.03, 1.0), metallic=0.0, roughness=0.92)
    mat_floor = create_pbr_material("Mat_Studio_Floor", (0.24, 0.25, 0.27, 1.0), metallic=0.1, roughness=0.45)

    # 4. 核心建模：流线型车身
    bm = bmesh.new()
    sections = [
        # 0: 车鼻尖 (Nose Tip)
        [(0.0, 2.38, 0.28), (0.28, 2.32, 0.30), (0.64, 2.20, 0.28), (0.68, 2.14, 0.16)],
        # 1: 前机盖与散热下压面 (Hood Front)
        [(0.0, 1.95, 0.42), (0.38, 1.92, 0.44), (0.86, 1.80, 0.46), (0.84, 1.75, 0.18)],
        # 2: 前轮拱顶点 (Front Wheel Arch Peak)
        [(0.0, 1.35, 0.56), (0.40, 1.35, 0.58), (0.92, 1.32, 0.68), (0.90, 1.32, 0.38)],
        # 3: 前挡风底沿 (Windshield Base)
        [(0.0, 0.75, 0.72), (0.40, 0.72, 0.74), (0.85, 0.68, 0.62), (0.86, 0.68, 0.18)],
        # 4: 驾驶舱车顶 (Roof Peak)
        [(0.0, -0.05, 1.18), (0.35, -0.05, 1.16), (0.78, -0.05, 0.66), (0.85, -0.05, 0.16)],
        # 5: 侧箱收腰与引擎舱前端 (Side Pod / Intake Base)
        [(0.0, -0.85, 0.96), (0.38, -0.85, 0.92), (0.85, -0.85, 0.74), (0.88, -0.85, 0.16)],
        # 6: 后轮拱肌肉隆起 (Rear Haunch Peak)
        [(0.0, -1.45, 0.82), (0.40, -1.45, 0.80), (0.96, -1.40, 0.82), (0.92, -1.40, 0.38)],
        # 7: 车尾鸭尾 (Rear Kammback Tail)
        [(0.0, -2.26, 0.74), (0.35, -2.26, 0.72), (0.80, -2.22, 0.66), (0.78, -2.20, 0.26)]
    ]

    vert_grid = []
    for s in sections:
        vert_grid.append([bm.verts.new(pt) for pt in s])
    bm.verts.ensure_lookup_table()

    for i in range(len(sections) - 1):
        for j in range(3):
            v1 = vert_grid[i][j]
            v2 = vert_grid[i][j+1]
            v3 = vert_grid[i+1][j+1]
            v4 = vert_grid[i+1][j]
            bm.faces.new([v1, v2, v3, v4])

    mesh_body = bpy.data.meshes.new("ME_Body_MainShell")
    bm.to_mesh(mesh_body)
    bm.free()

    obj_body = bpy.data.objects.new("GEO_Body_MainShell", mesh_body)
    link_to_col(obj_body, col_body)
    obj_body.data.materials.append(mat_paint)

    # 关键修改器：启用 show_on_cage，保证编辑模式点线直接贴在细分表面上
    m_mirror = obj_body.modifiers.new("Mirror_X", 'MIRROR')
    m_mirror.use_axis[0] = True
    m_mirror.use_clip = True
    m_mirror.show_on_cage = True
    m_mirror.show_in_editmode = True

    m_sol = obj_body.modifiers.new("Solidify", 'SOLIDIFY')
    m_sol.thickness = -0.012
    m_sol.offset = -1.0
    m_sol.show_on_cage = True
    m_sol.show_in_editmode = True

    m_sub = obj_body.modifiers.new("Subsurf", 'SUBSURF')
    m_sub.levels = 2
    m_sub.render_levels = 2
    m_sub.show_on_cage = True
    m_sub.show_in_editmode = True
    obj_body.data.shade_smooth()

    # 5. 环形全景玻璃座舱
    bm_glass = bmesh.new()
    g_sections = [
        [(0.0, 0.74, 0.73), (0.38, 0.71, 0.75)],
        [(0.0, 0.35, 1.02), (0.36, 0.34, 1.01)],
        [(0.0, -0.05, 1.19), (0.34, -0.05, 1.17)],
        [(0.0, -0.45, 1.08), (0.35, -0.45, 1.06)],
        [(0.0, -0.84, 0.97), (0.37, -0.84, 0.93)]
    ]
    g_grid = []
    for s in g_sections:
        g_grid.append([bm_glass.verts.new(pt) for pt in s])
    bm_glass.verts.ensure_lookup_table()
    for i in range(len(g_sections) - 1):
        bm_glass.faces.new([g_grid[i][0], g_grid[i][1], g_grid[i+1][1], g_grid[i+1][0]])

    mesh_glass = bpy.data.meshes.new("ME_Glass_Canopy")
    bm_glass.to_mesh(mesh_glass)
    bm_glass.free()

    obj_glass = bpy.data.objects.new("GEO_Glass_Canopy", mesh_glass)
    link_to_col(obj_glass, col_glass)
    obj_glass.data.materials.append(mat_glass)

    m_g_mir = obj_glass.modifiers.new("Mirror_X", 'MIRROR')
    m_g_mir.use_axis[0] = True
    m_g_mir.use_clip = True
    m_g_mir.show_on_cage = True
    m_g_sol = obj_glass.modifiers.new("Solidify", 'SOLIDIFY')
    m_g_sol.thickness = -0.008
    m_g_sol.show_on_cage = True
    m_g_sub = obj_glass.modifiers.new("Subsurf", 'SUBSURF')
    m_g_sub.levels = 2
    m_g_sub.show_on_cage = True
    obj_glass.data.shade_smooth()

    # 6. 精密贴合的气动套件（总宽精确计算，消灭浮空）
    # A. 前碳纤维下扰流铲（总宽 1.76m -> scale.x=1.76，紧贴车鼻底沿）
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    front_splitter = bpy.context.active_object
    front_splitter.name = "GEO_Aero_FrontSplitter"
    front_splitter.scale = (1.76, 0.42, 0.024)
    front_splitter.location = (0.0, 2.20, 0.14)
    link_to_col(front_splitter, col_aero)
    front_splitter.data.materials.append(mat_carbon)
    m_fs_bev = front_splitter.modifiers.new("Bevel", 'BEVEL')
    m_fs_bev.width = 0.010
    front_splitter.data.shade_smooth()

    # B. 前下扰流端板（精确位于前铲两端 x = +/- 0.88）
    for w_x, w_name in [(-0.88, "L"), (0.88, "R")]:
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        sp_winglet = bpy.context.active_object
        sp_winglet.name = f"GEO_Aero_SplitterWinglet_{w_name}"
        sp_winglet.scale = (0.02, 0.32, 0.12)
        sp_winglet.location = (w_x, 2.20, 0.19)
        link_to_col(sp_winglet, col_aero)
        sp_winglet.data.materials.append(mat_carbon)
        m_w_bev = sp_winglet.modifiers.new("Bevel", 'BEVEL')
        m_w_bev.width = 0.005

    # C. 前进气坝实体腔体（上接车鼻下沿 Z=0.28，下接前铲 Z=0.14，总宽 1.48m）
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    intake_dam = bpy.context.active_object
    intake_dam.name = "GEO_Aero_FrontIntakeDam"
    intake_dam.scale = (1.48, 0.24, 0.12)
    intake_dam.location = (0.0, 2.16, 0.20)
    link_to_col(intake_dam, col_aero)
    intake_dam.data.materials.append(mat_carbon)
    m_id_bev = intake_dam.modifiers.new("Bevel", 'BEVEL')
    m_id_bev.width = 0.012

    # 7. 侧裙导板（两侧各一根，紧贴车体下沿 x = +/- 0.86，长 2.5m）
    for sk_x, sk_name in [(-0.86, "L"), (0.86, "R")]:
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        side_skirt = bpy.context.active_object
        side_skirt.name = f"GEO_Aero_SideSkirt_{sk_name}"
        side_skirt.scale = (0.08, 2.50, 0.025)
        side_skirt.location = (sk_x, -0.05, 0.15)
        link_to_col(side_skirt, col_aero)
        side_skirt.data.materials.append(mat_carbon)
        m_sk_bev = side_skirt.modifiers.new("Bevel", 'BEVEL')
        m_sk_bev.width = 0.006

    # 8. 碳纤维尾翼与天鹅颈支架（主翼总宽 1.76m -> scale.x=1.76）
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    rear_wing = bpy.context.active_object
    rear_wing.name = "GEO_Aero_RearWing"
    rear_wing.scale = (1.76, 0.24, 0.022)
    rear_wing.location = (0.0, -2.12, 0.98)
    rear_wing.rotation_euler = (math.radians(-6.0), 0, 0)
    link_to_col(rear_wing, col_aero)
    rear_wing.data.materials.append(mat_carbon)
    m_rw_bev = rear_wing.modifiers.new("Bevel", 'BEVEL')
    m_rw_bev.width = 0.008
    rear_wing.data.shade_smooth()

    # 尾翼端板（精确位于主翼两端 x = +/- 0.88）
    for ep_x, ep_name in [(-0.88, "L"), (0.88, "R")]:
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        ep = bpy.context.active_object
        ep.name = f"GEO_Aero_WingEndplate_{ep_name}"
        ep.scale = (0.015, 0.32, 0.16)
        ep.location = (ep_x, -2.12, 0.98)
        link_to_col(ep, col_aero)
        ep.data.materials.append(mat_carbon)
        m_ep_bev = ep.modifiers.new("Bevel", 'BEVEL')
        m_ep_bev.width = 0.006

    # 天鹅颈碳纤维支架（扎入车体鸭尾）
    for wm_x, wm_name in [(-0.36, "L"), (0.36, "R")]:
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        wing_mount = bpy.context.active_object
        wing_mount.name = f"GEO_Aero_WingMount_{wm_name}"
        wing_mount.scale = (0.02, 0.14, 0.24)
        wing_mount.location = (wm_x, -2.08, 0.86)
        wing_mount.rotation_euler = (math.radians(-12), 0, 0)
        link_to_col(wing_mount, col_aero)
        wing_mount.data.materials.append(mat_carbon)
        m_wm_bev = wing_mount.modifiers.new("Bevel", 'BEVEL')
        m_wm_bev.width = 0.006

    # 9. 后扩散器与双出排气
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    diffuser = bpy.context.active_object
    diffuser.name = "GEO_Aero_DiffuserBase"
    diffuser.scale = (1.60, 0.48, 0.03)
    diffuser.location = (0.0, -2.12, 0.18)
    diffuser.rotation_euler = (math.radians(14.0), 0, 0)
    link_to_col(diffuser, col_aero)
    diffuser.data.materials.append(mat_carbon)

    for fin_x in [-0.50, -0.20, 0.20, 0.50]:
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        fin = bpy.context.active_object
        fin.name = f"GEO_Aero_DiffuserFin_{fin_x}"
        fin.scale = (0.014, 0.44, 0.08)
        fin.location = (fin_x, -2.12, 0.17)
        fin.rotation_euler = (math.radians(14.0), 0, 0)
        link_to_col(fin, col_aero)
        fin.data.materials.append(mat_carbon)

    for ex_x in [-0.18, 0.18]:
        bpy.ops.mesh.primitive_cylinder_add(radius=0.045, depth=0.18, vertices=24)
        exhaust = bpy.context.active_object
        exhaust.name = f"GEO_Exhaust_Tip_{ex_x}"
        exhaust.rotation_euler = (math.radians(90), 0, 0)
        exhaust.location = (ex_x, -2.28, 0.45)
        link_to_col(exhaust, col_aero)
        exhaust.data.materials.append(mat_exhaust)

    # 10. 后视镜（紧贴 A 柱底座）
    for m_x, m_sign in [(-0.82, -1), (0.82, 1)]:
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        mirror_arm = bpy.context.active_object
        mirror_arm.name = f"GEO_Aero_MirrorArm_{'L' if m_sign < 0 else 'R'}"
        mirror_arm.scale = (0.06, 0.02, 0.015)
        mirror_arm.location = (m_x, 0.52, 0.74)
        mirror_arm.rotation_euler = (0, math.radians(-15 * m_sign), math.radians(25 * m_sign))
        link_to_col(mirror_arm, col_aero)
        mirror_arm.data.materials.append(mat_carbon)

        bpy.ops.mesh.primitive_cube_add(size=1.0)
        mirror_housing = bpy.context.active_object
        mirror_housing.name = f"GEO_Aero_MirrorHousing_{'L' if m_sign < 0 else 'R'}"
        mirror_housing.scale = (0.08, 0.055, 0.04)
        mirror_housing.location = (m_x + (0.05 * m_sign), 0.53, 0.75)
        mirror_housing.rotation_euler = (0, math.radians(-10 * m_sign), math.radians(15 * m_sign))
        link_to_col(mirror_housing, col_aero)
        mirror_housing.data.materials.append(mat_carbon)
        m_mh_bev = mirror_housing.modifiers.new("Bevel", 'BEVEL')
        m_mh_bev.width = 0.012
        mirror_housing.data.shade_smooth()

    # 11. 车灯
    for hl_x, hl_sign in [(-0.58, -1), (0.58, 1)]:
        bpy.ops.mesh.primitive_cylinder_add(radius=0.012, depth=0.38, vertices=16)
        headlight = bpy.context.active_object
        headlight.name = f"GEO_Light_Headlight_{'L' if hl_sign < 0 else 'R'}"
        headlight.rotation_euler = (math.radians(80), math.radians(-18 * hl_sign), math.radians(28 * hl_sign))
        headlight.location = (hl_x, 2.12, 0.42)
        link_to_col(headlight, col_lights)
        headlight.data.materials.append(mat_headlight)

    bpy.ops.mesh.primitive_cube_add(size=1.0)
    taillight = bpy.context.active_object
    taillight.name = "GEO_Light_Taillight"
    taillight.scale = (1.52, 0.018, 0.018)
    taillight.location = (0.0, -2.26, 0.70)
    link_to_col(taillight, col_lights)
    taillight.data.materials.append(mat_taillight)

    # 12. 竞技轮毂与制动总成（★★★ 关键：中空中圈 end_fill_type='NOTHING'，露出锻造轮毂）
    wheel_specs = [
        {"name": "FL", "loc": Vector(( 0.94,  1.32, 0.35)), "is_left": True},
        {"name": "FR", "loc": Vector((-0.94,  1.32, 0.35)), "is_left": False},
        {"name": "RL", "loc": Vector(( 0.98, -1.38, 0.36)), "is_left": True},
        {"name": "RR", "loc": Vector((-0.98, -1.38, 0.36)), "is_left": False},
    ]

    tire_rad = 0.35
    tire_w = 0.28
    rim_rad = 0.265

    for spec in wheel_specs:
        w_name = spec["name"]
        w_loc = spec["loc"]
        is_left = spec["is_left"]
        sign_x = 1.0 if is_left else -1.0
        col_w = get_or_create_col(f"Wheel_{w_name}", col_wheels)

        # 中空无端盖轮胎
        bpy.ops.mesh.primitive_cylinder_add(radius=tire_rad, depth=tire_w, end_fill_type='NOTHING', vertices=36)
        tire = bpy.context.active_object
        tire.name = f"GEO_Tire_{w_name}"
        tire.rotation_euler = (0, math.radians(90), 0)
        tire.location = w_loc
        link_to_col(tire, col_w)
        tire.data.materials.append(mat_tire)
        m_t_sol = tire.modifiers.new("Solidify", 'SOLIDIFY')
        m_t_sol.thickness = -0.065
        m_t_bev = tire.modifiers.new("Bevel", 'BEVEL')
        m_t_bev.width = 0.02
        tire.data.shade_smooth()

        # 锻造轮辋中空中圈
        bpy.ops.mesh.primitive_cylinder_add(radius=rim_rad, depth=tire_w * 0.92, end_fill_type='NOTHING', vertices=32)
        rim = bpy.context.active_object
        rim.name = f"GEO_RimBarrel_{w_name}"
        rim.rotation_euler = (0, math.radians(90), 0)
        rim.location = w_loc
        link_to_col(rim, col_w)
        rim.data.materials.append(mat_rim)
        m_r_sol = rim.modifiers.new("Solidify", 'SOLIDIFY')
        m_r_sol.thickness = 0.012
        rim.data.shade_smooth()

        # 轮毂深凹陷中心轴盖
        hub_x = w_loc.x + (tire_w * 0.36 * sign_x)
        bpy.ops.mesh.primitive_cylinder_add(radius=0.062, depth=0.025, vertices=20)
        hub = bpy.context.active_object
        hub.name = f"GEO_Hub_{w_name}"
        hub.rotation_euler = (0, math.radians(90), 0)
        hub.location = Vector((hub_x, w_loc.y, w_loc.z))
        link_to_col(hub, col_w)
        hub.data.materials.append(mat_rim)
        hub.data.shade_smooth()

        # 5组高光立体雕塑双辐条 (10-Spoke)
        col_spokes = get_or_create_col(f"Spokes_{w_name}", col_w)
        for spoke_i in range(5):
            base_angle = spoke_i * (2 * math.pi / 5)
            for sub_offset in [-0.075, 0.075]:
                ang = base_angle + sub_offset
                bpy.ops.mesh.primitive_cube_add(size=1.0)
                spoke = bpy.context.active_object
                spoke.name = f"GEO_Spoke_{w_name}_{spoke_i}"
                spoke.scale = (0.024, 0.018, rim_rad * 0.86)
                
                radial_vec = Vector((0, math.sin(ang) * rim_rad * 0.46, math.cos(ang) * rim_rad * 0.46))
                spoke.location = Vector((hub_x - (0.010 * sign_x), w_loc.y + radial_vec.y, w_loc.z + radial_vec.z))
                spoke.rotation_euler = (ang, 0, 0)
                link_to_col(spoke, col_spokes)
                spoke.data.materials.append(mat_rim)
                m_sp_bev = spoke.modifiers.new("Bevel", 'BEVEL')
                m_sp_bev.width = 0.005
                spoke.data.shade_smooth()

        # 打孔碳陶刹车盘
        disc_x = w_loc.x - (tire_w * 0.06 * sign_x)
        bpy.ops.mesh.primitive_cylinder_add(radius=rim_rad * 0.84, depth=0.018, vertices=32)
        disc = bpy.context.active_object
        disc.name = f"GEO_BrakeDisc_{w_name}"
        disc.rotation_euler = (0, math.radians(90), 0)
        disc.location = Vector((disc_x, w_loc.y, w_loc.z))
        link_to_col(disc, col_w)
        disc.data.materials.append(mat_disc)
        disc.data.shade_smooth()

        # 6活塞金色卡钳 (固定在2点钟方向)
        caliper_x = disc_x
        caliper_y = w_loc.y + (rim_rad * 0.68 * math.cos(math.radians(35)))
        caliper_z = w_loc.z + (rim_rad * 0.68 * math.sin(math.radians(35)))
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        caliper = bpy.context.active_object
        caliper.name = f"GEO_Caliper_{w_name}"
        caliper.scale = (0.048, 0.08, 0.14)
        caliper.location = Vector((caliper_x, caliper_y, caliper_z))
        caliper.rotation_euler = (math.radians(-35), 0, 0)
        link_to_col(caliper, col_w)
        caliper.data.materials.append(mat_caliper)
        m_c_bev = caliper.modifiers.new("Bevel", 'BEVEL')
        m_c_bev.width = 0.012
        caliper.data.shade_smooth()

    # 13. 座舱剪影
    for seat_i, x_offset in enumerate([-0.28, 0.28]):
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        seat = bpy.context.active_object
        seat.name = f"GEO_Interior_Seat_{seat_i}"
        seat.scale = (0.22, 0.28, 0.36)
        seat.location = (x_offset, -0.22, 0.56)
        seat.rotation_euler = (math.radians(-16), 0, 0)
        link_to_col(seat, col_interior)
        seat.data.materials.append(mat_interior)

    bpy.ops.mesh.primitive_torus_add(major_radius=0.15, minor_radius=0.018, major_segments=20, minor_segments=10)
    wheel_ctrl = bpy.context.active_object
    wheel_ctrl.name = "GEO_Interior_SteeringWheel"
    wheel_ctrl.location = (0.28, 0.32, 0.70)
    wheel_ctrl.rotation_euler = (math.radians(24), 0, 0)
    link_to_col(wheel_ctrl, col_interior)
    wheel_ctrl.data.materials.append(mat_interior)

    # 14. 摄影棚地坪与环境（★★★ 关键防坑设置：锁定地坪选择权限）
    bpy.ops.mesh.primitive_plane_add(size=40.0)
    floor = bpy.context.active_object
    floor.name = "GEO_Studio_Floor"
    floor.location = (0, 0, 0)
    link_to_col(floor, col_studio)
    floor.data.materials.append(mat_floor)
    floor.hide_select = True  # 锁定地坪，用户在 3D 视口里怎么点都不会误选地面

    # 顶棚柔光
    bpy.ops.object.light_add(type='AREA', location=(0, 0, 7.5))
    light_top = bpy.context.active_object
    light_top.name = "Light_Studio_Top"
    light_top.data.energy = 1600
    light_top.data.size = 10.0
    link_to_col(light_top, col_studio)
    light_top.hide_select = True

    # 45度前侧主补光
    bpy.ops.object.light_add(type='AREA', location=(4.5, 5.0, 3.8))
    light_front = bpy.context.active_object
    light_front.name = "Light_Studio_FrontFill"
    light_front.data.energy = 900
    light_front.data.size = 4.5
    light_front.rotation_euler = (math.radians(50), math.radians(-15), math.radians(-40))
    link_to_col(light_front, col_studio)
    light_front.hide_select = True

    # 15. 相机设置（使用 TrackQuat 确保精准瞄准车身中心）
    cameras = [
        {"name": "Cam_GT_Front34", "loc": Vector((4.5, 4.8, 2.2))},
        {"name": "Cam_GT_Rear34", "loc": Vector((4.5, -4.8, 2.2))},
        {"name": "Cam_GT_Side", "loc": Vector((5.8, 0.0, 1.3))},
        {"name": "Cam_GT_Top", "loc": Vector((0.0, 0.0, 6.8))}
    ]

    target_pt = Vector((0.0, 0.0, 0.55))

    for cd in cameras:
        cam_obj = bpy.data.objects.get(cd["name"])
        if not cam_obj:
            bpy.ops.object.camera_add(location=cd["loc"])
            cam_obj = bpy.context.active_object
            cam_obj.name = cd["name"]
            cam_obj.data.lens = 50.0
            link_to_col(cam_obj, col_studio)
        else:
            cam_obj.location = cd["loc"]
        
        # 精确朝向目标点
        direction = target_pt - cam_obj.location
        if cd["name"] == "Cam_GT_Top":
            cam_obj.rotation_euler = (0, 0, math.radians(90))
        else:
            cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
            
        cam_obj.hide_select = True

    # 16. ★★★ 核心修复：将车身设为主激活对象并默认选中
    for obj in bpy.context.scene.objects:
        obj.select_set(False)
    
    obj_body.select_set(True)
    bpy.context.view_layer.objects.active = obj_body

    # 17. 渲染输出
    scene = bpy.context.scene
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    
    out_dir = r"D:\项目session\blender-supercar"
    render_targets = [
        ("Cam_GT_Front34", "car_render_front34.png"),
        ("Cam_GT_Rear34", "car_render_rear34.png"),
        ("Cam_GT_Side", "car_render_side.png"),
        ("Cam_GT_Top", "car_render_top.png"),
    ]

    for cam_name, img_name in render_targets:
        cam_obj = bpy.data.objects.get(cam_name)
        if cam_obj:
            scene.camera = cam_obj
            scene.render.filepath = os.path.join(out_dir, img_name)
            bpy.ops.render.render(write_still=True)
            print(f"RENDERED: {img_name}")

    # 保存场景至 v2 和 v3
    save_path_v3 = os.path.join(out_dir, "supercar_gt_v3.blend")
    save_path_v2 = os.path.join(out_dir, "supercar_gt_v2.blend")
    bpy.ops.wm.save_as_mainfile(filepath=save_path_v3)
    bpy.ops.wm.save_as_mainfile(filepath=save_path_v2)
    print("SAVED_PERFECT_SUCCESSFULLY")

if __name__ == "__main__":
    build_supercar_v3_perfect()
