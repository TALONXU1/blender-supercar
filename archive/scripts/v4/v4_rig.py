# -*- coding: utf-8 -*-
"""
V4 RIG PASS — 专业赛车骨架（悬挂 / 转向 / 轮轴 / 尾翼 DRS）+ 驱动器
输入: pipeline/v4_stage_model.blend
输出: pipeline/v4_stage_rig.blend
"""
import bpy, math, sys
from mathutils import Vector, Matrix
from math import radians

IN = r"D:\项目session\blender-supercar\pipeline\v4_stage_model.blend"
OUT = r"D:\项目session\blender-supercar\pipeline\v4_stage_rig.blend"

bpy.ops.wm.open_mainfile(filepath=IN)
scene = bpy.context.scene

# ============================================================
# 1. 清理非车体对象
# ============================================================
for o in list(bpy.data.objects):
    n = o.name
    if o.type in ('CAMERA', 'LIGHT') or n.startswith(("GEO_Studio_", "Cam_", "LGT_", "PROXY_")):
        bpy.data.objects.remove(o, do_unlink=True)

# 解除全部父子关系（保留世界变换）
bpy.ops.object.select_all(action='DESELECT')
parts = [o for o in bpy.data.objects if o.type in ('MESH', 'CURVE')]
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
bpy.ops.object.select_all(action='DESELECT')
print("PARTS:", len(parts))


# ============================================================
# 2. 建立骨架
# ============================================================
WHEELS = {
    'FL': Vector((-0.900, 1.450, 0.355)),
    'FR': Vector(( 0.900, 1.450, 0.355)),
    'RL': Vector((-0.860, -1.550, 0.355)),
    'RR': Vector(( 0.860, -1.550, 0.355)),
}

arm = bpy.data.armatures.new("RIG_F1_Race_Armature")
rig = bpy.data.objects.new("RIG_F1_Race", arm)
scene.collection.objects.link(rig)
rig.show_in_front = True
arm.display_type = 'OCTAHEDRAL'

bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='EDIT')
eb = arm.edit_bones

def bone(name, head, tail, parent=None, connect=False):
    b = eb.new(name)
    b.head = Vector(head)
    b.tail = Vector(tail)
    if parent:
        b.parent = eb[parent]
        b.use_connect = connect
    b.roll = 0.0
    return b

bone("Bone_Root", (0, 0, 0), (0, 0.5, 0))
bone("Bone_Heading", (0, 0, 0), (0, 0.5, 0), "Bone_Root")
bone("Bone_Body", (0, 0.18, 0.30), (0, 0.78, 0.30), "Bone_Heading")

for s, c in WHEELS.items():
    bone(f"Bone_Susp_{s}", c, c + Vector((0, 0, 0.30)), "Bone_Heading")
    bone(f"Bone_Hub_{s}", c, c + Vector((0, 0.22, 0)), f"Bone_Susp_{s}")
    bone(f"Bone_Wheel_{s}", c, c + Vector((0, 0.22, 0)), f"Bone_Hub_{s}")

bone("Bone_Steering_Wheel", (0, 0.160, 0.650), (0, 0.060, 0.650), "Bone_Body")
bone("Bone_DRS", (0, -2.200, 1.035), (0, -2.100, 1.035), "Bone_Body")
bone("Bone_Aim", (0, 0.30, 0.48), (0, 0.42, 0.48), "Bone_Body")
bone("Bone_CamAnchor", (0, -0.30, 1.10), (0, -0.20, 1.10), "Bone_Body")

bpy.ops.object.mode_set(mode='OBJECT')

# ============================================================
# 3. 绑定零件到骨骼
# ============================================================
def bind(obj, bone_name):
    mw = obj.matrix_world.copy()
    obj.parent = rig
    obj.parent_type = 'BONE'
    obj.parent_bone = bone_name
    obj.matrix_parent_inverse = Matrix.Identity(4)
    obj.matrix_world = mw
    obj["v4_bone"] = bone_name


def wheel_of(name):
    for s in ("FL", "FR", "RL", "RR"):
        if name.endswith("_" + s) or f"_{s}_" in name:
            return s
    return None


ROTATING_PREFIX = ("GEO_F1_Tire_", "GEO_F1_Rim_", "GEO_F1_RimLip_", "GEO_F1_RimHubPlate_",
                   "GEO_F1_RimSpokes_", "GEO_F1_CenterLock_", "GEO_F1_BrakeDisc_",
                   "GEO_F1_BrakeHoles_", "GEO_F1_BrakeGlow_", "DEC_Tire_Sidewall_")
STATIC_HUB_PREFIX = ("GEO_F1_BrakeCaliper_", "GEO_F1_BrakeDuct_")
STEER_PARTS = ("GEO_F1_Cockpit_SteeringWheel", "GEO_F1_Steering_LCDScreen",
               "GEO_F1_Steering_Paddle_Up", "GEO_F1_Steering_Paddle_Down")
DRS_PARTS = ("GEO_F1_RearWing_DRSFlap", "GEO_F1_RearWing_DRS_Actuator", "GEO_F1_RearWing_DRS_Piston")
DRS_DECAL_HINTS = ("Bybit", "Back_RedBull")

count = {"wheel": 0, "hub": 0, "body": 0, "steer": 0, "drs": 0}
unbound = []
for o in parts:
    n = o.name
    side = wheel_of(n)
    if side and n.startswith(ROTATING_PREFIX):
        bind(o, f"Bone_Wheel_{side}")
        count["wheel"] += 1
    elif side and n.startswith(STATIC_HUB_PREFIX):
        bind(o, f"Bone_Hub_{side}")
        count["hub"] += 1
    elif n in STEER_PARTS or n.startswith(("GEO_F1_Steering_Dial_", "GEO_F1_ShiftLED_")):
        bind(o, "Bone_Steering_Wheel")
        count["steer"] += 1
    elif n in DRS_PARTS or (n.startswith("DEC_RearWing_") and any(h in n for h in DRS_DECAL_HINTS)):
        bind(o, "Bone_DRS")
        count["drs"] += 1
    else:
        bind(o, "Bone_Body")
        count["body"] += 1
print("BOUND:", count)

# ============================================================
# 4. 自定义属性 + 驱动器
# ============================================================
props = {
    "steer": (0.0, -40.0, 40.0),
    "wheel_spin": (0.0, -100000.0, 100000.0),
    "rear_slip": (1.0, 0.8, 3.0),
    "drs": (0.0, 0.0, 1.0),
    "brake_heat": (0.0, 0.0, 1.5),
    "susp_f": (0.0, -0.06, 0.03),
    "susp_r": (0.0, -0.06, 0.03),
    "steer_ratio": (5.0, 1.0, 12.0),
}
for k, (v, lo, hi) in props.items():
    rig[k] = float(v)
    ui = rig.id_properties_ui(k)
    ui.update(min=lo, max=hi, soft_min=lo, soft_max=hi)

rig["rig_note"] = "V4 赛车骨架: steer=转向角, wheel_spin=累计滚动弧度, drs=尾翼开度, brake_heat=刹车过热"

pose = rig.pose
for pb in pose.bones:
    pb.rotation_mode = 'XYZ'

def add_driver(bone_name, path, index, expression, variables):
    pb = pose.bones[bone_name]
    fc = pb.driver_add(path, index)
    drv = fc.driver
    drv.type = 'SCRIPTED'
    drv.expression = expression
    for vname, prop in variables:
        var = drv.variables.new()
        var.name = vname
        var.type = 'SINGLE_PROP'
        var.targets[0].id_type = 'OBJECT'
        var.targets[0].id = rig
        var.targets[0].data_path = f'["{prop}"]'
    return fc

# 车轮滚动（前轮 = -spin，后轮 = -spin * rear_slip）
for s in ("FL", "FR"):
    add_driver(f"Bone_Wheel_{s}", "rotation_euler", 0, "-spin", [("spin", "wheel_spin")])
for s in ("RL", "RR"):
    add_driver(f"Bone_Wheel_{s}", "rotation_euler", 0, "-spin*slip", [("spin", "wheel_spin"), ("slip", "rear_slip")])

# 前轮转向（绕骨骼本地 Z 轴）
for s in ("FL", "FR"):
    add_driver(f"Bone_Hub_{s}", "rotation_euler", 2, "steer*0.0174532925", [("steer", "steer")])

# 方向盘（绕自身轴旋转，反向 + 减速比）
add_driver("Bone_Steering_Wheel", "rotation_euler", 1, "steer*ratio*0.0174532925", [("steer", "steer"), ("ratio", "steer_ratio")])

# DRS 尾翼
add_driver("Bone_DRS", "rotation_euler", 0, "-0.2792527*drs", [("drs", "drs")])

# 悬挂行程（前后分别由属性驱动）
for s in ("FL", "FR"):
    add_driver(f"Bone_Susp_{s}", "location", 1, "susp", [("susp", "susp_f")])
for s in ("RL", "RR"):
    add_driver(f"Bone_Susp_{s}", "location", 1, "susp", [("susp", "susp_r")])

# 刹车盘过热发光
glow = bpy.data.materials.get("Mat_Brake_HeatGlow")
if glow and glow.node_tree:
    em = next((n for n in glow.node_tree.nodes if n.type == 'EMISSION'), None)
    if em:
        fc = em.inputs['Strength'].driver_add("default_value")
        fc.driver.type = 'SCRIPTED'
        fc.driver.expression = "heat*9.0"
        var = fc.driver.variables.new()
        var.name = "heat"
        var.type = 'SINGLE_PROP'
        var.targets[0].id_type = 'OBJECT'
        var.targets[0].id = rig
        var.targets[0].data_path = '["brake_heat"]'

# ============================================================
# 5. 约束（限位，保证机械合理）
# ============================================================
def limit_rot(bone_name, axes):
    pb = pose.bones[bone_name]
    c = pb.constraints.new('LIMIT_ROTATION')
    c.name = "V4_LimitRot"
    c.use_limit_x = axes.get('x') is not None
    c.use_limit_y = axes.get('y') is not None
    c.use_limit_z = axes.get('z') is not None
    if axes.get('x'):
        c.min_x, c.max_x = [radians(a) for a in axes['x']]
    if axes.get('y'):
        c.min_y, c.max_y = [radians(a) for a in axes['y']]
    if axes.get('z'):
        c.min_z, c.max_z = [radians(a) for a in axes['z']]
    c.owner_space = 'LOCAL'
    return c

for s in ("FL", "FR"):
    limit_rot(f"Bone_Hub_{s}", {'z': (-38, 38)})
limit_rot("Bone_DRS", {'x': (-3, 18)})
limit_rot("Bone_Steering_Wheel", {'y': (-200, 200)})
for s in ("FL", "FR", "RL", "RR"):
    pb = pose.bones[f"Bone_Susp_{s}"]
    c = pb.constraints.new('LIMIT_LOCATION')
    c.name = "V4_SuspTravel"
    c.use_min_y = c.use_max_y = True
    c.min_y, c.max_y = -0.06, 0.03
    c.owner_space = 'LOCAL'

# 相机瞄准骨骼（供 Track To 使用）
aim = pose.bones["Bone_Aim"]

# ============================================================
# 6. 保存 + 姿态验证
# ============================================================
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("RIG SAVED:", OUT)
print("BONES:", [b.name for b in arm.bones])
