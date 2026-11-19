import bpy
import bmesh
import math
import os
import shutil
import time
from mathutils import Vector

def optimize_f1_with_skills():
    print("=== EXECUTING SKILLS OPTIMIZATION: NATURAL LIGHTING, PBR MATERIALS & CAMERAS ===")

    # 1. 打开主工程
    blend_path = r"D:\项目session\blender-supercar\scifi_f1_2035.blend"
    bpy.ops.wm.open_mainfile(filepath=blend_path)

    scene = bpy.context.scene

    # 2. 检索核心集合
    col_root = bpy.data.collections.get("SCIFI_F1_2035")
    col_wings = bpy.data.collections.get("04_Wings_Aerodynamics") or col_root
    col_sidepods = bpy.data.collections.get("03_Sidepods_EngineCowl") or col_root
    col_chassis = bpy.data.collections.get("01_Chassis_Monocoque") or col_root
    col_lights = bpy.data.collections.get("07_Telemetry_LED_Lights") or col_root
    col_studio = bpy.data.collections.get("09_Studio_Stage_Rig") or col_root

    def link_obj(obj, col):
        for c in obj.users_collection:
            c.objects.unlink(obj)
        col.objects.link(obj)

    def get_or_create_mat(name):
        mat = bpy.data.materials.get(name)
        if not mat:
            mat = bpy.data.materials.new(name)
            mat.use_nodes = True
        return mat

    mat_carbon = get_or_create_mat("Mat_Carbon_Fiber")
    mat_titanium = get_or_create_mat("Mat_Titanium_Hardware")
    mat_navy = get_or_create_mat("Mat_RedBull_MatteNavy")
    mat_yellow = get_or_create_mat("Mat_RedBull_SolarYellow")
    mat_red = get_or_create_mat("Mat_RedBull_Crimson")
    mat_white = get_or_create_mat("Mat_PZero_White")
    mat_gold = get_or_create_mat("Mat_Inconel_GoldHeatShield")

    # =========================================================================
    # A. 材质升级 (High-Tactile Shaders: Clearcoat, Velvet Sheen, Metallic)
    # =========================================================================
    # 1. 红牛哑光午夜蓝微清漆车漆 (Red Bull Matte Navy Livery)
    if mat_navy and mat_navy.node_tree:
        bsdf = mat_navy.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs['Base Color'].default_value = (0.009, 0.018, 0.042, 1.0)
            bsdf.inputs['Roughness'].default_value = 0.32
            if 'Clearcoat Weight' in bsdf.inputs:
                bsdf.inputs['Clearcoat Weight'].default_value = 0.40
                bsdf.inputs['Clearcoat Roughness'].default_value = 0.16
            elif 'Clearcoat' in bsdf.inputs:
                bsdf.inputs['Clearcoat'].default_value = 0.40
                bsdf.inputs['Clearcoat Roughness'].default_value = 0.16
            if 'Metallic' in bsdf.inputs:
                bsdf.inputs['Metallic'].default_value = 0.03
            if 'Sheen Weight' in bsdf.inputs:
                bsdf.inputs['Sheen Weight'].default_value = 0.35
                bsdf.inputs['Sheen Tint'].default_value = (0.2, 0.5, 1.0, 1.0)

    # 2. 碳纤维高光清漆层 (Glossy Clearcoat on Carbon Fiber)
    if mat_carbon and mat_carbon.node_tree:
        bsdf_c = mat_carbon.node_tree.nodes.get("Principled BSDF")
        if bsdf_c:
            bsdf_c.inputs['Base Color'].default_value = (0.025, 0.025, 0.028, 1.0)
            bsdf_c.inputs['Roughness'].default_value = 0.18
            if 'Clearcoat Weight' in bsdf_c.inputs:
                bsdf_c.inputs['Clearcoat Weight'].default_value = 1.0
                bsdf_c.inputs['Clearcoat Roughness'].default_value = 0.05
            elif 'Clearcoat' in bsdf_c.inputs:
                bsdf_c.inputs['Clearcoat'].default_value = 1.0
                bsdf_c.inputs['Clearcoat Roughness'].default_value = 0.05

    # 3. 钛合金微拉丝质感 (Titanium Hardware)
    if mat_titanium and mat_titanium.node_tree:
        bsdf_t = mat_titanium.node_tree.nodes.get("Principled BSDF")
        if bsdf_t:
            bsdf_t.inputs['Base Color'].default_value = (0.78, 0.80, 0.82, 1.0)
            bsdf_t.inputs['Metallic'].default_value = 1.0
            bsdf_t.inputs['Roughness'].default_value = 0.18

    # 4. Inconel 排气管金箔锤纹隔热盾 (Inconel Gold Heat Shield)
    if mat_gold and mat_gold.node_tree:
        nodes = mat_gold.node_tree.nodes
        links = mat_gold.node_tree.links
        bsdf_g = nodes.get("Principled BSDF")
        if bsdf_g:
            bsdf_g.inputs['Base Color'].default_value = (1.0, 0.78, 0.26, 1.0)
            bsdf_g.inputs['Metallic'].default_value = 1.0
            bsdf_g.inputs['Roughness'].default_value = 0.28
            # Voronoi 锤纹凹凸
            if not nodes.get("Voro_Foil"):
                tex_voro = nodes.new('ShaderNodeTexVoronoi')
                tex_voro.name = "Voro_Foil"
                tex_voro.inputs['Scale'].default_value = 180.0
                bump_foil = nodes.new('ShaderNodeBump')
                bump_foil.name = "Bump_Foil"
                bump_foil.inputs['Strength'].default_value = 0.15
                bump_foil.inputs['Distance'].default_value = 0.01
                links.new(tex_voro.outputs['Distance'], bump_foil.inputs['Height'])
                links.new(bump_foil.outputs['Normal'], bsdf_g.inputs['Normal'])

    # =========================================================================
    # B. 载具机械深化 (Vehicle Artist & Hard Surface Engineering)
    # =========================================================================
    
    # 1. 前翼双层俯冲风刀 (Canards / Dive Planes)
    for side_sign, side_name in [(-1, "L"), (1, "R")]:
        for c_idx, (c_z, c_chord, c_roll) in enumerate([(0.22, 0.18, 12), (0.32, 0.15, 18)]):
            c_name = f"GEO_F1_Canard_{'Upper' if c_idx==1 else 'Lower'}_{side_name}"
            if not bpy.data.objects.get(c_name):
                bpy.ops.mesh.primitive_cube_add(size=1.0)
                canard = bpy.context.active_object
                canard.name = c_name
                canard.scale = (0.006, c_chord, 0.065)
                canard.location = (0.975 * side_sign, 2.75 - (c_idx * 0.08), c_z)
                canard.rotation_euler = (math.radians(-16), math.radians(c_roll * side_sign), math.radians(-8 * side_sign))
                link_obj(canard, col_wings)
                canard.data.materials.append(mat_carbon)
                m_bev = canard.modifiers.new("Bevel", 'BEVEL')
                m_bev.width = 0.002

    # 2. 前翼多层副翼缝隙保持架与钛合金开度调节器 (Slot Gap Separators)
    for side_sign, side_name in [(-1, "L"), (1, "R")]:
        for s_i, s_x in enumerate([0.35, 0.60, 0.82]):
            sep_name = f"GEO_F1_SlotSeparator_{s_i}_{side_name}"
            if not bpy.data.objects.get(sep_name):
                bpy.ops.mesh.primitive_cylinder_add(radius=0.0025, depth=0.075, vertices=8)
                sep = bpy.context.active_object
                sep.name = sep_name
                sep.location = (s_x * side_sign, 2.65 - (s_i * 0.06), 0.145)
                sep.rotation_euler = (math.radians(-25), 0, 0)
                link_obj(sep, col_wings)
                sep.data.materials.append(mat_titanium)

    # 3. 侧箱肩膀鲨鱼鳃散热百叶窗 (Sidepod Cooling Louvers / Gills)
    for side_sign, side_name in [(-1, "L"), (1, "R")]:
        for g_i in range(8):
            gill_name = f"GEO_F1_CoolingGill_{g_i}_{side_name}"
            if not bpy.data.objects.get(gill_name):
                gy = 0.20 - (g_i * 0.11)
                gz = 0.52 + (math.sin(g_i * 0.35) * 0.04)
                gx = 0.44 + (g_i * 0.015)
                bpy.ops.mesh.primitive_cube_add(size=1.0)
                gill = bpy.context.active_object
                gill.name = gill_name
                gill.scale = (0.075, 0.012, 0.004)
                gill.location = (gx * side_sign, gy, gz)
                gill.rotation_euler = (math.radians(35), math.radians(-12 * side_sign), math.radians(-18 * side_sign))
                link_obj(gill, col_sidepods)
                gill.data.materials.append(mat_carbon)

    # 4. FIA 尾部防雨雾高亮安全灯 (Rear Rain Safety Light LED Array)
    rain_light_name = "GEO_F1_RearRainLight"
    if not bpy.data.objects.get(rain_light_name):
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        rl_box = bpy.context.active_object
        rl_box.name = rain_light_name
        rl_box.scale = (0.10, 0.035, 0.055)
        rl_box.location = (0.0, -2.62, 0.38)
        link_obj(rl_box, col_lights)
        rl_box.data.materials.append(mat_carbon)

        # 密集 8x3 LED 发光珠
        mat_rain_led = get_or_create_mat("Mat_RearRain_LED")
        bsdf_rl = mat_rain_led.node_tree.nodes.get("Principled BSDF")
        if bsdf_rl:
            bsdf_rl.inputs['Base Color'].default_value = (1.0, 0.05, 0.02, 1.0)
            if 'Emission Color' in bsdf_rl.inputs:
                bsdf_rl.inputs['Emission Color'].default_value = (1.0, 0.05, 0.02, 1.0)
                bsdf_rl.inputs['Emission Strength'].default_value = 15.0
            elif 'Emission' in bsdf_rl.inputs:
                bsdf_rl.inputs['Emission'].default_value = (1.0, 0.05, 0.02, 1.0)
                bsdf_rl.inputs['Emission Strength'].default_value = 15.0

        for rx in range(8):
            for rz in range(3):
                px = -0.040 + (rx * 0.0115)
                pz = 0.360 + (rz * 0.014)
                bpy.ops.mesh.primitive_cylinder_add(radius=0.0035, depth=0.008, vertices=8)
                r_bead = bpy.context.active_object
                r_bead.name = f"GEO_F1_RainLED_{rx}_{rz}"
                r_bead.rotation_euler = (math.radians(90), 0, 0)
                r_bead.location = (px, -2.64, pz)
                link_obj(r_bead, col_lights)
                r_bead.data.materials.append(mat_rain_led)

    # 5. 前轮后方气动整流除水板 (Wheel Deflector Wake Control Fins)
    for side_sign, side_name in [(-1, "L"), (1, "R")]:
        barge_name = f"GEO_F1_Bargeboard_WakeFin_{side_name}"
        if not bpy.data.objects.get(barge_name):
            bpy.ops.mesh.primitive_cube_add(size=1.0)
            barge = bpy.context.active_object
            barge.name = barge_name
            barge.scale = (0.012, 0.28, 0.16)
            barge.location = (0.72 * side_sign, 0.95, 0.25)
            barge.rotation_euler = (math.radians(-6), math.radians(8 * side_sign), math.radians(14 * side_sign))
            link_obj(barge, col_wings)
            barge.data.materials.append(mat_carbon)

    # =========================================================================
    # C. 自然光与物理天空跑道环境 (Natural Lighting & Pavement Environment)
    # =========================================================================
    
    # 1. 移除旧影棚黑天幕与旧摄影棚灯
    for old_obj_name in ["GEO_Studio_Floor", "GEO_Studio_Backdrop", "LGT_Studio_KeyArea", "LGT_Studio_RimArea", "LGT_Studio_TopStrip"]:
        old_o = bpy.data.objects.get(old_obj_name)
        if old_o:
            bpy.data.objects.remove(old_o, do_unlink=True)

    # 2. 120米真实赛道沥青地面 (Track Runway Ground Plane)
    runway_name = "GEO_F1_Ground_TrackRunway"
    runway = bpy.data.objects.get(runway_name)
    if not runway:
        bpy.ops.mesh.primitive_plane_add(size=120.0)
        runway = bpy.context.active_object
        runway.name = runway_name
        runway.location = (0.0, 0.0, 0.000)
        link_obj(runway, col_studio)
        runway.hide_select = True

    # 真实沥青赛道材质 (Procedural Asphalt Pavement with Damp Specular & Aggregate)
    mat_asphalt = get_or_create_mat("Mat_Track_Asphalt")
    runway.data.materials.clear()
    runway.data.materials.append(mat_asphalt)

    a_nodes = mat_asphalt.node_tree.nodes
    a_links = mat_asphalt.node_tree.links
    a_nodes.clear()
    a_out = a_nodes.new('ShaderNodeOutputMaterial')
    a_bsdf = a_nodes.new('ShaderNodeBsdfPrincipled')
    a_bsdf.inputs['Base Color'].default_value = (0.075, 0.078, 0.082, 1.0)
    a_bsdf.inputs['Roughness'].default_value = 0.45
    if 'Specular IOR Level' in a_bsdf.inputs:
        a_bsdf.inputs['Specular IOR Level'].default_value = 0.65
    elif 'Specular' in a_bsdf.inputs:
        a_bsdf.inputs['Specular'].default_value = 0.65

    # 沥青微颗粒凹凸
    tex_asph_noise = a_nodes.new('ShaderNodeTexNoise')
    tex_asph_noise.inputs['Scale'].default_value = 350.0
    tex_asph_noise.inputs['Detail'].default_value = 8.0
    bump_asph = a_nodes.new('ShaderNodeBump')
    bump_asph.inputs['Strength'].default_value = 0.08
    bump_asph.inputs['Distance'].default_value = 0.005
    a_links.new(tex_asph_noise.outputs['Fac'], bump_asph.inputs['Height'])
    a_links.new(bump_asph.outputs['Normal'], a_bsdf.inputs['Normal'])
    a_links.new(a_bsdf.outputs['BSDF'], a_out.inputs['Surface'])

    # 赛道 Pit Stop 黄色边界标志线与发车格标线
    for mk_x, mk_y, mk_sx, mk_sy, mk_mat, mk_name in [
        (1.85, 0.0, 0.12, 14.0, mat_yellow, "GEO_Track_Line_Yellow_R"),
        (-1.85, 0.0, 0.12, 14.0, mat_white, "GEO_Track_Line_White_L"),
        (0.0, 2.85, 1.6, 0.10, mat_white, "GEO_Track_Box_FrontLimit")
    ]:
        if not bpy.data.objects.get(mk_name):
            bpy.ops.mesh.primitive_plane_add(size=1.0)
            mk_obj = bpy.context.active_object
            mk_obj.name = mk_name
            mk_obj.scale = (mk_sx, mk_sy, 1.0)
            mk_obj.location = (mk_x, mk_y, 0.001)
            link_obj(mk_obj, col_studio)
            mk_obj.data.materials.append(mk_mat)
            mk_obj.hide_select = True

    # 3. 物理天空 Nishita 大气散射模型 (Physical Nishita Atmosphere)
    scene.world = bpy.data.worlds.new("World_NaturalSky")
    scene.world.use_nodes = True
    w_nodes = scene.world.node_tree.nodes
    w_links = scene.world.node_tree.links
    w_nodes.clear()
    w_out = w_nodes.new('ShaderNodeOutputWorld')
    w_bg = w_nodes.new('ShaderNodeBackground')
    w_bg.inputs['Strength'].default_value = 1.25

    tex_sky = w_nodes.new('ShaderNodeTexSky')
    tex_sky.sky_type = 'MULTIPLE_SCATTERING'
    tex_sky.sun_elevation = math.radians(20.5)      # 黄金时段低角度日光
    tex_sky.sun_rotation = math.radians(118.0)      # 侧后方黄金掠角
    tex_sky.sun_size = math.radians(0.9)            # 真实太阳视直径
    tex_sky.air_density = 1.0
    tex_sky.aerosol_density = 1.15
    tex_sky.ozone_density = 2.0
    tex_sky.sun_disc = True

    w_links.new(tex_sky.outputs['Color'], w_bg.inputs['Color'])
    w_links.new(w_bg.outputs['Background'], w_out.inputs['Surface'])

    # 4. 自然直射日光 (Direct Sunlight Key)
    sun_lamp_name = "LGT_Natural_Sun"
    sun_lamp = bpy.data.objects.get(sun_lamp_name)
    if not sun_lamp:
        sun_data = bpy.data.lights.new(name=sun_lamp_name, type='SUN')
        sun_data.energy = 5.2
        sun_data.color = (1.0, 0.965, 0.915)       # 暖日光
        sun_data.angle = math.radians(1.0)          # 产生柔和自然半影
        sun_lamp = bpy.data.objects.new(sun_lamp_name, sun_data)
        link_obj(sun_lamp, col_studio)

    # 旋转角度与 Nishita 天空完全对其
    sun_lamp.rotation_euler = (math.radians(69.5), math.radians(12.0), math.radians(-118.0))
    sun_lamp.location = (15.0, 25.0, 20.0)

    # =========================================================================
    # D. 电影级摄影机机位与构图重构 (Cinematic Camera Array)
    # =========================================================================
    # 清理旧相机
    for c in list(bpy.data.cameras):
        cam_o = bpy.data.objects.get(c.name)
        if cam_o:
            bpy.data.objects.remove(cam_o, do_unlink=True)
        bpy.data.cameras.remove(c)

    # 6 组专业汽车摄影机位配置
    cinematic_cameras = [
        ("Cam_F1_Hero_Trackside34", Vector((3.60, 4.30, 0.48)), Vector((0.0, 0.35, 0.34)), 70.0),
        ("Cam_F1_Onboard_DriverPOV", Vector((0.0, -0.06, 0.82)), Vector((0.0, 0.85, 0.52)), 36.0),
        ("Cam_F1_Rear_Diffuser_Low", Vector((-2.50, -4.40, 0.40)), Vector((0.0, -0.70, 0.36)), 65.0),
        ("Cam_F1_Side_Profile_Tele", Vector((8.50, 0.0, 0.58)), Vector((0.0, 0.0, 0.40)), 105.0),
        ("Cam_F1_Aero_Wheel_Macro", Vector((1.70, 1.75, 0.42)), Vector((0.90, 1.45, 0.355)), 85.0),
        ("Cam_F1_Top_Aero_Down", Vector((0.0, 0.20, 10.0)), Vector((0.0, 0.20, 0.35)), 55.0),
    ]

    for c_name, c_loc, t_pt, focal in cinematic_cameras:
        c_data = bpy.data.cameras.new(name=c_name)
        c_data.lens = focal
        c_data.clip_start = 0.05
        c_data.clip_end = 200.0
        c_obj = bpy.data.objects.new(c_name, c_data)
        c_obj.location = c_loc
        direction = t_pt - c_loc
        rot_quat = direction.to_track_quat('-Z', 'Y')
        c_obj.rotation_euler = rot_quat.to_euler()
        link_obj(c_obj, col_studio)

    # 解锁所有物件的交互选择
    for obj in bpy.data.objects:
        if obj.name.startswith("GEO_") or obj.name.startswith("DEC_"):
            if not obj.name.startswith("GEO_Track_") and obj.name != runway_name:
                obj.hide_select = False
                obj.select_set(False)

    # =========================================================================
    # E. Cycles GPU (OptiX) 真实物理光线追踪渲染
    # =========================================================================
    scene.render.engine = 'CYCLES'
    cprefs = bpy.context.preferences.addons['cycles'].preferences
    cprefs.compute_device_type = 'OPTIX'
    cprefs.get_devices()
    for d in cprefs.devices:
        d.use = (d.type == 'OPTIX')
    scene.cycles.device = 'GPU'
    scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = 'OPTIX'

    # 色彩管理 (AgX 高动态范围 + 高对比度 Look)
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - High Contrast'
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100

    out_dir = r"D:\项目session\blender-supercar"
    artifact_dir = r"C:\Users\86052\.gemini\antigravity\brain\fe45f8e6-8741-486f-93a1-a197a7712d30"

    render_tasks = [
        ("Cam_F1_Hero_Trackside34", "f1_render_front34.png"),
        ("Cam_F1_Rear_Diffuser_Low", "f1_render_rear34.png"),
        ("Cam_F1_Side_Profile_Tele", "f1_render_side.png"),
        ("Cam_F1_Top_Aero_Down", "f1_render_top.png"),
        ("Cam_F1_Aero_Wheel_Macro", "f1_render_wheel_detail.png"),
        ("Cam_F1_Onboard_DriverPOV", "f1_render_cockpit_detail.png"),
    ]

    print("--- STARTING CYCLES OPTIX BATCH RENDERING ---")
    for cam_name, img_name in render_tasks:
        cam_obj = bpy.data.objects.get(cam_name)
        if cam_obj:
            t_start = time.time()
            scene.camera = cam_obj
            dst_path = os.path.join(out_dir, img_name)
            scene.render.filepath = dst_path
            bpy.ops.render.render(write_still=True)
            print(f"RENDERED {img_name} in {time.time()-t_start:.2f}s")
            # 同步至 artifacts 目录
            art_path = os.path.join(artifact_dir, img_name)
            shutil.copy2(dst_path, art_path)

    # 保存主工程文件
    bpy.ops.wm.save_mainfile(filepath=blend_path)
    print("SAVED OPTIMIZED PROJECT:", blend_path)

if __name__ == "__main__":
    optimize_f1_with_skills()
