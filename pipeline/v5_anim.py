# -*- coding: utf-8 -*-
"""
V5 ANIM — 真实赛道整圈（Silverstone / 90.34 s / 162 拍 / 2161 帧）
输入: LATEST/v5_stage_env.blend
输出: LATEST/v5_stage_anim.blend
运行:
  blender -b -P pipeline/v5_anim.py
  blender -b -P pipeline/v5_anim.py -- --test 60,160,350,760,1120,1640,1730
  blender -b -P pipeline/v5_anim.py -- --render

五条硬规则（来自 track_data/TRACK_SPEC.md）
  1. 位置按 t 插值，不按帧均分
  2. 朝向取 heading_deg，不用位移差反推
  3. 位置走 racing_xy，不是 xy
  4. 关键帧 LINEAR，禁 Bezier
  5. v^2 * curv 不得超过 15.0 + 0.00714 v^2
"""
import bpy, json, math, os, sys, random
from mathutils import Vector, Matrix, Euler
from math import sin, cos, pi, radians, degrees, sqrt, exp

PROJ = r"D:\项目session\blender-supercar"
TRACK = os.path.join(PROJ, "track_data", "silverstone_track.json")
FRAMES_DIR = os.path.join(PROJ, "renders_v5", "frames")
STILLS_DIR = os.path.join(PROJ, "renders_v5", "stills")

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def argval(flag, default=None):
    if flag in ARGV:
        i = ARGV.index(flag)
        if i + 1 < len(ARGV) and not ARGV[i + 1].startswith("--"):
            return ARGV[i + 1]
        return True
    return default


IN = argval("--in", os.path.join(PROJ, "LATEST", "v5_stage_env.blend"))
OUT = argval("--out", os.path.join(PROJ, "LATEST", "v5_stage_anim.blend"))

# ---------------------------------------------------------------
# 0. 参数
# ---------------------------------------------------------------
FPS = 24
BEAT = 60.0 / 108.0                 # After Hours 108 BPM -> 0.5556 s
BEAT_F = BEAT * FPS                 # 13.3333 帧
TOTAL_BEATS = 162
FRAME_END = int(round(1 + TOTAL_BEATS * BEAT_F))    # 2161
R_TIRE = 0.357
WHEELBASE = 3.6

data = json.load(open(TRACK, encoding="utf-8"))
META = data["meta"]
P = data["points"]
N = len(P)
LAP_S = META["sim_lap_s"]           # 90.34
DT = LAP_S / (FRAME_END - 1)        # 每帧时间步（保证整圈正好铺满）

T_ARR = [p["t"] for p in P]
RX_ARR = [Vector((p["racing_xy"][0], p["racing_xy"][1], 0.0)) for p in P]
HD_ARR = [p["heading_deg"] for p in P]
V_ARR = [p["v_mps"] for p in P]
K_ARR = [abs(p["curv_1pm"] or 0.0) for p in P]


def _unwrap(deg_list):
    out = [deg_list[0]]
    for a in deg_list[1:]:
        d = (a - out[-1] + 180.0) % 360.0 - 180.0
        out.append(out[-1] + d)
    return out


_HD_UN = _unwrap(HD_ARR)
_SPAN = 4


def _ssign(i):
    a = _HD_UN[(i - _SPAN) % N]
    b = _HD_UN[(i + _SPAN) % N]
    return 1.0 if (b - a) >= 0 else -1.0


KS_ARR = [_ssign(i) * K_ARR[i] for i in range(N)]


def sample(t):
    """t -> (位置, 航向[rad, CCW from +X], 速度 m/s, 有符号曲率)"""
    t = max(0.0, min(LAP_S - 1e-6, t))
    lo, hi = 0, N - 1
    while hi - lo > 1:
        m = (lo + hi) // 2
        if T_ARR[m] <= t:
            lo = m
        else:
            hi = m
    span = max(T_ARR[lo + 1] - T_ARR[lo], 1e-9)
    f = (t - T_ARR[lo]) / span
    pos = RX_ARR[lo].lerp(RX_ARR[lo + 1], f)
    a = radians(HD_ARR[lo])
    b = radians(HD_ARR[lo + 1])
    d = (b - a + pi) % (2 * pi) - pi
    return pos, a + d * f, V_ARR[lo] + (V_ARR[lo + 1] - V_ARR[lo]) * f, \
        KS_ARR[lo] + (KS_ARR[lo + 1] - KS_ARR[lo]) * f


# ---------------------------------------------------------------
# 1. 每帧姿态与遥测预计算
# ---------------------------------------------------------------
GEAR_TOPS_KMH = [96.0, 134.0, 170.0, 204.0, 236.0, 267.0, 298.0, 340.0]


def gear_and_rpm_frac(v_kmh):
    for g_idx, top in enumerate(GEAR_TOPS_KMH):
        if v_kmh <= top or g_idx == 7:
            gear = g_idx + 1
            low = 55.0 if g_idx == 0 else GEAR_TOPS_KMH[g_idx - 1] * 0.80
            frac = max(0.0, min(1.0, (v_kmh - low) / max(top - low, 1.0)))
            return gear, frac
    return 8, 1.0


frame_data = {}
dist = 0.0
prev_pos = None
for f in range(1, FRAME_END + 1):
    t = (f - 1) * DT
    pos, h, v, k = sample(t)
    if prev_pos is not None:
        dist += (pos - prev_pos).length
    prev_pos = pos
    fwd = Vector((cos(h), sin(h), 0.0))
    right = Vector((sin(h), -cos(h), 0.0))
    frame_data[f] = dict(t=t, pos=pos, heading=h, v=v, k=k, dist=dist, fwd=fwd, right=right)

# 纵向加速度 / 有符号横向加速度 / 档位 / 转速比
for f in range(1, FRAME_END + 1):
    f0 = max(1, f - 2)
    f1 = min(FRAME_END, f + 2)
    dv = frame_data[f1]['v'] - frame_data[f0]['v']
    accel = dv / ((f1 - f0) * DT)
    v = frame_data[f]['v']
    k = frame_data[f]['k']
    gear, rpm_frac = gear_and_rpm_frac(v * 3.6)
    frame_data[f]['accel'] = accel
    frame_data[f]['lat'] = v * v * abs(k) / 9.81          # 无符号 g（供物理自检与侧倾幅值）
    frame_data[f]['lat_signed'] = v * v * k / 9.81        # 有符号 g（+左弯 / -右弯）
    frame_data[f]['gear'] = gear
    frame_data[f]['rpm_frac'] = rpm_frac
    frame_data[f]['kerb_prox'] = min(1.0, abs(k) / 0.0085)

# 平滑横向 G（用于相机地平线微倾耦合，避免突变）
for f in range(1, FRAME_END + 1):
    w0, w1 = max(1, f - 4), min(FRAME_END, f + 4)
    frame_data[f]['lat_smooth'] = sum(frame_data[j]['lat_signed'] for j in range(w0, w1 + 1)) / (w1 - w0 + 1)

# ---------------------------------------------------------------
# 2. 打开场景与集合整理（根 Scene Collection 零散落对象）
# ---------------------------------------------------------------
bpy.ops.wm.open_mainfile(filepath=IN)
scene = bpy.context.scene
rig = bpy.data.objects["RIG_F1_Race"]

# 把 RIG_F1_Race 归入 SCIFI_F1_2035 集合（保持根集合整洁）
_scifi_coll = bpy.data.collections.get("SCIFI_F1_2035")
if _scifi_coll:
    if rig.name not in _scifi_coll.objects:
        _scifi_coll.objects.link(rig)
    if rig.name in scene.collection.objects:
        scene.collection.objects.unlink(rig)

_lgt_coll = bpy.data.collections.get("V5_07_Lighting")
if not _lgt_coll:
    _lgt_coll = bpy.data.collections.new("V5_07_Lighting")
    scene.collection.children.link(_lgt_coll)

_cam_coll = bpy.data.collections.get("V5_08_Cameras")
if not _cam_coll:
    _cam_coll = bpy.data.collections.new("V5_08_Cameras")
    scene.collection.children.link(_cam_coll)

# 发车灯常暗（本圈是飞驰圈，不是静态发车）
_sl = bpy.data.materials.get("V5_StartLight")
if _sl and _sl.node_tree:
    for n in _sl.node_tree.nodes:
        if n.type == 'BSDF_PRINCIPLED' and 'Emission Strength' in n.inputs:
            n.inputs['Emission Strength'].default_value = 0.0

bone_root = rig.pose.bones["Bone_Root"]
bone_heading = rig.pose.bones["Bone_Heading"]
bone_body = rig.pose.bones["Bone_Body"]

# 真实 F1 转向传动比（~9.5:1），配合 Bone_Steering_Wheel 驱动器让车载镜头里方向盘转动清晰自然
rig["steer_ratio"] = 9.5

# --- 动态遥测材质准备 ---
# 1) FIA 尾部雨灯 / ERS 能量回收灯（独立红色发光材质，绝不与排气管/方向盘旋钮共用 Mat_Neon_Orange）
rain_emit_input = None
_rl = bpy.data.objects.get("GEO_F1_FIA_RainLight")
if _rl and hasattr(_rl.data, "materials"):
    _m_rain = bpy.data.materials.get("Mat_FIA_RainLight") or bpy.data.materials.new("Mat_FIA_RainLight")
    _m_rain.use_nodes = True
    _rnt = _m_rain.node_tree
    _rnt.nodes.clear()
    _rb = _rnt.nodes.new("ShaderNodeBsdfPrincipled")
    _rb.inputs['Base Color'].default_value = (0.10, 0.005, 0.005, 1.0)
    _rb.inputs['Roughness'].default_value = 0.22
    _rb.inputs['Emission Color'].default_value = (1.0, 0.018, 0.010, 1.0)
    _rb.inputs['Emission Strength'].default_value = 2.4
    _rout = _rnt.nodes.new("ShaderNodeOutputMaterial")
    _rnt.links.new(_rb.outputs['BSDF'], _rout.inputs['Surface'])
    if _rl.data.materials:
        _rl.data.materials[0] = _m_rain
    else:
        _rl.data.materials.append(_m_rain)
    rain_emit_input = _rb.inputs['Emission Strength']

# 2) 碳陶刹车盘与卡钳热辐射（兼容 env 阶段自定义节点，同时升级旧版纯黑不透明发光片）
brake_disc_emit_inputs = []
caliper_emit_inputs = []

_m_hg = bpy.data.materials.get("Mat_Brake_HeatGlow")
if _m_hg and _m_hg.node_tree and len(_m_hg.node_tree.nodes) <= 2:
    # 旧版只有 Emission + Output，brake_heat=0 时会变成不透明纯黑圆片挡住碳陶盘；改为透明叠加环形热辐射
    try:
        _m_hg.surface_render_method = 'BLENDED'
    except Exception:
        pass
    _hnt = _m_hg.node_tree
    if _hnt.animation_data:
        _hnt.animation_data_clear()
    _hnt.nodes.clear()
    _htc = _hnt.nodes.new("ShaderNodeTexCoord")
    _hmap = _hnt.nodes.new("ShaderNodeVectorMath")
    _hmap.operation = 'SUBTRACT'
    _hmap.inputs[1].default_value = (0.5, 0.5, 0.5)
    _hlen = _hnt.nodes.new("ShaderNodeVectorMath")
    _hlen.operation = 'LENGTH'
    _hramp = _hnt.nodes.new("ShaderNodeValToRGB")
    _hramp.color_ramp.interpolation = 'EASE'
    _hramp.color_ramp.elements[0].position = 0.16
    _hramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    _e1 = _hramp.color_ramp.elements.new(0.33)
    _e1.color = (1.0, 0.22, 0.025, 1.0)
    _hramp.color_ramp.elements[-1].position = 0.49
    _hramp.color_ramp.elements[-1].color = (0.45, 0.04, 0.005, 1.0)
    _htrans = _hnt.nodes.new("ShaderNodeBsdfTransparent")
    _hemit = _hnt.nodes.new("ShaderNodeEmission")
    _hemit.name = "V5_BrakeGlowEmit"
    _hemit.inputs['Strength'].default_value = 0.0
    _hmix = _hnt.nodes.new("ShaderNodeMixShader")
    _hmix.name = "V5_BrakeGlowMix"
    _hmix.inputs['Fac'].default_value = 0.0
    _hout = _hnt.nodes.new("ShaderNodeOutputMaterial")
    _hnt.links.new(_htc.outputs['Generated'], _hmap.inputs[0])
    _hnt.links.new(_hmap.outputs['Vector'], _hlen.inputs[0])
    _hnt.links.new(_hlen.outputs['Value'], _hramp.inputs['Fac'])
    _hnt.links.new(_hramp.outputs['Color'], _hemit.inputs['Color'])
    _hnt.links.new(_htrans.outputs['BSDF'], _hmix.inputs[1])
    _hnt.links.new(_hemit.outputs['Emission'], _hmix.inputs[2])
    _hnt.links.new(_hmix.outputs['Shader'], _hout.inputs['Surface'])
    brake_disc_emit_inputs.append(("glow_sheet", _hemit.inputs['Strength'], _hmix.inputs['Fac']))

for _mname in ("Mat_BrakeDisc_CarbonCeramic", "MAT_BrakeDiscGlow", "MAT_BrakeGlow"):
    _md = bpy.data.materials.get(_mname)
    if _md and _md.node_tree:
        _has_drv = bool(_md.node_tree.animation_data and _md.node_tree.animation_data.drivers)
        if not _has_drv:
            for _n in _md.node_tree.nodes:
                if _n.type == 'BSDF_PRINCIPLED' and 'Emission Strength' in _n.inputs:
                    if not _n.inputs['Emission Color'].is_linked:
                        _n.inputs['Emission Color'].default_value = (1.0, 0.16, 0.018, 1.0)
                    brake_disc_emit_inputs.append(("disc_bsdf", _n.inputs['Emission Strength'], None))
                    break
                if _n.type == 'EMISSION' and 'Strength' in _n.inputs:
                    brake_disc_emit_inputs.append(("disc_emit", _n.inputs['Strength'], None))
                    break

_mc = bpy.data.materials.get("Mat_Caliper_Anodized")
if _mc and _mc.node_tree:
    _has_drv = bool(_mc.node_tree.animation_data and _mc.node_tree.animation_data.drivers)
    if not _has_drv:
        for _n in _mc.node_tree.nodes:
            if _n.type == 'BSDF_PRINCIPLED' and 'Emission Strength' in _n.inputs:
                _n.inputs['Emission Color'].default_value = (1.0, 0.09, 0.012, 1.0)
                caliper_emit_inputs.append(_n.inputs['Emission Strength'])
                break

# 3) 方向盘顶部 15 颗换挡提示灯（分绿/黄/红三段独立材质，按档内转速点亮，不污染车身青色灯带）
shift_led_inputs = []
_LED_SPECS = [
    ("Mat_ShiftLED_Green", range(0, 5), (0.05, 1.0, 0.38)),
    ("Mat_ShiftLED_Yellow", range(5, 10), (1.0, 0.68, 0.04)),
    ("Mat_ShiftLED_Red", range(10, 15), (1.0, 0.04, 0.03)),
]
for _mname, _rng, _col in _LED_SPECS:
    _ml = bpy.data.materials.get(_mname) or bpy.data.materials.new(_mname)
    _ml.use_nodes = True
    _lnt = _ml.node_tree
    _lnt.nodes.clear()
    _lb = _lnt.nodes.new("ShaderNodeBsdfPrincipled")
    _lb.inputs['Base Color'].default_value = (_col[0] * 0.12, _col[1] * 0.12, _col[2] * 0.12, 1.0)
    _lb.inputs['Roughness'].default_value = 0.25
    _lb.inputs['Emission Color'].default_value = (*_col, 1.0)
    _lb.inputs['Emission Strength'].default_value = 0.5
    _lout = _lnt.nodes.new("ShaderNodeOutputMaterial")
    _lnt.links.new(_lb.outputs['BSDF'], _lout.inputs['Surface'])
    for _idx in _rng:
        _lob = bpy.data.objects.get(f"GEO_F1_ShiftLED_{_idx:02d}")
        if _lob and hasattr(_lob.data, "materials"):
            if _lob.data.materials:
                _lob.data.materials[0] = _ml
            else:
                _lob.data.materials.append(_ml)
    shift_led_inputs.append(_lb.inputs['Emission Strength'])


# --- 随车三点柔光（修正 light_linking 过滤，覆盖全部 243 个车体/车轮/贴花对象，绝不漏掉 GEO_F1_*）---
def _is_car_receiver(ob):
    if ob.type not in ('MESH', 'CURVE'):
        return False
    if ob.name.startswith(("V5_", "EM_", "GEO_Race")):
        return False
    return (ob.parent == rig) or ob.name.startswith(("GEO_F1_", "GEO_MERC_", "DEC_"))


_FILL = [
    dict(ahead=5.5, side=-6.0, up=4.0, energy=165.0, size=18.0, color=(0.60, 0.74, 1.0)),
    dict(ahead=5.5, side=6.0, up=4.0, energy=165.0, size=18.0, color=(1.0, 0.90, 0.78)),
    dict(ahead=-7.0, side=2.4, up=2.4, energy=215.0, size=10.0, color=(0.85, 0.92, 1.0)),
]
_car_coll = bpy.data.collections.get("V5_CarLightReceivers") or bpy.data.collections.new("V5_CarLightReceivers")
if _car_coll.name not in _lgt_coll.children:
    _lgt_coll.children.link(_car_coll)
_car_coll.hide_viewport = True      # 视口不重复干扰显隐，EEVEE 渲染 light_linking 完整生效

for _ob in bpy.data.objects:
    if _is_car_receiver(_ob) and _ob.name not in _car_coll.objects:
        _car_coll.objects.link(_ob)
print("car light receivers linked:", len(_car_coll.objects))

fill_lights = []
for i, spec in enumerate(_FILL):
    fd_l = bpy.data.lights.new(f"LGT_V5Car_{i}", 'AREA')
    fd_l.energy = spec['energy']
    fd_l.size = spec['size']
    fd_l.color = spec['color']
    fo = bpy.data.objects.new(f"LGT_V5Car_{i}", fd_l)
    _lgt_coll.objects.link(fo)
    try:
        fo.light_linking.receiver_collection = _car_coll
    except Exception as _e:
        print("light linking unavailable:", _e)
    fill_lights.append((fo, spec))

# --- 广播级景深焦点目标 Empty（全程锁定 Bone_Root + 0.45m Z）---
cam_focus = bpy.data.objects.get("V5_CamFocus")
if not cam_focus:
    cam_focus = bpy.data.objects.new("V5_CamFocus", None)
    cam_focus.empty_display_type = 'PLAIN_AXES'
    cam_focus.empty_display_size = 0.6
    _cam_coll.objects.link(cam_focus)

# ---------------------------------------------------------------
# 3. 逐帧烘焙（物理姿态 + 热力学刹车盘 + 6Hz 雨灯 + 换挡灯 + 焦点追踪）
# ---------------------------------------------------------------
cum_spin = 0.0
prev_dist = 0.0
prev_gear = frame_data[1]['gear']
shift_flash = 0.0
brake_heat_state = 0.0

print("BAKE START: %d frames, dt=%.5f s, lap=%.2f s" % (FRAME_END, DT, LAP_S))
for f in range(1, FRAME_END + 1):
    fd = frame_data[f]
    v, acc, lat, k = fd['v'], fd['accel'], fd['lat'], fd['k']
    v_kmh = v * 3.6

    # --- 位置 / 偏航（硬规则 1,2,3 + Bone_Root.z = 0.012）---
    yaw = fd['heading'] - pi / 2
    bone_root.location = (fd['pos'].x, fd['pos'].y, 0.012)
    bone_heading.rotation_euler = (0.0, 0.0, yaw)
    bone_root.keyframe_insert("location", frame=f)
    bone_heading.keyframe_insert("rotation_euler", frame=f)

    # --- 景深焦点 Empty 同步锁定 Bone_Root + 0.45m Z ---
    cam_focus.location = (fd['pos'].x, fd['pos'].y, 0.012 + 0.45)
    cam_focus.keyframe_insert("location", frame=f)

    # --- 车身姿态：俯仰 / 有符号侧倾 / 升沉 ---
    gear = fd['gear']
    if gear != prev_gear:
        shift_flash = 1.0
        prev_gear = gear
    else:
        shift_flash *= 0.72

    pitch = max(-1.9, min(1.4, acc * 0.085)) - 0.16 * shift_flash
    roll = max(-2.2, min(2.2, -fd['lat_signed'] * 0.26))
    heave = -0.006 + 0.0016 * sin(f * 1.31) + 0.0009 * sin(f * 2.77)
    fd['body_pitch_deg'] = pitch
    fd['body_roll_deg'] = roll
    fd['body_heave'] = heave

    bone_body.location = (0.0, 0.0, heave)
    bone_body.rotation_euler = (radians(pitch), radians(roll), 0.0)
    bone_body.keyframe_insert("location", frame=f)
    bone_body.keyframe_insert("rotation_euler", frame=f)

    # --- 机械驱动 + 碳陶刹车盘热惯性模型 ---
    cum_spin += (fd['dist'] - prev_dist) / R_TIRE
    prev_dist = fd['dist']
    rig["wheel_spin"] = cum_spin

    steer_deg = degrees(k * WHEELBASE)                   # 阿克曼转角
    rig["steer"] = max(-26.0, min(26.0, steer_deg))

    straight = abs(k) < 0.0016
    rig["drs"] = 1.0 if (straight and v_kmh > 240) else (0.0 if abs(k) > 0.004 else 0.5)

    # 重刹快速升温，松刹后按导风管对流时间常数（1.25..1.75 s）平滑退火至弯心与出弯
    if acc < -1.8:
        brake_pwr = ((-acc - 1.8) / 25.0) * (0.42 + 0.58 * min(1.0, v / 85.0))
        brake_heat_state = min(1.25, brake_heat_state + brake_pwr * (DT / 0.13))
    else:
        tau_cool = 1.75 - 0.50 * min(1.0, v / 85.0)
        brake_heat_state *= exp(-DT / tau_cool)
        if brake_heat_state < 0.003:
            brake_heat_state = 0.0

    rig["brake_heat"] = brake_heat_state
    rig["rear_slip"] = 1.0
    rig["susp_f"] = -0.004 - 0.014 * max(0.0, -acc) / 12.0
    rig["susp_r"] = -0.004 - 0.016 * max(0.0, acc) / 12.0
    for kk in ("wheel_spin", "steer", "drs", "brake_heat", "rear_slip", "susp_f", "susp_r"):
        rig.keyframe_insert(f'["{kk}"]', frame=f)

    # 刹车盘与卡钳红橙热辉光关键帧
    bh = brake_heat_state
    for kind, einp, minp in brake_disc_emit_inputs:
        if kind == "glow_sheet":
            einp.default_value = (bh ** 1.25) * 8.5
            einp.keyframe_insert("default_value", frame=f)
            minp.default_value = min(0.92, (bh ** 0.85) * 0.85)
            minp.keyframe_insert("default_value", frame=f)
        else:
            einp.default_value = (bh ** 1.35) * 5.2
            einp.keyframe_insert("default_value", frame=f)
    for cinp in caliper_emit_inputs:
        cinp.default_value = max(0.0, bh - 0.32) * 1.35
        cinp.keyframe_insert("default_value", frame=f)

    # FIA 尾部雨灯 / ERS 能量回收灯：重刹或高速收油（acc < -2.5）时 ~6 Hz 高频红闪，其余常亮微光
    if rain_emit_input is not None:
        if acc < -2.5:
            pulse_on = ((fd['t'] * 6.0) % 1.0) < 0.55
            rain_emit_input.default_value = 24.0 if pulse_on else 1.2
        else:
            rain_emit_input.default_value = 2.5
        rain_emit_input.keyframe_insert("default_value", frame=f)

    # 方向盘换挡提示灯：随档内转速比依次点亮绿 -> 黄 -> 红，升档瞬间闪烁
    rf = fd['rpm_frac']
    if len(shift_led_inputs) == 3:
        shift_led_inputs[0].default_value = 7.5 if rf > 0.28 else 0.35
        shift_led_inputs[1].default_value = 8.5 if rf > 0.58 else 0.25
        shift_led_inputs[2].default_value = (13.0 if shift_flash > 0.5 else 9.5) if rf > 0.82 else 0.20
        for sinp in shift_led_inputs:
            sinp.keyframe_insert("default_value", frame=f)

    # 随车柔光
    for fo, spec in fill_lights:
        lp = fd['pos'] + fd['fwd'] * spec['ahead'] + fd['right'] * spec['side'] + Vector((0, 0, spec['up']))
        fo.location = lp
        aim = (fd['pos'] + Vector((0, 0, 0.45))) - lp
        fo.rotation_euler = aim.to_track_quat('-Z', 'Y').to_euler()
        fo.keyframe_insert("location", frame=f)
        fo.keyframe_insert("rotation_euler", frame=f)

print("BAKE DONE")


def iter_fcurves(action):
    """Blender 5.x: Action 有 layered/slotted 结构，fcurves 在 channelbag 里"""
    fcs = list(getattr(action, "fcurves", []) or [])
    if fcs:
        return fcs
    for layer in getattr(action, "layers", []) or []:
        for strip in getattr(layer, "strips", []) or []:
            for cb in getattr(strip, "channelbags", []) or []:
                fcs.extend(cb.fcurves)
    return fcs


def force_all_actions_linear():
    total = 0
    for act in bpy.data.actions:
        for fc in iter_fcurves(act):
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
                total += 1
    return total


# ---------------------------------------------------------------
# 4. 物理自检（横向加速度上限 + 赛道内 + 航向连续）
# ---------------------------------------------------------------
VMAX = META["limits"]["v_max_mps"]
LIM = 15.0 + 0.00714 * VMAX ** 2
worst = max(frame_data.values(), key=lambda d: d['v'] ** 2 * abs(d['k']))
over = [f for f, d in frame_data.items() if d['v'] ** 2 * abs(d['k']) > LIM + 0.5]
jumps = []
for f in range(2, FRAME_END + 1):
    d0, d1 = frame_data[f - 1], frame_data[f]
    dh = abs((d1['heading'] - d0['heading'] + pi) % (2 * pi) - pi)
    if dh > 0.12:
        jumps.append((f, degrees(dh)))
print("[check] 最坏横向 %.2f m/s^2 (%.2f g) @ frame %d, t=%.1f s"
      % (worst['v'] ** 2 * abs(worst['k']), worst['v'] ** 2 * abs(worst['k']) / 9.81,
         int(round(worst['t'] / DT)) + 1, worst['t']))
print("[check] 超限帧 %d -> %s" % (len(over), "PASS" if not over else "FAIL"))
print("[check] 航向跳变帧(>6.9deg) %d -> %s" % (len(jumps), "PASS" if not jumps else str(jumps[:6])))
print("[check] v_max %.1f km/h, lap %.2f s, 帧数 %d" % (max(d['v'] for d in frame_data.values()) * 3.6, LAP_S, FRAME_END))

# ---------------------------------------------------------------
# 5. 26 机位（无遮挡精调 + V5_CamFocus 广播级景深 + 弯道 G 力微倾与路肩微振）
# ---------------------------------------------------------------
DOF_FOCUS_CAMS = {
    "Cam_S04_Hairpin",
    "Cam_S08_FastPan",
    "Cam_S09_WheelMacro",
    "Cam_S11_Luffield",
    "Cam_S13_WoodcoteTele",
    "Cam_S20_StoweTele",
    "Cam_S24_Club",
}


def make_cam(name, lens=50, fstop=4.0, use_focus_obj=True):
    cd = bpy.data.cameras.new(name + "_DATA")
    cd.lens = lens
    cd.clip_start = 0.5
    cd.clip_end = 9000
    cd.sensor_width = 36
    cd.dof.use_dof = True
    cd.dof.aperture_fstop = fstop
    cd.dof.aperture_blades = 9
    if use_focus_obj:
        cd.dof.focus_object = cam_focus
    ob = bpy.data.objects.new(name, cd)
    _cam_coll.objects.link(ob)
    return ob


def cam_look(ob, loc, target, roll_deg=0.0, fstop=None, lens=None):
    loc = Vector(loc)
    tgt = Vector(target)
    d = tgt - loc
    q = d.to_track_quat('-Z', 'Y')
    m = q.to_matrix().to_4x4()
    if abs(roll_deg) > 1e-6:
        m = m @ Matrix.Rotation(radians(roll_deg), 4, 'Z')
    ob.matrix_world = Matrix.Translation(loc) @ m
    if fstop is not None:
        ob.data.dof.aperture_fstop = fstop
        if ob.data.dof.focus_object is None:
            ob.data.dof.focus_distance = d.length
    if lens is not None:
        ob.data.lens = lens


def noise(t, seed=0.0, amp=1.0):
    return (sin(t * 2.3 + seed) * 0.55 + sin(t * 5.7 + seed * 2.3) * 0.3
            + sin(t * 11.3 + seed * 4.1) * 0.15) * amp


def micro_vib(f, seed, amp):
    """确定性高频悬挂/路肩微振（受车速与弯道路肩贴近度缩放，细腻不眩晕）"""
    return (sin(f * 1.43 + seed) * 0.52
            + sin(f * 2.91 + seed * 1.7) * 0.31
            + sin(f * 5.17 + seed * 3.1) * 0.17) * amp


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def key_cam(cam, f, loc, tgt, roll=0.0, fstop=4.0, lens=50, lens_key=True):
    cam_look(cam, loc, tgt, roll_deg=roll, fstop=fstop, lens=lens)
    cam.keyframe_insert("location", frame=f)
    cam.keyframe_insert("rotation_euler", frame=f)
    if cam.data.dof.focus_object is None:
        cam.data.dof.keyframe_insert("focus_distance", frame=f)
    cam.data.dof.keyframe_insert("aperture_fstop", frame=f)
    if lens_key:
        cam.data.keyframe_insert("lens", frame=f)


def C(fd, back=0.0, side=0.0, h=0.5):
    return fd['pos'] - fd['fwd'] * back + fd['right'] * side + Vector((0, 0, h))


def T(fd, ahead=0.0, side=0.0, h=0.45):
    return fd['pos'] + fd['fwd'] * ahead + fd['right'] * side + Vector((0, 0, h))


def fixed_point(f, back=0.0, side=0.0, h=0.5):
    fd = frame_data[f]
    return C(fd, back, side, h)


CAR_LEN = 4.7
CAR_W = 2.2
SENSOR_W = 36.0


def lens_for_framing(dist, frac, cos_a=0.0):
    """cos_a: 1=正对车头/车尾, 0=正侧面。按投影宽度算焦距"""
    w_eff = CAR_W + (CAR_LEN - CAR_W) * (1.0 - abs(cos_a))
    return max(20.0, min(320.0, frac * SENSOR_W * max(dist, 1.0) / max(w_eff, 0.5)))


SHOTS = [
    # (名字, t0, t1, 类型, 参数)  —— t 为赛道时间（秒），切点严格吸附 108 BPM 拍点
    ("Cam_S01_RearChase", 0.0, 4.6, "chase",
     dict(back0=8.0, back1=11.5, side0=1.1, side1=-1.1, h0=0.48, h1=1.15,
          aim0=2.4, aim1=3.6, lens0=38, lens1=31, fstop=4.0, roll1=1.2)),
    ("Cam_S02_Onboard", 4.6, 8.4, "onboard",
     dict(fwd=-0.46, side=0.06, h=0.89, pitch_deg=-8.5, lens=18, fstop=11.0)),
    ("Cam_S03_ChaseRise", 8.4, 12.4, "chase",
     dict(back0=8.8, back1=6.9, side0=-1.2, side1=3.2, h0=1.30, h1=4.20,
          aim0=4.4, aim1=3.0, lens0=30, lens1=29, fstop=4.0, roll1=3.2)),
    ("Cam_S04_Hairpin", 12.4, 16.6, "fixed",
     dict(t_pass=15.80, lead=-8.0, side=8.8, h=1.15,
          framing=0.34, fstop=3.5, aim_lerp=0.68, roll=-1.2)),
    ("Cam_S05_ChaseAintree", 16.6, 20.0, "chase",
     dict(back0=7.2, back1=9.0, side0=0.6, side1=-1.2, h0=0.60, h1=1.05,
          aim0=3.0, aim1=4.0, lens0=36, lens1=32, fstop=4.0, roll1=-1.2)),
    ("Cam_S06_Orbit1", 20.0, 23.4, "orbit",
     dict(a0=104, a1=52, r0=10.5, r1=8.0, h0=1.35, h1=1.05,
          lens=44, fstop=3.6, roll=-4.0, roll_end=3.2)),
    ("Cam_S07_ChaseAccel", 23.4, 26.6, "chase",
     dict(back0=9.4, back1=7.8, side0=-1.0, side1=1.2, h0=0.80, h1=0.55,
          aim0=4.4, aim1=3.6, lens0=32, lens1=34, fstop=4.0, roll1=0.8)),
    ("Cam_S08_FastPan", 26.6, 30.6, "fixed",
     dict(t_pass=29.50, lead=0.0, side=14.0, h=0.95,
          framing=0.27, fstop=4.0, aim_lerp=0.74, roll=-1.5)),
    ("Cam_S09_WheelMacro", 30.6, 32.8, "wheel",
     dict(side0=4.15, side1=3.85, back0=-1.20, back1=-0.45, h0=0.48, h1=0.62,
          lens0=35, lens1=31, fstop=2.8)),
    ("Cam_S09b_ChaseFast", 32.8, 35.2, "chase",
     dict(back0=6.4, back1=8.2, side0=-1.4, side1=1.0, h0=0.52, h1=0.85,
          aim0=3.6, aim1=4.6, lens0=30, lens1=27, fstop=3.2, roll1=1.8)),
    ("Cam_S10_OrbitBrooklands", 34.0, 37.4, "orbit",
     dict(a0=98, a1=44, r0=9.2, r1=7.0, h0=1.15, h1=0.95,
          lens=42, fstop=3.4, roll=2.8, roll_end=-2.2)),
    ("Cam_S11_Luffield", 37.4, 41.8, "fixed",
     dict(t_pass=41.40, lead=-9.0, side=10.5, h=1.05,
          framing=0.32, fstop=3.8, aim_lerp=0.68, roll=1.0)),
    ("Cam_S12_ChaseWoodcote", 41.8, 45.0, "chase",
     dict(back0=7.6, back1=9.4, side0=-0.8, side1=1.4, h0=0.75, h1=1.35,
          aim0=3.4, aim1=4.4, lens0=34, lens1=30, fstop=4.0, roll1=1.6)),
    ("Cam_S13_WoodcoteTele", 45.0, 48.4, "fixed",
     dict(t_pass=48.20, lead=-12.0, side=9.2, h=2.20,
          framing=0.25, fstop=4.0, aim_lerp=0.58, roll=0.0)),
    ("Cam_S14_HeliDrop", 48.4, 52.0, "heli",
     dict(h0=28.0, h1=12.5, back=18.0, back0=-6.0, back1=22.0, lens=78, fstop=5.6)),
    ("Cam_S15_OrbitCopse", 52.0, 55.6, "orbit",
     dict(a0=108, a1=48, r0=11.0, r1=7.8, h0=1.50, h1=1.05,
          lens=40, fstop=3.4, roll=-5.0, roll_end=2.6)),
    ("Cam_S16_ChaseCopse", 55.6, 59.2, "chase",
     dict(back0=7.0, back1=8.4, side0=0.5, side1=-1.1, h0=0.58, h1=1.05,
          aim0=3.4, aim1=4.4, lens0=36, lens1=32, fstop=4.0, roll1=-1.6)),
    ("Cam_S17_Maggotts", 59.2, 63.2, "fixed",
     dict(t_pass=62.50, lead=2.0, side=11.2, h=2.15,
          framing=0.28, fstop=4.0, aim_lerp=0.68, roll=-0.8)),
    ("Cam_S18_ChaseRise2", 63.2, 66.8, "chase",
     dict(back0=9.0, back1=6.6, side0=-1.4, side1=3.8, h0=1.30, h1=4.60,
          aim0=4.6, aim1=2.8, lens0=30, lens1=28, fstop=4.0, roll1=4.0)),
    ("Cam_S19_Onboard3", 66.8, 70.4, "onboard",
     dict(fwd=-0.48, side=-0.05, h=0.92, pitch_deg=-9.0, lens=18, fstop=11.0)),
    ("Cam_S20_StoweTele", 70.4, 74.8, "fixed",
     dict(t_pass=73.50, lead=-28.0, side=-13.0, h=2.60,
          framing=0.26, fstop=4.0, aim_lerp=0.60, roll=0.0)),
    ("Cam_S21_OrbitStowe", 74.8, 78.4, "orbit",
     dict(a0=112, a1=50, r0=11.5, r1=8.0, h0=1.60, h1=1.10,
          lens=38, fstop=3.4, roll=4.2, roll_end=-2.5)),
    ("Cam_S22_ChaseLow", 78.4, 82.0, "chase",
     dict(back0=6.6, back1=9.6, side0=1.1, side1=-1.5, h0=0.54, h1=1.45,
          aim0=3.0, aim1=4.4, lens0=38, lens1=31, fstop=3.2, roll1=-2.4)),
    ("Cam_S23_HeliReveal", 82.0, 85.6, "heli",
     dict(h0=22.0, h1=44.0, back=32.0, lens=70, fstop=6.3)),
    ("Cam_S24_Club", 85.6, 88.4, "fixed",
     dict(t_pass=87.30, lead=-8.0, side=-9.0, h=1.25,
          framing=0.31, fstop=3.5, aim_lerp=0.68, roll=-0.8)),
    ("Cam_S25_AerialOut", 88.4, 90.34, "aerial",
     dict(back0=9.0, back1=17.0, side0=2.5, side1=9.0, h0=3.0, h1=11.0,
          lens0=56, lens1=46, fstop=4.5)),
]


def TF(t):
    """赛道时间 -> 帧号，吸附到最近拍点"""
    f = 1.0 + t / DT
    k = round((f - 1) / BEAT_F)
    return max(1, min(FRAME_END, int(round(1 + k * BEAT_F))))


_windows = []
for name, t0, t1, typ, pr in SHOTS:
    _windows.append([name, TF(t0), TF(t1), typ, pr])

# 顺序修正：严格递增、不许为负长度
for i in range(len(_windows)):
    _windows[i][1] = max(_windows[i][1], 1)
    _windows[i][2] = min(FRAME_END, max(_windows[i][2], _windows[i][1] + 2))
    if i and _windows[i][1] <= _windows[i - 1][2]:
        _windows[i][1] = _windows[i - 1][2] + 1
        _windows[i][2] = max(_windows[i][2], _windows[i][1] + 2)
_windows[-1][2] = FRAME_END

_cams = {}
_markers = []
for name, f0, f1, typ, pr in _windows:
    use_focus_obj = (typ != "onboard")
    cam = make_cam(name, pr.get('lens', pr.get('lens0', 50)), pr.get('fstop', 4.0), use_focus_obj=use_focus_obj)
    _cams[name] = cam
    _markers.append((name, f0))
    span = max(1, f1 - f0)

    if typ == "chase":
        for f in range(f0, f1 + 1):
            e = smooth((f - f0) / span)
            fd = frame_data[f]
            loc = C(fd, pr['back0'] + (pr['back1'] - pr['back0']) * e,
                    pr['side0'] + (pr['side1'] - pr['side0']) * e,
                    pr['h0'] + (pr['h1'] - pr['h0']) * e)
            loc += Vector((noise(f * 0.06, 11.0, 0.022), noise(f * 0.06, 12.0, 0.022),
                           noise(f * 0.09, 13.0, 0.015)))
            tgt = T(fd, pr['aim0'] + (pr['aim1'] - pr['aim0']) * e, 0, 0.50)
            # 弯道横向 G 力地平线微倾耦合（柔和真实，限幅 ±1.8°）
            g_bank = max(-1.8, min(1.8, -fd['lat_smooth'] * 0.30))
            base_roll = pr.get('roll0', 0.0) + (pr.get('roll1', 0.0) - pr.get('roll0', 0.0)) * e
            key_cam(cam, f, loc, tgt,
                    roll=base_roll + g_bank + noise(f * 0.05, 14.0, 0.35),
                    fstop=pr['fstop'],
                    lens=pr['lens0'] + (pr['lens1'] - pr['lens0']) * e)

    elif typ == "fixed":
        fr = max(f0, min(f1, int(round(1 + pr['t_pass'] / DT))))
        loc = C(frame_data[fr], pr['lead'], pr['side'], pr['h'])
        aim = None
        for f in range(f0, f1 + 1):
            fd = frame_data[f]
            tgt = fd['pos'] + Vector((0, 0, 0.42))
            aim = tgt if aim is None else aim.lerp(tgt, pr.get('aim_lerp', 0.7))
            dv = loc - fd['pos']
            d = max(2.0, dv.length)
            cos_a = abs(fd['fwd'].dot(dv.normalized()))
            key_cam(cam, f, loc, aim, roll=pr.get('roll', 0.0), fstop=pr['fstop'],
                    lens=lens_for_framing(d, pr['framing'], cos_a), lens_key=True)

    elif typ == "wheel":
        for f in range(f0, f1 + 1):
            e = smooth((f - f0) / span)
            fd = frame_data[f]
            v_fac = fd['v'] / 90.0
            kerb = fd['kerb_prox']
            vib_amp = 0.0022 + 0.0032 * v_fac + 0.0035 * kerb
            loc = C(fd, pr['back0'] + (pr['back1'] - pr['back0']) * e,
                    pr['side0'] + (pr['side1'] - pr['side0']) * e,
                    pr['h0'] + (pr['h1'] - pr['h0']) * e)
            loc += fd['right'] * micro_vib(f, 81.0, vib_amp * 0.7) \
                + Vector((0.0, 0.0, micro_vib(f, 83.0, vib_amp)))
            tgt = fd['pos'] + fd['right'] * 0.72 + fd['fwd'] * (1.35 - 0.5 * e) + Vector((0, 0, 0.35))
            roll_vib = micro_vib(f, 85.0, 0.18 + 0.25 * kerb)
            key_cam(cam, f, loc, tgt,
                    roll=(1.0 - 2.0 * e) - fd['lat_smooth'] * 0.22 + roll_vib,
                    fstop=pr['fstop'],
                    lens=pr['lens0'] + (pr['lens1'] - pr['lens0']) * e)

    elif typ == "onboard":
        # 真实 F1 座舱肩部/防滚架机位：跟随车身俯仰/侧倾/升沉，展示实时方向盘转动、换挡灯、Halo 与前轮转向
        seed_base = 31.0 if "S02" in name else 61.0
        for f in range(f0, f1 + 1):
            fd = frame_data[f]
            v_fac = fd['v'] / 90.0
            kerb = fd['kerb_prox']
            vib = 0.0014 + 0.0022 * v_fac + 0.0026 * kerb

            # 车身局部 -> 世界变换（使座舱/Halo 在画面中稳固，赛道地平线随 G 力与路肩真实响应）
            yaw = fd['heading'] - pi / 2
            m_car = (Matrix.Translation((fd['pos'].x, fd['pos'].y, 0.012 + fd['body_heave']))
                     @ Euler((0.0, 0.0, yaw), 'XYZ').to_matrix().to_4x4()
                     @ Euler((radians(fd['body_pitch_deg']), radians(fd['body_roll_deg']), 0.0), 'XYZ').to_matrix().to_4x4())

            local_cam = Vector((
                pr.get('side', 0.0) + micro_vib(f, seed_base + 1.0, vib * 0.75),
                pr['fwd'] + micro_vib(f, seed_base + 2.0, vib * 0.45),
                pr['h'] + micro_vib(f, seed_base + 3.0, vib),
            ))
            pitch_rad = radians(pr.get('pitch_deg', -8.5))
            local_tgt = local_cam + Vector((
                radians(rig["steer"]) * 0.25,     # 轻微视线入弯引导
                18.0 * cos(pitch_rad),
                18.0 * sin(pitch_rad),
            ))
            loc = m_car @ local_cam
            tgt = m_car @ local_tgt
            # 地平线微倾耦合（车身侧倾 + 车手头部惯性补偿 + 路肩微振）
            cam_roll = -fd['body_roll_deg'] * 0.65 - fd['lat_smooth'] * 0.24 + micro_vib(f, seed_base + 4.0, 0.14 + 0.20 * kerb)
            cam.data.dof.focus_distance = 2.4     # 超焦距：0.65m 方向盘与远方弯心同时清晰
            key_cam(cam, f, loc, tgt, roll=cam_roll, fstop=pr['fstop'],
                    lens=pr['lens'], lens_key=False)
            cam.data.dof.keyframe_insert("focus_distance", frame=f)

    elif typ == "orbit":
        for f in range(f0, f1 + 1):
            e = smooth((f - f0) / span)
            fd = frame_data[f]
            ang = radians(pr['a0'] + (pr['a1'] - pr['a0']) * e)
            rad = pr['r0'] + (pr['r1'] - pr['r0']) * e
            ox = fd['fwd'].x * cos(ang) - fd['right'].x * sin(ang)
            oy = fd['fwd'].y * cos(ang) - fd['right'].y * sin(ang)
            loc = fd['pos'] + Vector((ox, oy, 0)) * rad + Vector(
                (0, 0, pr['h0'] + (pr['h1'] - pr['h0']) * e))
            loc += Vector((noise(f * 0.07, 51.0, 0.030), noise(f * 0.07, 52.0, 0.030),
                           noise(f * 0.09, 53.0, 0.015)))
            tgt = fd['pos'] + Vector((0, 0, 0.44))
            key_cam(cam, f, loc, tgt, roll=pr['roll'] + (pr['roll_end'] - pr['roll']) * e,
                    fstop=pr['fstop'], lens=pr['lens'], lens_key=False)

    elif typ == "heli":
        b0 = pr.get('back0', pr['back'])
        b1 = pr.get('back1', pr['back'])
        for f in range(f0, f1 + 1):
            e = smooth((f - f0) / span)
            fd = frame_data[f]
            loc = C(fd, b0 + (b1 - b0) * e, 0.0, pr['h0'] + (pr['h1'] - pr['h0']) * e)
            loc += Vector((noise(f * 0.03, 71.0, 0.08), noise(f * 0.03, 72.0, 0.08), 0))
            tgt = fd['pos'] + fd['fwd'] * 2.0 + Vector((0, 0, 0.55))
            key_cam(cam, f, loc, tgt, roll=noise(f * 0.02, 73.0, 0.9), fstop=pr['fstop'],
                    lens=pr['lens'], lens_key=False)

    elif typ == "aerial":
        for f in range(f0, f1 + 1):
            e = smooth((f - f0) / span)
            fd = frame_data[f]
            loc = C(fd, pr['back0'] + (pr['back1'] - pr['back0']) * e,
                    pr['side0'] + (pr['side1'] - pr['side0']) * e,
                    pr['h0'] + (pr['h1'] - pr['h0']) * e)
            loc += Vector((noise(f * 0.04, 91.0, 0.03 * (1 - e)), noise(f * 0.04, 92.0, 0.03 * (1 - e)),
                           noise(f * 0.05, 93.0, 0.02)))
            tgt = fd['pos'] + fd['fwd'] * 1.2 + Vector((0, 0, 0.52))
            key_cam(cam, f, loc, tgt, roll=-1.0 + 2.0 * e, fstop=pr['fstop'],
                    lens=pr['lens0'] + (pr['lens1'] - pr['lens0']) * e)

    dof_tag = f"DOF->{cam_focus.name} f/{pr['fstop']}" if name in DOF_FOCUS_CAMS else f"f/{pr['fstop']}"
    print("CAM %-24s %4d-%4d  t=%5.2f..%5.2f s  %-8s  %s" %
          (name, f0, f1, frame_data[f0]['t'], frame_data[f1]['t'], typ, dof_tag))


# 机位切换
scene.timeline_markers.clear()
for name, f0 in _markers:
    mk = scene.timeline_markers.new(name, frame=f0)
    mk.camera = _cams[name]
scene.camera = _cams[SHOTS[0][0]]

# 收尾淡出：最后 16 帧压曝光
scene.view_settings.exposure = 0.50
scene.view_settings.keyframe_insert("exposure", frame=1)
scene.view_settings.keyframe_insert("exposure", frame=FRAME_END - 16)
scene.view_settings.exposure = -4.2
scene.view_settings.keyframe_insert("exposure", frame=FRAME_END)
scene.view_settings.exposure = 0.50

# 硬规则 4：所有 Action 关键帧统一强制设为 LINEAR（含骨架、焦点 Empty、灯光、相机与遥测材质）
_linear_total = force_all_actions_linear()
print("LINEAR keyframes (all actions):", _linear_total)

# ---------------------------------------------------------------
# 5b. 相机视线遮挡与离地高度自动自检（Raycast Camera-to-Car Self-Check）
# ---------------------------------------------------------------
_deps = bpy.context.evaluated_depsgraph_get()
_car_names = {o.name for o in bpy.data.objects if _is_car_receiver(o)}
_occ_hits = []
_min_cam_z = 999.0

for _name, _f0, _f1, _typ, _pr in _windows:
    _cam_ob = _cams[_name]
    for _f in range(_f0, _f1 + 1, 2):
        scene.frame_set(_f)
        _deps.update()
        _ce = _cam_ob.evaluated_get(_deps)
        _re = rig.evaluated_get(_deps)
        _cpos = _ce.matrix_world.translation.copy()
        _min_cam_z = min(_min_cam_z, _cpos.z)
        if _typ == "onboard":
            # 车载镜头验证视线前方 12m 无赛道外建筑/灌木穿模，且距方向盘 > clip_start (0.5m)
            _pb_sw = _re.pose.bones.get("Bone_Steering_Wheel")
            if _pb_sw:
                _sw_pos = (_re.matrix_world @ _pb_sw.matrix).translation
                _sw_d = (_sw_pos - _cpos).length
                if _sw_d <= _ce.data.clip_start + 0.02:
                    _occ_hits.append((_f, _name, f"SteeringWheelNearClip({_sw_d:.2f}m)"))
            _fwd_dir = (-_ce.matrix_world.col[2].xyz).normalized()
            _hit, _loc, _nrm, _idx, _hob, _ = scene.ray_cast(_deps, _cpos + _fwd_dir * 2.2, _fwd_dir, distance=12.0)
            if _hit and _hob and _hob.name not in _car_names and not _hob.name.startswith(("V5_Track", "V5_RacingLine", "V5_Line_", "V5_Kerb_", "V5_SkyDome", "V5_Ground", "V5_Verge", "V5_Skid", "V5_BrakeZone")):
                _occ_hits.append((_f, _name, _hob.name))
            continue

        _tpos = (_re.matrix_world @ _re.pose.bones["Bone_Root"].matrix).translation + Vector((0.0, 0.0, 0.48))
        _vec = _tpos - _cpos
        _dist = _vec.length
        if _dist > 0.8:
            _dir = _vec.normalized()
            _cur = _cpos + _dir * 0.5
            _rem = _dist - 1.1
            while _rem > 0.05:
                _hit, _loc, _nrm, _idx, _hob, _ = scene.ray_cast(_deps, _cur, _dir, distance=_rem)
                if not _hit or _hob is None:
                    break
                if _hob.name in _car_names or _hob.name == "V5_SkyDome":
                    _step = (_loc - _cur).length + 0.05
                    _cur = _loc + _dir * 0.05
                    _rem -= _step
                    continue
                if _typ in ("heli", "aerial") and ("_Bridge_" in _hob.name and "_Deck" in _hob.name):
                    # 俯拍直升机镜头下赛车正常穿过人行天桥（1 帧自然穿越，非机位遮挡事故）
                    break
                _occ_hits.append((_f, _name, _hob.name))
                break

scene.frame_set(1)
_root_stranded = [o.name for o in scene.collection.objects]
print("[check] camera occlusion: %d blocked frames (min_cam_z=%.2f m) -> %s"
      % (len(_occ_hits), _min_cam_z, "PASS" if (not _occ_hits and _min_cam_z >= 0.18) else str(_occ_hits[:8])))
print("[check] root Scene Collection direct objects: %d -> %s"
      % (len(_root_stranded), "PASS" if not _root_stranded else str(_root_stranded)))

# ---------------------------------------------------------------
# 6. 渲染设置
# ---------------------------------------------------------------
scene.render.engine = 'BLENDER_EEVEE'
scene.eevee.taa_render_samples = 32
scene.eevee.use_raytracing = True
try:
    scene.eevee.ray_tracing_method = 'SCREEN'
except Exception:
    pass
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.render.fps = FPS
scene.frame_start = 1
scene.frame_end = FRAME_END
scene.render.use_motion_blur = True
scene.render.motion_blur_shutter = 0.17
scene.render.motion_blur_position = 'CENTER'
scene.render.image_settings.file_format = 'JPEG'
scene.render.image_settings.quality = 95
scene.render.filepath = os.path.join(FRAMES_DIR, "f_")
scene.view_settings.view_transform = 'AgX'
for look in ('High Contrast', 'AgX - High Contrast', 'Medium High Contrast'):
    try:
        scene.view_settings.look = look
        break
    except Exception:
        continue
scene.view_settings.exposure = 0.50
scene.view_settings.gamma = 1.0

# 泛光
try:
    ng = bpy.data.node_groups.get("Comp_V5") or bpy.data.node_groups.new("Comp_V5", 'CompositorNodeTree')
    ng.nodes.clear()
    rl = ng.nodes.new("CompositorNodeRLayers")
    glare = ng.nodes.new("CompositorNodeGlare")
    for val in ("Bloom", "BLOOM", "bloom"):
        try:
            glare.inputs['Type'].default_value = val
            break
        except Exception:
            continue
    for nm, v in (("Threshold", 2.0), ("Strength", 0.16), ("Size", 6)):
        if nm in glare.inputs:
            try:
                glare.inputs[nm].default_value = v
            except Exception:
                pass
    try:
        comp = ng.nodes.new("CompositorNodeComposite")
    except Exception:
        comp = ng.nodes.new("NodeGroupOutput")
        if not any(s.name == "Image" for s in ng.interface.items_tree):
            ng.interface.new_socket(name="Image", in_out='OUTPUT', socket_type='NodeSocketColor')
    ng.links.new(rl.outputs['Image'], glare.inputs['Image'])
    ng.links.new(glare.outputs['Image'], comp.inputs['Image'])
    scene.compositing_node_group = ng
    scene.use_nodes = True
    print("COMPOSITOR OK")
except Exception as e:
    print("COMPOSITOR FAILED:", e)

for _img in bpy.data.images:
    if _img.filepath and _img.filepath.startswith("//"):
        _img.filepath = bpy.path.abspath(_img.filepath)

bpy.ops.wm.save_as_mainfile(filepath=OUT, relative_remap=False)
print("ANIM SAVED:", OUT, flush=True)


# ---------------------------------------------------------------
# 7. 测试渲染（自动按时间轴标记切换对应机位）
# ---------------------------------------------------------------
def active_cam_at(frame):
    cur = scene.camera
    for name, f0 in _markers:
        if f0 <= frame:
            cur = _cams[name]
    return cur


def render_frames(frames, outdir, res=1600, samples=24):
    os.makedirs(outdir, exist_ok=True)
    orig_cam = scene.camera
    orig_rx, orig_ry = scene.render.resolution_x, scene.render.resolution_y
    orig_smp = scene.eevee.taa_render_samples
    scene.render.resolution_x = res
    scene.render.resolution_y = int(res * 9 / 16)
    scene.eevee.taa_render_samples = samples
    for f in frames:
        scene.camera = active_cam_at(f)
        scene.frame_set(f)
        scene.render.filepath = os.path.join(outdir, f"test_{f:04d}.jpg")
        bpy.ops.render.render(write_still=True)
        print("TEST FRAME", f, "CAM", scene.camera.name)
    scene.camera = orig_cam
    scene.render.resolution_x, scene.render.resolution_y = orig_rx, orig_ry
    scene.eevee.taa_render_samples = orig_smp


test = argval("--test")
if test:
    render_frames([int(x) for x in str(test).split(",")], os.path.join(PROJ, "renders_v5", "test"),
                  res=1600, samples=24)

if argval("--render"):
    os.makedirs(FRAMES_DIR, exist_ok=True)
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.filepath = os.path.join(FRAMES_DIR, "f_")
    bpy.ops.render.render(animation=True)
    print("RENDER DONE")
