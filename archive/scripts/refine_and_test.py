import bpy
import bmesh
import math
from mathutils import Vector, Euler

def point_camera_at(cam_obj, target_pos):
    """设置相机朝向目标点"""
    loc = cam_obj.location
    direction = target_pos - loc
    # 计算旋转
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot_quat.to_euler()

def refine_cameras_and_decals():
    blend_path = r"D:\项目session\blender-supercar\scifi_f1_2035.blend"
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    scene = bpy.context.scene

    # 1. 修复后翼 Oracle 顶面贴花朝向 (Top view 视角可读)
    dec_rw = bpy.data.objects.get("DEC_RearWing_Front_Oracle")
    if dec_rw:
        # 旋转 180 度使其从车头方向望去为正向可读
        dec_rw.rotation_euler.z += math.pi

    # 2. 精确重构 6 组摄影机坐标与镜头参数 (电影级黄金构图)
    cam_configs = {
        "Cam_F1_Hero_Trackside34": {
            "loc": Vector((4.80, 5.20, 1.05)),
            "target": Vector((0.0, 0.35, 0.45)),
            "lens": 46.0,
            "fstop": 8.0, # 全景锐利
            "focus_dist": 6.8
        },
        "Cam_F1_Side_Profile_Tele": {
            "loc": Vector((11.20, 0.05, 0.55)),
            "target": Vector((0.0, 0.05, 0.45)),
            "lens": 72.0, # 压缩感长焦，整车5.2m无切边
            "fstop": 11.0,
            "focus_dist": 11.2
        },
        "Cam_F1_Rear_Diffuser_Low": {
            "loc": Vector((-2.40, -4.80, 0.48)),
            "target": Vector((-0.10, -1.60, 0.55)),
            "lens": 52.0,
            "fstop": 5.6,
            "focus_dist": 4.2
        },
        "Cam_F1_Top_Aero_Down": {
            "loc": Vector((0.0, 0.10, 12.20)),
            "target": Vector((0.0, 0.10, 0.40)),
            "lens": 48.0,
            "fstop": 16.0,
            "focus_dist": 11.8
        },
        "Cam_F1_Aero_Wheel_Macro": {
            "loc": Vector((2.35, 2.35, 0.58)),
            "target": Vector((0.95, 1.45, 0.36)), # 右前轮心
            "lens": 68.0,
            "fstop": 4.5,
            "focus_dist": 1.75
        },
        "Cam_F1_Onboard_DriverPOV": {
            "loc": Vector((0.0, -0.15, 0.77)), # 驾驶员头盔眼位
            "target": Vector((0.0, 1.40, 0.50)), # 朝前看下前方赛道与车鼻
            "lens": 30.0, # FIA Onboard 超广角机位
            "fstop": 4.0,
            "focus_dist": 0.55
        }
    }

    for name, cfg in cam_configs.items():
        cam = bpy.data.objects.get(name)
        if not cam:
            continue
        cam.location = cfg["loc"]
        point_camera_at(cam, cfg["target"])
        if name == "Cam_F1_Top_Aero_Down":
            # 顶部机位固定横置视角 (车头朝右)
            cam.rotation_euler = Euler((0.0, 0.0, math.radians(90.0)))
        cam.data.lens = cfg["lens"]
        cam.data.dof.use_dof = True
        cam.data.dof.focus_distance = cfg["focus_dist"]
        cam.data.dof.aperture_fstop = cfg["fstop"]
        cam.data.clip_start = 0.05
        cam.data.clip_end = 250.0

    # 3. 渲染参数配置
    scene.view_settings.view_transform = 'AgX'
    try:
        scene.view_settings.look = 'AgX - High Contrast'
    except Exception:
        scene.view_settings.look = 'High Contrast'
    scene.view_settings.exposure = -4.2

    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'GPU'
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540

    cprefs = bpy.context.preferences.addons['cycles'].preferences
    cprefs.get_devices()
    for d in cprefs.devices:
        if d.type in ['OPTIX', 'CUDA']:
            d.use = True
        else:
            d.use = False

    # 保存
    bpy.ops.wm.save_mainfile(filepath=blend_path)

    # 依次渲染验证预览
    for cam_name in cam_configs.keys():
        cam_obj = bpy.data.objects.get(cam_name)
        if not cam_obj:
            continue
        scene.camera = cam_obj
        out_path = f"D:/项目session/blender-supercar/v2_{cam_name}.png"
        scene.render.filepath = out_path
        print(f">>> Rendering {cam_name}...")
        bpy.ops.render.render(write_still=True)
        print(f"Saved {out_path}")

    print("ALL REFINED PREVIEWS RENDERED")

if __name__ == '__main__':
    refine_cameras_and_decals()
