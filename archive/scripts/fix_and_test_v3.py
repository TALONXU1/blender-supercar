import bpy
import bmesh
import math
from mathutils import Vector, Euler

def point_camera_at(cam_obj, target_pos):
    direction = target_pos - cam_obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot_quat.to_euler()

def fix_all_issues():
    blend_path = r"D:\项目session\blender-supercar\scifi_f1_2035.blend"
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    scene = bpy.context.scene

    # 1. 彻底修正后翼贴花位置与 UV
    # DEC_RearWing_Front_Oracle: 归零旋转
    dec_rf = bpy.data.objects.get("DEC_RearWing_Front_Oracle")
    if dec_rf:
        dec_rf.rotation_euler = Euler((0.0, 0.0, 0.0))
        # 翻转 UV 使其正视/俯视方向正确
        mesh = dec_rf.data
        if mesh.uv_layers.active:
            for loop in mesh.uv_layers.active.data:
                loop.uv.x = 1.0 - loop.uv.x

    # DEC_RearWing_Back_RedBull: 翻转 UV X 使后视读取正常
    dec_rb = bpy.data.objects.get("DEC_RearWing_Back_RedBull")
    if dec_rb:
        dec_rb.rotation_euler = Euler((0.0, 0.0, 0.0))
        mesh = dec_rb.data
        if mesh.uv_layers.active:
            for loop in mesh.uv_layers.active.data:
                loop.uv.x = 1.0 - loop.uv.x

    # 2. 精确重设相机机位与焦段
    cam_configs = {
        "Cam_F1_Hero_Trackside34": {
            "loc": Vector((4.80, 5.20, 1.05)),
            "target": Vector((0.0, 0.35, 0.45)),
            "lens": 46.0,
            "fstop": 8.0,
            "focus_dist": 6.8
        },
        "Cam_F1_Side_Profile_Tele": {
            "loc": Vector((11.20, 0.05, 0.55)),
            "target": Vector((0.0, 0.05, 0.45)),
            "lens": 72.0,
            "fstop": 11.0,
            "focus_dist": 11.2
        },
        "Cam_F1_Rear_Diffuser_Low": {
            "loc": Vector((-2.10, -4.90, 0.50)),
            "target": Vector((-0.15, -1.80, 0.58)),
            "lens": 50.0,
            "fstop": 5.6,
            "focus_dist": 4.5
        },
        "Cam_F1_Top_Aero_Down": {
            "loc": Vector((0.0, 0.10, 12.20)),
            "target": Vector((0.0, 0.10, 0.40)),
            "lens": 48.0,
            "fstop": 16.0,
            "focus_dist": 11.8
        },
        "Cam_F1_Aero_Wheel_Macro": {
            "loc": Vector((2.70, 2.55, 0.55)),
            "target": Vector((0.95, 1.45, 0.36)),
            "lens": 52.0,
            "fstop": 4.5,
            "focus_dist": 2.1
        },
        "Cam_F1_Onboard_DriverPOV": {
            "loc": Vector((0.0, -0.15, 0.77)),
            "target": Vector((0.0, 1.40, 0.50)),
            "lens": 30.0,
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
            cam.rotation_euler = Euler((0.0, 0.0, math.radians(90.0)))
        cam.data.lens = cfg["lens"]
        cam.data.dof.use_dof = True
        cam.data.dof.focus_distance = cfg["focus_dist"]
        cam.data.dof.aperture_fstop = cfg["fstop"]

    # 保存主工程
    bpy.ops.wm.save_mainfile(filepath=blend_path)
    print("FIXES APPLIED AND SAVED")

    # 依次渲染验证
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

    for cam_name in ["Cam_F1_Rear_Diffuser_Low", "Cam_F1_Top_Aero_Down", "Cam_F1_Aero_Wheel_Macro", "Cam_F1_Onboard_DriverPOV"]:
        cam_obj = bpy.data.objects.get(cam_name)
        if not cam_obj:
            continue
        scene.camera = cam_obj
        out_path = f"D:/项目session/blender-supercar/v3_{cam_name}.png"
        scene.render.filepath = out_path
        print(f">>> Rendering {cam_name}...")
        bpy.ops.render.render(write_still=True)
        print(f"Saved {out_path}")

if __name__ == '__main__':
    fix_all_issues()
