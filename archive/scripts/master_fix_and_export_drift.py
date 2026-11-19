import bpy
import bmesh
import math
import os
import subprocess
import shutil
from mathutils import Vector, Euler, Matrix

def master_rebuild_and_export():
    print("=== EXECUTING MASTER RIG REBUILD, TIRE REFINEMENT & DRIFT VIDEO EXPORT ===")
    blend_path = r"D:\项目session\blender-supercar\scifi_f1_2035.blend"
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    scene = bpy.context.scene

    out_frames_dir = r"D:\项目session\blender-supercar\drift_frames"
    os.makedirs(out_frames_dir, exist_ok=True)
    out_dir = r"D:\项目session\blender-supercar\final_renders"
    os.makedirs(out_dir, exist_ok=True)
    artifact_dir = r"C:\Users\86052\.gemini\antigravity\brain\fe45f8e6-8741-486f-93a1-a197a7712d30"

    # =========================================================================
    # 1. 轮胎超精细化 PBR 材质与 3D 浮雕 (Tire Detailing & 3D Sidewall)
    # =========================================================================
    # 1.1 胎面热熔竞技橡胶 (Hot-Melt Competition Slick Rubber)
    mat_rubber = bpy.data.materials.get("Mat_PZero_Competition_Rubber")
    if mat_rubber and mat_rubber.node_tree:
        tree = mat_rubber.node_tree
        nodes = tree.nodes
        links = tree.links
        bsdf = nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs['Base Color'].default_value = (0.016, 0.016, 0.018, 1.0)
            bsdf.inputs['Roughness'].default_value = 0.26
            if 'Clearcoat Weight' in bsdf.inputs:
                bsdf.inputs['Clearcoat Weight'].default_value = 0.40
                bsdf.inputs['Clearcoat Roughness'].default_value = 0.18
            elif 'Clearcoat' in bsdf.inputs:
                bsdf.inputs['Clearcoat'].default_value = 0.40
                bsdf.inputs['Clearcoat Roughness'].default_value = 0.18
            
            # 微观颗粒 Bump
            tex_noise = nodes.get("Noise Texture") or nodes.new('ShaderNodeTexNoise')
            tex_noise.inputs['Scale'].default_value = 320.0
            tex_noise.inputs['Detail'].default_value = 10.0
            tex_noise.inputs['Roughness'].default_value = 0.80

            tex_coord = nodes.get("Texture Coordinate") or nodes.new('ShaderNodeTexCoord')
            links.new(tex_coord.outputs['Object'], tex_noise.inputs['Vector'])

            bump = nodes.get("Bump") or nodes.new('ShaderNodeBump')
            bump.inputs['Strength'].default_value = 0.12
            bump.inputs['Distance'].default_value = 0.003
            links.new(tex_noise.outputs['Fac'], bump.inputs['Height'])
            links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])

    # 1.2 胎侧 3D 浮雕凹凸 (Pirelli P ZERO 3D Embossed Relief)
    mat_sidewall = bpy.data.materials.get("Mat_PZero_Pirelli_Sidewall")
    if mat_sidewall and mat_sidewall.node_tree:
        tree_s = mat_sidewall.node_tree
        nodes_s = tree_s.nodes
        links_s = tree_s.links
        bsdf_s = nodes_s.get("Principled BSDF")
        tex_img = nodes_s.get("Image Texture")
        if bsdf_s and tex_img:
            bsdf_s.inputs['Roughness'].default_value = 0.32
            bump_s = nodes_s.get("Bump_Sidewall") or nodes_s.new('ShaderNodeBump')
            bump_s.name = "Bump_Sidewall"
            bump_s.inputs['Strength'].default_value = 0.40
            bump_s.inputs['Distance'].default_value = 0.005
            links_s.new(tex_img.outputs['Alpha'], bump_s.inputs['Height'])
            links_s.new(bump_s.outputs['Normal'], bsdf_s.inputs['Normal'])

    # =========================================================================
    # 2. 完全重置并解绑旧骨骼，获取精确轮心 (Exact Wheel Centers)
    # =========================================================================
    old_rig = bpy.data.objects.get("RIG_F1_Chassis")
    if old_rig:
        for o in bpy.data.objects:
            if o.parent == old_rig:
                mw = o.matrix_world.copy()
                o.parent = None
                o.matrix_world = mw
        bpy.data.objects.remove(old_rig, do_unlink=True)

    # 消除所有可能残存的关键帧和偏移
    for o in bpy.data.objects:
        if o.animation_data:
            o.animation_data_clear()

    # 精确轮心坐标 (经过几何严格校准)
    wheel_centers = {
        'FL': Vector((-1.0677,  1.4500, 0.3550)),
        'FR': Vector(( 1.0677,  1.4500, 0.3550)),
        'RL': Vector((-1.0678, -1.5500, 0.3550)),
        'RR': Vector(( 1.0678, -1.5500, 0.3550)),
    }

    # =========================================================================
    # 3. 构建完全正交向前(+Y)的专业赛车动作骨架 (Standard Forward Vehicle Rig)
    # =========================================================================
    arm_data = bpy.data.armatures.new("RIG_F1_Armature_Master")
    rig_obj = bpy.data.objects.new("RIG_F1_Chassis", arm_data)
    scene.collection.objects.link(rig_obj)

    bpy.context.view_layer.objects.active = rig_obj
    bpy.ops.object.mode_set(mode='EDIT')
    ebs = arm_data.edit_bones

    # 3.1 Root (基座，原点朝向 +Y)
    b_root = ebs.new("Bone_Root")
    b_root.head = Vector((0.0, 0.0, 0.0))
    b_root.tail = Vector((0.0, 1.0, 0.0))

    # 3.2 车身总控 (Chassis_Master):
    # Head at (0, 0, 0.355), Tail at (0, 1.0, 0.355) (向前 +Y)
    # 属性映射:
    # location = (X, Y, Z) 全局位移！
    # rotation_euler.x = Pitch (俯仰: 刹车点头 / 加速后仰)
    # rotation_euler.y = Roll (侧倾: 离心力向外倾斜)
    # rotation_euler.z = Yaw (偏航: 漂移大角度过弯)
    b_chassis = ebs.new("Bone_Chassis_Master")
    b_chassis.head = Vector((0.0, 0.0, 0.355))
    b_chassis.tail = Vector((0.0, 1.0, 0.355))
    b_chassis.parent = b_root

    # 3.3 左右前轮转向节 Hub:
    # 头部在各自轮心，尾部向前 +Y!
    # 当旋转本地 Z 轴 (rotation_euler.z) 时，绕垂直轴偏转转向！
    b_hub_fl = ebs.new("Bone_Hub_FL")
    b_hub_fl.head = wheel_centers['FL']
    b_hub_fl.tail = wheel_centers['FL'] + Vector((0.0, 0.5, 0.0))
    b_hub_fl.parent = b_chassis

    b_hub_fr = ebs.new("Bone_Hub_FR")
    b_hub_fr.head = wheel_centers['FR']
    b_hub_fr.tail = wheel_centers['FR'] + Vector((0.0, 0.5, 0.0))
    b_hub_fr.parent = b_chassis

    # 3.4 四个车轮滚动骨骼 (Wheel_FL, Wheel_FR, Wheel_RL, Wheel_RR):
    # 头部在轮心，尾部向前 +Y!
    # 当旋转本地 X 轴 (rotation_euler.x) 时，纯净绕横向轮轴滚动！
    b_whl_fl = ebs.new("Bone_Wheel_FL")
    b_whl_fl.head = wheel_centers['FL']
    b_whl_fl.tail = wheel_centers['FL'] + Vector((0.0, 0.5, 0.0))
    b_whl_fl.parent = b_hub_fl

    b_whl_fr = ebs.new("Bone_Wheel_FR")
    b_whl_fr.head = wheel_centers['FR']
    b_whl_fr.tail = wheel_centers['FR'] + Vector((0.0, 0.5, 0.0))
    b_whl_fr.parent = b_hub_fr

    b_whl_rl = ebs.new("Bone_Wheel_RL")
    b_whl_rl.head = wheel_centers['RL']
    b_whl_rl.tail = wheel_centers['RL'] + Vector((0.0, 0.5, 0.0))
    b_whl_rl.parent = b_chassis

    b_whl_rr = ebs.new("Bone_Wheel_RR")
    b_whl_rr.head = wheel_centers['RR']
    b_whl_rr.tail = wheel_centers['RR'] + Vector((0.0, 0.5, 0.0))
    b_whl_rr.parent = b_chassis

    # 3.5 方向盘骨骼 (Steering_Wheel):
    b_sw = ebs.new("Bone_Steering_Wheel")
    b_sw.head = Vector((0.0, 0.22, 0.62))
    b_sw.tail = Vector((0.0, 0.32, 0.65))
    b_sw.parent = b_chassis

    # 3.6 DRS 尾翼骨骼 (DRS_Flap):
    b_drs = ebs.new("Bone_DRS_Flap")
    b_drs.head = Vector((0.0, -2.35, 1.05))
    b_drs.tail = Vector((0.0, -2.45, 1.15))
    b_drs.parent = b_chassis

    bpy.ops.object.mode_set(mode='OBJECT')

    # =========================================================================
    # 4. 零件精确绑定到骨骼 (Preserving Global Matrices 100%)
    # =========================================================================
    def bind_to_bone(obj, bone_name):
        if not obj:
            return
        mw = obj.matrix_world.copy()
        obj.parent = rig_obj
        obj.parent_type = 'BONE'
        obj.parent_bone = bone_name
        obj.matrix_world = mw

    # 4.1 四轮旋转件 -> 各自 Wheel 骨骼
    for side in ['FL', 'FR', 'RL', 'RR']:
        bone_name = f"Bone_Wheel_{side}"
        base_names = [
            f"GEO_F1_Tire_{side}", f"GEO_F1_WheelCover_{side}", f"GEO_F1_ValveStem_{side}",
            f"GEO_F1_BrakeDisc_{side}", f"GEO_F1_BrakeBell_{side}", f"GEO_F1_Wheel_CenterNut_{side}",
            f"DEC_Tire_Sidewall_{side}"
        ]
        for name in base_names:
            bind_to_bone(bpy.data.objects.get(name), bone_name)
        for o in bpy.data.objects:
            if o.name.startswith(f"GEO_F1_Blade_{side}_") or o.name.startswith(f"GEO_F1_MagSpoke_{side}_") or o.name.startswith(f"GEO_F1_Tire_WearIndicator_{side}_"):
                bind_to_bone(o, bone_name)

    # 4.2 前轮转向静止件 (卡钳、整流罩、导风铲) -> Hub 骨骼
    for name in ["GEO_F1_BrakeCaliper_FL", "GEO_F1_Front_BrakeDrum_L", "GEO_F1_Front_BrakeDuctScoop_L", "GEO_F1_Wheel_AeroDeflector_FL", "GEO_F1_Wheel_DeflectorLight_FL"]:
        bind_to_bone(bpy.data.objects.get(name), "Bone_Hub_FL")

    for name in ["GEO_F1_BrakeCaliper_FR", "GEO_F1_Front_BrakeDrum_R", "GEO_F1_Front_BrakeDuctScoop_R", "GEO_F1_Wheel_AeroDeflector_FR", "GEO_F1_Wheel_DeflectorLight_FR"]:
        bind_to_bone(bpy.data.objects.get(name), "Bone_Hub_FR")

    # 4.3 后轮静止卡钳 -> Chassis
    for name in ["GEO_F1_BrakeCaliper_RL", "GEO_F1_Rear_BrakeDrum_L", "GEO_F1_BrakeCaliper_RR", "GEO_F1_Rear_BrakeDrum_R"]:
        bind_to_bone(bpy.data.objects.get(name), "Bone_Chassis_Master")

    # 4.4 方向盘总成 -> Bone_Steering_Wheel
    for o in bpy.data.objects:
        if o.name in ["GEO_F1_Cockpit_SteeringWheel", "GEO_F1_Steering_LCDScreen", "GEO_F1_Steering_Paddle_Up", "GEO_F1_Steering_Paddle_Down", "GEO_F1_Steering_CoiledCable"] or o.name.startswith("GEO_F1_ShiftLED_") or o.name.startswith("GEO_F1_Steering_Dial_"):
            bind_to_bone(o, "Bone_Steering_Wheel")

    # 4.5 DRS 尾翼副翼 -> Bone_DRS_Flap
    for name in ["GEO_F1_RearWing_DRSFlap", "DEC_RearWing_Back_RedBull", "DEC_RearWing_Top_Bybit"]:
        bind_to_bone(bpy.data.objects.get(name), "Bone_DRS_Flap")

    # 4.6 车身其余所有部件 -> Bone_Chassis_Master
    exclude_prefixes = ("GEO_Track_", "LGT_", "Cam_", "GEO_F1_Ground_", "GEO_F1_Drift_")
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.parent is None:
            if not any(o.name.startswith(p) for p in exclude_prefixes):
                bind_to_bone(o, "Bone_Chassis_Master")

    # =========================================================================
    # 5. 编排 150 帧真实物理漂移动画 (100% 坐标对齐)
    # =========================================================================
    scene.frame_start = 1
    scene.frame_end = 150
    scene.render.fps = 30

    pose = rig_obj.pose
    p_chassis = pose.bones["Bone_Chassis_Master"]
    p_hub_fl = pose.bones["Bone_Hub_FL"]
    p_hub_fr = pose.bones["Bone_Hub_FR"]
    p_whl_fl = pose.bones["Bone_Wheel_FL"]
    p_whl_fr = pose.bones["Bone_Wheel_FR"]
    p_whl_rl = pose.bones["Bone_Wheel_RL"]
    p_whl_rr = pose.bones["Bone_Wheel_RR"]
    p_sw = pose.bones["Bone_Steering_Wheel"]
    p_drs = pose.bones["Bone_DRS_Flap"]

    for b in [p_chassis, p_hub_fl, p_hub_fr, p_whl_fl, p_whl_fr, p_whl_rl, p_whl_rr, p_sw, p_drs]:
        b.rotation_mode = 'XYZ'

    # 漂移轨迹编排:
    # 车辆在赛道上从 Y = -35.0 冲向 Y = +45.0
    # Frame 1~25: 极速直线 260km/h，DRS 打开 (14°)
    # Frame 35: 重踩刹车，车头下压点头 (Pitch -1.4°)，DRS 闭合 (0°)，刹车盘发光
    # Frame 45: 虚晃进弯切线
    # Frame 65: 甩尾起漂！车身左滑，偏航角 Yaw -22°，前轮疯狂向右大角度反打 (Steer +20°)！
    # Frame 85: 弯心 Apex 极致大角度反打横滑 (Yaw -28°，反打 +23°，侧倾 Roll +2.8°，后轮 1.5倍打滑烧胎)
    # Frame 110: 出弯动力滑移，反打逐渐回中
    # Frame 130: 恢复直线抓地力，车尾回正，加速后仰 (Pitch +0.8°)
    # Frame 150: DRS 再次打开，狂暴冲线

    drift_trajectory = [
        # (frame, x, y, z, pitch_deg, roll_deg, yaw_deg, steer_deg, drs_deg, brake_glow)
        (1,   0.0, -35.0, 0.0,  0.0,  0.0,   0.0,   0.0, 14.0, 0.0),
        (25,  0.0, -12.0, 0.0,  0.0,  0.0,   0.0,   0.0, 14.0, 0.0),
        (35,  0.0,  -4.0, 0.0, -1.4,  0.0,  -1.0,  -6.0,  0.0, 8.5), # 刹车点头
        (48,  0.6,   3.5, 0.0, -0.6, -1.5,  -7.0, -10.0,  0.0, 6.0), # 变向切弯
        (65,  2.0,   9.5, 0.0,  0.2,  2.2, -22.0,  18.0,  0.0, 3.0), # 甩尾起漂反打！
        (85,  3.8,  16.0, 0.0,  0.4,  2.8, -28.0,  23.0,  0.0, 1.0), # 弯心极限横滑 Apex！
        (110, 5.2,  23.5, 0.0,  0.2,  1.6, -18.0,  14.0,  0.0, 0.0), # 动力滑移出弯
        (130, 5.8,  32.5, 0.0,  0.6,  0.4,  -4.0,   2.0,  0.0, 0.0), # 抓地回正
        (150, 6.0,  45.0, 0.0,  0.0,  0.0,   0.0,   0.0, 14.0, 0.0), # DRS重新弹开加速
    ]

    mat_brake_hot = bpy.data.materials.get("Mat_BrakeDisc_Hot")
    bsdf_brake = mat_brake_hot.node_tree.nodes.get("Principled BSDF") if mat_brake_hot else None

    total_roll_front = 0.0
    total_roll_rear = 0.0

    for i in range(len(drift_trajectory)):
        f, x, y, z, pitch, roll, yaw, steer, drs_ang, glow = drift_trajectory[i]
        scene.frame_set(f)

        # 车身位移与姿态 (完全对应的 Euler: X=Pitch, Y=Roll, Z=Yaw)
        p_chassis.location = Vector((x, y, z))
        p_chassis.rotation_euler = Euler((math.radians(pitch), math.radians(roll), math.radians(yaw)))
        p_chassis.keyframe_insert(data_path="location", frame=f)
        p_chassis.keyframe_insert(data_path="rotation_euler", frame=f)

        # 前轮 Hub 绕垂直 Z 轴精确转向 (Steer)
        p_hub_fl.rotation_euler = Euler((0.0, 0.0, math.radians(steer)))
        p_hub_fl.keyframe_insert(data_path="rotation_euler", frame=f)
        p_hub_fr.rotation_euler = Euler((0.0, 0.0, math.radians(steer)))
        p_hub_fr.keyframe_insert(data_path="rotation_euler", frame=f)

        # 方向盘沿转向柱反向旋转联动
        p_sw.rotation_euler = Euler((0.0, math.radians(-steer * 4.2), 0.0))
        p_sw.keyframe_insert(data_path="rotation_euler", frame=f)

        # DRS 尾翼开合
        p_drs.rotation_euler = Euler((math.radians(drs_ang), 0.0, 0.0))
        p_drs.keyframe_insert(data_path="rotation_euler", frame=f)

        # 车轮纯净沿 X 轴向前滚动计算 (半径 R = 0.355m)
        if i > 0:
            prev = drift_trajectory[i-1]
            dist = math.hypot(x - prev[1], y - prev[2])
            total_roll_front += dist / 0.355
            # 漂移区间 (Frame 50~110) 后轮 1.45 倍烧胎空转打滑
            slip = 1.45 if 50 <= f <= 110 else 1.0
            total_roll_rear += (dist / 0.355) * slip

        # 4轮纯物理 X 轴正向滚动
        p_whl_fl.rotation_euler = Euler((total_roll_front, 0.0, 0.0))
        p_whl_fl.keyframe_insert(data_path="rotation_euler", frame=f)
        p_whl_fr.rotation_euler = Euler((total_roll_front, 0.0, 0.0))
        p_whl_fr.keyframe_insert(data_path="rotation_euler", frame=f)

        p_whl_rl.rotation_euler = Euler((total_roll_rear, 0.0, 0.0))
        p_whl_rl.keyframe_insert(data_path="rotation_euler", frame=f)
        p_whl_rr.rotation_euler = Euler((total_roll_rear, 0.0, 0.0))
        p_whl_rr.keyframe_insert(data_path="rotation_euler", frame=f)

        # 刹车盘发光
        if bsdf_brake and 'Emission Strength' in bsdf_brake.inputs:
            bsdf_brake.inputs['Emission Strength'].default_value = glow
            bsdf_brake.inputs['Emission Strength'].keyframe_insert(data_path="default_value", frame=f)

    # =========================================================================
    # 6. 严谨构图的电影级追踪摄影机 (Cinematic Action Tracking Camera)
    # =========================================================================
    cam_drift = bpy.data.objects.get("Cam_F1_Drift_Action")
    if not cam_drift:
        cam_d = bpy.data.cameras.new("Cam_F1_Drift_Action_Data")
        cam_drift = bpy.data.objects.new("Cam_F1_Drift_Action", cam_d)
        scene.collection.objects.link(cam_drift)

    cam_drift.data.lens = 42.0
    cam_drift.data.clip_start = 0.1
    cam_drift.data.clip_end = 500.0

    # 动态追踪点 (确保赛车始终在画面黄金分割区域，全车清晰可见)
    cam_keyframes = [
        # (frame, cam_loc, target_loc)
        (1,   Vector((6.5, -20.0, 0.85)), Vector((0.0, -35.0, 0.4))),
        (25,  Vector((7.0,  -3.0, 0.80)), Vector((0.0, -12.0, 0.4))),
        (48,  Vector((7.5,   6.0, 0.75)), Vector((0.6,   3.5, 0.4))),
        (65,  Vector((8.2,  11.5, 0.70)), Vector((2.0,   9.5, 0.4))),
        (85,  Vector((8.8,  17.5, 0.65)), Vector((3.8,  16.0, 0.4))), # 弯心近距离超低贴地反打特写！
        (110, Vector((9.2,  26.0, 0.75)), Vector((5.2,  23.5, 0.4))),
        (130, Vector((9.5,  34.0, 0.80)), Vector((5.8,  32.5, 0.4))),
        (150, Vector((9.8,  44.0, 0.90)), Vector((6.0,  45.0, 0.4))),
    ]

    for f, c_loc, t_loc in cam_keyframes:
        scene.frame_set(f)
        cam_drift.location = c_loc
        direction = t_loc - c_loc
        rot_quat = direction.to_track_quat('-Z', 'Y')
        euler = rot_quat.to_euler()
        if 65 <= f <= 100:
            euler.y += math.radians(2.5) # 荷兰倾角
        cam_drift.rotation_euler = euler
        cam_drift.keyframe_insert(data_path="location", frame=f)
        cam_drift.keyframe_insert(data_path="rotation_euler", frame=f)

    scene.camera = cam_drift
    scene.frame_set(85)

    # 保存工程
    bpy.ops.wm.save_mainfile(filepath=blend_path)
    print("=== MAIN BLEND FILE SAVED WITH REBUILT RIG & KEYFRAMES ===")

    # =========================================================================
    # 7. 渲染 1080P 30FPS H.264 视频与弯心高光帧
    # =========================================================================
    # 7.1 渲染弯心高光帧 (Frame 85) Cycles GPU
    print(">>> Rendering Cycles Apex Still (Frame 85)...")
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'GPU'
    scene.cycles.samples = 96
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
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

    apex_path = os.path.join(out_dir, "f1_drift_f085_apex_countersteer.png")
    scene.render.filepath = apex_path
    bpy.ops.render.render(write_still=True)
    shutil.copy2(apex_path, os.path.join(artifact_dir, "f1_drift_f085_apex_countersteer.png"))
    print(f"Cycles Apex Still Saved: {apex_path}")

    # 7.2 渲染 150 帧序列并用 FFmpeg 编码最终 MP4
    print(">>> Rendering 150 frames via EEVEE...")
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.image_settings.file_format = 'JPEG'
    scene.render.image_settings.quality = 95
    scene.render.fps = 30
    scene.frame_start = 1
    scene.frame_end = 150
    scene.render.filepath = os.path.join(out_frames_dir, "frame_")

    bpy.ops.render.render(animation=True)
    print("150 Frames Render Complete!")

    final_mp4 = os.path.join(out_dir, "f1_drift_cinematic_1080p.mp4")
    if os.path.exists(final_mp4):
        os.remove(final_mp4)

    cmd = [
        r"C:\Users\86052\scoop\shims\ffmpeg.exe",
        "-y",
        "-framerate", "30",
        "-i", os.path.join(out_frames_dir, "frame_%04d.jpg"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "18",
        "-preset", "fast",
        final_mp4
    ]
    print(">>> Encoding MP4 via FFmpeg...")
    subprocess.run(cmd, check=True)
    print(f"Final MP4 Video Generated: {final_mp4}")

    # 同步到 Artifacts 目录
    dst_mp4 = os.path.join(artifact_dir, "f1_drift_cinematic_1080p.mp4")
    shutil.copy2(final_mp4, dst_mp4)
    print(f"Synced Final MP4 Video to Artifacts: {dst_mp4}")
    print("=== MASTER PIPELINE FINISHED SUCCESSFULLY ===")

if __name__ == '__main__':
    master_rebuild_and_export()
