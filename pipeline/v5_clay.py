# -*- coding: utf-8 -*-
"""
V5 白模（clay）版本：把所有材质替换成统一灰模，保留光影、景深（DOF）、运动模糊与组件层级。
输入: LATEST/v5_stage_anim.blend
输出: LATEST/v5_stage_anim_clay.blend（原文件不动）

用法:
  blender -b -P pipeline/v5_clay.py
  blender -b -P pipeline/v5_clay.py -- --render-stills
"""
import bpy
import os
import sys

PROJ = r"D:\项目session\blender-supercar"
ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def argval(flag, default=None):
    if flag in ARGV:
        i = ARGV.index(flag)
        if i + 1 < len(ARGV) and not ARGV[i + 1].startswith("--"):
            return ARGV[i + 1]
        return True
    return default


SRC = argval("--in", os.path.join(PROJ, "LATEST", "v5_stage_anim.blend"))
DST = argval("--out", os.path.join(PROJ, "LATEST", "v5_stage_anim_clay.blend"))
CLAY_STILLS_DIR = os.path.join(PROJ, "renders_v5", "clay_stills")

bpy.ops.wm.open_mainfile(filepath=SRC)
scene = bpy.context.scene
rig = bpy.data.objects.get("RIG_F1_Race")


def iter_fcurves(action):
    fcs = list(getattr(action, "fcurves", []) or [])
    if fcs:
        return fcs
    for layer in getattr(action, "layers", []) or []:
        for strip in getattr(layer, "strips", []) or []:
            for cb in getattr(strip, "channelbags", []) or []:
                fcs.extend(cb.fcurves)
    return fcs


def clay(name, value, rough=0.62, spec=0.08):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs['Base Color'].default_value = (value, value, value, 1.0)
    b.inputs['Roughness'].default_value = rough
    if 'Specular IOR Level' in b.inputs:
        b.inputs['Specular IOR Level'].default_value = spec
    b.inputs['Metallic'].default_value = 0.0
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(b.outputs['BSDF'], out.inputs['Surface'])
    return m


# 车体浅灰雕塑泥（0.76 避免 Standard 视图高光过曝）+ 环境深中性灰（低镜面防太阳反光楔形）
M_CAR = clay("CLAY_Car", 0.76, rough=0.50, spec=0.12)
M_ENV = clay("CLAY_Env", 0.34, rough=0.76, spec=0.03)
M_ROAD = clay("CLAY_Road", 0.24, rough=0.84, spec=0.02)

# 天空穹顶：平滑高度渐变中性灰自发光（去掉黄昏色彩且无分层条带）
sky = bpy.data.objects.get("V5_SkyDome")
if sky and hasattr(sky.data, "materials"):
    _m = bpy.data.materials.get("CLAY_SkyEmit") or bpy.data.materials.new("CLAY_SkyEmit")
    _m.use_nodes = True
    nt = _m.node_tree
    nt.nodes.clear()
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = 'EASE'
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.19, 0.195, 0.205, 1.0)
    ramp.color_ramp.elements[1].position = 0.55
    ramp.color_ramp.elements[1].color = (0.095, 0.100, 0.112, 1.0)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs['Strength'].default_value = 1.0
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tc.outputs['Generated'], sep.inputs['Vector'])
    nt.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], e.inputs['Color'])
    nt.links.new(e.outputs['Emission'], o.inputs['Surface'])
    if sky.data.materials:
        for i in range(len(sky.data.materials)):
            sky.data.materials[i] = _m
    else:
        sky.data.materials.append(_m)


def is_car_object(ob):
    """精确区分赛车几何（含 MESH 与 Halo CURVE）与赛道环境（V5_* / EM_* / GEO_Race*）"""
    if ob.name.startswith(("V5_", "EM_", "GEO_Race")):
        return False
    if rig is not None and ob.parent == rig:
        return True
    if ob.name.startswith(("GEO_F1_", "GEO_MERC_", "DEC_")):
        return True
    for c in ob.users_collection:
        if c.name.startswith(("01_", "02_", "03_", "04_", "05_", "06_", "07_", "08_",
                              "Wheel_", "Susp_", "Steering_", "SCIFI_F1")):
            return True
    return False


# 车 vs 环境（覆盖 MESH 与 CURVE，例如 GEO_F1_Halo_Hoop；Empty 组件保持不动）
n_car = n_env = 0
ROAD_PREFIX = ("V5_Track", "V5_RacingLine", "V5_Skid", "V5_BrakeZone", "V5_PitLane")
for ob in bpy.data.objects:
    if ob.type not in ('MESH', 'CURVE', 'SURFACE', 'FONT'):
        continue
    if ob.name.startswith("V5_SkyDome"):
        continue
    if not hasattr(ob.data, "materials"):
        continue
    is_car = is_car_object(ob)
    if is_car:
        mat = M_CAR
        n_car += 1
    else:
        mat = M_ROAD if ob.name.startswith(ROAD_PREFIX) else M_ENV
        n_env += 1
    me = ob.data
    if me.materials:
        for i in range(len(me.materials)):
            me.materials[i] = mat
    else:
        me.materials.append(mat)

# 白模漫反射率（0.76）远高于深蓝车漆：适度压低随车补光，保留纯粹的主光雕塑立体感并防止高光过曝
for ob in bpy.data.objects:
    if ob.type == 'LIGHT' and ob.name.startswith("LGT_V5Car_"):
        ob.data.energy *= 0.32

# 世界：中性灰环境底光
world = scene.world
if world:
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs['Color'].default_value = (0.055, 0.058, 0.064, 1.0)
    bg.inputs['Strength'].default_value = 0.95
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(bg.outputs[0], out.inputs[0])

# 关掉泛光（白模不需要眩光），但完整保留所有相机的 DOF（V5_CamFocus）与运动模糊
try:
    scene.use_nodes = False
except Exception:
    pass
scene.render.use_motion_blur = True

# 曝光回到中性 Standard，并同步修正 scene.animation_data 里的曝光关键帧（防止关键帧把曝光顶回 +0.50 导致过曝）
CLAY_EXP = -0.35
CLAY_FADE_EXP = -6.5
try:
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = CLAY_EXP
    scene.view_settings.gamma = 1.0
except Exception:
    pass

if scene.animation_data and scene.animation_data.action:
    for fc in iter_fcurves(scene.animation_data.action):
        if fc.data_path == "view_settings.exposure":
            for kp in fc.keyframe_points:
                if kp.co.x >= scene.frame_end - 1:
                    kp.co.y = CLAY_FADE_EXP
                else:
                    kp.co.y = CLAY_EXP
                kp.interpolation = 'LINEAR'
            fc.update()

print("clay: car geom=%d env geom=%d (DOF & motion blur preserved)" % (n_car, n_env))

bpy.ops.wm.save_as_mainfile(filepath=DST)
print("CLAY SAVED:", DST)

# 可选：直接渲染 6 张代表性 1080p 白模测试剧照（~12 s）
if argval("--render-stills"):
    os.makedirs(CLAY_STILLS_DIR, exist_ok=True)
    markers = sorted(scene.timeline_markers, key=lambda m: m.frame)

    def _active_cam(frame):
        cur = scene.camera
        for mk in markers:
            if mk.frame <= frame and mk.camera:
                cur = mk.camera
        return cur

    orig_cam = scene.camera
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 20
    scene.render.image_settings.file_format = 'JPEG'
    scene.render.image_settings.quality = 94

    CLAY_TEST_SHOTS = [
        (60, "01_rear_chase"),
        (160, "02_onboard_cockpit"),
        (350, "04_hairpin_dof"),
        (760, "09_wheel_macro"),
        (1120, "13_woodcote_tele"),
        (1730, "20_stowe_tele"),
    ]
    for f, tag in CLAY_TEST_SHOTS:
        scene.camera = _active_cam(f)
        scene.frame_set(f)
        out_path = os.path.join(CLAY_STILLS_DIR, f"clay_test_{tag}_f{f:04d}.jpg")
        scene.render.filepath = out_path
        bpy.ops.render.render(write_still=True)
        print("CLAY STILL:", out_path)
    scene.camera = orig_cam
