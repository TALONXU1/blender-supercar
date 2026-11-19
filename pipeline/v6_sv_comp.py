# -*- coding: utf-8 -*-
"""
V6 SPIDER-VERSE 3D MEGA-CIRCUIT ANIMATION, 24 BLOCKBUSTER CAMERAS & 2.39:1 COMPOSITOR
=====================================================================================
赛道数据: track_data/spiderverse_circuit.json
          (Neo-Monaco x Nueva York 2099 Sky-Harbor / 3.72 km / ΔZ=+42.35 m / 17.4° Bank /
           53.3333 s / 96 Beats @ 108 BPM / 1,281 Frames @ 24 fps)
输入工程: v6_spiderverse/v6_stage_lookdev.blend   (只读输入，100% 隔离 V5)
输出工程: v6_spiderverse/v6_stage_anim_sv.blend
相机清单: v6_spiderverse/v6_shots_manifest.json

用法:
  python pipeline/v6_sv_comp.py --manifest-only
  blender -b -P pipeline/v6_sv_comp.py
  blender -b -P pipeline/v6_sv_comp.py -- --test 35,282,413,414,635,960,1041,1067,1068,1134
"""
import json
import math
import os
import sys
from math import sin, cos, pi, radians, degrees, sqrt, exp, atan2

PROJ = r"D:\项目session\blender-supercar"
TRACK_JSON = os.path.join(PROJ, "track_data", "spiderverse_circuit.json")
MANIFEST_OUT = os.path.join(PROJ, "v6_spiderverse", "v6_shots_manifest.json")

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]


def argval(flag, default=None):
    if flag in ARGV:
        i = ARGV.index(flag)
        if i + 1 < len(ARGV) and not ARGV[i + 1].startswith("--"):
            return ARGV[i + 1]
        return True
    return default


MANIFEST_ONLY = bool(argval("--manifest-only", False))
IN_BLEND = argval("--in", os.path.join(PROJ, "v6_spiderverse", "v6_stage_lookdev.blend"))
OUT_BLEND = argval("--out", os.path.join(PROJ, "v6_spiderverse", "v6_stage_anim_sv.blend"))
TEST_FRAMES = argval("--test", None)

os.makedirs(os.path.dirname(os.path.abspath(OUT_BLEND)), exist_ok=True)

# ---------------------------------------------------------------------------
# 0. 读取三维高程+倾角赛道数据并构建精确 C2 闭环插值器
# ---------------------------------------------------------------------------
raw = json.load(open(TRACK_JSON, encoding="utf-8"))
META = raw["meta"]
PTS = raw["points"]
N_PTS = len(PTS)
FPS = int(META.get("fps", 24))
BPM = float(META.get("bpm", 108.0))
BEAT_S = 60.0 / BPM
BEAT_F = BEAT_S * FPS                       # 13.3333333 帧/拍
TOTAL_BEATS = int(META.get("beats", 96))
FRAME_END = int(META.get("frame_end", 1281))
LAP_S = float(META["sim_lap_s"])            # 53.3333 s
LAP_LEN = float(META["measured_length_km"]) * 1000.0
HALF_W = float(META.get("track_half_width_m", 7.0))
DT = LAP_S / (FRAME_END - 1)
R_TIRE = 0.357
WHEELBASE = 3.6


def _unwrap_deg(arr):
    out = [float(arr[0])]
    for a in arr[1:]:
        d = (float(a) - out[-1] + 180.0) % 360.0 - 180.0
        out.append(out[-1] + d)
    return out


# 构造带闭环尾点 (idx = N_PTS, t = LAP_S) 的连续数组，消除 f=1281 接缝误差
_hd_un = _unwrap_deg([p["heading_deg"] for p in PTS] + [PTS[0]["heading_deg"]])
T_ARR = [float(p["t"]) for p in PTS] + [LAP_S]
S_ARR = [float(p["s"]) for p in PTS] + [LAP_LEN]
CX_ARR = [float(p["xy"][0]) for p in PTS] + [float(PTS[0]["xy"][0])]
CY_ARR = [float(p["xy"][1]) for p in PTS] + [float(PTS[0]["xy"][1])]
CZ_ARR = [float(p["z"]) for p in PTS] + [float(PTS[0]["z"])]
RX_ARR = [float(p["racing_xy"][0]) for p in PTS] + [float(PTS[0]["racing_xy"][0])]
RY_ARR = [float(p["racing_xy"][1]) for p in PTS] + [float(PTS[0]["racing_xy"][1])]
RZ_ARR = [float(p["racing_z"]) for p in PTS] + [float(PTS[0]["racing_z"])]
OFF_ARR = [float(p["racing_offset_m"]) for p in PTS] + [float(PTS[0]["racing_offset_m"])]
PT_ARR = [float(p["pitch_deg"]) for p in PTS] + [float(PTS[0]["pitch_deg"])]
BK_ARR = [float(p["bank_deg"]) for p in PTS] + [float(PTS[0]["bank_deg"])]
KV_ARR = [float(p["curv_1pm"]) for p in PTS] + [float(PTS[0]["curv_1pm"])]
VL_ARR = [float(p["v_mps"]) for p in PTS] + [float(PTS[0]["v_mps"])]
TUN_ARR = [bool(p["tunnel"]) for p in PTS] + [bool(PTS[0]["tunnel"])]
BRG_ARR = [bool(p["bridge"]) for p in PTS] + [bool(PTS[0]["bridge"])]
ZN_ARR = [str(p["zone"]) for p in PTS] + [str(PTS[0]["zone"])]


def _v_add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _v_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _v_mul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def _v_len(a):
    return sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def _v_norm(a):
    ln = max(1e-12, _v_len(a))
    return (a[0] / ln, a[1] / ln, a[2] / ln)


def _v_lerp(a, b, f):
    return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f)


def _v_dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def ribbon_basis_tuples(h_rad, pt_rad, bk_rad):
    """与 @track / @env-2 100% 共享的三维正交路面基底 (T=前向切线, R=倾角右向, U=倾角法向向上)"""
    ch, sh = cos(h_rad), sin(h_rad)
    cp, sp = cos(pt_rad), sin(pt_rad)
    cb, sb = cos(bk_rad), sin(bk_rad)
    T = _v_norm((cp * ch, cp * sh, sp))
    R0 = (sh, -ch, 0.0)
    U0 = _v_norm((-sp * ch, -sp * sh, cp))
    R = _v_norm((cb * R0[0] - sb * U0[0], cb * R0[1] - sb * U0[1], cb * R0[2] - sb * U0[2]))
    U = _v_norm((sb * R0[0] + cb * U0[0], sb * R0[1] + cb * U0[1], sb * R0[2] + cb * U0[2]))
    return T, R, U


def sample_3d(t_sec):
    t_c = max(0.0, min(LAP_S - 1e-7, t_sec))
    lo, hi = 0, N_PTS
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if T_ARR[mid] <= t_c:
            lo = mid
        else:
            hi = mid
    span = max(T_ARR[lo + 1] - T_ARR[lo], 1e-9)
    u = (t_c - T_ARR[lo]) / span
    lerp1 = lambda arr: arr[lo] + (arr[lo + 1] - arr[lo]) * u

    h_deg = lerp1(_hd_un)
    pt_deg = lerp1(PT_ARR)
    bk_deg = lerp1(BK_ARR)
    T, R, U = ribbon_basis_tuples(radians(h_deg), radians(pt_deg), radians(bk_deg))

    c_pos = (lerp1(CX_ARR), lerp1(CY_ARR), lerp1(CZ_ARR))
    r_pos = (lerp1(RX_ARR), lerp1(RY_ARR), lerp1(RZ_ARR))
    return dict(
        t=t_c,
        s=lerp1(S_ARR),
        c_pos=c_pos,
        pos=r_pos,
        off=lerp1(OFF_ARR),
        heading_deg=h_deg,
        heading=radians(h_deg),
        pitch_deg=pt_deg,
        pitch=radians(pt_deg),
        bank_deg=bk_deg,
        bank=radians(bk_deg),
        k=lerp1(KV_ARR),
        v=lerp1(VL_ARR),
        tunnel=TUN_ARR[lo if u < 0.5 else lo + 1],
        bridge=BRG_ARR[lo if u < 0.5 else lo + 1],
        zone=ZN_ARR[lo],
        T=T,
        R=R,
        U=U,
    )


def sample_at_s(s_query):
    s_c = s_query % LAP_LEN
    lo, hi = 0, N_PTS
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if S_ARR[mid] <= s_c:
            lo = mid
        else:
            hi = mid
    span = max(S_ARR[lo + 1] - S_ARR[lo], 1e-9)
    u = (s_c - S_ARR[lo]) / span
    t_q = T_ARR[lo] + (T_ARR[lo + 1] - T_ARR[lo]) * u
    return sample_3d(t_q)


# ---------------------------------------------------------------------------
# 1. 预计算全部 1,281 帧三维运动学与遥测状态
# ---------------------------------------------------------------------------
GEAR_TOPS_KMH = [96.0, 134.0, 170.0, 204.0, 236.0, 267.0, 298.0, 348.0]


def gear_and_rpm(v_kmh):
    for gi, top in enumerate(GEAR_TOPS_KMH):
        if v_kmh <= top or gi == 7:
            low = 55.0 if gi == 0 else GEAR_TOPS_KMH[gi - 1] * 0.80
            frac = max(0.0, min(1.0, (v_kmh - low) / max(top - low, 1.0)))
            return gi + 1, frac
    return 8, 1.0


frame_data = {}
cum_dist = 0.0
prev_p = None
for f in range(1, FRAME_END + 1):
    fd = sample_3d((f - 1) * DT)
    if prev_p is not None:
        cum_dist += _v_len(_v_sub(fd["pos"], prev_p))
    prev_p = fd["pos"]
    fd["dist"] = cum_dist
    frame_data[f] = fd

for f in range(1, FRAME_END + 1):
    f0, f1 = max(1, f - 2), min(FRAME_END, f + 2)
    dt_span = (f1 - f0) * DT
    fd = frame_data[f]
    fd["accel"] = (frame_data[f1]["v"] - frame_data[f0]["v"]) / dt_span
    fd["dpitch_dt"] = (frame_data[f1]["pitch_deg"] - frame_data[f0]["pitch_deg"]) / dt_span
    v, k, bk = fd["v"], fd["k"], fd["bank"]
    # 倾角抵消部分横向 G 力后的车体净横向 G（+左弯，-右弯）
    net_lat_mps2 = v * v * k - 9.81 * sin(-bk)
    fd["lat_signed"] = net_lat_mps2 / 9.81
    fd["lat"] = abs(fd["lat_signed"])
    g, rf = gear_and_rpm(v * 3.6)
    fd["gear"] = g
    fd["rpm_frac"] = rf
    fd["kerb_prox"] = max(min(1.0, abs(k) / 0.010), min(1.0, max(0.0, abs(fd["off"]) - 3.2) / 1.8))

for f in range(1, FRAME_END + 1):
    w0, w1 = max(1, f - 4), min(FRAME_END, f + 4)
    frame_data[f]["lat_smooth"] = sum(frame_data[j]["lat_signed"] for j in range(w0, w1 + 1)) / (w1 - w0 + 1)


# ---------------------------------------------------------------------------
# 2. 24 个大片级超强冲击力机位（96 拍 = 1,281 帧，全部约束在 ±8.2m 护栏与封闭隧道内部！）
# ---------------------------------------------------------------------------
def beat_frame(b):
    return max(1, min(FRAME_END, int(round(1.0 + b * BEAT_F))))


def smooth01(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3.0 - 2.0 * u)


def micro_vib(f, seed, amp):
    return (sin(f * 1.53 + seed) * 0.52
            + sin(f * 3.17 + seed * 1.7) * 0.31
            + sin(f * 5.83 + seed * 3.1) * 0.17) * amp


def safe_track_cam_pos(fd, back=0.0, rel_side=0.0, up=0.5, max_cl=6.3):
    """在三维赛道局部标架中定位相机，并严格限制在中线 ±max_cl 米与隧道拱顶内，杜绝穿墙！"""
    # P_race = C_pos - off * R => 赛车相对中线在 +R 方向的坐标为 -off
    car_r = -fd["off"]
    in_tun = fd["tunnel"] or (2622.0 <= fd["s"] <= 3182.0)
    lim_r = min(max_cl, 5.6) if in_tun else max_cl
    cl_r = max(-lim_r, min(lim_r, car_r + rel_side))
    safe_up = max(0.20, min(3.75, up) if in_tun else up)
    base = _v_add(fd["c_pos"], _v_mul(fd["R"], cl_r))
    base = _v_sub(base, _v_mul(fd["T"], back))
    base = _v_add(base, _v_mul(fd["U"], safe_up))
    return base


def fixed_cl_pos(s_cam, cl_side, up):
    fd_s = sample_at_s(s_cam)
    in_tun = fd_s["tunnel"] or (2622.0 <= fd_s["s"] <= 3182.0)
    lim_r = 5.6 if in_tun else 6.4
    cl_r = max(-lim_r, min(lim_r, cl_side))
    safe_up = max(0.22, min(3.75, up) if in_tun else up)
    base = _v_add(fd_s["c_pos"], _v_mul(fd_s["R"], cl_r))
    return _v_add(base, _v_mul(fd_s["U"], safe_up)), fd_s["U"]


def lens_for_framing(dist, frac, cos_a=0.0, lo=16.0, hi=300.0):
    w_eff = 2.2 + (4.7 - 2.2) * (1.0 - abs(cos_a))
    return max(lo, min(hi, frac * 36.0 * max(dist, 1.2) / max(w_eff, 0.5)))


SHOTS = [
    # ==================== ACT I: EARTH-1610 MILES (Beats 0..32, f=1..427) ====================
    # 1. FPV 摩天楼高空俯冲直扑扩散器尾焰 (Canyon Start，避开顶部高架拱梁)
    ("Cam_S01_CanyonFPVDrop", 0, 4, "chase",
     dict(back0=9.6, back1=4.8, side0=-1.8, side1=0.6, h0=6.6, h1=0.44,
          aim0=3.6, aim1=3.8, lens0=22, lens1=15, fstop=3.2, roll0=-14.0, roll1=3.5)),
    # 2. 15mm 贴地 22cm 擦湿滑霓虹路面反向仰拍前翼+摩天楼群 (15° 荷兰角倾斜)
    ("Cam_S02_ScraperFrontWing", 4, 8, "scraper",
     dict(back0=-4.6, back1=-3.4, side0=1.75, side1=1.45, h0=0.23, h1=0.26,
          aim_back=0.2, aim_h=0.46, lens0=15, lens1=16, fstop=2.8, roll0=15.0, roll1=11.0)),
    # 3. 峡谷 S 弯贴护栏极近距甩镜摇摄 (Chicane Apex f=125)
    ("Cam_S03_ChicaneWhipPan", 8, 12, "fixed",
     dict(s_cam=406.0, cl_side=-5.9, h=0.58, framing=0.33, fstop=2.8, aim_lerp=0.76, roll=-5.0, max_lens=135)),
    # 4. Halo 座舱超广角：实时 12fps 方向盘修舵 + 15 颗换挡灯 + 峡谷高架光刃掠过
    ("Cam_S04_HaloCockpitCanyon", 12, 16, "onboard",
     dict(fwd=-0.46, side=0.06, h=0.89, pitch_deg=-8.2, lens=17, fstop=11.0)),
    # 5. DRS 加速动态广角畸变冲刺 (26mm -> 14.5mm FOV Warp 冲向 Eau Rouge 坡底!)
    ("Cam_S05_ViaductFOVWarp", 16, 20, "chase",
     dict(back0=5.2, back1=7.0, side0=-0.9, side1=0.9, h0=0.55, h1=0.34,
          aim0=2.8, aim1=4.5, lens0=26, lens1=14.5, fstop=3.2, roll0=2.0, roll1=-5.0)),
    # 6. [CLIP 1 起点 f=269] Eau-Rouge 318km/h 坡底触底钛合金火花暴射 + +13.5° 陡坡仰冲!
    ("Cam_S06_EauRougeSparkScrape", 20, 24, "scraper",
     dict(back0=3.8, back1=4.9, side0=-2.1, side1=1.8, h0=0.24, h1=0.52,
          aim_back=-1.4, aim_h=0.48, lens0=15, lens1=17, fstop=2.8, roll0=-14.0, roll1=12.0)),
    # 7. [CLIP 1 后半] Raidillon 陡坡陀螺环绕攀升，回望脚下 40m 深摩天楼峡谷与螺旋翼尖涡流
    ("Cam_S07_RaidillonSkyClimb", 24, 28, "orbit",
     dict(a0=142, a1=46, r0=6.4, r1=5.2, h0=0.75, h1=1.85,
          lens=21, fstop=3.2, roll=-8.0, roll_end=7.0)),
    # 8. 长焦贴地仰望坡顶剪影（正对前方 115m 双塔斜拉桥门洞与 255m 巨型蜘蛛侠次元圆月 + f=413..414 冲击帧 #1!）
    ("Cam_S08_MoonCrestTele300", 28, 32, "chase",
     dict(back0=14.5, back1=9.8, side0=-0.65, side1=0.55, h0=0.34, h1=0.44,
          aim0=6.5, aim1=9.0, lens0=78, lens1=105, fstop=2.8, roll0=-2.5, roll1=2.0)),

    # ==================== ACT II: EARTH-65 GWEN WATERCOLOR (Beats 32..67, f=428..894) ====================
    # 9. 跨海斜拉天空大桥：格温水彩青品天空 + 115m 双塔斜拉索扇面高速切割
    ("Cam_S09_BridgePylonReveal", 32, 36, "chase",
     dict(back0=5.8, back1=8.6, side0=2.8, side1=-2.8, h0=0.34, h1=2.40,
          aim0=3.2, aim1=2.2, lens0=17, lens1=20, fstop=3.2, roll0=9.0, roll1=-7.0)),
    # 10. 悬索桥纯正侧面刀锋横移跟拍（车轮手绘残影弧 + 水彩海湾远景红青错位）
    ("Cam_S10_CableStaySideBlade", 36, 40, "scraper",
     dict(back0=0.4, back1=-0.5, side0=-5.0, side1=-4.6, h0=0.48, h1=0.62,
          aim_back=-0.2, aim_h=0.44, lens0=32, lens1=28, fstop=2.8, roll0=-3.0, roll1=3.0)),
    # 11. [CLIP 2 起点 f=585] 天空桥末端贴地倒退迎面导引，冲入 17.4° 巨型倾角碗状弯
    ("Cam_S11_BridgeDeckPursuit", 40, 45, "scraper",
     dict(back0=-5.8, back1=-4.2, side0=1.2, side1=-1.6, h0=0.28, h1=0.42,
          aim_back=0.0, aim_h=0.45, lens0=16, lens1=18, fstop=3.0, roll0=11.0, roll1=-10.0)),
    # 12. [CLIP 2 核心] 17.4° 倾角碗外侧玻璃高墙导轨机位（距翼尖仅 0.8m 贴墙高速掠过!）
    ("Cam_S12_BankedWallRailCam", 45, 50, "rail",
     dict(back0=-2.8, back1=3.4, cl_side=-6.1, h0=0.82, h1=0.96,
          lens0=18, lens1=16, fstop=2.8, extra_roll=-8.0)),
    # 13. 倾角碗出弯 135°->38° 甩尾环绕，双排气管星芒回火喷射
    ("Cam_S13_BowlWhipOrbit", 50, 54, "orbit",
     dict(a0=136, a1=38, r0=5.8, r1=4.8, h0=1.15, h1=0.52,
          lens=22, fstop=3.0, roll=10.0, roll_end=-8.0)),
    # 14. Corkscrew 悬崖盲坡顶俯冲切入（路面在轮胎下方骤降 40 米!）
    ("Cam_S14_CorkscrewCrestDive", 54, 59, "chase",
     dict(back0=7.6, back1=4.6, side0=-2.4, side1=2.0, h0=3.60, h1=0.52,
          aim0=2.6, aim1=4.2, lens0=24, lens1=16, fstop=3.2, roll0=-13.0, roll1=12.0)),
    # 15. Corkscrew -13.94° 极限下坠座舱第一视角（车头直插霓虹海港深渊!）
    ("Cam_S15_CorkscrewPlungePOV", 59, 63, "onboard",
     dict(fwd=-0.46, side=-0.05, h=0.91, pitch_deg=-8.8, lens=16, fstop=11.0)),
    # 16. 坡底 318km/h 重压拉平火花狂飙 + f=893..895 次元撕裂冲入 2099 赛博宇宙!
    ("Cam_S16_BottomOutSparks", 63, 67, "scraper",
     dict(back0=3.9, back1=5.8, side0=1.95, side1=-1.5, h0=0.24, h1=0.48,
          aim_back=-1.5, aim_h=0.46, lens0=15, lens1=17, fstop=2.8, roll0=-12.0, roll1=8.0)),

    # ==================== ACT III: EARTH-928 2099 CYBER (Beats 67..96, f=895..1281) ====================
    # 17. 冲入 520m 封闭赛博激光隧道（28->14mm 极速畸变，341.2 km/h 全场最高速!）
    ("Cam_S17_TunnelPortalWarp", 67, 71, "chase",
     dict(back0=6.8, back1=4.5, side0=0.0, side1=0.4, h0=0.62, h1=0.38,
          aim0=3.5, aim1=5.0, lens0=28, lens1=14, fstop=2.8, roll0=0.0, roll1=6.0)),
    # 18. [CLIP 3 起点 f=993] 341 km/h 激光隧道座舱爆闪：六边形红青光肋以 95m/s 疯狂掠过!
    ("Cam_S18_TunnelCockpitStrobe", 71, 75, "onboard",
     dict(fwd=-0.48, side=0.0, h=0.92, pitch_deg=-8.5, lens=16, fstop=11.0)),
    # 19. [CLIP 3 中段] 隧道内 180° 贴地极速甩镜环绕 -> f=1041 340km/h 刺眼隧道出口硬切!
    ("Cam_S19_TunnelWhipOrbit180", 75, 78, "orbit",
     dict(a0=22, a1=168, r0=4.5, r1=5.2, h0=0.36, h1=0.68,
          lens=16, fstop=2.8, roll=14.0, roll_end=-12.0)),
    # 20. [CLIP 3 高潮] 隧道出口爆闪硬切海港近距迎面重刹 + 碳陶刹车盘炽热红光 + f=1067..1068 巨幅冲击帧 #2!
    ("Cam_S20_HarborBrakeImpact", 78, 82, "scraper",
     dict(back0=-9.2, back1=-4.2, side0=-2.8, side1=-2.0, h0=0.52, h1=0.36,
          aim_back=0.2, aim_h=0.44, lens0=34, lens1=24, fstop=2.8, roll0=6.0, roll1=-5.0)),
    # 21. 81 km/h 悬崖海港发夹弯前轮/炽热碳陶盘超微距特写 (Apex f=1134)
    ("Cam_S21_HairpinWheelMacro", 82, 86, "scraper",
     dict(back0=-1.1, back1=-0.3, side0=-2.85, side1=-2.55, h0=0.30, h1=0.38,
          aim_back=-0.9, aim_h=0.35, lens0=26, lens1=22, fstop=2.8, roll0=9.0, roll1=-6.0)),
    # 22. 出弯弹射贴地尾随：双排气星芒爆震 + 6Hz 雨灯 + 湿胎水雾霓虹弧
    ("Cam_S22_HarborLaunchChase", 86, 90, "chase",
     dict(back0=4.2, back1=6.5, side0=-1.3, side1=1.4, h0=0.28, h1=0.65,
          aim0=2.4, aim1=3.8, lens0=17, lens1=20, fstop=3.0, roll0=-8.0, roll1=6.0)),
    # 23. 海港终点直道低角度斜向掠影：湿滑黑曜石镜面完整倒映 2099 摩天大楼霓虹
    ("Cam_S23_WetMirrorSkyline", 90, 93, "scraper",
     dict(back0=-3.6, back1=2.8, side0=4.2, side1=3.8, h0=0.34, h1=0.48,
          aim_back=-0.4, aim_h=0.45, lens0=20, lens1=22, fstop=2.8, roll0=-9.0, roll1=5.0)),
    # 24. 冲线龙门架近距仰拍拉升收尾 + 末 10 帧电影院压黑淡出
    ("Cam_S24_FinishGantryRise", 93, 96, "chase",
     dict(back0=4.2, back1=8.2, side0=-1.1, side1=1.8, h0=0.40, h1=2.65,
          aim0=2.4, aim1=1.8, lens0=28, lens1=25, fstop=3.2, roll0=4.0, roll1=-5.0)),
]

windows = []
for s_name, b0, b1, s_typ, s_pr in SHOTS:
    f0 = beat_frame(b0)
    f1 = beat_frame(b1)
    windows.append([s_name, f0, f1, s_typ, s_pr])

for i in range(len(windows)):
    windows[i][1] = max(1, windows[i][1])
    if i > 0 and windows[i][1] <= windows[i - 1][2]:
        windows[i][1] = windows[i - 1][2] + 1
    windows[i][2] = min(FRAME_END, max(windows[i][2], windows[i][1] + 2))
windows[-1][2] = FRAME_END

# 预计算每一帧相机世界位置/目标点/滚转角/焦距/光圈（同时导出给 @sfx 的 3D 多普勒引擎）
cam_traj = {}
manifest_shots = []

for s_name, f0, f1, s_typ, pr in windows:
    span = max(1, f1 - f0)
    fixed_loc, fixed_up = (None, None)
    if s_typ == "fixed":
        fixed_loc, fixed_up = fixed_cl_pos(pr["s_cam"], pr["cl_side"], pr["h"])
    aim_prev = None

    for f in range(f0, f1 + 1):
        e = smooth01((f - f0) / span)
        fd = frame_data[f]
        v_fac = fd["v"] / 90.0
        kerb = fd["kerb_prox"]

        if s_typ == "chase":
            back = pr["back0"] + (pr["back1"] - pr["back0"]) * e
            side = pr["side0"] + (pr["side1"] - pr["side0"]) * e
            up = pr["h0"] + (pr["h1"] - pr["h0"]) * e
            loc = safe_track_cam_pos(fd, back=back, rel_side=side, up=up, max_cl=6.2)
            vib = 0.008 + 0.006 * v_fac
            loc = _v_add(loc, _v_mul(fd["U"], micro_vib(f, 13.0, vib)))
            aim_d = pr["aim0"] + (pr["aim1"] - pr["aim0"]) * e
            tgt = _v_add(_v_add(fd["pos"], _v_mul(fd["T"], aim_d)), _v_mul(fd["U"], 0.48))
            g_bank = max(-3.5, min(3.5, -fd["lat_smooth"] * 0.45))
            roll = pr["roll0"] + (pr["roll1"] - pr["roll0"]) * e + g_bank
            lens = pr["lens0"] + (pr["lens1"] - pr["lens0"]) * e
            up_vec = _v_norm(_v_lerp(fd["U"], (0.0, 0.0, 1.0), 0.35))

        elif s_typ == "scraper":
            back = pr["back0"] + (pr["back1"] - pr["back0"]) * e
            side = pr["side0"] + (pr["side1"] - pr["side0"]) * e
            up = pr["h0"] + (pr["h1"] - pr["h0"]) * e
            loc = safe_track_cam_pos(fd, back=back, rel_side=side, up=up, max_cl=6.3)
            vib = 0.003 + 0.004 * v_fac + 0.004 * kerb
            loc = _v_add(loc, _v_mul(fd["U"], micro_vib(f, 41.0, vib)))
            tgt = _v_add(_v_sub(fd["pos"], _v_mul(fd["T"], pr["aim_back"])), _v_mul(fd["U"], pr["aim_h"]))
            roll = pr["roll0"] + (pr["roll1"] - pr["roll0"]) * e + micro_vib(f, 43.0, 0.35 * (0.4 + kerb))
            lens = pr["lens0"] + (pr["lens1"] - pr["lens0"]) * e
            up_vec = fd["U"]

        elif s_typ == "rail":
            back = pr["back0"] + (pr["back1"] - pr["back0"]) * e
            up = pr["h0"] + (pr["h1"] - pr["h0"]) * e
            loc = _v_add(fd["c_pos"], _v_mul(fd["R"], pr["cl_side"]))
            loc = _v_sub(loc, _v_mul(fd["T"], back))
            loc = _v_add(loc, _v_mul(fd["U"], up))
            tgt = _v_add(fd["pos"], _v_mul(fd["U"], 0.44))
            roll = pr.get("extra_roll", 0.0) + micro_vib(f, 57.0, 0.25)
            lens = pr["lens0"] + (pr["lens1"] - pr["lens0"]) * e
            up_vec = fd["U"]

        elif s_typ == "orbit":
            ang = radians(pr["a0"] + (pr["a1"] - pr["a0"]) * e)
            rad = pr["r0"] + (pr["r1"] - pr["r0"]) * e
            up = pr["h0"] + (pr["h1"] - pr["h0"]) * e
            # 沿赛道切向 cos(ang) 与法平面右向 -sin(ang) 环绕，并自动约束在护栏/隧道内
            back = -rad * cos(ang)
            side = -rad * sin(ang)
            loc = safe_track_cam_pos(fd, back=back, rel_side=side, up=up, max_cl=5.6 if fd["tunnel"] else 6.3)
            tgt = _v_add(fd["pos"], _v_mul(fd["U"], 0.45))
            roll = pr["roll"] + (pr["roll_end"] - pr["roll"]) * e
            lens = pr["lens"]
            up_vec = _v_norm(_v_lerp(fd["U"], (0.0, 0.0, 1.0), 0.25))

        elif s_typ == "fixed":
            loc = fixed_loc
            tgt_raw = _v_add(fd["pos"], _v_mul(fd["U"], 0.44))
            aim_prev = tgt_raw if aim_prev is None else _v_lerp(aim_prev, tgt_raw, pr.get("aim_lerp", 0.72))
            tgt = aim_prev
            dv = _v_sub(loc, fd["pos"])
            d = max(2.0, _v_len(dv))
            cos_a = abs(_v_dot(fd["T"], _v_norm(dv)))
            lens = lens_for_framing(d, pr["framing"], cos_a, lo=18.0, hi=pr.get("max_lens", 280.0))
            roll = pr.get("roll", 0.0)
            up_vec = _v_norm(_v_lerp(fixed_up, (0.0, 0.0, 1.0), 0.5))

        elif s_typ == "onboard":
            vib = 0.0014 + 0.0022 * v_fac + 0.0025 * kerb
            lx = pr.get("side", 0.0) + micro_vib(f, 71.0, vib * 0.7)
            ly = pr["fwd"] + micro_vib(f, 72.0, vib * 0.4)
            lz = pr["h"] + micro_vib(f, 73.0, vib)
            loc = _v_add(fd["pos"], _v_add(_v_mul(fd["R"], lx), _v_add(_v_mul(fd["T"], ly), _v_mul(fd["U"], lz))))
            p_rad = radians(pr.get("pitch_deg", -8.5))
            steer_rad = fd["k"] * WHEELBASE
            tx = lx + steer_rad * 2.5
            ty = ly + 18.0 * cos(p_rad)
            tz = lz + 18.0 * sin(p_rad)
            tgt = _v_add(fd["pos"], _v_add(_v_mul(fd["R"], tx), _v_add(_v_mul(fd["T"], ty), _v_mul(fd["U"], tz))))
            roll = -fd["lat_smooth"] * 0.25 + micro_vib(f, 74.0, 0.16 + 0.20 * kerb)
            lens = pr["lens"]
            up_vec = fd["U"]

        cam_traj[f] = dict(
            shot=s_name,
            type=s_typ,
            loc=loc,
            tgt=tgt,
            up=up_vec,
            roll=roll,
            lens=lens,
            fstop=pr["fstop"],
        )

    manifest_shots.append(dict(
        name=s_name,
        f0=f0,
        f1=f1,
        t0_vid=round((f0 - 1) / float(FPS), 4),
        t1_vid=round(f1 / float(FPS), 4),
        type=s_typ,
        zone=frame_data[(f0 + f1) // 2]["zone"],
        sample_cam_xyz=[round(x, 3) for x in cam_traj[(f0 + f1) // 2]["loc"]],
    ))

# 导出 JSON 清单供 @sfx 与检验脚本读取精确相机轨迹与三幕/冲击帧/片段定义
manifest_payload = dict(
    fps=FPS,
    bpm=BPM,
    beats=TOTAL_BEATS,
    frame_end=FRAME_END,
    duration_vid_s=round(FRAME_END / float(FPS), 6),
    acts=[
        dict(act=1, universe="Earth-1610 Miles", sv_dimension=0.0, f0=1, f1=427),
        dict(act=2, universe="Earth-65 Gwen", sv_dimension=1.0, f0=428, f1=894),
        dict(act=3, universe="Earth-928 2099", sv_dimension=2.0, f0=895, f1=1281),
    ],
    portal_glitches=[[426, 429], [893, 896]],
    impact_frames=[[413, 414], [1067, 1068]],
    showcase_clips=[
        dict(name="clip1_miles_1610", f0=269, f1=364, ss=round(268 / 24.0, 6), dur=4.0),
        dict(name="clip2_gwen_65", f0=585, f1=680, ss=round(584 / 24.0, 6), dur=4.0),
        dict(name="clip3_2099_impact", f0=993, f1=1088, ss=round(992 / 24.0, 6), dur=4.0),
    ],
    shots=manifest_shots,
    per_frame_cam=[
        dict(
            f=f,
            shot=cam_traj[f]["shot"],
            type=cam_traj[f]["type"],
            cam_xyz=[round(x, 3) for x in cam_traj[f]["loc"]],
            car_xyz=[round(x, 3) for x in frame_data[f]["pos"]],
            v_mps=round(frame_data[f]["v"], 3),
            tunnel=bool(frame_data[f]["tunnel"]),
        )
        for f in range(1, FRAME_END + 1)
    ],
)
with open(MANIFEST_OUT, "w", encoding="utf-8") as fp:
    json.dump(manifest_payload, fp, ensure_ascii=False, indent=2)
print("V6 SHOTS MANIFEST SAVED:", MANIFEST_OUT, f"({len(manifest_shots)} shots, {FRAME_END} frames)")

if MANIFEST_ONLY:
    sys.exit(0)

# ===========================================================================
# 3. BLENDER 场景构建：三维姿态烘焙 + 12fps On-Twos + 24 机位 + 2.39:1 合成器
# ===========================================================================
import bpy
import numpy as np
from mathutils import Vector, Matrix, Euler

bpy.ops.wm.open_mainfile(filepath=IN_BLEND)
scene = bpy.context.scene
rig = bpy.data.objects["RIG_F1_Race"]


def iter_fcurves(action):
    fcs = list(getattr(action, "fcurves", []) or [])
    if fcs:
        return fcs
    for layer in getattr(action, "layers", []) or []:
        for strip in getattr(layer, "strips", []) or []:
            for cb in getattr(strip, "channelbags", []) or []:
                fcs.extend(cb.fcurves)
    return fcs


# 清除旧动画残留（从全新三维赛道重烘焙 1..1281）
if rig.animation_data:
    rig.animation_data_clear()

# Outliner 整洁：RIG_F1_Race 归入 SCIFI_F1_2035，机位归入 V6_08_Cameras，灯光归入 V5_07_Lighting / V6_07_Lighting
_scifi_coll = bpy.data.collections.get("SCIFI_F1_2035")
if _scifi_coll:
    if rig.name not in _scifi_coll.objects:
        _scifi_coll.objects.link(rig)
    if rig.name in scene.collection.objects:
        scene.collection.objects.unlink(rig)

_lgt_coll = (bpy.data.collections.get("V6_07_Lighting")
             or bpy.data.collections.get("V5_07_Lighting")
             or bpy.data.collections.new("V6_07_Lighting"))
if _lgt_coll.name not in scene.collection.children:
    scene.collection.children.link(_lgt_coll)

_cam_coll = bpy.data.collections.get("V6_08_Cameras") or bpy.data.collections.new("V6_08_Cameras")
if _cam_coll.name not in scene.collection.children:
    scene.collection.children.link(_cam_coll)

# 移除任何旧 Cam_S* 对象
for _old_ob in list(bpy.data.objects):
    if _old_ob.type == 'CAMERA' and _old_ob.name.startswith("Cam_S"):
        bpy.data.objects.remove(_old_ob, do_unlink=True)


def _is_car_receiver(ob):
    if ob.type not in ('MESH', 'CURVE'):
        return False
    if ob.name.startswith(("V5_", "V6_", "EM_", "GEO_Race")):
        return False
    return (ob.parent == rig) or ob.name.startswith(("GEO_F1_", "GEO_MERC_", "DEC_"))


# 随车三点柔光（沿三维赛道标架跟随，Light Linking 专属照亮赛车，绝不在湿滑镜面沥青上留假光斑！）
_car_coll = bpy.data.collections.get("V5_CarLightReceivers") or bpy.data.collections.new("V5_CarLightReceivers")
if _car_coll.name not in _lgt_coll.children:
    _lgt_coll.children.link(_car_coll)
_car_coll.hide_viewport = True
for _ob in bpy.data.objects:
    if _is_car_receiver(_ob) and _ob.name not in _car_coll.objects:
        _car_coll.objects.link(_ob)

for _old_l in [o for o in bpy.data.objects if o.type == 'LIGHT' and o.name.startswith("LGT_V5Car_")]:
    bpy.data.objects.remove(_old_l, do_unlink=True)

_FILL = [
    dict(ahead=5.2, side=-5.5, up=3.6, energy=140.0, size=14.0, color=(0.30, 0.90, 1.0)),
    dict(ahead=5.2, side=5.5, up=3.6, energy=140.0, size=14.0, color=(1.0, 0.30, 0.66)),
    dict(ahead=-6.5, side=1.8, up=2.4, energy=190.0, size=9.0, color=(0.88, 0.94, 1.0)),
]
fill_lights = []
for i, spec in enumerate(_FILL):
    ld = bpy.data.lights.new(f"LGT_V5Car_{i}", 'AREA')
    ld.energy = spec["energy"]
    ld.size = spec["size"]
    ld.color = spec["color"]
    ld.use_shadow = False
    lo = bpy.data.objects.new(f"LGT_V5Car_{i}", ld)
    _lgt_coll.objects.link(lo)
    try:
        lo.light_linking.receiver_collection = _car_coll
    except Exception:
        pass
    fill_lights.append((lo, spec))

cam_focus = bpy.data.objects.get("V5_CamFocus")
if not cam_focus:
    cam_focus = bpy.data.objects.new("V5_CamFocus", None)
    cam_focus.empty_display_type = 'PLAIN_AXES'
    cam_focus.empty_display_size = 0.6
if cam_focus.name not in _cam_coll.objects:
    _cam_coll.objects.link(cam_focus)
for _c in list(cam_focus.users_collection):
    if _c != _cam_coll:
        _c.objects.unlink(cam_focus)
if cam_focus.animation_data:
    cam_focus.animation_data_clear()

# 动态遥测材质（刹车盘热辉光、卡钳余热、独立 6Hz FIA 尾部雨灯、方向盘 15 颗三色换挡灯）
rig["steer_ratio"] = 9.5

rain_emit_input = None
_rl_ob = bpy.data.objects.get("GEO_F1_FIA_RainLight")
if _rl_ob and hasattr(_rl_ob.data, "materials"):
    _m_rain = bpy.data.materials.get("Mat_FIA_RainLight") or bpy.data.materials.new("Mat_FIA_RainLight")
    _m_rain.use_nodes = True
    if _m_rain.node_tree.animation_data:
        _m_rain.node_tree.animation_data_clear()
    _rnt = _m_rain.node_tree
    _rnt.nodes.clear()
    _rb = _rnt.nodes.new("ShaderNodeBsdfPrincipled")
    _rb.inputs['Base Color'].default_value = (0.12, 0.005, 0.010, 1.0)
    _rb.inputs['Roughness'].default_value = 0.20
    _rb.inputs['Emission Color'].default_value = (1.0, 0.02, 0.04, 1.0)
    _rb.inputs['Emission Strength'].default_value = 3.0
    _rout = _rnt.nodes.new("ShaderNodeOutputMaterial")
    _rnt.links.new(_rb.outputs['BSDF'], _rout.inputs['Surface'])
    if _rl_ob.data.materials:
        _rl_ob.data.materials[0] = _m_rain
    else:
        _rl_ob.data.materials.append(_m_rain)
    rain_emit_input = _rb.inputs['Emission Strength']

brake_disc_emit_inputs = []
caliper_emit_inputs = []

_m_hg = bpy.data.materials.get("Mat_Brake_HeatGlow")
if _m_hg and _m_hg.node_tree:
    if _m_hg.node_tree.animation_data:
        _m_hg.node_tree.animation_data_clear()
    _e_existing = _m_hg.node_tree.nodes.get("V5_BrakeGlowEmit")
    _m_existing = _m_hg.node_tree.nodes.get("V5_BrakeGlowMix")
    if _e_existing and _m_existing:
        brake_disc_emit_inputs.append(("glow_sheet", _e_existing.inputs['Strength'], _m_existing.inputs['Fac']))
    elif len(_m_hg.node_tree.nodes) <= 2:
        try:
            _m_hg.surface_render_method = 'BLENDED'
        except Exception:
            pass
        _hnt = _m_hg.node_tree
        _hnt.nodes.clear()
        _htc = _hnt.nodes.new("ShaderNodeTexCoord")
        _hsub = _hnt.nodes.new("ShaderNodeVectorMath")
        _hsub.operation = 'SUBTRACT'
        _hsub.inputs[1].default_value = (0.5, 0.5, 0.5)
        _hlen = _hnt.nodes.new("ShaderNodeVectorMath")
        _hlen.operation = 'LENGTH'
        _hramp = _hnt.nodes.new("ShaderNodeValToRGB")
        _hramp.color_ramp.interpolation = 'EASE'
        _hramp.color_ramp.elements[0].position = 0.16
        _hramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
        _el = _hramp.color_ramp.elements.new(0.33)
        _el.color = (1.0, 0.20, 0.03, 1.0)
        _hramp.color_ramp.elements[-1].position = 0.49
        _hramp.color_ramp.elements[-1].color = (0.55, 0.03, 0.01, 1.0)
        _htr = _hnt.nodes.new("ShaderNodeBsdfTransparent")
        _hem = _hnt.nodes.new("ShaderNodeEmission")
        _hem.name = "V5_BrakeGlowEmit"
        _hmx = _hnt.nodes.new("ShaderNodeMixShader")
        _hmx.name = "V5_BrakeGlowMix"
        _hout = _hnt.nodes.new("ShaderNodeOutputMaterial")
        _hnt.links.new(_htc.outputs['Generated'], _hsub.inputs[0])
        _hnt.links.new(_hsub.outputs['Vector'], _hlen.inputs[0])
        _hnt.links.new(_hlen.outputs['Value'], _hramp.inputs['Fac'])
        _hnt.links.new(_hramp.outputs['Color'], _hem.inputs['Color'])
        _hnt.links.new(_htr.outputs['BSDF'], _hmx.inputs[1])
        _hnt.links.new(_hem.outputs['Emission'], _hmx.inputs[2])
        _hnt.links.new(_hmx.outputs['Shader'], _hout.inputs['Surface'])
        brake_disc_emit_inputs.append(("glow_sheet", _hem.inputs['Strength'], _hmx.inputs['Fac']))

for _mname in ("Mat_BrakeDisc_CarbonCeramic", "MAT_BrakeDiscGlow", "MAT_BrakeGlow"):
    _md = bpy.data.materials.get(_mname)
    if _md and _md.node_tree:
        if _md.node_tree.animation_data and _md.node_tree.animation_data.action:
            _md.node_tree.animation_data_clear()
        _has_drv = bool(_md.node_tree.animation_data and _md.node_tree.animation_data.drivers)
        if not _has_drv:
            for _n in _md.node_tree.nodes:
                if _n.type == 'BSDF_PRINCIPLED' and 'Emission Strength' in _n.inputs:
                    if not _n.inputs['Emission Color'].is_linked:
                        _n.inputs['Emission Color'].default_value = (1.0, 0.16, 0.02, 1.0)
                    brake_disc_emit_inputs.append(("disc_bsdf", _n.inputs['Emission Strength'], None))
                    break
                if _n.type == 'EMISSION' and 'Strength' in _n.inputs:
                    brake_disc_emit_inputs.append(("disc_emit", _n.inputs['Strength'], None))
                    break

_mc = bpy.data.materials.get("Mat_Caliper_Anodized")
if _mc and _mc.node_tree:
    if _mc.node_tree.animation_data and _mc.node_tree.animation_data.action:
        _mc.node_tree.animation_data_clear()
    _has_drv = bool(_mc.node_tree.animation_data and _mc.node_tree.animation_data.drivers)
    if not _has_drv:
        for _n in _mc.node_tree.nodes:
            if _n.type == 'BSDF_PRINCIPLED' and 'Emission Strength' in _n.inputs:
                if not _n.inputs['Emission Color'].is_linked:
                    _n.inputs['Emission Color'].default_value = (1.0, 0.08, 0.015, 1.0)
                caliper_emit_inputs.append(_n.inputs['Emission Strength'])
                break

shift_led_inputs = []
for _mname, _rng, _col in [
    ("Mat_ShiftLED_Green", range(0, 5), (0.05, 1.0, 0.42)),
    ("Mat_ShiftLED_Yellow", range(5, 10), (1.0, 0.70, 0.04)),
    ("Mat_ShiftLED_Red", range(10, 15), (1.0, 0.03, 0.08)),
]:
    _ml = bpy.data.materials.get(_mname) or bpy.data.materials.new(_mname)
    _ml.use_nodes = True
    if _ml.node_tree.animation_data:
        _ml.node_tree.animation_data_clear()
    _lnt = _ml.node_tree
    _lnt.nodes.clear()
    _lb = _lnt.nodes.new("ShaderNodeBsdfPrincipled")
    _lb.inputs['Base Color'].default_value = (_col[0] * 0.1, _col[1] * 0.1, _col[2] * 0.1, 1.0)
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

# ---------------------------------------------------------------------------
# 4. 烘焙三维车身世界轨迹 (24 fps LINEAR) + 局部 12 fps On-Twos 次级动态
# ---------------------------------------------------------------------------
bone_root = rig.pose.bones["Bone_Root"]
bone_heading = rig.pose.bones["Bone_Heading"]
bone_body = rig.pose.bones["Bone_Body"]
bone_heading.rotation_mode = 'XYZ'
bone_body.rotation_mode = 'XYZ'

cum_spin = 0.0
prev_dist = 0.0
prev_gear = frame_data[1]["gear"]
shift_flash = 0.0
brake_heat_state = 0.0
prev_head_euler = None

for f in range(1, FRAME_END + 1):
    fd = frame_data[f]
    v, acc, k = fd["v"], fd["accel"], fd["k"]
    v_kmh = v * 3.6
    R_v = Vector(fd["R"])
    T_v = Vector(fd["T"])
    U_v = Vector(fd["U"])
    P_v = Vector(fd["pos"])

    # 三维世界位置与三维正交姿态矩阵 (R=+X, T=+Y, U=+Z) -> 轮胎零高度误差贴合 17.4° 倾角与 ±14° 坡面
    root_world = P_v + U_v * 0.012
    bone_root.location = root_world
    m_rot = Matrix((R_v, T_v, U_v)).transposed()
    eul = m_rot.to_euler('XYZ', prev_head_euler) if prev_head_euler is not None else m_rot.to_euler('XYZ')
    prev_head_euler = eul
    bone_heading.rotation_euler = eul
    bone_root.keyframe_insert("location", frame=f)
    bone_heading.keyframe_insert("rotation_euler", frame=f)

    # 景深焦点 Empty 同步锁定车身 + 0.45m 法向高度 (24 fps LINEAR)
    cam_focus.location = P_v + U_v * 0.462
    cam_focus.keyframe_insert("location", frame=f)

    # 随车柔光三维跟随 (24 fps LINEAR)
    for lo, spec in fill_lights:
        lp = P_v + T_v * spec["ahead"] + R_v * spec["side"] + U_v * spec["up"]
        lo.location = lp
        aim_v = (P_v + U_v * 0.45) - lp
        lo.rotation_euler = aim_v.to_track_quat('-Z', 'Y').to_euler()
        lo.keyframe_insert("location", frame=f)
        lo.keyframe_insert("rotation_euler", frame=f)

    # 次级动态与遥测（仅在奇数帧与末帧写入 CONSTANT -> 正宗 12 fps On-Twos 手绘动画节奏！）
    cum_spin += (fd["dist"] - prev_dist) / R_TIRE
    prev_dist = fd["dist"]

    gear = fd["gear"]
    if gear != prev_gear:
        shift_flash = 1.0
        prev_gear = gear
    else:
        shift_flash *= 0.72

    if acc < -2.0:
        brake_pwr = ((-acc - 2.0) / 22.0) * (0.48 + 0.52 * min(1.0, v / 88.0))
        brake_heat_state = min(1.35, brake_heat_state + brake_pwr * (DT / 0.11))
    else:
        tau_cool = 2.85 - 0.45 * min(1.0, v / 88.0)
        brake_heat_state *= exp(-DT / tau_cool)
        # 紧发夹弯带刹入弯（Trail-Braking）余热保持，确保 S21 发夹弯轮毂微距碳陶盘呈樱桃炽红！
        if abs(k) > 0.014 and brake_heat_state > 0.22:
            brake_heat_state = max(brake_heat_state, 0.82)
        if brake_heat_state < 0.003:
            brake_heat_state = 0.0
    fd["brake_heat"] = brake_heat_state
    fd["shift_flash"] = shift_flash

    if f % 2 == 1 or f == FRAME_END:
        # 坡底正曲率压缩下沉 + 加减速俯仰 + 弯道净横向 G 侧倾
        comp_squat = -0.009 * max(0.0, fd["dpitch_dt"] / 14.0)
        pitch_body = max(-2.1, min(1.6, acc * 0.088)) - 0.22 * shift_flash
        roll_body = max(-2.4, min(2.4, -fd["lat_signed"] * 0.28))
        heave = -0.005 + comp_squat + 0.0018 * sin(f * 1.41) + 0.0010 * sin(f * 2.89)
        bone_body.location = (0.0, 0.0, heave)
        bone_body.rotation_euler = (radians(pitch_body), radians(roll_body), 0.0)
        bone_body.keyframe_insert("location", frame=f)
        bone_body.keyframe_insert("rotation_euler", frame=f)

        rig["wheel_spin"] = cum_spin
        rig["steer"] = max(-26.0, min(26.0, degrees(k * WHEELBASE)))
        straight = abs(k) < 0.0022
        rig["drs"] = 1.0 if (straight and v_kmh > 245.0) else (0.0 if abs(k) > 0.005 else 0.5)
        rig["brake_heat"] = brake_heat_state
        rig["rear_slip"] = 1.0
        rig["susp_f"] = -0.004 - 0.015 * max(0.0, -acc) / 14.0 + comp_squat * 0.6
        rig["susp_r"] = -0.004 - 0.016 * max(0.0, acc) / 14.0 + comp_squat * 0.6
        for kk in ("wheel_spin", "steer", "drs", "brake_heat", "rear_slip", "susp_f", "susp_r"):
            rig.keyframe_insert(f'["{kk}"]', frame=f)

        bh = brake_heat_state
        for kind, einp, minp in brake_disc_emit_inputs:
            if kind == "glow_sheet":
                einp.default_value = (bh ** 1.1) * 22.0
                einp.keyframe_insert("default_value", frame=f)
                minp.default_value = min(0.97, (bh ** 0.75) * 0.94)
                minp.keyframe_insert("default_value", frame=f)
            else:
                einp.default_value = (bh ** 1.2) * 15.0
                einp.keyframe_insert("default_value", frame=f)
        for cinp in caliper_emit_inputs:
            cinp.default_value = max(0.0, bh - 0.22) * 3.2
            cinp.keyframe_insert("default_value", frame=f)

        if rain_emit_input is not None:
            if acc < -2.5 or fd["tunnel"]:
                pulse_on = ((fd["t"] * 6.0) % 1.0) < 0.55
                rain_emit_input.default_value = 28.0 if pulse_on else (3.5 if fd["tunnel"] else 1.4)
            else:
                rain_emit_input.default_value = 3.2
            rain_emit_input.keyframe_insert("default_value", frame=f)

        rf = fd["rpm_frac"]
        if len(shift_led_inputs) == 3:
            shift_led_inputs[0].default_value = 8.5 if rf > 0.26 else 0.4
            shift_led_inputs[1].default_value = 9.5 if rf > 0.56 else 0.3
            shift_led_inputs[2].default_value = (15.0 if shift_flash > 0.45 else 10.5) if rf > 0.80 else 0.25
            for sinp in shift_led_inputs:
                sinp.keyframe_insert("default_value", frame=f)

# 设置 RIG 曲线插值：Bone_Root & Bone_Heading 为 LINEAR，其余全部 CONSTANT (12fps On-Twos)
if rig.animation_data and rig.animation_data.action:
    for fc in iter_fcurves(rig.animation_data.action):
        is_world = ("Bone_Root" in fc.data_path) or ("Bone_Heading" in fc.data_path)
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR' if is_world else 'CONSTANT'
        fc.update()

for mat in bpy.data.materials:
    if mat.node_tree and mat.node_tree.animation_data and mat.node_tree.animation_data.action:
        for fc in iter_fcurves(mat.node_tree.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = 'CONSTANT'
            fc.update()

# ---------------------------------------------------------------------------
# 5. 驱动 V6_09_ComicFX 三维速度特效（涡流彩带 / 尾焰菱形激波 / 钛合金火花 / 湿胎水雾弧 / 车轮残影）
# ---------------------------------------------------------------------------
fx_coll = bpy.data.collections.get("V6_09_ComicFX")
fx_objs = list(fx_coll.all_objects) if fx_coll else [
    o for o in bpy.data.objects if o.name.startswith(("V6_FX_", "SV_FX_"))
]
ONBOARD_WINDOWS = [(f0, f1) for _, f0, f1, typ, _ in windows if typ == "onboard"]


def _is_onboard_frame(f):
    return any(a <= f <= b for a, b in ONBOARD_WINDOWS)


fx_stats = dict(vortex=0, smear=0, exhaust=0, sparks=0, spray=0)
for idx, fob in enumerate(fx_objs):
    if fob.type not in ('MESH', 'CURVE'):
        continue
    if fob.animation_data:
        fob.animation_data_clear()
    nm_low = fob.name.lower()
    base_s = tuple(fob.scale)
    base_r = tuple(fob.rotation_euler)

    is_wheel = any(k in nm_low for k in ("wheel", "smear", "rim"))
    is_exhaust = any(k in nm_low for k in ("exhaust", "shock", "diamond", "afterburn", "burst", "cone", "flame"))
    is_spark = any(k in nm_low for k in ("spark", "plank", "titanium", "scrape", "slash"))
    is_spray = any(k in nm_low for k in ("spray", "rooster", "mist", "wake", "water"))
    is_front = any(k in nm_low for k in ("front", "fw_", "_fl", "_fr", "nose"))

    if is_wheel:
        fx_stats["smear"] += 1
    elif is_exhaust:
        fx_stats["exhaust"] += 1
    elif is_spark:
        fx_stats["sparks"] += 1
    elif is_spray:
        fx_stats["spray"] += 1
    else:
        fx_stats["vortex"] += 1

    for f in range(1, FRAME_END + 1, 2):
        fd = frame_data[f]
        v_kmh = fd["v"] * 3.6
        if is_wheel:
            gate = max(0.0, min(1.0, (v_kmh - 80.0) / 60.0))
            if gate <= 0.02:
                fob.scale = (0.001, 0.001, 0.001)
            else:
                jit = 0.88 + 0.25 * abs(sin(f * 2.3 + idx * 1.4))
                fob.scale = (base_s[0], base_s[1] * gate * jit, base_s[2] * gate * jit)
                fob.rotation_euler = (base_r[0] + 0.45 * sin(f * 3.3 + idx * 2.0), base_r[1], base_r[2])
                fob.keyframe_insert("rotation_euler", frame=f)
        elif is_exhaust:
            # 换挡爆震、重刹降档回火、发夹弯退档补油以及隧道/坡道全油门加速时喷出双排气管激波菱形火舌!
            full_pull = (v_kmh > 285.0 and fd["accel"] > -0.5 and ((f // 2 + idx) % 2 == 0))
            hairpin_blip = (1055 <= f <= 1140 and ((f // 2) % 2 == 0))
            pop = (fd["shift_flash"] > 0.35) or (fd["accel"] < -4.5 and ((f // 2) % 2 == 0)) or hairpin_blip
            if pop or full_pull:
                amp = 1.38 if fd["shift_flash"] > 0.45 else (1.08 + 0.32 * abs(sin(f * 3.7 + idx)))
                fob.scale = (base_s[0] * amp, base_s[1] * amp * 1.2, base_s[2] * amp)
            else:
                fob.scale = (0.001, 0.001, 0.001)
        elif is_spark:
            # Eau-Rouge 坡底压缩、Corkscrew 坡底拉平、海港重刹/发夹弯压路肩或 >302km/h 极速时狂飙金色钛合金火花!
            compression_zone = (266 <= f <= 324) or (406 <= f <= 422) or (838 <= f <= 885) or (1056 <= f <= 1090)
            kerb_hit = ((fd["kerb_prox"] > 0.42 and v_kmh > 75.0) or (1112 <= f <= 1144)) and ((f // 2 + idx) % 2 == 0)
            high_v_scrape = (v_kmh > 302.0 and ((f // 2 + idx) % 2 == 0))
            if compression_zone or kerb_hit or high_v_scrape:
                amp = (1.42 if compression_zone else 1.18) * (0.85 + 0.35 * abs(sin(f * 2.9 + idx)))
                fob.scale = (base_s[0] * amp, base_s[1] * amp * 1.25, base_s[2] * amp)
            else:
                fob.scale = (0.001, 0.001, 0.001)
        elif is_spray:
            gate = max(0.0, min(1.25, (v_kmh - 135.0) / 140.0))
            if gate <= 0.03 or (_is_onboard_frame(f) and is_front):
                fob.scale = (0.001, 0.001, 0.001)
            else:
                fl = 0.88 + 0.26 * abs(cos(f * 2.7 + idx))
                fob.scale = (base_s[0] * fl, base_s[1] * gate, base_s[2] * gate * fl)
        else:
            drs_b = 1.32 if (abs(fd["k"]) < 0.0022 and v_kmh > 245.0) else 1.0
            gate = max(0.0, min(1.0, (v_kmh - 205.0) / 55.0)) * drs_b
            if gate <= 0.02 or (_is_onboard_frame(f) and is_front):
                fob.scale = (0.001, 0.001, 0.001)
            else:
                fx_w = 1.0 + 0.18 * sin(f * 2.5 + idx * 1.7)
                fz_w = 1.0 + 0.22 * cos(f * 3.1 + idx * 2.3)
                fob.scale = (base_s[0] * fx_w, base_s[1] * min(1.5, gate), base_s[2] * fz_w)
        fob.keyframe_insert("scale", frame=f)

    if fob.animation_data and fob.animation_data.action:
        for fc in iter_fcurves(fob.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = 'CONSTANT'
            fc.update()

for mat in bpy.data.materials:
    if mat.name.startswith("MAT_SV_") and mat.node_tree:
        fl_node = mat.node_tree.nodes.get("SV_FlutterPhase")
        if fl_node and fl_node.outputs:
            if mat.node_tree.animation_data:
                mat.node_tree.animation_data_clear()
            for f in range(1, FRAME_END + 1, 2):
                fl_node.outputs[0].default_value = float((f // 2) * 0.41)
                fl_node.outputs[0].keyframe_insert("default_value", frame=f)
            if mat.node_tree.animation_data and mat.node_tree.animation_data.action:
                for fc in iter_fcurves(mat.node_tree.animation_data.action):
                    for kp in fc.keyframe_points:
                        kp.interpolation = 'CONSTANT'
                    fc.update()

print("[v6_comic_fx]", fx_stats)

# ---------------------------------------------------------------------------
# 6. 构建全部 24 台大片级摄影机 (24 fps LINEAR, 支持三维倾角地平线耦合)
# ---------------------------------------------------------------------------
def cam_matrix_from_look(loc_t, tgt_t, up_t, roll_deg=0.0):
    loc = Vector(loc_t)
    tgt = Vector(tgt_t)
    up_h = Vector(up_t).normalized()
    fwd = (tgt - loc).normalized()
    right = fwd.cross(up_h)
    if right.length < 1e-6:
        right = fwd.cross(Vector((0.0, 0.0, 1.0)))
    right.normalize()
    true_up = right.cross(fwd).normalized()
    # Blender Camera 局部坐标: +X = Right, +Y = Up, -Z = Forward
    m_rot = Matrix((right, true_up, -fwd)).transposed().to_4x4()
    if abs(roll_deg) > 1e-5:
        m_rot = m_rot @ Matrix.Rotation(radians(roll_deg), 4, 'Z')
    return Matrix.Translation(loc) @ m_rot


cams_dict = {}
markers_list = []
for s_name, f0, f1, s_typ, pr in windows:
    cd = bpy.data.cameras.new(s_name + "_DATA")
    cd.clip_start = 0.35
    cd.clip_end = 6000.0
    cd.sensor_width = 36.0
    cd.dof.use_dof = True
    # 压弱传统光学高斯虚化（交给合成器焦外红青印刷错位 CMYK Misregistration）
    cd.dof.aperture_fstop = min(16.0, pr["fstop"] * 2.1)
    cd.dof.aperture_blades = 9
    if s_typ != "onboard":
        cd.dof.focus_object = cam_focus
    else:
        cd.dof.focus_distance = 2.4

    cam_ob = bpy.data.objects.new(s_name, cd)
    cam_ob.rotation_mode = 'XYZ'
    _cam_coll.objects.link(cam_ob)
    cams_dict[s_name] = cam_ob
    markers_list.append((s_name, f0))

    prev_c_eul = None
    for f in range(f0, f1 + 1):
        ct = cam_traj[f]
        mw = cam_matrix_from_look(ct["loc"], ct["tgt"], ct["up"], roll_deg=ct["roll"])
        cam_ob.location = mw.translation
        c_eul = mw.to_euler('XYZ', prev_c_eul) if prev_c_eul is not None else mw.to_euler('XYZ')
        prev_c_eul = c_eul
        cam_ob.rotation_euler = c_eul
        cam_ob.data.lens = ct["lens"]
        cam_ob.keyframe_insert("location", frame=f)
        cam_ob.keyframe_insert("rotation_euler", frame=f)
        cam_ob.data.keyframe_insert("lens", frame=f)

    for act_Owner in (cam_ob.animation_data, cam_ob.data.animation_data):
        if act_Owner and act_Owner.action:
            for fc in iter_fcurves(act_Owner.action):
                for kp in fc.keyframe_points:
                    kp.interpolation = 'LINEAR'
                fc.update()

scene.timeline_markers.clear()
for s_name, f0 in markers_list:
    mk = scene.timeline_markers.new(s_name, frame=f0)
    mk.camera = cams_dict[s_name]
scene.camera = cams_dict[windows[0][0]]

for act_ob in [cam_focus] + [lo for lo, _ in fill_lights]:
    if act_ob.animation_data and act_ob.animation_data.action:
        for fc in iter_fcurves(act_ob.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
            fc.update()

# ---------------------------------------------------------------------------
# 7. 三幕平行宇宙属性 `scene["sv_dimension"]` 与曝光时间轴重置 (1..1281)
# ---------------------------------------------------------------------------
if scene.animation_data and scene.animation_data.action:
    bpy.data.actions.remove(scene.animation_data.action)

scene["sv_dimension"] = 0.0
for fr, val in [
    (1, 0.0), (425, 0.0),
    (426, 2.0), (427, 0.5), (428, 1.0), (429, 0.2), (430, 1.0),
    (892, 1.0),
    (893, 0.0), (894, 1.6), (895, 2.0), (896, 1.2), (897, 2.0),
    (FRAME_END, 2.0),
]:
    scene["sv_dimension"] = float(val)
    scene.keyframe_insert('["sv_dimension"]', frame=fr)

base_exp = float(scene.view_settings.exposure) if abs(scene.view_settings.exposure) < 1.5 else 0.15
SHOT_EXP_TRIM = {
    "Cam_S06_EauRougeSparkScrape": -0.34,
    "Cam_S07_RaidillonSkyClimb": +0.72,
    "Cam_S17_TunnelPortalWarp": -1.12,
    "Cam_S18_TunnelCockpitStrobe": -0.28,
    "Cam_S19_TunnelWhipOrbit180": +0.46,
    "Cam_S20_HarborBrakeImpact": -0.22,
    "Cam_S21_HairpinWheelMacro": +1.18,
    "Cam_S22_HarborLaunchChase": -1.04,
    "Cam_S23_WetMirrorSkyline": +0.76,
    "Cam_S24_FinishGantryRise": +1.08,
}
for s_nm, sf0, sf1, _, _ in windows:
    trim = SHOT_EXP_TRIM.get(s_nm, 0.0)
    if s_nm == "Cam_S24_FinishGantryRise":
        scene.view_settings.exposure = base_exp + trim
        scene.view_settings.keyframe_insert("exposure", frame=sf0)
        scene.view_settings.keyframe_insert("exposure", frame=1271)
        scene.view_settings.exposure = -4.2
        scene.view_settings.keyframe_insert("exposure", frame=FRAME_END)
    else:
        scene.view_settings.exposure = base_exp + trim
        scene.view_settings.keyframe_insert("exposure", frame=sf0)
        scene.view_settings.keyframe_insert("exposure", frame=sf1)
scene.view_settings.exposure = base_exp

if scene.animation_data and scene.animation_data.action:
    for fc in iter_fcurves(scene.animation_data.action):
        is_dim = "sv_dimension" in fc.data_path
        for kp in fc.keyframe_points:
            kp.interpolation = 'CONSTANT' if is_dim else 'LINEAR'
        fc.update()

# 座舱近景适度收细 Solidify 描边修改器
solidify_targets = []
for ob in bpy.data.objects:
    if ob.type == 'MESH' and not ob.name.startswith(("V5_", "V6_")):
        for mod in ob.modifiers:
            if mod.type == 'SOLIDIFY' and mod.use_flip_normals:
                solidify_targets.append((ob, mod, float(mod.thickness)))

if solidify_targets:
    for ob, _, _ in solidify_targets:
        if ob.animation_data:
            ob.animation_data_clear()
    for f in list(range(1, FRAME_END + 1, 4)) + [FRAME_END]:
        mul = 0.62 if _is_onboard_frame(f) else 1.0
        for ob, mod, base_th in solidify_targets:
            mod.thickness = base_th * mul
            ob.keyframe_insert(f'modifiers["{mod.name}"].thickness', frame=f)
    for ob, _, _ in solidify_targets:
        if ob.animation_data and ob.animation_data.action:
            for fc in iter_fcurves(ob.animation_data.action):
                for kp in fc.keyframe_points:
                    kp.interpolation = 'CONSTANT'
                fc.update()

# ---------------------------------------------------------------------------
# 8. 三维相机遮挡自检 (`[check] 3D camera occlusion`)
# ---------------------------------------------------------------------------
deps = bpy.context.evaluated_depsgraph_get()
car_and_fx_names = {
    o.name for o in bpy.data.objects
    if o.type in ('MESH', 'CURVE') and (
        _is_car_receiver(o) or o.name.startswith(("V6_FX_", "SV_FX_"))
        or (fx_coll and o.name in fx_coll.all_objects)
    )
}
# 半透明体积光片不计为实体遮挡
SKIP_OCC_SUBSTR = ("GodRay", "LightBlade", "SkyDome", "Moon", "Portal", "Mist")

occ_hits = []
focus_dists = {}
for s_name, f0, f1, s_typ, _ in windows:
    cam_ob = cams_dict[s_name]
    for f in range(f0, f1 + 1, 2):
        scene.frame_set(f)
        deps.update()
        ce = cam_ob.evaluated_get(deps)
        cpos = ce.matrix_world.translation.copy()
        fpos = cam_focus.evaluated_get(deps).matrix_world.translation.copy()
        d = (fpos - cpos).length
        focus_dists[f] = max(0.6, d)
        focus_dists[min(FRAME_END, f + 1)] = max(0.6, d)
        if s_typ == "onboard" or d <= 0.85:
            continue
        u_dir = (fpos - cpos).normalized()
        cur = cpos + u_dir * 0.40
        rem = d - 1.05
        while rem > 0.05:
            hit, loc, _, _, hob, _ = scene.ray_cast(deps, cur, u_dir, distance=rem)
            if not hit or hob is None:
                break
            if hob.name in car_and_fx_names or any(k in hob.name for k in SKIP_OCC_SUBSTR) or not hob.visible_camera:
                step = (loc - cur).length + 0.06
                cur = loc + u_dir * 0.06
                rem -= step
                continue
            occ_hits.append((f, s_name, hob.name, round((loc - cpos).length, 1), round(d, 1)))
            break

for f in range(1, FRAME_END + 1):
    if f not in focus_dists:
        focus_dists[f] = max(0.6, _v_len(_v_sub(cam_traj[f]["tgt"], cam_traj[f]["loc"])))

print(f"[check] 3D camera occlusion: {len(occ_hits)} blocked frames -> {'PASS' if not occ_hits else occ_hits[:10]}")

# ---------------------------------------------------------------------------
# 9. Cinema-Scope 2.39:1 高反差蜘蛛侠多通道合成器 (`Comp_V6_SpiderVerse`)
# ---------------------------------------------------------------------------
COMP_MASK_DIR = os.path.join(PROJ, "v6_spiderverse", "comp_masks")
os.makedirs(COMP_MASK_DIR, exist_ok=True)


def _save_and_load_mask_png(name, rgba_arr):
    old = bpy.data.images.get(name)
    if old:
        bpy.data.images.remove(old)
    h, w = rgba_arr.shape[:2]
    png_path = os.path.join(COMP_MASK_DIR, f"{name}.png")
    tmp = bpy.data.images.new(name + "_TMP", width=w, height=h, alpha=False)
    tmp.pixels.foreach_set(rgba_arr.ravel())
    tmp.filepath_raw = png_path
    tmp.file_format = 'PNG'
    tmp.save()
    bpy.data.images.remove(tmp)
    im = bpy.data.images.load(png_path, check_existing=True)
    im.name = name
    im.filepath = bpy.path.abspath(png_path)
    return im


def build_packed_speedlines(name="SV_RadialSpeedLines", w=1920, h=1080):
    yg, xg = np.mgrid[0:h, 0:w].astype(np.float32)
    nx = (xg / (w - 1.0)) * 2.0 - 1.0
    ny = (yg / (h - 1.0)) * 2.0 - 1.0
    rad = np.hypot(nx * 1.04, ny * 1.32)
    ang = np.arctan2(ny, nx)
    rng = np.random.default_rng(1610)
    spikes = np.zeros_like(rad)
    for n_freq, wgt in ((108, 0.55), (184, 0.40), (280, 0.28)):
        ph = float(rng.uniform(0.0, 2.0 * pi))
        wv = np.cos(ang * n_freq + ph)
        sharp = np.clip((wv - 0.85) / 0.15, 0.0, 1.0) ** 1.55
        reach = 0.68 + 0.22 * np.sin(ang * 17.0 + ph * 1.5)
        env = np.clip((rad - reach) / np.maximum(1.36 - reach, 0.15), 0.0, 1.0) ** 1.30
        spikes = np.maximum(spikes, sharp * env * wgt * 1.95)
    val = np.clip(spikes, 0.0, 1.0)
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[..., 0] = val
    rgba[..., 1] = val
    rgba[..., 2] = val
    return _save_and_load_mask_png(name, rgba)


def build_packed_halftone_7px(name="SV_Halftone7px", w=1920, h=1080, pitch_px=8.0):
    """1920x1080 旋转 22.5° 的 8.0px 高对比 Ben-Day 半调圆网点屏幕纹理（0.06..0.94 全动态范围）"""
    yg, xg = np.mgrid[0:h, 0:w].astype(np.float32)
    ca, sa = cos(radians(22.5)), sin(radians(22.5))
    u = (xg * ca - yg * sa) / pitch_px
    v = (xg * sa + yg * ca) / pitch_px
    du = u - np.round(u)
    dv = v - np.round(v)
    dist = np.hypot(du, dv)
    dots = np.clip(1.0 - (dist / 0.44) ** 2.1, 0.0, 1.0)
    tex = 0.06 + 0.88 * dots
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[..., 0] = tex
    rgba[..., 1] = tex
    rgba[..., 2] = tex
    return _save_and_load_mask_png(name, rgba)


def build_portal_slash_tear(name="SV_PortalSlashTear", w=1920, h=1080):
    """次元穿越帧斜切漫画分镜裂缝与红青黄故障碎块叠加层 (f=426..429, f=893..896)"""
    yg, xg = np.mgrid[0:h, 0:w].astype(np.float32)
    nx = xg / max(1.0, w - 1.0)
    ny = yg / max(1.0, h - 1.0)
    # 主斜切漫画白边黑沟裂口 + 锯齿闪电折线
    jag = 0.018 * np.sin(ny * 47.0) + 0.009 * np.cos(ny * 113.0)
    d1 = np.abs((nx - 0.52) + (ny - 0.50) * 0.62 + jag)
    d2 = np.abs((nx - 0.24) - (ny - 0.50) * 0.48 - jag * 0.8)
    rgba = np.zeros((h, w, 4), dtype=np.float32)
    # 电光青 / 品红 / 明黄次元裂口辉光带
    cyan_band = (d1 < 0.026) & (d1 >= 0.011)
    mag_band = (d2 < 0.022) & (d2 >= 0.009)
    white_core = (d1 < 0.006) | (d2 < 0.005)
    ink_edge = ((d1 >= 0.006) & (d1 < 0.011)) | ((d2 >= 0.005) & (d2 < 0.009))
    rgba[cyan_band] = (0.05, 0.96, 1.0, 1.0)
    rgba[mag_band] = (1.0, 0.08, 0.52, 1.0)
    rgba[ink_edge] = (0.035, 0.025, 0.08, 1.0)
    rgba[white_core] = (1.0, 0.96, 0.28, 1.0)
    return _save_and_load_mask_png(name, rgba)


def build_packed_cinemascope_mask(name="SV_CinemaScopeBars", w=1920, h=1080):
    """2.39:1 宽银幕遮幅蒙版（上下各 138 px 纯正电影院黑边）"""
    bar = 138
    mask = np.zeros((h, w, 4), dtype=np.float32)
    mask[..., 3] = 1.0
    mask[:bar, :, 0:3] = 1.0
    mask[h - bar:, :, 0:3] = 1.0
    return _save_and_load_mask_png(name, mask)


def get_paper_image():
    ext_p = os.path.join(PROJ, "v6_spiderverse", "textures", "sv_paper_grain.png")
    if os.path.exists(ext_p):
        im = bpy.data.images.load(ext_p, check_existing=True)
        im.filepath = bpy.path.abspath(im.filepath)
        return im
    return build_packed_halftone_7px("SV_PaperFallback", 1024, 1024, 5.0)


sl_img = build_packed_speedlines()
ht_img = build_packed_halftone_7px()
portal_img = build_portal_slash_tear()
cs_img = build_packed_cinemascope_mask()
paper_img = get_paper_image()

vl = scene.view_layers[0]
vl.use_pass_normal = True
vl.use_pass_mist = True
vl.use_pass_z = True
vl.use_pass_emit = False
vl.use_pass_cryptomatte_object = True
if hasattr(vl, "pass_cryptomatte_depth"):
    vl.pass_cryptomatte_depth = 6

if scene.world:
    scene.world.mist_settings.start = 10.0
    scene.world.mist_settings.depth = 155.0
    try:
        scene.world.mist_settings.falloff = 'QUADRATIC'
    except Exception:
        pass

ng = bpy.data.node_groups.get("Comp_V6_SpiderVerse") or bpy.data.node_groups.new("Comp_V6_SpiderVerse", 'CompositorNodeTree')
if ng.animation_data:
    ng.animation_data_clear()
ng.nodes.clear()


def val_node(nm, v):
    n = ng.nodes.new("ShaderNodeValue")
    n.name = nm
    n.label = nm
    n.outputs[0].default_value = float(v)
    return n


def math_op(op, a, b=None, clamp=False):
    n = ng.nodes.new("ShaderNodeMath")
    n.operation = op
    n.use_clamp = clamp
    if isinstance(a, (int, float)):
        n.inputs[0].default_value = float(a)
    else:
        ng.links.new(a, n.inputs[0])
    if b is not None:
        if isinstance(b, (int, float)):
            n.inputs[1].default_value = float(b)
        else:
            ng.links.new(b, n.inputs[1])
    return n.outputs[0]


def mix_rgba(blend, fac, col_a, col_b, clamp_fac=True, clamp_res=False):
    n = ng.nodes.new("ShaderNodeMix")
    n.data_type = 'RGBA'
    n.blend_type = blend
    n.clamp_factor = clamp_fac
    n.clamp_result = clamp_res
    if isinstance(fac, (int, float)):
        n.inputs[0].default_value = float(fac)
    else:
        ng.links.new(fac, n.inputs[0])
    if isinstance(col_a, (tuple, list)):
        n.inputs[6].default_value = tuple(col_a)
    else:
        ng.links.new(col_a, n.inputs[6])
    if isinstance(col_b, (tuple, list)):
        n.inputs[7].default_value = tuple(col_b)
    else:
        ng.links.new(col_b, n.inputs[7])
    return n.outputs[2]


def color_ramp(fac_sock, stops, interp='LINEAR'):
    n = ng.nodes.new("ShaderNodeValToRGB")
    n.color_ramp.interpolation = interp
    cr = n.color_ramp
    cr.elements[0].position = stops[0][0]
    cr.elements[0].color = stops[0][1]
    cr.elements[1].position = stops[-1][0]
    cr.elements[1].color = stops[-1][1]
    for pos, col in stops[1:-1]:
        el = cr.elements.new(pos)
        el.color = col
    ng.links.new(fac_sock, n.inputs['Factor'])
    return n.outputs['Color']


n_focus_dist = val_node("V6_FocusDist", 10.0)
n_dof_span = val_node("V6_DofSpan", 16.0)
n_kuw_size = val_node("V6_KuwaharaSize", 4.6)
n_kuw_mix = val_node("V6_KuwaharaMix", 0.68)
n_miles_wash = val_node("V6_Miles1610Wash", 0.50)
n_gwen_wash = val_node("V6_GwenWash", 0.0)
n_cyber_wash = val_node("V6_Cyber2099Wash", 0.0)
n_split_x = val_node("V6_SplitPxX", 6.2)
n_split_y = val_node("V6_SplitPxY", 1.8)
n_glitch_mask = val_node("V6_GlitchMask", 0.0)
n_portal_slash = val_node("V6_PortalSlashFac", 0.0)
n_car_ink_scale = val_node("V6_CarInkScale", 0.90)
n_halftone_fac = val_node("V6_HalftoneFac", 0.58)
n_speed_fac = val_node("V6_SpeedLineFac", 0.0)
n_sl_flip_x = val_node("V6_SLFlipX", 1.0)
n_sl_flip_y = val_node("V6_SLFlipY", 1.0)
n_tunnel_flash = val_node("V6_TunnelExitFlash", 0.0)
n_impact_a = val_node("V6_ImpactFrameA", 0.0)
n_impact_b = val_node("V6_ImpactFrameB", 0.0)

rl = ng.nodes.new("CompositorNodeRLayers")
img_raw = rl.outputs['Image']
depth_s = rl.outputs['Depth']
mist_s = rl.outputs['Mist']
norm_s = rl.outputs['Normal']

cry = ng.nodes.new("CompositorNodeCryptomatteV2")
cry.source = 'RENDER'
cry.scene = scene
cry.layer_name = f"{vl.name}.CryptoObject"
cry.matte_id = ",".join(sorted(car_and_fx_names))
car_matte = cry.outputs['Matte']
bg_matte = math_op('SUBTRACT', 1.0, car_matte, clamp=True)

# Stage 1: 受控霓虹辉光泛光 (Glare Threshold=1.15, Strength=0.16 防止火花/光肋高光大面积过曝裁剪)
glare = ng.nodes.new("CompositorNodeGlare")
glare.inputs['Type'].default_value = 'Bloom'
glare.inputs['Threshold'].default_value = 1.15
glare.inputs['Strength'].default_value = 0.16
glare.inputs['Size'].default_value = 7
ng.links.new(img_raw, glare.inputs['Image'])
img_bloom = glare.outputs['Image']

# Stage 2: Anisotropic Kuwahara 背景水彩笔触滤镜 + 三大蜘蛛侠平行宇宙鲜明色标染洗（主角赛车 100% 锐利跃出！）
kuw = ng.nodes.new("CompositorNodeKuwahara")
kuw.inputs['Type'].default_value = 'Anisotropic'
kuw.inputs['Sharpness'].default_value = 1.05
kuw.inputs['Eccentricity'].default_value = 1.45
ng.links.new(img_bloom, kuw.inputs['Image'])
ng.links.new(n_kuw_size.outputs[0], kuw.inputs['Size'])

mist_bg_c = color_ramp(mist_s, [(0.00, (0.68, 0.68, 0.68, 1.0)), (0.14, (1.0, 1.0, 1.0, 1.0))])
bw_mist_bg = ng.nodes.new("CompositorNodeRGBToBW")
ng.links.new(mist_bg_c, bw_mist_bg.inputs['Image'])
dz_kuw = math_op('ABSOLUTE', math_op('SUBTRACT', depth_s, n_focus_dist.outputs[0]))
defoc_kuw = math_op('DIVIDE', math_op('MAXIMUM', math_op('SUBTRACT', dz_kuw, 1.6), 0.0), n_dof_span.outputs[0], clamp=True)
kuw_bg_drive = math_op('MAXIMUM', bw_mist_bg.outputs[0], defoc_kuw, clamp=True)
kuw_fac = math_op('MULTIPLY', math_op('MULTIPLY', bg_matte, kuw_bg_drive, clamp=True),
                  n_kuw_mix.outputs[0], clamp=True)
img_kuw = mix_rgba('MIX', kuw_fac, img_bloom, kuw.outputs['Image'])

# Act I (1610 Miles): 暖调布鲁克林绯红/琥珀钠灯街景辉光 vs 普鲁士深靛暗部
miles_grad = color_ramp(mist_s, [
    (0.0, (0.98, 0.36, 0.10, 1.0)),
    (0.45, (1.00, 0.22, 0.26, 1.0)),
    (1.0, (0.92, 0.42, 0.16, 1.0)),
])
img_act1 = mix_rgba('SOFT_LIGHT', math_op('MULTIPLY', bg_matte, n_miles_wash.outputs[0], clamp=True), img_kuw, miles_grad)

# Act II (65 Gwen): 空气感粉彩薄荷青绿 + 亮品红/蜜桃水彩天空染洗（显著拉升 G/Teal 通道与通透空气感）
gwen_grad = color_ramp(mist_s, [
    (0.0, (0.12, 0.98, 0.86, 1.0)),
    (0.42, (1.00, 0.38, 0.78, 1.0)),
    (1.0, (1.00, 0.78, 0.54, 1.0)),
])
gwen_bg_fac = math_op('MULTIPLY', bg_matte, n_gwen_wash.outputs[0], clamp=True)
img_act2_soft = mix_rgba('SOFT_LIGHT', gwen_bg_fac, img_act1, gwen_grad)
img_act2 = mix_rgba('SCREEN', math_op('MULTIPLY', gwen_bg_fac, math_op('MULTIPLY', mist_s, 0.26, clamp=True), clamp=True),
                    img_act2_soft, gwen_grad)

# Act III (928 2099): 黑曜石深紫外暗部 + 凌厉激光绯红/朱红霓虹尖峰 (R >> G)
cyber_grad = color_ramp(mist_s, [
    (0.0, (0.12, 0.01, 0.28, 1.0)),
    (0.48, (0.72, 0.01, 0.22, 1.0)),
    (1.0, (1.00, 0.02, 0.12, 1.0)),
])
img_styled = mix_rgba('SOFT_LIGHT', math_op('MULTIPLY', bg_matte, n_cyber_wash.outputs[0], clamp=True), img_act2, cyber_grad)

# Stage 3: 焦平面外红青印刷错位 (Focal-Plane CMYK Misregistration，赛车强制 0px)
dz = math_op('ABSOLUTE', math_op('SUBTRACT', depth_s, n_focus_dist.outputs[0]))
defocus_norm = math_op('DIVIDE', math_op('MAXIMUM', math_op('SUBTRACT', dz, 2.0), 0.0), n_dof_span.outputs[0], clamp=True)
off_focus_raw = math_op('MAXIMUM', defocus_norm, math_op('MULTIPLY', mist_s, 0.78, clamp=True), clamp=True)
cmyk_mask = math_op('MAXIMUM', math_op('MULTIPLY', off_focus_raw, bg_matte, clamp=True),
                    n_glitch_mask.outputs[0], clamp=True)

trn_r = ng.nodes.new("CompositorNodeTranslate")
trn_r.inputs['Extension X'].default_value = 'Extend'
trn_r.inputs['Extension Y'].default_value = 'Extend'
ng.links.new(img_styled, trn_r.inputs['Image'])
ng.links.new(n_split_x.outputs[0], trn_r.inputs['X'])
ng.links.new(n_split_y.outputs[0], trn_r.inputs['Y'])

trn_b = ng.nodes.new("CompositorNodeTranslate")
trn_b.inputs['Extension X'].default_value = 'Extend'
trn_b.inputs['Extension Y'].default_value = 'Extend'
ng.links.new(img_styled, trn_b.inputs['Image'])
ng.links.new(math_op('MULTIPLY', n_split_x.outputs[0], -1.0), trn_b.inputs['X'])
ng.links.new(math_op('MULTIPLY', n_split_y.outputs[0], -1.0), trn_b.inputs['Y'])

sep_r = ng.nodes.new("CompositorNodeSeparateColor")
sep_g = ng.nodes.new("CompositorNodeSeparateColor")
sep_b = ng.nodes.new("CompositorNodeSeparateColor")
ng.links.new(trn_r.outputs['Image'], sep_r.inputs['Image'])
ng.links.new(img_styled, sep_g.inputs['Image'])
ng.links.new(trn_b.outputs['Image'], sep_b.inputs['Image'])

cmb_cmyk = ng.nodes.new("CompositorNodeCombineColor")
ng.links.new(sep_r.outputs['Red'], cmb_cmyk.inputs['Red'])
ng.links.new(sep_g.outputs['Green'], cmb_cmyk.inputs['Green'])
ng.links.new(sep_b.outputs['Blue'], cmb_cmyk.inputs['Blue'])
ng.links.new(sep_g.outputs['Alpha'], cmb_cmyk.inputs['Alpha'])
img_cmyk = mix_rgba('MIX', cmyk_mask, img_styled, cmb_cmyk.outputs['Image'])

# Stage 4: 屏幕空间 8.0px 高对比 Ben-Day 半调圆网点（0.06..0.94 动态范围，1080p 清晰可见）+ 纸纹
bw_pre = ng.nodes.new("CompositorNodeRGBToBW")
ng.links.new(img_cmyk, bw_pre.inputs['Image'])
midtone_band = color_ramp(bw_pre.outputs[0], [
    (0.03, (0.0, 0.0, 0.0, 1.0)),
    (0.16, (1.0, 1.0, 1.0, 1.0)),
    (0.62, (0.90, 0.90, 0.90, 1.0)),
    (0.90, (0.0, 0.0, 0.0, 1.0)),
])
bw_mid_mask = ng.nodes.new("CompositorNodeRGBToBW")
ng.links.new(midtone_band, bw_mid_mask.inputs['Image'])

n_ht = ng.nodes.new("CompositorNodeImage")
n_ht.image = ht_img
ht_car_bg = math_op('ADD', car_matte, math_op('MULTIPLY', bg_matte, 0.24), clamp=True)
ht_w = math_op('MULTIPLY', math_op('MULTIPLY', bw_mid_mask.outputs[0], ht_car_bg, clamp=True), n_halftone_fac.outputs[0], clamp=True)
img_halftoned = mix_rgba('SOFT_LIGHT', ht_w, img_cmyk, n_ht.outputs['Image'])

n_pap = ng.nodes.new("CompositorNodeImage")
n_pap.image = paper_img
n_pap_scl = ng.nodes.new("CompositorNodeScale")
n_pap_scl.inputs['Type'].default_value = 'Render Size'
n_pap_scl.inputs['Frame Type'].default_value = 'Stretch'
ng.links.new(n_pap.outputs['Image'], n_pap_scl.inputs['Image'])
img_paper = mix_rgba('SOFT_LIGHT', 0.06, img_halftoned, n_pap_scl.outputs['Image'])

# Stage 5: Normal (Kirsch) + Mist (Sobel) 远近自适应漫画墨线 + 背景后置水彩柔化（锁定 PopRatio >= 1.35！）
sep_nrm = ng.nodes.new("CompositorNodeSeparateColor")
ng.links.new(norm_s, sep_nrm.inputs['Image'])
cmb_nrm = ng.nodes.new("CompositorNodeCombineColor")
ng.links.new(sep_nrm.outputs['Red'], cmb_nrm.inputs['Red'])
ng.links.new(sep_nrm.outputs['Green'], cmb_nrm.inputs['Green'])
ng.links.new(sep_nrm.outputs['Blue'], cmb_nrm.inputs['Blue'])
cmb_nrm.inputs['Alpha'].default_value = 1.0

flt_nrm = ng.nodes.new("CompositorNodeFilter")
flt_nrm.inputs['Type'].default_value = 'Kirsch'
ng.links.new(cmb_nrm.outputs['Image'], flt_nrm.inputs['Image'])
bw_nrm = ng.nodes.new("CompositorNodeRGBToBW")
ng.links.new(flt_nrm.outputs['Image'], bw_nrm.inputs['Image'])
bw_nrm_edge = ng.nodes.new("CompositorNodeRGBToBW")
ng.links.new(color_ramp(bw_nrm.outputs[0], [(0.32, (0, 0, 0, 1)), (0.68, (1, 1, 1, 1))]), bw_nrm_edge.inputs['Image'])

cmb_mist = ng.nodes.new("CompositorNodeCombineColor")
ng.links.new(mist_s, cmb_mist.inputs['Red'])
ng.links.new(mist_s, cmb_mist.inputs['Green'])
ng.links.new(mist_s, cmb_mist.inputs['Blue'])
cmb_mist.inputs['Alpha'].default_value = 1.0

flt_mist = ng.nodes.new("CompositorNodeFilter")
flt_mist.inputs['Type'].default_value = 'Sobel'
ng.links.new(cmb_mist.outputs['Image'], flt_mist.inputs['Image'])
bw_mist_e = ng.nodes.new("CompositorNodeRGBToBW")
ng.links.new(flt_mist.outputs['Image'], bw_mist_e.inputs['Image'])
bw_mist_edge = ng.nodes.new("CompositorNodeRGBToBW")
ng.links.new(color_ramp(bw_mist_e.outputs[0], [(0.042, (0, 0, 0, 1)), (0.110, (1, 1, 1, 1))]), bw_mist_edge.inputs['Image'])

bg_ink_fade = math_op('SUBTRACT', 1.0, math_op('MULTIPLY', mist_s, 1.75, clamp=True), clamp=True)
bg_nrm_w = math_op('MULTIPLY', bg_matte, math_op('MULTIPLY', bg_ink_fade, 0.10))
car_or_bg = math_op('ADD', bg_nrm_w, math_op('MULTIPLY', car_matte, n_car_ink_scale.outputs[0]))
ink_mask = math_op('MULTIPLY', math_op('MAXIMUM',
                                       math_op('MULTIPLY', bw_nrm_edge.outputs[0], car_or_bg, clamp=True),
                                       math_op('MULTIPLY', bw_mist_edge.outputs[0], math_op('MULTIPLY', bg_ink_fade, 0.18), clamp=True),
                                       clamp=True), 0.85, clamp=True)
img_inked_raw = mix_rgba('MIX', ink_mask, img_paper, (0.008, 0.006, 0.022, 1.0))

# 背景后置画布柔化（仅作用于 bg_matte，100% 保护主角赛车锐利墨线、双边缘光、网点与排线！）
kuw_post = ng.nodes.new("CompositorNodeKuwahara")
kuw_post.inputs['Type'].default_value = 'Classic'
kuw_post.inputs['Size'].default_value = 8.5
ng.links.new(img_inked_raw, kuw_post.inputs['Image'])
img_inked = mix_rgba('MIX', math_op('MULTIPLY', bg_matte, 0.90, clamp=True), img_inked_raw, kuw_post.outputs['Image'])

# Stage 6: 12fps 沸腾边缘放射速度线 + 次元斜切裂缝 (Portal Tear, 严格按非黑像素抠像绝不黑屏!) + f=1041 隧道出口爆闪
n_sl = ng.nodes.new("CompositorNodeImage")
n_sl.image = sl_img
n_sl_scl = ng.nodes.new("CompositorNodeScale")
n_sl_scl.inputs['Type'].default_value = 'Relative'
ng.links.new(n_sl.outputs['Image'], n_sl_scl.inputs['Image'])
ng.links.new(n_sl_flip_x.outputs[0], n_sl_scl.inputs['X'])
ng.links.new(n_sl_flip_y.outputs[0], n_sl_scl.inputs['Y'])
bw_sl = ng.nodes.new("CompositorNodeRGBToBW")
ng.links.new(n_sl_scl.outputs['Image'], bw_sl.inputs['Image'])

img_speed = mix_rgba('MIX', math_op('MULTIPLY', bw_sl.outputs[0], n_speed_fac.outputs[0], clamp=True),
                     img_inked, (0.60, 0.72, 0.85, 1.0))

n_pt = ng.nodes.new("CompositorNodeImage")
n_pt.image = portal_img
sep_pt = ng.nodes.new("CompositorNodeSeparateColor")
ng.links.new(n_pt.outputs['Image'], sep_pt.inputs['Image'])
pt_max_rgb = math_op('MAXIMUM', sep_pt.outputs['Red'], math_op('MAXIMUM', sep_pt.outputs['Green'], sep_pt.outputs['Blue']))
pt_nonblack = math_op('GREATER_THAN', pt_max_rgb, 0.015)
pt_fac = math_op('MULTIPLY', pt_nonblack, n_portal_slash.outputs[0], clamp=True)
img_portal = mix_rgba('MIX', pt_fac, img_speed, n_pt.outputs['Image'])

img_exit_flash = mix_rgba('SCREEN', n_tunnel_flash.outputs[0], img_portal, (0.95, 0.92, 1.0, 1.0))

# Stage 7: 双帧高反差黑白赤红木刻冲击帧 (Impact #1 @ f=413..414, Impact #2 @ f=1067..1068)
# 注意：直接基于 bw_pre (纯场景亮度，不重复叠加 Emission pass!) + 速度线 + car_matte 驱动，保证白/绯红/墨黑三色均衡！
imp_drive = math_op(
    'ADD',
    math_op('MULTIPLY', bw_pre.outputs[0], 1.10),
    math_op('ADD', math_op('MULTIPLY', bw_sl.outputs[0], 0.34), math_op('MULTIPLY', car_matte, 0.14)),
    clamp=True,
)
imp_col_a = color_ramp(imp_drive, [
    (0.000, (1.15, 1.12, 1.05, 1.0)),
    (0.048, (1.25, 0.012, 0.045, 1.0)),
    (0.135, (0.002, 0.002, 0.006, 1.0)),
], interp='CONSTANT')
imp_col_b = color_ramp(imp_drive, [
    (0.000, (0.002, 0.002, 0.006, 1.0)),
    (0.046, (1.25, 0.012, 0.045, 1.0)),
    (0.132, (1.18, 1.15, 1.08, 1.0)),
], interp='CONSTANT')

img_imp1 = mix_rgba('MIX', n_impact_a.outputs[0], img_exit_flash, imp_col_a)
img_imp2 = mix_rgba('MIX', n_impact_b.outputs[0], img_imp1, imp_col_b)

# Stage 8: 2.39:1 宽银幕电影院遮幅黑边 (1920x804 有效画幅，上下各 138px 天鹅绒纯黑遮幅)
n_cs = ng.nodes.new("CompositorNodeImage")
n_cs.image = cs_img
bw_cs = ng.nodes.new("CompositorNodeRGBToBW")
ng.links.new(n_cs.outputs['Image'], bw_cs.inputs['Image'])
img_final = mix_rgba('MIX', bw_cs.outputs[0], img_imp2, (0.0, 0.0, 0.0, 1.0))

try:
    comp_out = ng.nodes.new("CompositorNodeComposite")
except Exception:
    comp_out = ng.nodes.new("NodeGroupOutput")
    if not any(s.name == "Image" for s in ng.interface.items_tree):
        ng.interface.new_socket(name="Image", in_out='OUTPUT', socket_type='NodeSocketColor')
ng.links.new(img_final, comp_out.inputs['Image'])

scene.compositing_node_group = ng
scene.use_nodes = True

# ---------------------------------------------------------------------------
# 10. 逐帧烘焙合成器动态参数 (1..1281)
# ---------------------------------------------------------------------------
PORTAL_GLITCH = {
    426: (16.0, -4.5, 0.85),
    427: (-20.0, 5.5, 1.00),
    428: (14.0, -3.5, 0.78),
    429: (-8.0, 2.0, 0.45),
    893: (17.0, 5.0, 0.85),
    894: (-21.0, -6.0, 1.00),
    895: (14.0, 3.5, 0.78),
    896: (-8.0, -2.0, 0.45),
}
IMPACT_A = {413, 1067}
IMPACT_B = {414, 1068}
TUNNEL_EXIT_FLASH = {1040: 0.30, 1041: 0.72, 1042: 0.48, 1043: 0.18}
FLIPS = ((1.0, 1.0), (-1.0, 1.0), (1.0, -1.0), (-1.0, -1.0))

PORTAL_SLASH = {426: 0.55, 427: 1.00, 428: 0.95, 429: 0.45, 893: 0.55, 894: 1.00, 895: 0.95, 896: 0.45}

for f in range(1, FRAME_END + 1):
    fd = frame_data[f]
    v_kmh = fd["v"] * 3.6
    d_foc = focus_dists[f]
    lens = cam_traj[f]["lens"]
    is_onb = (cam_traj[f]["type"] == "onboard")

    if f <= 427:
        kuw_sz, kuw_mx = 5.8, 0.80
        ml_w, gw_w, cy_w = 0.54, 0.0, 0.0
        bsx, bsy = 6.4, 1.6
        ht_f = 0.62
    elif f <= 894:
        kuw_sz, kuw_mx = 9.8, 0.97
        ml_w, gw_w, cy_w = 0.0, 0.68, 0.0
        bsx, bsy = 7.0, -2.0
        ht_f = 0.56
    else:
        kuw_sz, kuw_mx = 5.8, 0.78
        ml_w, gw_w, cy_w = 0.0, 0.0, 0.64
        bsx, bsy = 7.5, 2.2
        ht_f = 0.60

    if f in PORTAL_GLITCH:
        sx, sy, glm = PORTAL_GLITCH[f]
    elif f in IMPACT_A or f in IMPACT_B:
        sx, sy, glm = 14.0, -4.0, 0.55
    else:
        sx, sy, glm = bsx, bsy, 0.0

    d_eq = d_foc * (50.0 / max(15.0, lens))
    car_ink = 0.56 if is_onb else (max(0.24, min(0.90, 18.5 / d_eq)) if d_eq > 20.0 else 0.90)

    if f in IMPACT_A or f in IMPACT_B:
        sl_f = 0.95
    else:
        sl_f = max(0.0, min(0.65, (v_kmh - 282.0) / 52.0 * 0.65))

    flx, fly = FLIPS[((f - 1) // 2) % 4]

    n_focus_dist.outputs[0].default_value = d_foc
    n_dof_span.outputs[0].default_value = max(4.5, d_foc * 0.44)
    n_kuw_size.outputs[0].default_value = kuw_sz
    n_kuw_mix.outputs[0].default_value = kuw_mx
    n_miles_wash.outputs[0].default_value = ml_w
    n_gwen_wash.outputs[0].default_value = gw_w
    n_cyber_wash.outputs[0].default_value = cy_w
    n_split_x.outputs[0].default_value = sx
    n_split_y.outputs[0].default_value = sy
    n_glitch_mask.outputs[0].default_value = glm
    n_portal_slash.outputs[0].default_value = PORTAL_SLASH.get(f, 0.0)
    n_car_ink_scale.outputs[0].default_value = car_ink
    n_halftone_fac.outputs[0].default_value = ht_f
    n_speed_fac.outputs[0].default_value = sl_f
    n_sl_flip_x.outputs[0].default_value = flx
    n_sl_flip_y.outputs[0].default_value = fly
    n_tunnel_flash.outputs[0].default_value = TUNNEL_EXIT_FLASH.get(f, 0.0)
    n_impact_a.outputs[0].default_value = 1.0 if f in IMPACT_A else 0.0
    n_impact_b.outputs[0].default_value = 1.0 if f in IMPACT_B else 0.0

    for vn in (n_focus_dist, n_dof_span, n_kuw_size, n_kuw_mix, n_miles_wash, n_gwen_wash, n_cyber_wash,
               n_split_x, n_split_y, n_glitch_mask, n_portal_slash, n_car_ink_scale, n_halftone_fac,
               n_speed_fac, n_sl_flip_x, n_sl_flip_y, n_tunnel_flash, n_impact_a, n_impact_b):
        vn.outputs[0].keyframe_insert("default_value", frame=f)

if ng.animation_data and ng.animation_data.action:
    for fc in iter_fcurves(ng.animation_data.action):
        step_k = any(k in fc.data_path for k in ("V6_SLFlip", "V6_Impact", "V6_Glitch", "V6_PortalSlash"))
        for kp in fc.keyframe_points:
            kp.interpolation = 'CONSTANT' if step_k else 'LINEAR'
        fc.update()

# ---------------------------------------------------------------------------
# 11. 最终渲染设置（开启 EEVEE 屏幕空间光线追踪反射湿滑霓虹路面！）
# ---------------------------------------------------------------------------
scene.render.engine = 'BLENDER_EEVEE'
scene.eevee.use_raytracing = True
try:
    scene.eevee.ray_tracing_method = 'SCREEN'
    scene.eevee.ray_tracing_options.resolution_scale = '2'
    scene.eevee.ray_tracing_options.trace_max_roughness = 0.55
except Exception:
    pass
try:
    scene.eevee.shadow_pool_size = '1024'
except Exception:
    pass
if hasattr(scene.render, "compositor_device"):
    scene.render.compositor_device = 'CPU'
if hasattr(scene.render, "compositor_precision"):
    scene.render.compositor_precision = 'FULL'
if hasattr(scene.render, "use_compositor_frames_cache"):
    scene.render.use_compositor_frames_cache = False
scene.eevee.taa_render_samples = 20
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.render.fps = FPS
scene.frame_start = 1
scene.frame_end = FRAME_END
scene.render.use_motion_blur = True
scene.render.motion_blur_shutter = 0.07
scene.render.motion_blur_position = 'CENTER'
scene.render.image_settings.file_format = 'JPEG'
scene.render.image_settings.quality = 95
scene.render.filepath = os.path.join(PROJ, "renders_v6", "frames", "f_")

for _img in bpy.data.images:
    if _img.filepath and _img.filepath.startswith("//"):
        _img.filepath = bpy.path.abspath(_img.filepath)

# 清理根集合残留（确保 0 root objects）
for _rob in list(scene.collection.objects):
    if _rob.type == 'CAMERA':
        _cam_coll.objects.link(_rob)
        scene.collection.objects.unlink(_rob)
    elif _rob.type == 'LIGHT':
        _lgt_coll.objects.link(_rob)
        scene.collection.objects.unlink(_rob)

scene.frame_set(1)
scene.camera = cams_dict[windows[0][0]]
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND, relative_remap=False)
print("V6 SKY-HARBOR ANIM+COMP SAVED:", OUT_BLEND, "| root_objs=", len(scene.collection.objects), flush=True)

if TEST_FRAMES:
    t_dir = os.path.join(PROJ, "renders_v6", "test")
    os.makedirs(t_dir, exist_ok=True)
    orig_c = scene.camera
    for tf in [int(x) for x in str(TEST_FRAMES).split(",")]:
        cur_c = scene.camera
        for nm, f0 in markers_list:
            if f0 <= tf:
                cur_c = cams_dict[nm]
        scene.camera = cur_c
        scene.frame_set(tf)
        scene.render.filepath = os.path.join(t_dir, f"sv_skyharbor_{tf:04d}.jpg")
        bpy.ops.render.render(write_still=True)
        print("SV SKY-HARBOR TEST:", tf, cur_c.name, flush=True)
    scene.camera = orig_c
