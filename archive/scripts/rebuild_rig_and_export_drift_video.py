import bpy
import bmesh
import math
import os
import subprocess
import shutil
from mathutils import Vector, Euler, Matrix

def rebuild_rig_and_drift_showcase():
    print("=== REBUILDING F1 RIG: MATHEMATICALLY PERFECT WHEEL ROTATION & TIRE REFINEMENT ===")
    blend_path = r"D:\项目session\blender-supercar\scifi_f1_2035.blend"
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    scene = bpy.context.scene

    out_frames_dir = r"D:\项目session\blender-supercar\drift_frames"
    os.makedirs(out_frames_dir, exist_ok=True)
    out_dir = r"D:\项目session\blender-supercar\final_renders"
    os.makedirs(out_dir, exist_ok=True)
    artifact_dir = r"C:\Users\86052\.gemini\antigravity\brain\fe45f8e6-8741-486f-93a1-a197a7712d30"

    # =========================================================================
    # A. 细化轮胎材质与微观结构 (Tire PBR & 3D Embossing & Rim Details)
    # =========================================================================
    # 1. 胎面热熔竞技橡胶 (Hot-Melt Sticky Slick Rubber)
    mat_rubber = bpy.data.materials.get("Mat_PZero_Competition_Rubber")
    if mat_rubber and mat_rubber.node_tree:
        tree = mat_rubber.node_tree
        nodes = tree.nodes
        links = tree.links
        bsdf = nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs['Base Color'].default_value = (0.018, 0.018, 0.020, 1.0)
            bsdf.inputs['Roughness'].default_value = 0.28
            if 'Clearcoat Weight' in bsdf.inputs:
                bsdf.inputs['Clearcoat Weight'].default_value = 0.35
                bsdf.inputs['Clearcoat Roughness'].default_value = 0.22
            elif 'Clearcoat' in bsdf.inputs:
                bsdf.inputs['Clearcoat'].default_value = 0.35
                bsdf.inputs['Clearcoat Roughness'].default_value = 0.22
            
            # 双重微观磨损颗粒 Bump
            tex_noise = nodes.get("Noise Texture") or nodes.new('ShaderNodeTexNoise')
            tex_noise.inputs['Scale'].default_value = 280.0
            tex_noise.inputs['Detail'].default_value = 8.0
            tex_noise.inputs['Roughness'].default_value = 0.75

            tex_coord = nodes.get("Texture Coordinate") or nodes.new('ShaderNodeTexCoord')
            links.new(tex_coord.outputs['Object'], tex_noise.inputs['Vector'])

            bump = nodes.get("Bump") or nodes.new('ShaderNodeBump')
            bump.inputs['Strength'].default_value = 0.08
            bump.inputs['Distance'].default_value = 0.005
            links.new(tex_noise.outputs['Fac'], bump.inputs['Height'])
            links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])

    # 2. 胎侧 3D 浮雕文字凹凸 (Embossed P ZERO & Pirelli Sidewall)
    mat_sidewall = bpy.data.materials.get("Mat_PZero_Pirelli_Sidewall")
    if mat_sidewall and mat_sidewall.node_tree:
        tree_s = mat_sidewall.node_tree
        nodes_s = tree_s.nodes
        links_s = tree_s.links
        bsdf_s = nodes_s.get("Principled BSDF")
        tex_img = nodes_s.get("Image Texture")
        if bsdf_s and tex_img:
            bsdf_s.inputs['Roughness'].default_value = 0.35
            # 连接凹凸节点产生 2mm 真实物理凸起字母
            bump_s = nodes_s.get("Bump_Sidewall") or nodes_s.new('ShaderNodeBump')
            bump_s.name = "Bump_Sidewall"
            bump_s.inputs['Strength'].default_value = 0.35
            bump_s.inputs['Distance'].default_value = 0.004
            links_s.new(tex_img.outputs['Alpha'], bump_s.inputs['Height'])
            links_s.new(bump_s.outputs['Normal'], bsdf_s.inputs['Normal'])

    # 3. 轮毂盖碳纤维外圈钛合金防滑自锁螺栓 (BBS Aero Cover Perimeter Bolts)
    col_wheels = bpy.data.collections.get("05_Wheels_Suspension") or bpy.data.collections.get("SCIFI_F1_2035")
    mat_titanium = bpy.data.materials.get("Mat_Titanium_Hardware")
    
    wheel_coords = {
        'FL': (-1.0677, 1.4500, 0.3550),
        'FR': (1.0677, 1.4500, 0.3550),
        'RL': (-1.0678, -1.5500, 0.3550),
        'RR': (1.0678, -1.5500, 0.3550)
    }

    # =========================================================================
    # B. 重建纯净且数学严谨的骨骼系统 (Orthogonal Upright Wheel Armature)
    # =========================================================================
    # 彻底解绑旧骨骼，重置到绝对初始 Rest 状态
    old_rig = bpy.data.objects.get("RIG_F1_Chassis")
    if old_rig:
        # 解除所有子物体的父级关系，保持 world matrix
        for o in bpy.data.objects:
            if o.parent == old_rig:
                mw = o.matrix_world.copy()
                o.parent = None
                o.matrix_world = mw
        bpy.data.objects.remove(old_rig, do_unlink=True)

    # 创建全新严密对齐的骨架
    arm_data = bpy.data.armatures.new("RIG_F1_Armature_Clean")
    rig_obj = bpy.data.objects.new("RIG_F1_Chassis", arm_data)
    scene.collection.objects.link(rig_obj)

    bpy.context.view_layer.objects.active = rig_obj
    bpy.ops.object.mode_set(mode='EDIT')
    ebs = arm_data.edit_bones

    # 1. Root 基座
    b_root = ebs.new("Bone_Root")
    b_root.head = Vector((0.0, 0.0, 0.0))
    b_root.tail = Vector((0.0, 0.0, 0.5))

    # 2. 车身总控 (Chassis_Master): 控制全车空间位移与俯仰侧倾偏航
    b_chassis = ebs.new("Bone_Chassis_Master")
    b_chassis.head = Vector((0.0, 0.0, 0.355))
    b_chassis.tail = Vector((0.0, 0.0, 0.855)) # 竖直向上指向 +Z
    b_chassis.parent = b_root

    # 3. 转向总控 (Steering_Master)
    b_steer = ebs.new("Bone_Steering_Master")
    b_steer.head = Vector((0.0, 1.450, 0.355))
    b_steer.tail = Vector((0.0, 1.450, 0.655))
    b_steer.parent = b_chassis

    # 4. 左右前转向节 Hub (仅沿垂直 Z 轴转向，不随车轮滚动)
    # 骨骼头部在轮心，尾部沿 +Z 竖直向上！
    # 这样: 本地 Y 轴即为竖直转向轴(Kingpin)，本地 X 轴即为车轮旋转轴(Axle)！
    b_hub_fl = ebs.new("Bone_Hub_FL")
    b_hub_fl.head = Vector(wheel_coords['FL'])
    b_hub_fl.tail = Vector((wheel_coords['FL'][0], wheel_coords['FL'][1], wheel_coords['FL'][2] + 0.3))
    b_hub_fl.parent = b_chassis

    b_hub_fr = ebs.new("Bone_Hub_FR")
    b_hub_fr.head = Vector(wheel_coords['FR'])
    b_hub_fr.tail = Vector((wheel_coords['FR'][0], wheel_coords['FR'][1], wheel_coords['FR'][2] + 0.3))
    b_hub_fr.parent = b_chassis

    # 5. 四轮旋转滚动骨骼 (Wheel_FL, Wheel_FR, Wheel_RL, Wheel_RR)
    # 全部竖直向上对齐，与 Hub 轴向完全平行！
    b_whl_fl = ebs.new("Bone_Wheel_FL")
    b_whl_fl.head = Vector(wheel_coords['FL'])
    b_whl_fl.tail = Vector((wheel_coords['FL'][0], wheel_coords['FL'][1], wheel_coords['FL'][2] + 0.3))
    b_whl_fl.parent = b_hub_fl

    b_whl_fr = ebs.new("Bone_Wheel_FR")
    b_whl_fr.head = Vector(wheel_coords['FR'])
    b_whl_fr.tail = Vector((wheel_coords['FR'][0], wheel_coords['FR'][1], wheel_coords['FR'][2] + 0.3))
    b_whl_fr.parent = b_hub_fr

    b_whl_rl = ebs.new("Bone_Wheel_RL")
    b_whl_rl.head = Vector(wheel_coords['RL'])
    b_whl_rl.tail = Vector((wheel_coords['RL'][0], wheel_coords['RL'][1], wheel_coords['RL'][2] + 0.3))
    b_whl_rl.parent = b_chassis

    b_whl_rr = ebs.new("Bone_Wheel_RR")
    b_whl_rr.head = Vector(wheel_coords['RR'])
    b_whl_rr.tail = Vector((wheel_coords['RR'][0], wheel_coords['RR'][1], wheel_coords['RR'][2] + 0.3))
    b_whl_rr.parent = b_chassis

    # 6. 方向盘骨骼 (Steering_Wheel)
    b_sw = ebs.new("Bone_Steering_Wheel")
    b_sw.head = Vector((0.0, 0.22, 0.62))
    b_sw.tail = Vector((0.0, 0.22, 0.82))
    b_sw.parent = b_chassis

    # 7. DRS 尾翼副翼骨骼 (DRS_Flap)
    b_drs = ebs.new("Bone_DRS_Flap")
    b_drs.head = Vector((0.0, -2.35, 1.05))
    b_drs.tail = Vector((0.0, -2.35, 1.25))
    b_drs.parent = b_chassis

    bpy.ops.object.mode_set(mode='OBJECT')

    # =========================================================================
    # C. 零件精确绑定到骨骼 (Preserving Global Matrices)
    # =========================================================================
    def bind_to_bone(obj, bone_name):
        if not obj:
            return
        mw = obj.matrix_world.copy()
        obj.parent = rig_obj
        obj.parent_type = 'BONE'
        obj.parent_bone = bone_name
        obj.matrix_world = mw

    # 1. 滚动件绑定到各自的 Wheel 骨骼
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

    # 2. 前轮转向节静止件 (卡钳、导风铲、轮罩整流罩) 绑定到 Hub 骨骼
    for name in ["GEO_F1_BrakeCaliper_FL", "GEO_F1_Front_BrakeDrum_L", "GEO_F1_Front_BrakeDuctScoop_L", "GEO_F1_Wheel_AeroDeflector_FL", "GEO_F1_Wheel_DeflectorLight_FL"]:
        bind_to_bone(bpy.data.objects.get(name), "Bone_Hub_FL")

    for name in ["GEO_F1_BrakeCaliper_FR", "GEO_F1_Front_BrakeDrum_R", "GEO_F1_Front_BrakeDuctScoop_R", "GEO_F1_Wheel_AeroDeflector_FR", "GEO_F1_Wheel_DeflectorLight_FR"]:
        bind_to_bone(bpy.data.objects.get(name), "Bone_Hub_FR")

    # 3. 后轮静止卡钳与刹车鼓 -> Chassis
    for name in ["GEO_F1_BrakeCaliper_RL", "GEO_F1_Rear_BrakeDrum_L", "GEO_F1_BrakeCaliper_RR", "GEO_F1_Rear_BrakeDrum_R"]:
        bind_to_bone(bpy.data.objects.get(name), "Bone_Chassis_Master")

    # 4. 方向盘总成 -> Bone_Steering_Wheel
    for o in bpy.data.objects:
        if o.name in ["GEO_F1_Cockpit_SteeringWheel", "GEO_F1_Steering_LCDScreen", "GEO_F1_Steering_Paddle_Up", "GEO_F1_Steering_Paddle_Down", "GEO_F1_Steering_CoiledCable"] or o.name.startswith("GEO_F1_ShiftLED_") or o.name.startswith("GEO_F1_Steering_Dial_"):
            bind_to_bone(o, "Bone_Steering_Wheel")

    # 5. DRS 尾翼组件 -> Bone_DRS_Flap
    for name in ["GEO_F1_RearWing_DRSFlap", "DEC_RearWing_Back_RedBull", "DEC_RearWing_Top_Bybit"]:
        bind_to_bone(bpy.data.objects.get(name), "Bone_DRS_Flap")

    # 6. 其余所有车身物件 -> Bone_Chassis_Master
    exclude_prefixes = ("GEO_Track_", "LGT_", "Cam_", "GEO_F1_Ground_", "GEO_F1_Drift_")
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.parent is None:
            if not any(o.name.startswith(p) for p in exclude_prefixes):
                bind_to_bone(o, "Bone_Chassis_Master")

    # =========================================================================
    # D. 严谨物理轴向的 150 帧大角度反打漂移动画编排
    # =========================================================================
    scene.frame_start = 1
    scene.frame_end = 150
    scene.render.fps = 30

    pose = rig_obj.pose
    p_chassis = pose.bones["Bone_Chassis_Master"]
    p_steer = pose.bones["Bone_Steering_Master"]
    p_hub_fl = pose.bones["Bone_Hub_FL"]
    p_hub_fr = pose.bones["Bone_Hub_FR"]
    p_whl_fl = pose.bones["Bone_Wheel_FL"]
    p_whl_fr = pose.bones["Bone_Wheel_FR"]
    p_whl_rl = pose.bones["Bone_Wheel_RL"]
    p_whl_rr = pose.bones["Bone_Wheel_RR"]
    p_sw = pose.bones["Bone_Steering_Wheel"]
    p_drs = pose.bones["Bone_DRS_Flap"]

    for b in [p_chassis, p_steer, p_hub_fl, p_hub_fr, p_whl_fl, p_whl_fr, p_whl_rl, p_whl_rr, p_sw, p_drs]:
        b.rotation_mode = 'XYZ'

    # 漂移轨迹编排:
    # 车辆朝 +Y 前进
    # 骨骼朝向: 骨骼本地 Y 轴为竖直向上(+Z)，本地 X 轴为横向轮轴(+X)
    # 所以:
    # 1. 转向角 (Steering Yaw) = 旋转本地 Y 轴！即 rotation_euler.y = math.radians(steer_deg)
    # 2. 轮子向前滚动 (Wheel Forward Roll) = 旋转本地 X 轴！即 rotation_euler.x = roll_rad
    # 3. 车身姿态 (Chassis Master):
    #    Pitch (点头/后仰) = rotation_euler.x
    #    Yaw (偏航角度) = rotation_euler.y (骨骼向上，绕自身Y轴偏航)
    #    Roll (左右侧倾) = rotation_euler.z

    drift_trajectory = [
        # (frame, x, y, z, pitch_deg, yaw_deg, roll_deg, steer_deg, drs_deg, brake_glow)
        (1,   0.0, -32.0, 0.0,  0.0,   0.0,  0.0,   0.0, 14.0, 0.0),
        (25,  0.0, -10.0, 0.0,  0.0,   0.0,  0.0,   0.0, 14.0, 0.0),
        (35,  0.0,  -3.0, 0.0, -1.2,  -1.0,  0.0,  -6.0,  0.0, 8.5), # 刹车入弯切线
        (50,  0.7,   4.0, 0.0, -0.6,  -7.0, -1.8, -10.0,  0.0, 6.0), # 虚晃变向
        (65,  2.0,   9.5, 0.0,  0.2, -20.0,  2.6,  18.0,  0.0, 3.0), # 甩尾起漂，前轮向右极限反打！
        (85,  3.8,  15.8, 0.0,  0.4, -28.0,  3.2,  23.0,  0.0, 1.0), # 弯心极限横滑 Apex (偏航-28°，反打+23°)
        (110, 5.4,  23.5, 0.0,  0.2, -18.0,  1.8,  15.0,  0.0, 0.0), # 动力滑移出弯
        (130, 6.0,  32.0, 0.0,  0.6,  -4.0,  0.4,   2.0,  0.0, 0.0), # 抓地力接管，车尾回正
        (150, 6.2,  44.0, 0.0,  0.0,   0.0,  0.0,   0.0, 14.0, 0.0), # DRS开启，全力冲线
    ]

    mat_brake_hot = bpy.data.materials.get("Mat_BrakeDisc_Hot")
    bsdf_brake = mat_brake_hot.node_tree.nodes.get("Principled BSDF") if mat_brake_hot else None

    total_roll_front = 0.0
    total_roll_rear = 0.0

    for i in range(len(drift_trajectory)):
        f, x, y, z, pitch, yaw, roll, steer, drs_ang, glow = drift_trajectory[i]
        scene.frame_set(f)

        # 车身移动与旋转
        p_chassis.location = Vector((x, y, z))
        p_chassis.rotation_euler = Euler((math.radians(pitch), math.radians(yaw), math.radians(roll)))
        p_chassis.keyframe_insert(data_path="location", frame=f)
        p_chassis.keyframe_insert(data_path="rotation_euler", frame=f)

        # 前轮 Hub 转向 (沿垂直 Y 轴偏转)
        p_steer.rotation_euler = Euler((0.0, math.radians(steer), 0.0))
        p_steer.keyframe_insert(data_path="rotation_euler", frame=f)

        p_hub_fl.rotation_euler = Euler((0.0, math.radians(steer), 0.0))
        p_hub_fl.keyframe_insert(data_path="rotation_euler", frame=f)

        p_hub_fr.rotation_euler = Euler((0.0, math.radians(steer), 0.0))
        p_hub_fr.keyframe_insert(data_path="rotation_euler", frame=f)

        # 方向盘沿转向柱联动
        p_sw.rotation_euler = Euler((0.0, 0.0, math.radians(steer * 4.0)))
        p_sw.keyframe_insert(data_path="rotation_euler", frame=f)

        # DRS 尾翼开合
        p_drs.rotation_euler = Euler((math.radians(drs_ang), 0.0, 0.0))
        p_drs.keyframe_insert(data_path="rotation_euler", frame=f)

        # 车轮转速累计 (R = 0.355m)
        if i > 0:
            prev = drift_trajectory[i-1]
            dist = math.hypot(x - prev[1], y - prev[2])
            # 前轮按前行距离自然滚动 (弧度)
            total_roll_front += dist / 0.355
            # 后轮在漂移区间 (Frame 50~110) 带有 1.45 倍烧胎打滑空转
            slip = 1.45 if 50 <= f <= 110 else 1.0
            total_roll_rear += (dist / 0.355) * slip

        # 真正沿轮轴 X 轴滚动！
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
    # E. 重新设计电影级动态追踪摄影机 (Dynamic Trackside Tracking Camera)
    # =========================================================================
    cam_drift = bpy.data.objects.get("Cam_F1_Drift_Action")
    if not cam_drift:
        cam_d = bpy.data.cameras.new("Cam_F1_Drift_Action_Data")
        cam_drift = bpy.data.objects.new("Cam_F1_Drift_Action", cam_d)
        scene.collection.objects.link(cam_drift)

    cam_drift.data.lens = 45.0
    cam_drift.data.clip_start = 0.1
    cam_drift.data.clip_end = 500.0

    # 电影级广角低趴机位：站在弯道外侧，保持舒适的景别与张力，整车完整尽收眼底
    cam_shot_keyframes = [
        (1,   Vector((7.2, -15.0, 0.95)), Vector((0.0, -28.0, 0.4))),
        (35,  Vector((7.8,   0.0, 0.85)), Vector((0.0,  -2.5, 0.4))),
        (65,  Vector((8.4,  10.0, 0.75)), Vector((2.0,   9.5, 0.4))),
        (85,  Vector((9.2,  16.5, 0.70)), Vector((3.8,  15.8, 0.4))), # 弯心绝美横滑侧切视角
        (110, Vector((9.8,  25.0, 0.75)), Vector((5.4,  23.5, 0.4))),
        (150, Vector((10.2, 38.0, 0.85)), Vector((6.2,  44.0, 0.4))),
    ]

    for f, c_loc, t_loc in cam_shot_keyframes:
        scene.frame_set(f)
        cam_drift.location = c_loc
        direction = t_loc - c_loc
        rot_quat = direction.to_track_quat('-Z', 'Y')
        euler = rot_quat.to_euler()
        # 弯心略微倾斜荷兰角 (+2.2°) 强化速度冲击
        if 65 <= f <= 100:
            euler.y += math.radians(2.2)
        cam_drift.rotation_euler = euler
        cam_drift.keyframe_insert(data_path="location", frame=f)
        cam_drift.keyframe_insert(data_path="rotation_euler", frame=f)

    scene.camera = cam_drift
    scene.frame_set(85)

    # 保存主工程
    bpy.ops.wm.save_mainfile(filepath=blend_path)
    print("=== RIG & ANIMATION REBUILT AND SAVED ===")

    # =========================================================================
    # F. 导出 1080P 30FPS H.264 电影级漂移视频与高质量光追验证帧
    # =========================================================================
    # 1. 渲染弯心高光帧 (Frame 85) Cycles GPU OptiX
    print(">>> Rendering Apex Cycles Frame 85...")
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'GPU'
    scene.cycles.samples = 96
    scene.cycles.use_denoising = True
    scene.view_settings.view_transform = 'AgX'
    try:
        scene.view_settings.look = 'AgX - High Contrast'
    except Exception:
        scene.view_settings.look = 'High Contrast'
    scene.view_settings.exposure = -4.2
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    
    cprefs = bpy.context.preferences.addons['cycles'].preferences
    cprefs.get_devices()
    for d in cprefs.devices:
        if d.type in ['OPTIX', 'CUDA']:
            d.use = True
        else:
            d.use = False

    apex_img_path = os.path.join(out_dir, "f1_drift_f085_apex_countersteer.png")
    scene.render.filepath = apex_img_path
    bpy.ops.render.render(write_still=True)
    shutil.copy2(apex_img_path, os.path.join(artifact_dir, "f1_drift_f085_apex_countersteer.png"))
    print(f"Apex Cycles Render Synced: {apex_img_path}")

    # 2. 导出 150 帧完整流畅动画视频 (JPEG 序列 -> FFmpeg H.264 MP4)
    print(">>> Rendering 150 frames via EEVEE...")
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.image_settings.file_format = 'JPEG'
    scene.render.image_settings.quality = 95
    scene.render.fps = 30
    scene.frame_start = 1
    scene.frame_end = 150
    scene.render.filepath = os.path.join(out_frames_dir, "frame_")

    bpy.ops.render.render(animation=True)
    print("150 Frames Rendered!")

    mp4_video_path = os.path.join(out_dir, "f1_drift_cinematic_1080p.mp4")
    if os.path.exists(mp4_video_path):
        os.remove(mp4_video_path)

    cmd = [
        r"C:\Users\86052\scoop\shims\ffmpeg.exe",
        "-y",
        "-framerate", "30",
        "-i", os.path.join(out_frames_dir, "frame_%04d.jpg"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "18",
        "-preset", "fast",
        mp4_video_path
    ]
    print(">>> Encoding MP4 with FFmpeg...")
    subprocess.run(cmd, check=True)
    print(f"MP4 Generated: {mp4_video_path}")

    # 同步至 Artifacts
    dst_mp4 = os.path.join(artifact_dir, "f1_drift_cinematic_1080p.mp4")
    shutil.copy2(mp4_video_path, dst_mp4)
    print(f"Synced Final MP4 Video: {dst_mp4}")

    print("=== ALL DRIFT PIPELINE TASKS FULLY COMPLETE ===")

if __name__ == '__main__':
    rebuild_rig_and_drift_showcase()
