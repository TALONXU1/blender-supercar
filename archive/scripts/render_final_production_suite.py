import bpy
import os
import shutil

def render_final_suite():
    print("=== STARTING FULL PRODUCTION CYCLE SUITE RENDERING ===")
    blend_path = r"D:\项目session\blender-supercar\scifi_f1_2035.blend"
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    scene = bpy.context.scene

    out_dir = r"D:\项目session\blender-supercar\final_renders"
    os.makedirs(out_dir, exist_ok=True)

    artifact_dir = r"C:\Users\86052\.gemini\antigravity\brain\fe45f8e6-8741-486f-93a1-a197a7712d30"

    # 1. 核心渲染设置 (1080p, 128 samples, GPU OptiX, AgX)
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'GPU'
    scene.cycles.samples = 128
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.02
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100

    scene.view_settings.view_transform = 'AgX'
    try:
        scene.view_settings.look = 'AgX - High Contrast'
    except Exception:
        scene.view_settings.look = 'High Contrast'
    scene.view_settings.exposure = -4.2

    cprefs = bpy.context.preferences.addons['cycles'].preferences
    cprefs.get_devices()
    for d in cprefs.devices:
        if d.type in ['OPTIX', 'CUDA']:
            d.use = True
        else:
            d.use = False

    cam_map = [
        ("Cam_F1_Hero_Trackside34", "f1_render_hero_front34.png"),
        ("Cam_F1_Side_Profile_Tele", "f1_render_side_tele.png"),
        ("Cam_F1_Rear_Diffuser_Low", "f1_render_rear_diffuser.png"),
        ("Cam_F1_Top_Aero_Down", "f1_render_top_aero.png"),
        ("Cam_F1_Aero_Wheel_Macro", "f1_render_wheel_macro.png"),
        ("Cam_F1_Onboard_DriverPOV", "f1_render_cockpit_onboard.png"),
    ]

    rendered_files = []

    # 2. 依次输出 6 张电影级正式大片
    for cam_name, file_name in cam_map:
        cam_obj = bpy.data.objects.get(cam_name)
        if not cam_obj:
            print(f"Camera {cam_name} not found!")
            continue
        scene.camera = cam_obj
        filepath = os.path.join(out_dir, file_name)
        scene.render.filepath = filepath
        print(f">>> [CYCLES] Rendering {cam_name} -> {filepath}...")
        bpy.ops.render.render(write_still=True)
        rendered_files.append((filepath, file_name))
        print(f"Saved {filepath}")

    # 3. 输出 1 张粘土白模 / 线框工程图 (Clay Topology Pass)
    print(">>> Rendering Clay Topology Wireframe Pass...")
    hero_cam = bpy.data.objects.get("Cam_F1_Hero_Trackside34")
    scene.camera = hero_cam
    
    # 创建白模覆盖材质
    mat_clay = bpy.data.materials.new("Mat_Clay_Override")
    mat_clay.use_nodes = True
    bsdf_clay = mat_clay.node_tree.nodes.get("Principled BSDF")
    if bsdf_clay:
        bsdf_clay.inputs['Base Color'].default_value = (0.75, 0.75, 0.77, 1.0)
        bsdf_clay.inputs['Roughness'].default_value = 0.45

    # 隐藏地面跑道以凸显赛车纯净机械悬垂线框
    ground = bpy.data.objects.get("GEO_F1_Ground_TrackRunway")
    if ground:
        ground.hide_render = True

    # 临时将 view layer material override 设为白模
    view_layer = scene.view_layers[0]
    view_layer.material_override = mat_clay

    clay_filepath = os.path.join(out_dir, "f1_render_wireframe_clay.png")
    scene.render.filepath = clay_filepath
    scene.cycles.samples = 64
    bpy.ops.render.render(write_still=True)
    rendered_files.append((clay_filepath, "f1_render_wireframe_clay.png"))
    print(f"Saved {clay_filepath}")

    # 恢复场景
    view_layer.material_override = None
    if ground:
        ground.hide_render = False

    # 4. 同步拷贝至 Artifacts 目录
    for src_path, fname in rendered_files:
        dst_path = os.path.join(artifact_dir, fname)
        shutil.copy2(src_path, dst_path)
        print(f"Artifact Synced: {dst_path}")

    print("=== ALL 7 PRODUCTION RENDERS COMPLETED & ARTIFACTS SYNCED ===")

if __name__ == '__main__':
    render_final_suite()
