import bpy
import mathutils

def prepare_and_contact_sheet():
    blend_path = r"D:\项目session\blender-supercar\scifi_f1_2035.blend"
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    scene = bpy.context.scene

    # 1. 确保物理曝光与色彩管理锁定
    scene.view_settings.view_transform = 'AgX'
    try:
        scene.view_settings.look = 'AgX - High Contrast'
    except Exception:
        scene.view_settings.look = 'High Contrast'
    scene.view_settings.exposure = -4.2

    # 2. Cycles 渲染设置 (快速高画质验证)
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'GPU'
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.resolution_percentage = 100

    cprefs = bpy.context.preferences.addons['cycles'].preferences
    cprefs.get_devices()
    for d in cprefs.devices:
        if d.type in ['OPTIX', 'CUDA']:
            d.use = True
        else:
            d.use = False

    # 3. 校准所有摄影机焦点与机位
    cams = {
        "Cam_F1_Hero_Trackside34": {
            "loc": (3.80, 4.20, 0.65),
            "rot": (81.0, 0.0, 140.0), # 看向车头车身
            "lens": 52.0,
            "focus_target": "GEO_F1_Nosecone"
        },
        "Cam_F1_Side_Profile_Tele": {
            "loc": (8.80, -0.20, 0.48),
            "rot": (88.0, 0.0, 90.0),
            "lens": 90.0,
            "focus_target": "GEO_F1_Monocoque_Chassis"
        },
        "Cam_F1_Rear_Diffuser_Low": {
            "loc": (-2.80, -4.60, 0.42),
            "rot": (86.0, 0.0, -32.0),
            "lens": 58.0,
            "focus_target": "GEO_F1_RearRainLight"
        },
        "Cam_F1_Top_Aero_Down": {
            "loc": (0.0, -0.15, 9.50),
            "rot": (0.0, 0.0, 90.0), # 俯视，车头朝右或朝上
            "lens": 55.0,
            "focus_target": "GEO_F1_Monocoque_Chassis"
        },
        "Cam_F1_Aero_Wheel_Macro": {
            "loc": (1.90, 1.85, 0.45),
            "rot": (84.0, 0.0, 135.0), # 聚焦前右轮与前翼风刀
            "lens": 75.0,
            "focus_target": "GEO_F1_WheelCover_FR"
        },
        "Cam_F1_Onboard_DriverPOV": {
            "loc": (0.0, -0.06, 0.81),
            "rot": (79.0, 0.0, 180.0), # 驾驶舱内看方向盘与前方赛道
            "lens": 35.0,
            "focus_target": "GEO_F1_Steering_LCDScreen"
        }
    }

    import math
    for cam_name, cfg in cams.items():
        cam_obj = bpy.data.objects.get(cam_name)
        if not cam_obj:
            continue
        cam_obj.location = mathutils.Vector(cfg["loc"])
        cam_obj.rotation_euler = mathutils.Euler((math.radians(cfg["rot"][0]), math.radians(cfg["rot"][1]), math.radians(cfg["rot"][2])))
        cam_obj.data.lens = cfg["lens"]
        
        target_obj = bpy.data.objects.get(cfg["focus_target"])
        if target_obj:
            cam_obj.data.dof.use_dof = True
            cam_obj.data.dof.focus_object = target_obj
            cam_obj.data.dof.aperture_fstop = 5.6 # 深景深避免脱焦虚化
        else:
            cam_obj.data.dof.use_dof = False

    # 保存修正后的相机参数到 blend 文件
    bpy.ops.wm.save_mainfile(filepath=blend_path)

    # 4. 依次渲染 6 张快速预览
    for cam_name in cams.keys():
        cam_obj = bpy.data.objects.get(cam_name)
        if not cam_obj:
            continue
        scene.camera = cam_obj
        out_path = f"D:/项目session/blender-supercar/preview_{cam_name}.png"
        scene.render.filepath = out_path
        print(f">>> Rendering preview for {cam_name}...")
        bpy.ops.render.render(write_still=True)
        print(f"Saved {out_path}")

    print("ALL 6 PREVIEWS RENDERED SUCCESSFULLY")

if __name__ == '__main__':
    prepare_and_contact_sheet()
