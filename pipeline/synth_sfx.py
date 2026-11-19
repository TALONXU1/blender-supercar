# -*- coding: utf-8 -*-
"""
V5 SFX — Telemetry-Synced F1 1.6L V6 Turbo-Hybrid Audio Synthesizer
====================================================================
Reads:
  - track_data/silverstone_track.json  (t, v_mps, curv_1pm, s, racing_xy, heading_deg)
  - pipeline/v5_anim.py                (read-only AST parse of 26 SHOTS & camera trajectories)

Writes:
  - renders_v5/sfx_engine_90s.wav      (48 kHz, 16-bit stereo PCM, 2161/24 = 90.0417 s)

Usage:
  python pipeline/synth_sfx.py
"""
import ast
import json
import math
import os
import sys
import time
import wave
from math import cos, pi, radians, sin, sqrt

import numpy as np
from scipy import signal

PROJ = r"D:\项目session\blender-supercar"
TRACK_JSON = os.path.join(PROJ, "track_data", "silverstone_track.json")
ANIM_PY = os.path.join(PROJ, "pipeline", "v5_anim.py")
OUT_WAV = os.path.join(PROJ, "renders_v5", "sfx_engine_90s.wav")

SR = 48000
FPS = 24
SAMPLES_PER_FRAME = SR // FPS  # 2000 exact samples per frame
SPEED_OF_SOUND = 343.0         # m/s


# ---------------------------------------------------------------------------
# 1. Parse SHOTS & Timeline Constants from pipeline/v5_anim.py (Read-Only AST)
# ---------------------------------------------------------------------------
def load_shots_from_anim(anim_path):
    with open(anim_path, encoding="utf-8") as f:
        src = f.read()
    tree = ast.parse(src, filename=anim_path)
    shots = None
    total_beats = 162
    bpm = 108.0
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    if tgt.id == "TOTAL_BEATS" and isinstance(node.value, ast.Constant):
                        total_beats = int(node.value.value)
                    elif tgt.id == "SHOTS":
                        safe_ns = {"dict": dict, "True": True, "False": False, "None": None}
                        shots = eval(
                            compile(ast.Expression(node.value), "<SHOTS>", "eval"),
                            {"__builtins__": {}},
                            safe_ns,
                        )
    if not shots:
        raise RuntimeError(f"Could not parse SHOTS from {anim_path}")
    return shots, bpm, total_beats


# ---------------------------------------------------------------------------
# 2. Reconstruct Exact Car Telemetry & 26 Camera Trajectories (Matching v5_anim.py)
# ---------------------------------------------------------------------------
def build_timeline_and_cameras(track_path, anim_path):
    with open(track_path, encoding="utf-8") as f:
        data = json.load(f)

    meta = data["meta"]
    pts = data["points"]
    n_pts = len(pts)
    lap_s = float(meta["sim_lap_s"])  # 90.34 s

    shots, bpm, total_beats = load_shots_from_anim(anim_path)
    beat_s = 60.0 / bpm
    beat_f = beat_s * FPS
    frame_end = int(round(1 + total_beats * beat_f))  # 2161
    dt_frame = lap_s / (frame_end - 1)                # 90.34 / 2160

    t_arr = np.array([p["t"] for p in pts], dtype=np.float64)
    rx_arr = np.array([p["racing_xy"][0] for p in pts], dtype=np.float64)
    ry_arr = np.array([p["racing_xy"][1] for p in pts], dtype=np.float64)
    hd_deg = np.array([p["heading_deg"] for p in pts], dtype=np.float64)
    hd_rad_unwrapped = np.unwrap(np.radians(hd_deg))
    v_arr = np.array([p["v_mps"] for p in pts], dtype=np.float64)
    k_abs_arr = np.array([abs(p["curv_1pm"] or 0.0) for p in pts], dtype=np.float64)
    s_arr = np.array([p["s"] for p in pts], dtype=np.float64)

    span_idx = 4
    signs = np.array(
        [
            1.0 if (hd_rad_unwrapped[(i + span_idx) % n_pts] - hd_rad_unwrapped[(i - span_idx) % n_pts]) >= 0 else -1.0
            for i in range(n_pts)
        ],
        dtype=np.float64,
    )
    ks_arr = signs * k_abs_arr

    def sample_track(t_q):
        t_c = np.clip(t_q, 0.0, lap_s - 1e-6)
        px = np.interp(t_c, t_arr, rx_arr)
        py = np.interp(t_c, t_arr, ry_arr)
        hd = np.interp(t_c, t_arr, hd_rad_unwrapped)
        vv = np.interp(t_c, t_arr, v_arr)
        kk = np.interp(t_c, t_arr, ks_arr)
        ss = np.interp(t_c, t_arr, s_arr)
        return px, py, hd, vv, kk, ss

    # Frame-level data (1-indexed 1..frame_end to match v5_anim.py)
    f_indices = np.arange(frame_end, dtype=np.float64)
    t_frames = f_indices * dt_frame
    px_f, py_f, hd_f, v_f, k_f, s_f = sample_track(t_frames)

    frame_data = {}
    for idx in range(frame_end):
        f = idx + 1
        h = float(hd_f[idx])
        frame_data[f] = {
            "t": float(t_frames[idx]),
            "pos": np.array([px_f[idx], py_f[idx], 0.0], dtype=np.float64),
            "heading": h,
            "v": float(v_f[idx]),
            "k": float(k_f[idx]),
            "s": float(s_f[idx]),
            "fwd": np.array([cos(h), sin(h), 0.0], dtype=np.float64),
            "right": np.array([sin(h), -cos(h), 0.0], dtype=np.float64),
        }

    def tf_snap(t_sec):
        f = 1.0 + t_sec / dt_frame
        k_beat = round((f - 1.0) / beat_f)
        return max(1, min(frame_end, int(round(1.0 + k_beat * beat_f))))

    windows = []
    for name, t0, t1, typ, pr in shots:
        windows.append([name, tf_snap(t0), tf_snap(t1), typ, pr])

    for i in range(len(windows)):
        windows[i][1] = max(windows[i][1], 1)
        windows[i][2] = min(frame_end, max(windows[i][2], windows[i][1] + 2))
        if i and windows[i][1] <= windows[i - 1][2]:
            windows[i][1] = windows[i - 1][2] + 1
            windows[i][2] = max(windows[i][2], windows[i][1] + 2)
    windows[-1][2] = frame_end

    def smooth01(u):
        u = max(0.0, min(1.0, u))
        return u * u * (3.0 - 2.0 * u)

    def car_rel(fd, back=0.0, side=0.0, h=0.5):
        return fd["pos"] - fd["fwd"] * back + fd["right"] * side + np.array([0.0, 0.0, h])

    def car_aim(fd, ahead=0.0, side=0.0, h=0.45):
        return fd["pos"] + fd["fwd"] * ahead + fd["right"] * side + np.array([0.0, 0.0, h])

    # Precompute camera positions & aim targets for each shot (with 2-frame pad for crossfades)
    shot_specs = []
    for s_idx, (name, f0, f1, typ, pr) in enumerate(windows):
        span = max(1, f1 - f0)
        f_pad0 = max(1, f0 - 3)
        f_pad1 = min(frame_end, f1 + 3)
        frames_slice = np.arange(f_pad0, f_pad1 + 1, dtype=int)
        cam_locs = np.zeros((len(frames_slice), 3), dtype=np.float64)
        cam_aims = np.zeros((len(frames_slice), 3), dtype=np.float64)

        fixed_loc = None
        if typ == "fixed":
            fr = max(f0, min(f1, int(round(1.0 + pr["t_pass"] / dt_frame))))
            fixed_loc = car_rel(frame_data[fr], pr["lead"], pr["side"], pr["h"])

        aim_prev = None
        for j, f in enumerate(frames_slice):
            e = smooth01((f - f0) / span)
            fd = frame_data[int(f)]
            if typ == "chase":
                loc = car_rel(
                    fd,
                    pr["back0"] + (pr["back1"] - pr["back0"]) * e,
                    pr["side0"] + (pr["side1"] - pr["side0"]) * e,
                    pr["h0"] + (pr["h1"] - pr["h0"]) * e,
                )
                tgt = car_aim(fd, pr["aim0"] + (pr["aim1"] - pr["aim0"]) * e, 0.0, 0.52)
            elif typ == "fixed":
                loc = fixed_loc.copy()
                tgt_raw = fd["pos"] + np.array([0.0, 0.0, 0.34])
                aim_prev = tgt_raw if aim_prev is None else (
                    aim_prev + (tgt_raw - aim_prev) * pr.get("aim_lerp", 0.7)
                )
                tgt = aim_prev.copy()
            elif typ == "wheel":
                loc = car_rel(
                    fd,
                    pr["back0"] + (pr["back1"] - pr["back0"]) * e,
                    pr["side0"] + (pr["side1"] - pr["side0"]) * e,
                    pr["h0"] + (pr["h1"] - pr["h0"]) * e,
                )
                tgt = fd["pos"] + fd["right"] * 0.72 + fd["fwd"] * (1.35 - 0.5 * e) + np.array([0.0, 0.0, 0.34])
            elif typ == "onboard":
                loc = (
                    fd["pos"]
                    + fd["fwd"] * pr["fwd"]
                    + fd["right"] * pr.get("side", 0.0)
                    + np.array([0.0, 0.0, pr["h"]])
                )
                tgt = loc + fd["fwd"] * 22.0 + np.array([0.0, 0.0, -0.34])
            elif typ == "orbit":
                ang = radians(pr["a0"] + (pr["a1"] - pr["a0"]) * e)
                rad = pr["r0"] + (pr["r1"] - pr["r0"]) * e
                ox = fd["fwd"][0] * cos(ang) - fd["right"][0] * sin(ang)
                oy = fd["fwd"][1] * cos(ang) - fd["right"][1] * sin(ang)
                loc = fd["pos"] + np.array([ox, oy, 0.0]) * rad + np.array(
                    [0.0, 0.0, pr["h0"] + (pr["h1"] - pr["h0"]) * e]
                )
                tgt = fd["pos"] + np.array([0.0, 0.0, 0.42])
            elif typ == "heli":
                b0 = pr.get("back0", pr.get("back", 24.0))
                b1 = pr.get("back1", pr.get("back", 24.0))
                loc = car_rel(fd, b0 + (b1 - b0) * e, 0.0, pr["h0"] + (pr["h1"] - pr["h0"]) * e)
                tgt = fd["pos"] + fd["fwd"] * 2.0 + np.array([0.0, 0.0, 0.55])
            elif typ == "aerial":
                loc = car_rel(
                    fd,
                    pr["back0"] + (pr["back1"] - pr["back0"]) * e,
                    pr["side0"] + (pr["side1"] - pr["side0"]) * e,
                    pr["h0"] + (pr["h1"] - pr["h0"]) * e,
                )
                tgt = fd["pos"] + fd["fwd"] * 1.2 + np.array([0.0, 0.0, 0.55])
            else:
                loc = car_rel(fd, 8.0, 0.0, 1.0)
                tgt = fd["pos"] + np.array([0.0, 0.0, 0.45])

            cam_locs[j] = loc
            cam_aims[j] = tgt

        shot_specs.append(
            {
                "index": s_idx,
                "name": name,
                "f0": f0,
                "f1": f1,
                "type": typ,
                "params": pr,
                "frames": frames_slice,
                "cam_locs": cam_locs,
                "cam_aims": cam_aims,
            }
        )

    return {
        "lap_s": lap_s,
        "frame_end": frame_end,
        "dt_frame": dt_frame,
        "sample_track": sample_track,
        "shot_specs": shot_specs,
        "v_max": float(v_arr.max()),
    }


# ---------------------------------------------------------------------------
# 3. 8-Speed F1 Seamless Gearbox, RPM, Throttle, Turbo & Shift Transients
# ---------------------------------------------------------------------------
def simulate_powertrain(tl):
    """
    Simulate powertrain at 1000 Hz control rate across the exact 90.0417 s video timeline,
    then return control envelopes ready for fast interpolation to 48 kHz.
    """
    frame_end = tl["frame_end"]
    lap_s = tl["lap_s"]
    total_dur = frame_end / float(FPS)  # 2161 / 24 = 90.0416667 s

    ctrl_sr = 1000.0
    n_ctrl = int(math.ceil(total_dur * ctrl_sr)) + 2
    t_vid = np.arange(n_ctrl, dtype=np.float64) / ctrl_sr

    # Exact video-to-track simulation time mapping: f_idx = t_vid * 24, t_sim = f_idx * (LAP_S / 2160)
    f_cont = t_vid * FPS
    t_sim = np.clip(f_cont * (lap_s / float(frame_end - 1)), 0.0, lap_s - 1e-6)

    px, py, hd, v_mps, curv_s, s_m = tl["sample_track"](t_sim)
    v_kmh = v_mps * 3.6

    # Smooth longitudinal acceleration dv/dt (savitzky-golay / smoothed central diff)
    v_smooth = signal.savgol_filter(v_mps, 31, 2, mode="interp")
    accel = np.gradient(v_smooth, 1.0 / ctrl_sr)
    lat_g = (v_mps ** 2) * np.abs(curv_s) / 9.81

    # Tractive demand includes F1 aerodynamic drag (so 331 km/h straights stay 100% WOT!)
    a_aero_drag = 1.15 + 0.00178 * (v_mps ** 2)
    a_tractive = accel + a_aero_drag
    raw_throttle = np.clip((a_tractive - 1.0) / 11.5, 0.0, 1.0)
    # Under real braking (accel < -3.5 m/s^2), driver is firmly off-throttle on the brake pedal
    brake_mask = np.clip((-accel - 2.2) / 3.5, 0.0, 1.0)
    raw_throttle = raw_throttle * (1.0 - brake_mask)

    # Smooth pedal application (~28 ms pedal filter)
    b_ped, a_ped = signal.butter(2, 18.0 / (0.5 * ctrl_sr), btype="low")
    throttle = np.clip(signal.filtfilt(b_ped, a_ped, raw_throttle), 0.0, 1.0)

    # 8-speed F1 gearbox ratios (top speed per gear at 12,550 RPM)
    # Aligned with v5_anim.py shift points (204 / 298 km/h) while keeping v>=80 km/h in 9,800 - 12,550 RPM
    v_top_12550 = np.array([85.0, 107.5, 135.5, 169.0, 204.0, 246.0, 298.0, 338.0], dtype=np.float64)
    up_kmh = v_top_12550[:-1] * (12450.0 / 12550.0)
    dn_kmh = up_kmh - 2.3

    gear = np.zeros(n_ctrl, dtype=np.int32)
    # Initial gear at frame 1 (~297.5 km/h -> Gear 8, 0-indexed 7)
    g = int(np.searchsorted(up_kmh, v_kmh[0]))
    last_shift_t = -1.0

    upshift_times = []
    downshift_times = []

    for i in range(n_ctrl):
        tv = t_vid[i]
        vk = v_kmh[i]
        if tv - last_shift_t >= 0.135:
            if g < 7 and vk > up_kmh[g] and accel[i] > -2.5:
                g += 1
                last_shift_t = tv
                upshift_times.append(tv)
            elif g > 0 and vk < dn_kmh[g - 1]:
                g -= 1
                last_shift_t = tv
                downshift_times.append(tv)
        gear[i] = g + 1

    # Wheel-coupled target RPM + clutch/drivetrain seamless shift slew (~38 ms)
    rpm_target = np.clip(v_kmh / v_top_12550[gear - 1] * 12550.0, 7200.0, 12620.0)
    b_rpm, a_rpm = signal.butter(2, 16.0 / (0.5 * ctrl_sr), btype="low")
    rpm = signal.lfilter(b_rpm, a_rpm, rpm_target, zi=signal.lfilter_zi(b_rpm, a_rpm) * rpm_target[0])[0]

    # Build upshift cut/pop (~45 ms) and downshift rev-match throttle blip (~58 ms)
    upshift_cut = np.ones(n_ctrl, dtype=np.float64)
    upshift_pop = np.zeros(n_ctrl, dtype=np.float64)
    downshift_blip = np.zeros(n_ctrl, dtype=np.float64)

    for t_up in upshift_times:
        i0 = int(round(t_up * ctrl_sr))
        # 45 ms ignition-cut torque hole + hot collector pop
        dur_n = 48
        i1 = min(n_ctrl, i0 + dur_n)
        if i1 > i0:
            u = np.linspace(0.0, 1.0, i1 - i0, endpoint=False)
            # Torque dip during first 28 ms, slight bark rebound on re-ignition at 30-45 ms
            cut_env = np.where(
                u < 0.62,
                1.0 - 0.65 * np.sin(np.pi * (u / 0.62)),
                1.0 + 0.18 * np.sin(np.pi * ((u - 0.62) / 0.38)),
            )
            upshift_cut[i0:i1] *= cut_env
            # Sharp 45 ms ignition-cut exhaust pop envelope
            pop_env = np.sin(np.pi * np.minimum(1.0, u / 0.22)) ** 0.6 * np.exp(-3.4 * u)
            upshift_pop[i0:i1] += pop_env

        # Subtle post-shift drivetrain torsional ring (~75 ms)
        r1 = min(n_ctrl, i0 + 80)
        if r1 > i0:
            tr = np.arange(r1 - i0) / ctrl_sr
            rpm[i0:r1] += 55.0 * np.sin(2.0 * np.pi * 29.0 * tr) * np.exp(-38.0 * tr)

    for t_dn in downshift_times:
        i0 = max(0, int(round(t_dn * ctrl_sr)) - 6)
        dur_n = 62  # ~58-62 ms electronic rev-match blip
        i1 = min(n_ctrl, i0 + dur_n)
        if i1 > i0:
            u = np.linspace(0.0, 1.0, i1 - i0, endpoint=False)
            blip = (np.sin(np.pi * u) ** 0.75) * np.exp(-1.1 * u)
            downshift_blip[i0:i1] = np.maximum(downshift_blip[i0:i1], blip)
            rpm[i0:i1] += 410.0 * blip

    rpm = np.clip(rpm, 7200.0, 12750.0)
    eff_throttle = np.clip(throttle + 0.72 * downshift_blip, 0.0, 1.0)

    # MGU-H / Turbocharger spool state (asymmetric spool dynamics + lift-off flutter)
    turbo_target = 0.62 * eff_throttle + 0.38 * np.clip((rpm - 7400.0) / 5200.0, 0.0, 1.0)
    turbo_spool = np.zeros(n_ctrl, dtype=np.float64)
    sp = float(turbo_target[0])
    alpha_up = 1.0 - math.exp(-1.0 / (0.15 * ctrl_sr))
    alpha_dn = 1.0 - math.exp(-1.0 / (0.30 * ctrl_sr))
    for i in range(n_ctrl):
        tgt = turbo_target[i]
        sp += (alpha_up if tgt > sp else alpha_dn) * (tgt - sp)
        turbo_spool[i] = sp

    d_throt = np.gradient(throttle, 1.0 / ctrl_sr)
    wastegate_flutter = np.clip(-d_throt / 6.0, 0.0, 1.0) * turbo_spool

    return {
        "t_vid": t_vid,
        "t_sim": t_sim,
        "px": px,
        "py": py,
        "hd": hd,
        "v_mps": v_mps,
        "v_kmh": v_kmh,
        "accel": accel,
        "curv": curv_s,
        "lat_g": lat_g,
        "gear": gear,
        "rpm": rpm,
        "throttle": throttle,
        "eff_throttle": eff_throttle,
        "upshift_cut": upshift_cut,
        "upshift_pop": upshift_pop,
        "downshift_blip": downshift_blip,
        "turbo_spool": turbo_spool,
        "wastegate_flutter": wastegate_flutter,
        "upshift_times": upshift_times,
        "downshift_times": downshift_times,
    }


# ---------------------------------------------------------------------------
# 4. DSP Helpers: Resonators, Fractional Stereo Delay, Outdoor Slapback Reverb
# ---------------------------------------------------------------------------
def bandpass_sos(f_lo, f_hi, order=2):
    nyq = 0.5 * SR
    lo = max(15.0 / nyq, min(0.92, f_lo / nyq))
    hi = max(lo + 0.01, min(0.96, f_hi / nyq))
    return signal.butter(order, [lo, hi], btype="bandpass", output="sos")


def lowpass_sos(f_cut, order=2):
    nyq = 0.5 * SR
    fc = max(40.0 / nyq, min(0.95, f_cut / nyq))
    return signal.butter(order, fc, btype="lowpass", output="sos")


def highpass_sos(f_cut, order=2):
    nyq = 0.5 * SR
    fc = max(15.0 / nyq, min(0.90, f_cut / nyq))
    return signal.butter(order, fc, btype="highpass", output="sos")


def apply_formant_bank(x, profile="exhaust"):
    """
    Multi-formant acoustic resonator bank modeling exhaust collector/tailpipe
    or carbon cockpit airbox resonances (zero harsh pure-sine buzz!).
    """
    if profile == "onboard":
        # Cockpit tub + overhead carbon airbox trumpet resonances
        bands = [
            (130.0, 290.0, 0.42),
            (320.0, 740.0, 0.52),
            (780.0, 1650.0, 0.62),
            (1600.0, 3400.0, 0.72),
            (3100.0, 5800.0, 0.30),
        ]
    elif profile == "distant":
        # Open-air propagated F1 wail
        bands = [
            (170.0, 420.0, 0.34),
            (420.0, 960.0, 0.65),
            (950.0, 2200.0, 0.62),
            (2100.0, 4200.0, 0.34),
        ]
    else:
        # Rear central tailpipe + sidepod collector bark
        bands = [
            (135.0, 340.0, 0.56),
            (340.0, 780.0, 0.72),
            (780.0, 1750.0, 0.64),
            (1750.0, 3500.0, 0.42),
            (3300.0, 5600.0, 0.18),
        ]

    acc = np.zeros_like(x)
    for flo, fhi, gain in bands:
        sos = bandpass_sos(flo, fhi, order=2)
        acc += gain * signal.sosfilt(sos, x)
    return 0.22 * x + 0.78 * acc


def stereo_pan_and_itd(mono_sig, pan_curve, itd_scale=1.0):
    """
    Equal-power stereo pan + sub-millisecond Interaural Time Difference (Haas cue).
    pan_curve in [-1.0 (Left), +1.0 (Right)].
    """
    pan = np.clip(pan_curve, -0.95, 0.95)
    angle = (pan + 1.0) * (0.25 * np.pi)  # [0, pi/2]
    g_l = np.cos(angle)
    g_r = np.sin(angle)

    # Fractional sample ITD up to +-0.34 ms (~16 samples at 48 kHz)
    max_delay_samp = 16.0 * itd_scale
    if max_delay_samp > 0.5:
        idx = np.arange(len(mono_sig), dtype=np.float64)
        # Positive pan (source on Right): Right arrives early, Left delayed
        d_l = np.clip(pan, 0.0, 1.0) * max_delay_samp
        d_r = np.clip(-pan, 0.0, 1.0) * max_delay_samp
        sig_l = np.interp(np.clip(idx - d_l, 0.0, len(mono_sig) - 1.0), idx, mono_sig) * g_l
        sig_r = np.interp(np.clip(idx - d_r, 0.0, len(mono_sig) - 1.0), idx, mono_sig) * g_r
    else:
        sig_l = mono_sig * g_l
        sig_r = mono_sig * g_r

    return sig_l, sig_r


def add_outdoor_track_reverb(sig_l, sig_r, wet=0.18):
    """
    Multi-tap stereo outdoor Silverstone grandstand/field reflections with HF air damping.
    """
    if wet <= 1e-4:
        return sig_l, sig_r
    n = len(sig_l)
    mid = 0.5 * (sig_l + sig_r)
    damped = signal.sosfilt(lowpass_sos(2900.0, order=2), mid)
    damped = signal.sosfilt(highpass_sos(140.0, order=1), damped)

    taps_l = [(int(0.047 * SR), 0.42), (int(0.089 * SR), 0.31), (int(0.149 * SR), 0.21), (int(0.223 * SR), 0.12)]
    taps_r = [(int(0.059 * SR), 0.40), (int(0.103 * SR), 0.30), (int(0.167 * SR), 0.20), (int(0.241 * SR), 0.12)]

    rev_l = np.zeros(n, dtype=np.float64)
    rev_r = np.zeros(n, dtype=np.float64)
    for d, g in taps_l:
        if d < n:
            rev_l[d:] += g * damped[:-d]
    for d, g in taps_r:
        if d < n:
            rev_r[d:] += g * damped[:-d]

    return sig_l + wet * rev_l, sig_r + wet * rev_r


# ---------------------------------------------------------------------------
# 5. Per-Shot Acoustic Perspective & Synthesis Engine
# ---------------------------------------------------------------------------
def synthesize_full_lap(tl, pt):
    frame_end = tl["frame_end"]
    n_total = frame_end * SAMPLES_PER_FRAME  # 4,322,000 samples = 90.041667 s
    xfade_half = int(0.025 * SR)             # +-25 ms = 50 ms total equal-power crossfade (2400 samples)

    # Master car-frame crankshaft phase across full 90.0417 s so co-moving cuts stay phase-coherent
    t_all = np.arange(n_total, dtype=np.float64) / float(SR)
    rpm_all = np.interp(t_all, pt["t_vid"], pt["rpm"])
    theta_car_master = np.cumsum(2.0 * np.pi * (rpm_all / 60.0) / float(SR))

    # Deterministic seeded RNG for organic combustion turbulence, overrun crackle & stereo wind
    rng = np.random.default_rng(202605)

    out_l = np.zeros(n_total, dtype=np.float64)
    out_r = np.zeros(n_total, dtype=np.float64)

    shot_specs = tl["shot_specs"]
    n_shots = len(shot_specs)
    doppler_log = []

    for s_idx, spec in enumerate(shot_specs):
        f0, f1 = spec["f0"], spec["f1"]
        typ = spec["type"]
        name = spec["name"]

        # Exact core window in sample indices:
        # Shot 0 starts at 0; cut k (between shot k-1 ending at f1_prev and shot k starting at f0=f1_prev+1)
        # sits at cut_samp = (f0 - 1) * SAMPLES_PER_FRAME
        core_s0 = 0 if s_idx == 0 else (f0 - 1) * SAMPLES_PER_FRAME
        core_s1 = n_total if s_idx == n_shots - 1 else f1 * SAMPLES_PER_FRAME

        s0 = max(0, core_s0 - (xfade_half if s_idx > 0 else 0))
        s1 = min(n_total, core_s1 + (xfade_half if s_idx < n_shots - 1 else 0))
        n_seg = s1 - s0
        t_seg = np.arange(s0, s1, dtype=np.float64) / float(SR)

        # Interpolate powertrain states onto 48 kHz segment
        tv_ctrl = pt["t_vid"]
        rpm = np.interp(t_seg, tv_ctrl, pt["rpm"])
        v_mps = np.interp(t_seg, tv_ctrl, pt["v_mps"])
        curv = np.interp(t_seg, tv_ctrl, pt["curv"])
        lat_g = np.interp(t_seg, tv_ctrl, pt["lat_g"])
        throttle = np.interp(t_seg, tv_ctrl, pt["throttle"])
        eff_throt = np.interp(t_seg, tv_ctrl, pt["eff_throttle"])
        up_cut = np.interp(t_seg, tv_ctrl, pt["upshift_cut"])
        up_pop = np.interp(t_seg, tv_ctrl, pt["upshift_pop"])
        dn_blip = np.interp(t_seg, tv_ctrl, pt["downshift_blip"])
        turbo_sp = np.interp(t_seg, tv_ctrl, pt["turbo_spool"])
        wg_flut = np.interp(t_seg, tv_ctrl, pt["wastegate_flutter"])

        px_car = np.interp(t_seg, tv_ctrl, pt["px"])
        py_car = np.interp(t_seg, tv_ctrl, pt["py"])
        hd_car = np.interp(t_seg, tv_ctrl, pt["hd"])
        vx_car = np.cos(hd_car) * v_mps
        vy_car = np.sin(hd_car) * v_mps

        # Interpolate 3D camera world position on this segment
        f_float = 1.0 + t_seg * float(FPS)
        f_grid = spec["frames"].astype(np.float64)
        cam_x = np.interp(f_float, f_grid, spec["cam_locs"][:, 0])
        cam_y = np.interp(f_float, f_grid, spec["cam_locs"][:, 1])
        cam_z = np.interp(f_float, f_grid, spec["cam_locs"][:, 2])

        # Vector from camera to car acoustic source (exhaust/engine center z=0.38 m)
        rx = px_car - cam_x
        ry = py_car - cam_y
        rz = 0.38 - cam_z
        dist = np.sqrt(rx * rx + ry * ry + rz * rz)
        dist_safe = np.maximum(dist, 0.8)

        # Camera velocity & radial velocity dr/dt
        if typ == "fixed":
            vx_rel, vy_rel, vz_rel = vx_car, vy_car, np.zeros_like(vx_car)
        else:
            vcam_x = np.gradient(cam_x, 1.0 / SR)
            vcam_y = np.gradient(cam_y, 1.0 / SR)
            vcam_z = np.gradient(cam_z, 1.0 / SR)
            # Lightly smooth numerical camera velocity to avoid frame-rate derivative steps
            sos_v = lowpass_sos(12.0, order=2)
            vcam_x = signal.sosfiltfilt(sos_v, vcam_x)
            vcam_y = signal.sosfiltfilt(sos_v, vcam_y)
            vcam_z = signal.sosfiltfilt(sos_v, vcam_z)
            vx_rel = vx_car - vcam_x
            vy_rel = vy_car - vcam_y
            vz_rel = -vcam_z

        v_radial = (vx_rel * rx + vy_rel * ry + vz_rel * rz) / dist_safe
        if typ == "onboard":
            doppler = np.ones(n_seg, dtype=np.float64)
        elif typ == "fixed":
            doppler = SPEED_OF_SOUND / np.maximum(120.0, SPEED_OF_SOUND + v_radial)
            doppler_log.append((name, float(dist.min()), float(doppler.max()), float(doppler.min())))
        else:
            # Subtle natural micro-Doppler on chase/orbit/heli camera motion
            doppler = np.clip(SPEED_OF_SOUND / (SPEED_OF_SOUND + 0.55 * v_radial), 0.96, 1.04)

        # Crankshaft phase anchored to master car phase at segment start
        f_crank = (rpm / 60.0) * doppler
        # Subtle cycle-to-cycle combustion FM micro-jitter (~0.24%) for organic internal-combustion life
        jitter_raw = rng.standard_normal(n_seg)
        jitter = signal.sosfilt(bandpass_sos(28.0, 170.0, order=2), jitter_raw)
        f_crank_jit = f_crank * (1.0 + 0.0024 * jitter)
        theta_crank = theta_car_master[s0] + np.cumsum(2.0 * np.pi * f_crank_jit / float(SR))

        # --- Layer A: F1 1.6L 90-deg V6 Combustion & Exhaust Harmonics ---
        # Crank orders: 3.0 = primary V6 firing freq (RPM/60 * 3 ~ 500-620 Hz);
        # 1.0 & 1.5 = crankshaft & 3-cylinder single-bank orders for authentic V6 guttural growl!
        overrun = np.clip(1.0 - eff_throt * 3.5, 0.0, 1.0)
        load_bright = 0.35 + 0.65 * eff_throt

        # Perspective tilt between rear exhaust growl vs cockpit intake scream
        intake_bias = 1.35 if typ == "onboard" else (1.12 if typ == "orbit" else 1.0)
        sub_bias = 0.80 if typ in ("heli", "aerial") else (0.90 if typ == "onboard" else 1.15)

        harmonics_spec = [
            # (crank_order, base_amp, load_exp, phase_offset)
            (1.0, 0.16 * sub_bias, 0.3, 0.20),          # Crank 1x (~185 Hz rumble)
            (1.5, 0.30 * sub_bias, 0.2, 0.75),          # 3-cyl bank 0.5*f0 (~280 Hz V6 signature!)
            (2.0, 0.12 * sub_bias, 0.4, 1.40),          # 2/3*f0 asymmetry
            (3.0, 1.00, 0.35, 0.00),                    # 1.0*f0 Primary V6 firing note (~560 Hz)
            (4.5, 0.34, 0.45, 0.55),                    # 1.5*f0 Odd bank harmonic (~840 Hz)
            (6.0, 0.68 * intake_bias, 0.75, 0.31),      # 2.0*f0 Second firing harmonic (~1120 Hz)
            (7.5, 0.22, 0.85, 1.15),                    # 2.5*f0 Half-order grit
            (9.0, 0.46 * intake_bias, 1.05, 0.82),      # 3.0*f0 Third harmonic (~1680 Hz)
            (12.0, 0.31 * intake_bias, 1.25, 1.64),     # 4.0*f0 Fourth harmonic (~2240 Hz)
            (15.0, 0.21 * intake_bias, 1.45, 2.15),     # 5.0*f0 Fifth harmonic (~2800 Hz)
            (18.0, 0.14 * intake_bias, 1.65, 0.44),     # 6.0*f0 Sixth harmonic (~3360 Hz)
            (21.0, 0.09 * intake_bias, 1.80, 1.90),     # 7.0*f0 Seventh harmonic (~3920 Hz)
            (24.0, 0.06 * intake_bias, 1.95, 2.70),     # 8.0*f0 Eighth harmonic (~4480 Hz)
        ]

        eng_raw = np.zeros(n_seg, dtype=np.float64)
        for order_m, amp0, l_exp, ph0 in harmonics_spec:
            f_h = order_m * f_crank
            aa_mask = np.clip((18500.0 - f_h) / 3500.0, 0.0, 1.0)
            dyn_amp = amp0 * (load_bright ** l_exp) * aa_mask
            if order_m in (1.5, 4.5):
                # Bank half-orders burble harder on off-throttle braking overrun
                dyn_amp = dyn_amp * (1.0 + 0.55 * overrun)
            eng_raw += dyn_amp * np.sin(order_m * theta_crank + ph0)

        # Turbulent combustion gas pulse modulation (eliminates static oscillator buzz)
        turb_noise = signal.sosfilt(bandpass_sos(240.0, 3400.0, order=2), rng.standard_normal(n_seg))
        valve_pulse = (0.5 + 0.5 * np.sin(3.0 * theta_crank - 0.4)) ** 2
        eng_raw = eng_raw * (1.0 + 0.07 * turb_noise) + 0.24 * turb_noise * valve_pulse * (0.30 + 0.70 * eff_throt)

        # Asymmetric exhaust collector saturation driven by throttle load & upshift ignition cut
        drive = 1.05 + 0.85 * eff_throt + 0.35 * dn_blip
        shaped = np.tanh(drive * (0.48 * eng_raw + 0.08 * (eng_raw ** 2))) - np.tanh(0.08 * drive)

        # Apply acoustic formant resonator bank matching camera perspective
        formant_mode = "onboard" if typ == "onboard" else (
            "distant" if (typ in ("heli", "aerial") or (typ == "fixed" and dist.min() > 40.0)) else "exhaust"
        )
        eng_voiced = apply_formant_bank(shaped, profile=formant_mode)

        # Apply load amplitude curve & 45 ms upshift ignition cut
        eng_amp = (0.52 + 0.48 * eff_throt + 0.14 * overrun) * up_cut
        eng_core = eng_voiced * eng_amp

        # --- Layer B: MGU-H Turbo Whistle (~2.6 - 5.4 kHz subtle hybrid sheen) & ERS Gear Whine ---
        f_turbo = (2650.0 + 2750.0 * turbo_sp + 160.0 * wg_flut * np.sin(2.0 * np.pi * 34.0 * t_seg)) * doppler
        f_turbo = np.clip(f_turbo, 1500.0, 14000.0)
        ph_turbo = np.cumsum(2.0 * np.pi * f_turbo / float(SR))
        air_sheen = signal.sosfilt(bandpass_sos(2400.0, 5800.0, order=2), rng.standard_normal(n_seg))
        turbo_gain = 0.055 if typ == "onboard" else (0.042 if typ in ("chase", "orbit", "wheel") else 0.028)
        mguh_sig = turbo_gain * (0.25 + 0.75 * turbo_sp) * (
            0.72 * np.sin(ph_turbo) * (1.0 + 0.20 * air_sheen) + 0.28 * air_sheen
        )

        # Subtle straight-cut gearbox / MGU-K regeneration whine (strongest onboard & wheel macro)
        f_ers = np.clip((1450.0 + 21.0 * v_mps) * doppler, 900.0, 9000.0)
        ph_ers = np.cumsum(2.0 * np.pi * f_ers / float(SR))
        ers_harvest = np.clip(overrun * 0.8 + eff_throt * 0.4, 0.0, 1.0)
        ers_gain = 0.036 if typ == "onboard" else (0.026 if typ == "wheel" else 0.010)
        ers_sig = ers_gain * ers_harvest * np.sin(ph_ers)

        # --- Layer C: Crisp ~45 ms Upshift Ignition-Cut Pop & Braking Overrun Crackle ---
        pop_low = signal.sosfilt(bandpass_sos(140.0, 620.0, order=2), rng.standard_normal(n_seg))
        pop_mid = signal.sosfilt(bandpass_sos(750.0, 2900.0, order=2), rng.standard_normal(n_seg))
        upshift_bark = up_pop * (0.62 * np.tanh(2.4 * pop_low) + 0.38 * pop_mid)

        # Subtle stochastic exhaust overrun burble/crackle under heavy high-RPM braking
        crackle_gate = overrun * np.clip((rpm - 9000.0) / 3000.0, 0.0, 1.0)
        sparse = np.clip(rng.standard_normal(n_seg) - 2.35, 0.0, 4.0)
        sparse_env = signal.sosfilt(lowpass_sos(45.0, order=1), sparse)
        overrun_crackle = 0.16 * crackle_gate * sparse_env * pop_mid

        car_mono = eng_core + mguh_sig + ers_sig + 0.52 * upshift_bark + overrun_crackle

        # --- Layer D: Camera-Perspective Distance Attenuation, Air Absorption & Stereo Pan ---
        v_norm = np.clip(v_mps / max(tl["v_max"], 1.0), 0.0, 1.0)

        if typ == "fixed":
            d_min = float(dist.min())
            if d_min <= 28.0:
                # Close trackside pass-by (S04, S08, S11, S17, S24): dramatic swell + aero wake tear!
                dist_gain = ((d_min + 8.5) / (dist + 8.5)) ** 0.82
                dist_gain = np.clip(dist_gain * 1.18, 0.08, 1.22)
            else:
                # Long-lens broadcast telephoto (S13_WoodcoteTele, S20_StoweTele): parabolic mic pickup
                dist_gain = 0.56 * ((d_min + 35.0) / (dist + 35.0)) ** 0.58
                car_mono = signal.sosfilt(lowpass_sos(4300.0, order=2), car_mono)

            # High-frequency air absorption at longer distances (split blend dry vs air-damped)
            car_air_lp = signal.sosfilt(lowpass_sos(2400.0, order=2), car_mono)
            air_mix = np.clip((dist - 18.0) / 140.0, 0.0, 0.72)
            car_persp = ((1.0 - air_mix) * car_mono + air_mix * car_air_lp) * dist_gain

            # True 3D stereo panning mounted on tripod facing pass-by / mid-shot axis:
            # Approaching from one speaker, tearing dead-center at pass-by, exiting opposite!
            i_closest = int(np.argmin(dist))
            i_ref = int(round(0.65 * i_closest + 0.35 * (n_seg // 2)))
            apex_dx = px_car[i_ref] - cam_x[i_ref]
            apex_dy = py_car[i_ref] - cam_y[i_ref]
            apex_norm = max(math.hypot(apex_dx, apex_dy), 1e-6)
            f_tripod_x, f_tripod_y = apex_dx / apex_norm, apex_dy / apex_norm
            # Tripod right-ear vector = f_tripod x +Z = (f_tripod_y, -f_tripod_x)
            right_ear_x, right_ear_y = f_tripod_y, -f_tripod_x
            horiz_dist = np.maximum(np.hypot(rx, ry), 1.0)
            sin_az = (rx * right_ear_x + ry * right_ear_y) / horiz_dist
            pan_curve = np.clip(sin_az * 0.94, -0.86, 0.86)

            sig_l, sig_r = stereo_pan_and_itd(car_persp * 1.16, pan_curve, itd_scale=1.0)

            # Close pass-by aerodynamic wake tear ("WHOOSH!") right as car passes tripod
            if d_min <= 28.0:
                wake_env = np.exp(-(((dist - d_min) / 8.5) ** 2)) * (v_norm ** 1.4)
                wake_n_l = signal.sosfilt(bandpass_sos(110.0, 1900.0, order=2), rng.standard_normal(n_seg))
                wake_n_r = signal.sosfilt(bandpass_sos(110.0, 1900.0, order=2), rng.standard_normal(n_seg))
                w_l, w_r = stereo_pan_and_itd(0.38 * wake_env * (wake_n_l + wake_n_r) * 0.5, pan_curve, itd_scale=1.2)
                sig_l += w_l
                sig_r += w_r

            # Outdoor Silverstone trackside slapback reverb
            sig_l, sig_r = add_outdoor_track_reverb(sig_l, sig_r, wet=0.22 if d_min <= 28.0 else 0.30)

        elif typ == "onboard":
            # Raw cockpit presence: tight stereo chassis + overhead airbox + heavy helmet aero wind rush
            tub_low = signal.sosfilt(lowpass_sos(240.0, order=2), car_mono)
            car_persp = 0.92 * car_mono + 0.24 * tub_low
            # Slight stereo width from dual sidepod exhausts + cockpit reflections
            pan_curve = np.clip(-0.08 * curv / 0.03, -0.15, 0.15)
            sig_l, sig_r = stereo_pan_and_itd(car_persp, pan_curve, itd_scale=0.3)

        elif typ in ("heli", "aerial"):
            # Elevated helicopter / aerial perspective: air HF rolloff + altitude attenuation + wide reverb
            alt = np.maximum(cam_z, 2.0)
            alt_gain = np.clip((9.5 / (alt + 9.0)) ** 0.56, 0.28, 0.68)
            car_lp = signal.sosfilt(lowpass_sos(3200.0, order=2), car_mono)
            car_hp = signal.sosfilt(highpass_sos(115.0, order=1), car_lp)
            car_persp = car_hp * alt_gain
            pan_curve = 0.22 * np.sin(2.0 * np.pi * 0.18 * t_seg)
            sig_l, sig_r = stereo_pan_and_itd(car_persp, pan_curve, itd_scale=0.6)
            sig_l, sig_r = add_outdoor_track_reverb(sig_l, sig_r, wet=0.34)

        else:
            # Chase / Orbit / WheelMacro: punchy rear-exhaust & mechanical presence!
            low_punch = signal.sosfilt(lowpass_sos(320.0, order=2), car_mono)
            punch_amt = 0.30 if typ == "chase" else (0.24 if typ == "orbit" else 0.22)
            car_persp = (0.82 * car_mono + punch_amt * low_punch) * (
                np.clip((9.0 / (dist + 3.0)) ** 0.30, 0.72, 1.02)
            )
            # Subtle camera-relative stereo pan as car shifts in frame during chase/orbit/wheel
            cam_aim_x = np.interp(f_float, f_grid, spec["cam_aims"][:, 0]) - cam_x
            cam_aim_y = np.interp(f_float, f_grid, spec["cam_aims"][:, 1]) - cam_y
            aim_len = np.maximum(np.hypot(cam_aim_x, cam_aim_y), 1e-6)
            cam_rx, cam_ry = cam_aim_y / aim_len, -cam_aim_x / aim_len
            sin_view = (rx * cam_rx + ry * cam_ry) / np.maximum(np.hypot(rx, ry), 1.0)
            if typ == "orbit":
                # Gentle orbit sweep across stereo field
                u_orb = np.linspace(-0.28, 0.28, n_seg)
                pan_curve = np.clip(sin_view * 0.6 + u_orb, -0.42, 0.42)
            elif typ == "wheel":
                pan_curve = np.clip(sin_view * 0.7 - 0.18, -0.45, 0.45)
            else:
                pan_curve = np.clip(sin_view * 0.75, -0.35, 0.35)
            sig_l, sig_r = stereo_pan_and_itd(car_persp, pan_curve, itd_scale=0.5)
            sig_l, sig_r = add_outdoor_track_reverb(sig_l, sig_r, wet=0.10)

        # --- Layer E: Aerodynamic Wind Rush (~ v^2) & Kerb / Tire Scrub Rumble (|curv| > 0.008) ---
        wind_scale = {
            "onboard": 0.28,
            "wheel": 0.22,
            "chase": 0.14,
            "orbit": 0.13,
            "heli": 0.11,
            "aerial": 0.11,
            "fixed": 0.05,
        }.get(typ, 0.12)

        w_raw_l = rng.standard_normal(n_seg)
        w_raw_r = rng.standard_normal(n_seg)
        wind_l = (
            0.55 * signal.sosfilt(bandpass_sos(75.0, 260.0, order=2), w_raw_l)
            + 0.35 * signal.sosfilt(bandpass_sos(260.0, 1450.0, order=2), w_raw_l)
            + 0.18 * signal.sosfilt(bandpass_sos(1450.0, 4600.0, order=2), w_raw_l)
        )
        wind_r = (
            0.55 * signal.sosfilt(bandpass_sos(75.0, 260.0, order=2), w_raw_r)
            + 0.35 * signal.sosfilt(bandpass_sos(260.0, 1450.0, order=2), w_raw_r)
            + 0.18 * signal.sosfilt(bandpass_sos(1450.0, 4600.0, order=2), w_raw_r)
        )
        wind_env = wind_scale * (v_norm ** 2)
        sig_l += wind_env * wind_l
        sig_r += wind_env * wind_r

        # Serrated kerb rumble when cornering hard (|curv| > 0.008) + WheelMacro tire/kerb detail
        kerb_gate_raw = np.clip((np.abs(curv) - 0.008) / 0.007, 0.0, 1.0)
        kerb_gate = signal.sosfilt(lowpass_sos(8.0, order=2), kerb_gate_raw)
        kerb_scale = {
            "wheel": 0.30,
            "onboard": 0.22,
            "chase": 0.16,
            "orbit": 0.15,
            "fixed": 0.09,
            "heli": 0.04,
            "aerial": 0.04,
        }.get(typ, 0.12)

        if np.any(kerb_gate > 1e-3) or typ == "wheel":
            # Concrete serrated kerb rib spacing ~0.28 m -> f_kerb = v_mps / 0.28 Hz
            f_kerb = np.clip(v_mps / 0.28, 35.0, 340.0)
            ph_kerb = np.cumsum(2.0 * np.pi * f_kerb / float(SR))
            kerb_vib = (
                0.58 * np.sin(ph_kerb)
                + 0.28 * np.sin(0.5 * ph_kerb + 0.6)
                + 0.22 * np.sin(2.0 * ph_kerb + 1.1)
            )
            kerb_thud = signal.sosfilt(bandpass_sos(55.0, 280.0, order=2), rng.standard_normal(n_seg))
            kerb_sig = kerb_scale * kerb_gate * (0.65 * kerb_vib + 0.45 * kerb_thud)

            # High-G tire scrub / asphalt contact roar (especially vivid on WheelMacro!)
            tire_env = (0.14 if typ == "wheel" else 0.05) * np.clip((lat_g - 1.4) / 3.8, 0.0, 1.0) + (
                0.08 * v_norm if typ == "wheel" else 0.0
            )
            tire_l = signal.sosfilt(bandpass_sos(550.0, 2600.0, order=2), w_raw_l) * tire_env
            tire_r = signal.sosfilt(bandpass_sos(550.0, 2600.0, order=2), w_raw_r) * tire_env

            # Kerb hits inner wheel corresponding to turn sign
            turn_sign = np.sign(curv)
            sig_l += kerb_sig * (0.55 - 0.20 * turn_sign) + tire_l
            sig_r += kerb_sig * (0.55 + 0.20 * turn_sign) + tire_r

        # --- Equal-Power 50 ms Crossfade Window Across Shot Cuts (Zero Clicks/Pops!) ---
        win = np.ones(n_seg, dtype=np.float64)
        if s_idx > 0:
            n_in = min(2 * xfade_half, n_seg)
            u_in = np.linspace(0.0, 1.0, n_in, endpoint=True)
            win[:n_in] *= np.sin(0.5 * np.pi * u_in)
        if s_idx < n_shots - 1:
            n_out = min(2 * xfade_half, n_seg)
            u_out = np.linspace(0.0, 1.0, n_out, endpoint=True)
            win[-n_out:] *= np.cos(0.5 * np.pi * u_out)

        out_l[s0:s1] += sig_l * win
        out_r[s0:s1] += sig_r * win

    # Master bus polish: remove sub-28 Hz DC/rumble, gentle glue saturation, 0.12 s fade-in + 1.5 s fade-out
    sos_hp = highpass_sos(28.0, order=2)
    out_l = signal.sosfilt(sos_hp, out_l)
    out_r = signal.sosfilt(sos_hp, out_r)

    # Smooth 0.12 s fade-in at frame 1 & smooth 1.50 s fade-out at end matching visual fade
    n_fi = int(0.12 * SR)
    out_l[:n_fi] *= np.sin(0.5 * np.pi * np.linspace(0.0, 1.0, n_fi))
    out_r[:n_fi] *= np.sin(0.5 * np.pi * np.linspace(0.0, 1.0, n_fi))

    n_fo = int(1.50 * SR)
    fade_out = np.cos(0.5 * np.pi * np.linspace(0.0, 1.0, n_fo)) ** 1.2
    out_l[-n_fo:] *= fade_out
    out_r[-n_fo:] *= fade_out

    # Gentle master bus peak control (preserving full pass-by & upshift transient punch!) + normalize to -1.5 dBFS
    peak_raw = max(float(np.max(np.abs(out_l))), float(np.max(np.abs(out_r))), 1e-9)
    gain_pre = 0.85 / peak_raw
    out_l = np.tanh(out_l * gain_pre) / math.tanh(0.85)
    out_r = np.tanh(out_r * gain_pre) / math.tanh(0.85)

    target_peak = 10.0 ** (-1.5 / 20.0)  # -1.50 dBFS
    cur_peak = max(float(np.max(np.abs(out_l))), float(np.max(np.abs(out_r))), 1e-9)
    out_l *= target_peak / cur_peak
    out_r *= target_peak / cur_peak

    return out_l, out_r, doppler_log


def write_stereo_wav_16bit(path, left, right):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    stereo = np.empty((len(left), 2), dtype=np.int16)
    stereo[:, 0] = np.clip(np.round(left * 32767.0), -32767, 32767).astype(np.int16)
    stereo[:, 1] = np.clip(np.round(right * 32767.0), -32767, 32767).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(stereo.tobytes())


def main():
    t0 = time.perf_counter()
    print("[synth_sfx] Loading Silverstone telemetry & 26-shot timeline...")
    tl = build_timeline_and_cameras(TRACK_JSON, ANIM_PY)
    pt = simulate_powertrain(tl)

    out_l, out_r, doppler_log = synthesize_full_lap(tl, pt)

    assert not np.isnan(out_l).any() and not np.isnan(out_r).any(), "NaN detected in audio!"
    assert not np.isinf(out_l).any() and not np.isinf(out_r).any(), "Inf detected in audio!"

    write_stereo_wav_16bit(OUT_WAV, out_l, out_r)
    dt_run = time.perf_counter() - t0

    peak_db = 20.0 * math.log10(max(float(np.max(np.abs(out_l))), float(np.max(np.abs(out_r))), 1e-12))
    rms = math.sqrt(0.5 * (float(np.mean(out_l ** 2)) + float(np.mean(out_r ** 2))))
    rms_db = 20.0 * math.log10(max(rms, 1e-12))
    fast_mask = pt["v_kmh"] >= 80.0

    print(f"[synth_sfx] Saved: {OUT_WAV} ({os.path.getsize(OUT_WAV):,} bytes) in {dt_run:.2f} s")
    print(
        f"[synth_sfx] Duration: {len(out_l)/SR:.4f} s ({len(out_l):,} samples @ {SR} Hz stereo, {tl['frame_end']} frames)"
    )
    print(
        f"[synth_sfx] Gearbox: 8-speed, {len(pt['upshift_times'])} upshifts, {len(pt['downshift_times'])} downshifts | "
        f"RPM (v>=80 km/h): {pt['rpm'][fast_mask].min():.0f}..{pt['rpm'][fast_mask].max():.0f} RPM"
    )
    print(f"[synth_sfx] Levels: Peak = {peak_db:.2f} dBFS, RMS = {rms_db:.2f} dBFS")
    for sname, dmin, dmax, dmin_dop in doppler_log:
        print(f"  [Doppler] {sname:22s} closest={dmin:5.1f} m  pitch={dmax:.3f}x -> {dmin_dop:.3f}x")


if __name__ == "__main__":
    main()
