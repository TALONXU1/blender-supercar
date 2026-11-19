import bpy
import bmesh
import math
import os
from mathutils import Vector, Euler, Matrix

def create_f1_rig_and_drift():
    print("=== BUILDING F1 SKELETAL RIG & DRIFT ANIMATION ===")
    blend_path = r"D:\项目session\blender-supercar\scifi_f1_2035.blend"
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    scene = bpy.context.scene

    # =========================================================================
    # 1. 深入细化机械建模 (Cockpit Pedals, Harness Buckle, Coiled Cable, Vortex Fins)
    # =========================================================================
    col_cockpit = bpy.data.collections.get("06_Cockpit_Interior") or bpy.data.collections.get("SCIFI_F1_2035")
    col_aero = bpy.data.collections.get("04_Wings_Aerodynamics") or bpy.data.collections.get("SCIFI_F1_2035")
    
    mat_titanium = bpy.data.materials.get("Mat_Titanium_Hardware")
    mat_carbon = bpy.data.materials.get("Mat_Forged_Carbon") or bpy.data.materials.get("Mat_Carbon_Fiber")
    mat_red = bpy.data.materials.get("Mat_RedBull_Crimson")
    mat_gold = bpy.data.materials.get("Mat_Anodized_Gold")

    def add_mesh_obj(name, col, mat, bm_func):
        mesh = bpy.data.meshes.new(f"{name}_Mesh")
        bm = bmesh.new()
        bm_func(bm)
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.get(name)
        if not obj:
            obj = bpy.data.objects.new(name, mesh)
            col.objects.link(obj)
        else:
            obj.data = mesh
        if mat:
            obj.data.materials.clear()
            obj.data.materials.append(mat)
        return obj

    # 1.1 驾驶舱钛合金竞技踏板组 (Brake & Throttle Pedals)
    # 刹车踏板 (宽踏板，打孔防滑)
    def bm_brake(bm):
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(0.045, 0.015, 0.08), verts=bm.verts)
        bmesh.ops.rotate(bm, cent=(0,0,0), matrix=Euler((math.radians(-25), 0, 0)).to_matrix(), verts=bm.verts)
        bmesh.ops.translate(bm, vec=(-0.05, 0.82, 0.26), verts=bm.verts)
    add_mesh_obj("GEO_F1_Pedal_Brake", col_cockpit, mat_titanium, bm_brake)

    # 油门踏板 (长窄条形)
    def bm_throttle(bm):
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(0.025, 0.012, 0.095), verts=bm.verts)
        bmesh.ops.rotate(bm, cent=(0,0,0), matrix=Euler((math.radians(-25), 0, 0)).to_matrix(), verts=bm.verts)
        bmesh.ops.translate(bm, vec=(0.05, 0.84, 0.25), verts=bm.verts)
    add_mesh_obj("GEO_F1_Pedal_Throttle", col_cockpit, mat_titanium, bm_throttle)

    # 1.2 六点式安全带中央阳极氧化红快拆锁扣 (6-Point Harness Rotary Camlock)
    def bm_camlock(bm):
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=24, radius1=0.038, radius2=0.036, depth=0.02)
        bmesh.ops.rotate(bm, cent=(0,0,0), matrix=Euler((math.radians(70), 0, 0)).to_matrix(), verts=bm.verts)
        bmesh.ops.translate(bm, vec=(0.0, 0.04, 0.33), verts=bm.verts)
    add_mesh_obj("GEO_F1_Seatbelt_Camlock", col_cockpit, mat_red, bm_camlock)

    # 1.3 方向盘弹簧螺旋数据线缆 (Coiled Telemetry Harness Cable)
    def bm_cable(bm):
        # 螺旋弹簧线圈造型
        segs = 48
        r_spiral = 0.016
        pitch = 0.003
        for i in range(segs):
            theta = i * 0.5
            cx = math.sin(theta) * r_spiral
            cz = math.cos(theta) * r_spiral + 0.52
            cy = 0.16 + i * pitch
            # 小圆环顶点
            v1 = bm.verts.new((cx, cy, cz))
            v2 = bm.verts.new((cx + 0.003, cy, cz + 0.003))
    add_mesh_obj("GEO_F1_Steering_CoiledCable", col_cockpit, mat_carbon, bm_cable)

    # 1.4 车头两侧碳纤维涡流发生刀片 (Nose Bulkhead Vortex Generators)
    for side, sign in [("L", -1), ("R", 1)]:
        def bm_vortex(bm):
            bmesh.ops.create_cube(bm, size=1.0)
            bmesh.ops.scale(bm, vec=(0.004, 0.045, 0.025), verts=bm.verts)
            bmesh.ops.rotate(bm, cent=(0,0,0), matrix=Euler((0, 0, math.radians(sign * 18))).to_matrix(), verts=bm.verts)
            bmesh.ops.translate(bm, vec=(sign * 0.21, 1.48, 0.46), verts=bm.verts)
        add_mesh_obj(f"GEO_F1_Nose_VortexFin_{side}", col_aero, mat_carbon, bm_vortex)

    # =========================================================================
    # 2. 碳陶制动盘高温热发光着色器 (Glowing Hot Brake Disc Shader)
    # =========================================================================
    mat_brake_hot = bpy.data.materials.get("Mat_BrakeDisc_Hot")
    if not mat_brake_hot:
        mat_brake_hot = bpy.data.materials.new("Mat_BrakeDisc_Hot")
        mat_brake_hot.use_nodes = True
    
    nodes_b = mat_brake_hot.node_tree.nodes
    links_b = mat_brake_hot.node_tree.links
    bsdf_b = nodes_b.get("Principled BSDF")
    if bsdf_b:
        bsdf_b.inputs['Base Color'].default_value = (0.04, 0.04, 0.04, 1.0)
        bsdf_b.inputs['Roughness'].default_value = 0.38
        bsdf_b.inputs['Metallic'].default_value = 0.65
        # 发光槽
        if 'Emission Color' in bsdf_b.inputs:
            bsdf_b.inputs['Emission Color'].default_value = (1.0, 0.18, 0.02, 1.0) # 亮炽红橙色
            bsdf_b.inputs['Emission Strength'].default_value = 0.0 # 默认不发光
    
    # 赋予前轮制动盘
    for disc_name in ["GEO_F1_BrakeDisc_FL", "GEO_F1_BrakeDisc_FR"]:
        d_obj = bpy.data.objects.get(disc_name)
        if d_obj:
            d_obj.data.materials.clear()
            d_obj.data.materials.append(mat_brake_hot)

    # =========================================================================
    # 3. 动作骨骼系统构建 (RIG_F1_Chassis Armature)
    # =========================================================================
    rig_obj = bpy.data.objects.get("RIG_F1_Chassis")
    if rig_obj:
        bpy.data.objects.remove(rig_obj, do_unlink=True)
    
    arm_data = bpy.data.armatures.new("RIG_F1_Armature")
    rig_obj = bpy.data.objects.new("RIG_F1_Chassis", arm_data)
    scene.collection.objects.link(rig_obj)
    
    # 切换到 EDIT MODE 创建骨骼
    bpy.context.view_layer.objects.active = rig_obj
    bpy.ops.object.mode_set(mode='EDIT')
    ebs = arm_data.edit_bones

    # 3.1 Root 骨骼 (地面基座)
    b_root = ebs.new("Bone_Root")
    b_root.head = Vector((0.0, 0.0, 0.0))
    b_root.tail = Vector((0.0, 1.0, 0.0))

    # 3.2 车体主骨骼 (Chassis_Master, 控制车体俯仰、侧倾、偏航及坐标位移)
    b_chassis = ebs.new("Bone_Chassis_Master")
    b_chassis.head = Vector((0.0, 0.0, 0.35))
    b_chassis.tail = Vector((0.0, 1.0, 0.35))
    b_chassis.parent = b_root

    # 3.3 转向总控骨骼 (Steering_Master, 旋转 Z 轴驱动左右前轮与座舱方向盘)
    b_steer = ebs.new("Bone_Steering_Master")
    b_steer.head = Vector((0.0, 1.45, 0.35))
    b_steer.tail = Vector((0.0, 1.85, 0.35))
    b_steer.parent = b_chassis

    # 3.4 左右前轮转向轴心 Hub 骨骼 (随转向转动，但不随车轮滚动)
    b_hub_fl = ebs.new("Bone_Hub_FL")
    b_hub_fl.head = Vector((-0.95, 1.45, 0.36))
    b_hub_fl.tail = Vector((-0.95, 1.75, 0.36))
    b_hub_fl.parent = b_chassis

    b_hub_fr = ebs.new("Bone_Hub_FR")
    b_hub_fr.head = Vector((0.95, 1.45, 0.36))
    b_hub_fr.tail = Vector((0.95, 1.75, 0.36))
    b_hub_fr.parent = b_chassis

    # 3.5 四轮滚动骨骼 (Wheel_FL, Wheel_FR, Wheel_RL, Wheel_RR, 旋转 X 轴滚动/漂移打滑)
    b_whl_fl = ebs.new("Bone_Wheel_FL")
    b_whl_fl.head = Vector((-0.95, 1.45, 0.36))
    b_whl_fl.tail = Vector((-1.15, 1.45, 0.36))
    b_whl_fl.parent = b_hub_fl

    b_whl_fr = ebs.new("Bone_Wheel_FR")
    b_whl_fr.head = Vector((0.95, 1.45, 0.36))
    b_whl_fr.tail = Vector((1.15, 1.45, 0.36))
    b_whl_fr.parent = b_hub_fr

    b_whl_rl = ebs.new("Bone_Wheel_RL")
    b_whl_rl.head = Vector((-0.92, -1.55, 0.36))
    b_whl_rl.tail = Vector((-1.15, -1.55, 0.36))
    b_whl_rl.parent = b_chassis

    b_whl_rr = ebs.new("Bone_Wheel_RR")
    b_whl_rr.head = Vector((0.92, -1.55, 0.36))
    b_whl_rr.tail = Vector((1.15, -1.55, 0.36))
    b_whl_rr.parent = b_chassis

    # 3.6 座舱方向盘骨骼 (Steering_Wheel)
    b_sw = ebs.new("Bone_Steering_Wheel")
    b_sw.head = Vector((0.0, 0.22, 0.62))
    b_sw.tail = Vector((0.0, 0.32, 0.65))
    b_sw.parent = b_chassis

    # 3.7 DRS 尾翼主动气动副翼骨骼 (DRS_Flap)
    b_drs = ebs.new("Bone_DRS_Flap")
    b_drs.head = Vector((0.0, -2.35, 1.05))
    b_drs.tail = Vector((0.0, -2.45, 1.15))
    b_drs.parent = b_chassis

    bpy.ops.object.mode_set(mode='OBJECT')

    # =========================================================================
    # 4. 物件绑定到骨骼 (Non-Destructive Bone Parenting with World Matrix Preservation)
    # =========================================================================
    def bind_to_bone(obj, bone_name):
        if not obj:
            return
        mw = obj.matrix_world.copy()
        obj.parent = rig_obj
        obj.parent_type = 'BONE'
        obj.parent_bone = bone_name
        obj.matrix_world = mw

    # 4.1 左前轮旋转部件 -> Bone_Wheel_FL
    # 包括轮胎、轮毂盖、轮毂辐条、气门嘴、刹车盘、胎侧贴纸等
    whl_fl_roll_names = [
        "GEO_F1_Tire_FL", "GEO_F1_WheelCover_FL", "GEO_F1_ValveStem_FL",
        "GEO_F1_BrakeDisc_FL", "GEO_F1_BrakeBell_FL", "GEO_F1_Wheel_CenterNut_FL",
        "DEC_Tire_Sidewall_FL"
    ]
    for o in bpy.data.objects:
        if o.name in whl_fl_roll_names or o.name.startswith("GEO_F1_Blade_FL_") or o.name.startswith("GEO_F1_MagSpoke_FL_") or o.name.startswith("GEO_F1_Tire_WearIndicator_FL_"):
            bind_to_bone(o, "Bone_Wheel_FL")

    # 4.2 左前轮转向但不滚动的部件 -> Bone_Hub_FL (刹车卡钳、刹车导风罩、轮罩整流罩)
    whl_fl_hub_names = [
        "GEO_F1_BrakeCaliper_FL", "GEO_F1_Front_BrakeDrum_L",
        "GEO_F1_Front_BrakeDuctScoop_L", "GEO_F1_Wheel_AeroDeflector_FL",
        "GEO_F1_Wheel_DeflectorLight_FL"
    ]
    for name in whl_fl_hub_names:
        bind_to_bone(bpy.data.objects.get(name), "Bone_Hub_FL")

    # 4.3 右前轮旋转部件 -> Bone_Wheel_FR
    whl_fr_roll_names = [
        "GEO_F1_Tire_FR", "GEO_F1_WheelCover_FR", "GEO_F1_ValveStem_FR",
        "GEO_F1_BrakeDisc_FR", "GEO_F1_BrakeBell_FR", "GEO_F1_Wheel_CenterNut_FR",
        "DEC_Tire_Sidewall_FR"
    ]
    for o in bpy.data.objects:
        if o.name in whl_fr_roll_names or o.name.startswith("GEO_F1_Blade_FR_") or o.name.startswith("GEO_F1_MagSpoke_FR_") or o.name.startswith("GEO_F1_Tire_WearIndicator_FR_"):
            bind_to_bone(o, "Bone_Wheel_FR")

    # 4.4 右前轮转向但不滚动部件 -> Bone_Hub_FR
    whl_fr_hub_names = [
        "GEO_F1_BrakeCaliper_FR", "GEO_F1_Front_BrakeDrum_R",
        "GEO_F1_Front_BrakeDuctScoop_R", "GEO_F1_Wheel_AeroDeflector_FR",
        "GEO_F1_Wheel_DeflectorLight_FR"
    ]
    for name in whl_fr_hub_names:
        bind_to_bone(bpy.data.objects.get(name), "Bone_Hub_FR")

    # 4.5 左后轮旋转部件 -> Bone_Wheel_RL
    whl_rl_roll_names = [
        "GEO_F1_Tire_RL", "GEO_F1_WheelCover_RL", "GEO_F1_ValveStem_RL",
        "GEO_F1_BrakeDisc_RL", "GEO_F1_BrakeBell_RL", "GEO_F1_Wheel_CenterNut_RL",
        "DEC_Tire_Sidewall_RL"
    ]
    for o in bpy.data.objects:
        if o.name in whl_rl_roll_names or o.name.startswith("GEO_F1_Blade_RL_") or o.name.startswith("GEO_F1_MagSpoke_RL_") or o.name.startswith("GEO_F1_Tire_WearIndicator_RL_"):
            bind_to_bone(o, "Bone_Wheel_RL")
    for name in ["GEO_F1_BrakeCaliper_RL", "GEO_F1_Rear_BrakeDrum_L"]:
        bind_to_bone(bpy.data.objects.get(name), "Bone_Chassis_Master")

    # 4.6 右后轮旋转部件 -> Bone_Wheel_RR
    whl_rr_roll_names = [
        "GEO_F1_Tire_RR", "GEO_F1_WheelCover_RR", "GEO_F1_ValveStem_RR",
        "GEO_F1_BrakeDisc_RR", "GEO_F1_BrakeBell_RR", "GEO_F1_Wheel_CenterNut_RR",
        "DEC_Tire_Sidewall_RR"
    ]
    for o in bpy.data.objects:
        if o.name in whl_rr_roll_names or o.name.startswith("GEO_F1_Blade_RR_") or o.name.startswith("GEO_F1_MagSpoke_RR_") or o.name.startswith("GEO_F1_Tire_WearIndicator_RR_"):
            bind_to_bone(o, "Bone_Wheel_RR")
    for name in ["GEO_F1_BrakeCaliper_RR", "GEO_F1_Rear_BrakeDrum_R"]:
        bind_to_bone(bpy.data.objects.get(name), "Bone_Chassis_Master")

    # 4.7 DRS 尾翼上层主翼翼片 -> Bone_DRS_Flap
    bind_to_bone(bpy.data.objects.get("GEO_F1_RearWing_DRSFlap"), "Bone_DRS_Flap")
    bind_to_bone(bpy.data.objects.get("DEC_RearWing_Back_RedBull"), "Bone_DRS_Flap")
    bind_to_bone(bpy.data.objects.get("DEC_RearWing_Top_Bybit"), "Bone_DRS_Flap")

    # 4.8 座舱方向盘组件 -> Bone_Steering_Wheel
    sw_names = [
        "GEO_F1_Cockpit_SteeringWheel", "GEO_F1_Steering_LCDScreen",
        "GEO_F1_Steering_Paddle_Up", "GEO_F1_Steering_Paddle_Down",
        "GEO_F1_Steering_CoiledCable"
    ]
    for o in bpy.data.objects:
        if o.name in sw_names or o.name.startswith("GEO_F1_ShiftLED_") or o.name.startswith("GEO_F1_Steering_Dial_"):
            bind_to_bone(o, "Bone_Steering_Wheel")

    # 4.9 其余所有车身物件(底盘、前翼、侧箱、引擎盖、排气、鲨鱼鳍等) -> Bone_Chassis_Master
    exclude_prefixes = ("GEO_Track_", "LGT_", "Cam_", "GEO_F1_Ground_")
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.parent is None:
            if not any(o.name.startswith(p) for p in exclude_prefixes):
                bind_to_bone(o, "Bone_Chassis_Master")

    # =========================================================================
    # 5. 编排 150 帧真实物理漂移动画 (High-Octane Cinematic Drift Sequence)
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

    p_chassis.rotation_mode = 'XYZ'
    p_steer.rotation_mode = 'XYZ'
    p_hub_fl.rotation_mode = 'XYZ'
    p_hub_fr.rotation_mode = 'XYZ'
    p_whl_fl.rotation_mode = 'XYZ'
    p_whl_fr.rotation_mode = 'XYZ'
    p_whl_rl.rotation_mode = 'XYZ'
    p_whl_rr.rotation_mode = 'XYZ'
    p_sw.rotation_mode = 'XYZ'
    p_drs.rotation_mode = 'XYZ'

    # 漂移轨迹编排 (S弯大角度烟幕反打漂移):
    # F1: 直道末端 260km/h 高速逼近，DRS 开启
    # F30: 刹车重踩，DRS 闭合，车头压缩点头 (Pitch dive -1.2°)，前制动盘发光
    # F45: 进弯切线，向右快速虚晃重心 (Weight transfer flick)
    # F60: 猛烈甩尾突破抓地力极限，车身左滑横移，偏航角暴增至 -26°，前轮疯狂向右反打反打 (Counter-steer +20°)!
    # F85: 弯心 Apex 极致横滑，侧倾 +2.8°，后轮 1.5 倍打滑转速烟幕横飞
    # F115: 弯道出口回正，大马力油门接管，反打逐渐回中
    # F140: 车体剧烈回弹恢复直线，DRS 重新弹开，狂暴加速离去

    drift_keyframes = [
        # (frame, x, y, z, pitch_deg, roll_deg, yaw_deg, steer_deg, drs_deg, brake_glow)
        (1,   0.0, -28.0, 0.0,  0.0,  0.0,   0.0,   0.0, 14.0, 0.0),
        (25,  0.0,  -8.0, 0.0,  0.0,  0.0,   0.0,   0.0, 14.0, 0.0),
        (35,  0.0,  -2.0, 0.0, -1.2,  0.0,  -1.0,  -7.0,  0.0, 8.5), # 刹车点头+入弯切线
        (50,  0.8,   4.5, 0.0, -0.6, -1.5,  -8.0, -12.0,  0.0, 6.0), # 虚晃变向
        (65,  2.2,  10.0, 0.0,  0.2,  2.5, -22.0,  18.0,  0.0, 3.0), # 甩尾起漂，前轮剧烈反打！
        (85,  4.1,  16.5, 0.0,  0.4,  3.2, -28.5,  22.5,  0.0, 1.0), # 弯心极限漂移角度！
        (110, 5.6,  24.0, 0.0,  0.2,  1.8, -20.0,  14.0,  0.0, 0.0), # 出弯动力滑移
        (130, 6.2,  32.5, 0.0,  0.6,  0.4,  -5.0,   3.0,  0.0, 0.0), # 抓地力恢复，加速后仰抬升
        (150, 6.3,  42.0, 0.0,  0.0,  0.0,   0.0,   0.0, 14.0, 0.0), # DRS重新打开，极速冲刺
    ]

    # 插值写入关键帧
    total_wheel_roll_front = 0.0
    total_wheel_roll_rear = 0.0

    # 预先计算车轮滚动
    for i in range(len(drift_keyframes)):
        kf = drift_keyframes[i]
        f, x, y, z, pitch, roll, yaw, steer, drs_ang, glow = kf
        scene.frame_set(f)

        p_chassis.location = Vector((x, y, z))
        p_chassis.rotation_euler = Euler((math.radians(pitch), math.radians(roll), math.radians(yaw)))
        p_chassis.keyframe_insert(data_path="location", frame=f)
        p_chassis.keyframe_insert(data_path="rotation_euler", frame=f)

        # 转向与前轮 Hub 同步反打
        p_steer.rotation_euler = Euler((0.0, 0.0, math.radians(steer)))
        p_steer.keyframe_insert(data_path="rotation_euler", frame=f)

        p_hub_fl.rotation_euler = Euler((0.0, 0.0, math.radians(steer)))
        p_hub_fl.keyframe_insert(data_path="rotation_euler", frame=f)
        p_hub_fr.rotation_euler = Euler((0.0, 0.0, math.radians(steer)))
        p_hub_fr.keyframe_insert(data_path="rotation_euler", frame=f)

        # 座舱方向盘旋转 (按反打比例同向大幅转动)
        p_sw.rotation_euler = Euler((0.0, math.radians(-steer * 4.5), 0.0))
        p_sw.keyframe_insert(data_path="rotation_euler", frame=f)

        # DRS 尾翼开合
        p_drs.rotation_euler = Euler((math.radians(drs_ang), 0.0, 0.0))
        p_drs.keyframe_insert(data_path="rotation_euler", frame=f)

        # 车轮滚动累计
        if i > 0:
            prev_kf = drift_keyframes[i-1]
            dist = math.hypot(x - prev_kf[1], y - prev_kf[2])
            # 前轮按实际路程滚动
            total_wheel_roll_front += dist / 0.36
            # 后轮在漂移段(F50-F110)带打滑空转 (1.45倍加速烧胎)
            slip = 1.45 if 50 <= f <= 110 else 1.0
            total_wheel_roll_rear += (dist / 0.36) * slip

        p_whl_fl.rotation_euler = Euler((total_wheel_roll_front, 0.0, 0.0))
        p_whl_fl.keyframe_insert(data_path="rotation_euler", frame=f)
        p_whl_fr.rotation_euler = Euler((total_wheel_roll_front, 0.0, 0.0))
        p_whl_fr.keyframe_insert(data_path="rotation_euler", frame=f)

        p_whl_rl.rotation_euler = Euler((total_wheel_roll_rear, 0.0, 0.0))
        p_whl_rl.keyframe_insert(data_path="rotation_euler", frame=f)
        p_whl_rr.rotation_euler = Euler((total_wheel_roll_rear, 0.0, 0.0))
        p_whl_rr.keyframe_insert(data_path="rotation_euler", frame=f)

        # 刹车盘高温发光强度关键帧
        if bsdf_b and 'Emission Strength' in bsdf_b.inputs:
            bsdf_b.inputs['Emission Strength'].default_value = glow
            bsdf_b.inputs['Emission Strength'].keyframe_insert(data_path="default_value", frame=f)

    # =========================================================================
    # 6. 赛道漂移烧胎橡胶印 (Procedural Tire Skid Marks on Track)
    # =========================================================================
    mat_skid = bpy.data.materials.get("Mat_Tire_SkidMark")
    if not mat_skid:
        mat_skid = bpy.data.materials.new("Mat_Tire_SkidMark")
        mat_skid.use_nodes = True
        bsdf_skid = mat_skid.node_tree.nodes.get("Principled BSDF")
        if bsdf_skid:
            bsdf_skid.inputs['Base Color'].default_value = (0.015, 0.015, 0.015, 1.0)
            bsdf_skid.inputs['Roughness'].default_value = 0.95
            if hasattr(mat_skid, 'blend_method'):
                mat_skid.blend_method = 'BLEND'

    # 生成一条紧贴地面的双轨漂移胎印带
    mesh_skid = bpy.data.meshes.new("GEO_F1_Drift_SkidMarks_Mesh")
    bm_s = bmesh.new()
    skid_pts = [
        (0.4, 3.0), (1.1, 6.5), (2.4, 11.0), (4.2, 17.5), (5.5, 25.0), (6.1, 33.0)
    ]
    for pt in skid_pts:
        # 左轮与右轮两条黑色胎痕
        bmesh.ops.create_cube(bm_s, size=1.0)
        bmesh.ops.scale(bm_s, vec=(0.28, 1.2, 0.002), verts=bm_s.verts[-8:])
        bmesh.ops.translate(bm_s, vec=(pt[0] - 0.75, pt[1], 0.002), verts=bm_s.verts[-8:])

        bmesh.ops.create_cube(bm_s, size=1.0)
        bmesh.ops.scale(bm_s, vec=(0.28, 1.2, 0.002), verts=bm_s.verts[-8:])
        bmesh.ops.translate(bm_s, vec=(pt[0] + 0.75, pt[1], 0.002), verts=bm_s.verts[-8:])

    bm_s.to_mesh(mesh_skid)
    bm_s.free()
    obj_skid = bpy.data.objects.get("GEO_F1_Drift_SkidMarks")
    if not obj_skid:
        obj_skid = bpy.data.objects.new("GEO_F1_Drift_SkidMarks", mesh_skid)
        scene.collection.objects.link(obj_skid)
    else:
        obj_skid.data = mesh_skid
    obj_skid.data.materials.clear()
    obj_skid.data.materials.append(mat_skid)

    # =========================================================================
    # 7. 电影级动态跟随追踪摄影机 (Cinematic Drift Chase Camera)
    # =========================================================================
    cam_drift = bpy.data.objects.get("Cam_F1_Drift_Action")
    if not cam_drift:
        cam_data_d = bpy.data.cameras.new("Cam_F1_Drift_Action_Data")
        cam_drift = bpy.data.objects.new("Cam_F1_Drift_Action", cam_data_d)
        scene.collection.objects.link(cam_drift)
    
    cam_drift.data.lens = 42.0
    cam_drift.data.clip_start = 0.1
    cam_drift.data.clip_end = 500.0

    # 摄影机跟随轨迹: 从弯道外侧低角度仰拍，顺着滑移方向平滑推近，并在 Apex 处带来极致视觉冲击
    cam_keyframes = [
        (1,   Vector((5.5, -12.0, 0.65)), Vector((0.0, -25.0, 0.4))),
        (35,  Vector((6.2,   3.0, 0.60)), Vector((0.0,  -1.5, 0.4))),
        (65,  Vector((7.0,  12.0, 0.55)), Vector((2.2,  10.0, 0.4))),
        (85,  Vector((7.6,  18.5, 0.52)), Vector((4.1,  16.5, 0.4))), # 弯心近距离超低贴地特写
        (110, Vector((8.2,  27.0, 0.58)), Vector((5.6,  24.0, 0.4))),
        (150, Vector((8.5,  38.0, 0.70)), Vector((6.3,  42.0, 0.4))),
    ]

    for f, c_loc, t_loc in cam_keyframes:
        scene.frame_set(f)
        cam_drift.location = c_loc
        direction = t_loc - c_loc
        rot_quat = direction.to_track_quat('-Z', 'Y')
        euler = rot_quat.to_euler()
        # 加上微小的荷兰角 (Dutch Tilt) 强化速度张力
        euler.y += math.radians(2.5 if 60 <= f <= 100 else 0.0)
        cam_drift.rotation_euler = euler
        cam_drift.keyframe_insert(data_path="location", frame=f)
        cam_drift.keyframe_insert(data_path="rotation_euler", frame=f)

    # 启用动态模糊强化漂移临场感
    scene.render.use_motion_blur = True
    scene.render.motion_blur_shutter = 0.5

    # 默认选定为当前主摄影机
    scene.camera = cam_drift
    scene.frame_set(85) # 停在弯心高光帧

    # 保存主工程
    bpy.ops.wm.save_mainfile(filepath=blend_path)
    print("=== F1 SKELETAL RIG & DRIFT ANIMATION BUILT SUCCESSFULLY ===")

if __name__ == '__main__':
    create_f1_rig_and_drift()
