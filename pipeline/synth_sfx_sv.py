# -*- coding: utf-8 -*-
"""
V6 SPIDER-VERSE EDITION — 3D Sky-Harbor Mega-Circuit Telemetry SFX & Master Mix
===============================================================================
100% V5 Isolation:
  - Reads track_data/spiderverse_circuit.json, audio/audio.wav, audio/cue.json,
    and (when present) pipeline/v6_sv_comp.py strictly READ-ONLY.
  - Writes ONLY to renders_v6/:
      * renders_v6/sfx_spiderverse_53s.wav   (& synced sfx_spiderverse_90s.wav alias)
      * renders_v6/audio_v6_sv_mix_53s.m4a   (& synced audio_v6_sv_mix_90s.m4a alias)

3D Sky-Harbor Set-Piece Acoustics (53.375 s / 1,281 frames @ 24 fps / 96 beats @ 108 BPM):
  1) canyon_grid (f=1..224, Act I Earth-1610): Tight +/-8.2m skyscraper canyon slapback,
     12Hz On-Twos comic mid-punch, DJ vinyl-scratch & whip-crack upshift transients.
  2) eau_rouge_climb (f=224..422, Z=+3->+42m, +13.5 deg pitch): Heavy uphill gravity engine
     load + Golden Titanium Skid-Block Spark Scrape Crackles on bottom G-compression (f~282)
     + Blind Crest Horizon-Moon Impact Hit & Portal 1->2 Glitch (f=414..416).
  3) sky_bridge & banked_bowl_plunge (f=422..898, Z=+42m -> +1.5m, +17.4 deg Carousel Bowl &
     -13.9 deg Corkscrew, Act II Earth-65 Gwen): Cable-stayed bridge stay-cable whooshes,
     wet-tire neon rooster-tail spray sizzle in high-G banking, lush dual-LFO stereo chorus +
     octave-up watercolor shimmer, & Portal 2->3 Glitch (f=897..900).
  4) strobe_tunnel_harbor (f=898..1281, Act III Earth-928 2099):
     - 520m Enclosed Vaulted Tunnel Roar (tunnel==True, f=908..1041, 341.2 km/h): claustrophobic
       concrete cylinder modal reverb + 12m hexagonal laser-arch supersonic rib pulses (s % 12m)
       + blinding f=1041 exit decompression!
     - Menacing Spider-2099 / Prowler 5-voice F-minor distorted cyber-brass synth growl!
     - Harbor Hairpin 340->81 km/h Heavy-Brake Slam (f=1067..1068): 2099 warning horn shriek +
       2-frame 4x stereo grain-stutter + seismic 118->43.65 Hz Sub-Bass Impact Drop!

Usage:
  python pipeline/synth_sfx_sv.py
  python pipeline/synth_sfx_sv.py --reel-wav <temp_reel_12s.wav>
"""
import argparse
import ast
import glob
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import time
import wave
from math import cos, pi, radians, sin

import numpy as np
from scipy import signal
from scipy.ndimage import maximum_filter1d

PROJ = r"D:\项目session\blender-supercar"
FFMPEG = r"C:\Users\86052\scoop\shims\ffmpeg.exe"

CIRCUIT_JSON = os.path.join(PROJ, "track_data", "spiderverse_circuit.json")
AUDIO_WAV = os.path.join(PROJ, "audio", "audio.wav")
CUE_JSON = os.path.join(PROJ, "audio", "cue.json")
V6_COMP_PY = os.path.join(PROJ, "pipeline", "v6_sv_comp.py")
V6_MANIFEST_JSON = os.path.join(PROJ, "v6_spiderverse", "v6_shots_manifest.json")

OUT_DIR = os.path.join(PROJ, "renders_v6")
OUT_WAV_53 = os.path.join(OUT_DIR, "sfx_spiderverse_53s.wav")
OUT_MIX_53 = os.path.join(OUT_DIR, "audio_v6_sv_mix_53s.m4a")
# Keep legacy V6 paths synced so any script referencing *_90s finds the fresh V6 circuit master
OUT_WAV_ALIAS = os.path.join(OUT_DIR, "sfx_spiderverse_90s.wav")
OUT_MIX_ALIAS = os.path.join(OUT_DIR, "audio_v6_sv_mix_90s.m4a")

SR = 48000
FPS = 24
SPF = SR // FPS
SPEED_OF_SOUND = 343.0


# ---------------------------------------------------------------------------
# Filter & Audio IO Helpers
# ---------------------------------------------------------------------------
def bp_sos(flo, fhi, order=2):
    nyq = 0.5 * SR
    lo = max(16.0 / nyq, min(0.92, flo / nyq))
    hi = max(lo + 0.01, min(0.96, fhi / nyq))
    return signal.butter(order, [lo, hi], btype="bandpass", output="sos")


def lp_sos(fc, order=2):
    nyq = 0.5 * SR
    return signal.butter(order, max(25.0 / nyq, min(0.95, fc / nyq)), btype="lowpass", output="sos")


def hp_sos(fc, order=2):
    nyq = 0.5 * SR
    return signal.butter(order, max(15.0 / nyq, min(0.90, fc / nyq)), btype="highpass", output="sos")


def write_wav_16bit(path, left, right):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    out = np.empty((len(left), 2), dtype=np.int16)
    out[:, 0] = np.clip(np.round(left * 32767.0), -32767, 32767).astype(np.int16)
    out[:, 1] = np.clip(np.round(right * 32767.0), -32767, 32767).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(out.tobytes())


def decode_audio_slice_48k(path, ss_sec=0.0, dur_sec=None, n_samples=None):
    cmd = [FFMPEG, "-v", "error"]
    if ss_sec > 0.0:
        cmd += ["-ss", f"{ss_sec:.6f}"]
    cmd += ["-i", path]
    if dur_sec is not None:
        cmd += ["-t", f"{dur_sec:.6f}"]
    cmd += ["-ar", str(SR), "-ac", "2", "-f", "f32le", "-"]
    proc = subprocess.run(cmd, capture_output=True, check=True)
    raw = np.frombuffer(proc.stdout, dtype=np.float32).reshape(-1, 2).astype(np.float64)
    if n_samples is not None:
        if len(raw) < n_samples:
            raw = np.pad(raw, ((0, n_samples - len(raw)), (0, 0)))
        raw = raw[:n_samples]
    return raw[:, 0].copy(), raw[:, 1].copy()


def brickwall_true_peak_limit(left, right, ceiling_db=-1.65):
    ceil_lin = 10.0 ** (ceiling_db / 20.0)
    peak_inst = np.maximum(np.abs(left), np.abs(right))
    win_la = int(0.0035 * SR)
    req_att = np.maximum(1.0, maximum_filter1d(peak_inst, size=win_la) / ceil_lin)
    smooth_att = signal.sosfiltfilt(lp_sos(32.0, order=1), req_att)
    att = np.maximum(req_att, smooth_att)
    y_l = left / att
    y_r = right / att
    os_l = signal.resample_poly(y_l, 4, 1)
    os_r = signal.resample_poly(y_r, 4, 1)
    tp = max(float(np.max(np.abs(os_l))), float(np.max(np.abs(os_r))), 1e-9)
    if tp > ceil_lin:
        scale = ceil_lin / tp
        y_l *= scale
        y_r *= scale
    return y_l, y_r


def stereo_pan_and_itd(mono_sig, pan_curve, itd_scale=1.0):
    pan = np.clip(pan_curve, -0.95, 0.95)
    ang = (pan + 1.0) * (0.25 * np.pi)
    g_l = np.cos(ang)
    g_r = np.sin(ang)
    max_d = 16.0 * itd_scale
    if max_d > 0.5:
        idx = np.arange(len(mono_sig), dtype=np.float64)
        d_l = np.clip(pan, 0.0, 1.0) * max_d
        d_r = np.clip(-pan, 0.0, 1.0) * max_d
        return (
            np.interp(np.clip(idx - d_l, 0.0, len(mono_sig) - 1.0), idx, mono_sig) * g_l,
            np.interp(np.clip(idx - d_r, 0.0, len(mono_sig) - 1.0), idx, mono_sig) * g_r,
        )
    return mono_sig * g_l, mono_sig * g_r


# ---------------------------------------------------------------------------
# 1. Load 3D Sky-Harbor Circuit & Optional Camera Shot Specs from v6_sv_comp.py
# ---------------------------------------------------------------------------
def try_parse_v6_comp_shots(frame_end, lap_s, bpm):
    """
    Loads exact 24-shot schedule & per-frame 3D camera world coordinates from
    v6_spiderverse/v6_shots_manifest.json (written by v6_sv_comp.py),
    falling back cleanly to v6_sv_comp.py SHOTS AST or the 24-shot 96-beat schedule.
    """
    beat_f = (60.0 / bpm) * FPS  # 13.3333 frames/beat
    dt_frame = lap_s / float(frame_end - 1)
    impact_frames = [413, 1067]
    manifest_cam = None
    windows = []

    if os.path.exists(V6_MANIFEST_JSON):
        try:
            with open(V6_MANIFEST_JSON, encoding="utf-8") as mf:
                mdata = json.load(mf)
            if isinstance(mdata, dict):
                if isinstance(mdata.get("impact_frames"), list):
                    ints = [int(x[0]) if isinstance(x, list) else int(x) for x in mdata["impact_frames"]]
                    if ints:
                        impact_frames = sorted(set(ints))
                pfc = mdata.get("per_frame_cam") or mdata.get("frames")
                if isinstance(pfc, list) and len(pfc) >= frame_end:
                    cam_xyz = np.zeros((frame_end, 3), dtype=np.float64)
                    f_types, f_names = [], []
                    for idx_f in range(frame_end):
                        entry = pfc[idx_f]
                        loc = entry.get("cam_xyz") or entry.get("cam_loc") or entry.get("loc") or [0, 0, 1]
                        cam_xyz[idx_f] = [float(loc[0]), float(loc[1]), float(loc[2])]
                        f_types.append(str(entry.get("type") or "chase").lower())
                        f_names.append(str(entry.get("shot") or entry.get("name") or f"Shot_{idx_f}"))
                    manifest_cam = {"cam_xyz": cam_xyz, "types": f_types, "names": f_names}

                if isinstance(mdata.get("shots"), list) and len(mdata["shots"]) >= 8:
                    for sh in mdata["shots"]:
                        nm = str(sh.get("name") or "Shot")
                        sf0 = int(sh.get("f0") or 1)
                        sf1 = int(sh.get("f1") or sf0 + 4)
                        stp = str(sh.get("type") or "chase").lower()
                        windows.append([nm, sf0, sf1, stp, sh])
        except Exception as exc:
            print("[synth_sfx_sv] Note: manifest parse skipped:", exc)

    if not windows and os.path.exists(V6_COMP_PY):
        try:
            with open(V6_COMP_PY, encoding="utf-8") as f:
                src = f.read()
            if "spiderverse_circuit" in src:
                tree = ast.parse(src, filename=V6_COMP_PY)
                safe_ns = {"dict": dict, "True": True, "False": False, "None": None}
                parsed_shots = None
                for node in tree.body:
                    if isinstance(node, ast.Assign):
                        for tgt in node.targets:
                            if isinstance(tgt, ast.Name) and tgt.id == "SHOTS":
                                parsed_shots = eval(
                                    compile(ast.Expression(node.value), "<SHOTS>", "eval"),
                                    {"__builtins__": {}},
                                    safe_ns,
                                )
                if parsed_shots and isinstance(parsed_shots, (list, tuple)) and len(parsed_shots) >= 12:
                    max_end = max(float(it[2]) for it in parsed_shots if len(it) >= 3)
                    for item in parsed_shots:
                        if len(item) >= 4:
                            nm = str(item[0])
                            a0, a1 = float(item[1]), float(item[2])
                            typ = str(item[3]).lower()
                            pr = item[4] if (len(item) >= 5 and isinstance(item[4], dict)) else {}
                            if max_end > 200.0:
                                f0, f1 = int(round(a0)), int(round(a1))
                            elif max_end > 65.0:  # 0..96 beats across the whole table!
                                f0 = int(round(1.0 + a0 * beat_f))
                                f1 = int(round(1.0 + a1 * beat_f))
                            else:                 # 0..53.33 seconds across the whole table!
                                f0 = int(round(1.0 + a0 / dt_frame))
                                f1 = int(round(1.0 + a1 / dt_frame))
                            windows.append([nm, f0, f1, typ, pr])
        except Exception:
            windows = []

    if not windows:
        default_24_shots = [
            ("SV01_CanyonScrape",    0,  4, "scraper", {"side": 2.4, "back": -0.8, "h": 0.22}),
            ("SV02_FPVDropExhaust",  4,  8, "chase",   {"back": 6.5, "side": 0.0,  "h": 1.8}),
            ("SV03_ChicaneWhip",     8, 12, "fixed",   {"f_pass": 125, "lead": -4.0, "side": 8.0, "h": 0.65}),
            ("SV04_CanyonCockpit",  12, 16, "onboard", {"fwd": -0.46, "side": 0.05, "h": 0.89}),
            ("SV05_EauRougeEntry",  16, 20, "chase",   {"back": 6.2, "side": -1.4, "h": 0.45}),
            ("SV06_SparkScrapeLow", 20, 24, "scraper", {"side": -2.3, "back": 1.2, "h": 0.20}),
            ("SV07_RaidillonClimb", 24, 28, "orbit",   {"r": 7.5, "h": 1.2}),
            ("SV08_CrestMoonTele",  28, 32, "fixed",   {"f_pass": 414, "lead": -9.0, "side": -8.2, "h": 1.1}),
            ("SV09_BridgeEntry",    32, 36, "chase",   {"back": 7.8, "side": 1.5,  "h": 0.9}),
            ("SV10_StayCablePan",   36, 40, "fixed",   {"f_pass": 508, "lead": 0.0, "side": 9.2, "h": 1.2}),
            ("SV11_SkyBridgeAero",  40, 45, "onboard", {"fwd": -0.46, "side": -0.05, "h": 0.90}),
            ("SV12_BowlBankRail",   45, 50, "rail",    {"side": -2.8, "back": 0.6, "h": 0.55}),
            ("SV13_CarouselOrbit",  50, 54, "orbit",   {"r": 8.2, "h": 1.5}),
            ("SV14_CorkscrewDive",  54, 59, "chase",   {"back": 6.8, "side": 1.2,  "h": 1.6}),
            ("SV15_PlungeWhip",     59, 63, "fixed",   {"f_pass": 830, "lead": -5.0, "side": -8.4, "h": 0.9}),
            ("SV16_HarborDrop",     63, 67, "chase",   {"back": 7.2, "side": -1.1, "h": 0.65}),
            ("SV17_TunnelPortal",   67, 71, "fixed",   {"f_pass": 912, "lead": -6.0, "side": 7.6, "h": 0.85}),
            ("SV18_TunnelCockpit",  71, 75, "onboard", {"fwd": -0.48, "side": 0.04, "h": 0.90}),
            ("SV19_TunnelWhipOrb",  75, 78, "orbit",   {"r": 6.4, "h": 0.85}),
            ("SV20_TunnelExitSmash",78, 81, "fixed",   {"f_pass": 1042, "lead": -6.0, "side": -8.2, "h": 0.80}),
            ("SV21_HairpinImpact",  81, 85, "fixed",   {"f_pass": 1082, "lead": -8.0, "side": 8.5, "h": 0.95}),
            ("SV22_HairpinApex",    85, 89, "orbit",   {"r": 7.2, "h": 0.95}),
            ("SV23_HarborLaunch",   89, 93, "chase",   {"back": 6.5, "side": 1.0,  "h": 0.50}),
            ("SV24_FinishHeliOut",  93, 96, "aerial",  {"back": 14.0, "side": 4.0, "h": 6.5}),
        ]
        for nm, b0, b1, typ, pr in default_24_shots:
            f0 = int(round(1.0 + b0 * beat_f))
            f1 = int(round(1.0 + b1 * beat_f))
            windows.append([nm, f0, min(frame_end, f1), typ, pr])

    clean_wins = []
    for nm, f0, f1, typ, pr in windows:
        if clean_wins and clean_wins[-1][2] >= frame_end - 2:
            break
        s_f0 = 1 if not clean_wins else max(f0, clean_wins[-1][2] + 1)
        s_f1 = min(frame_end, max(s_f0 + 2, f1))
        clean_wins.append([nm, s_f0, s_f1, typ, pr])
    clean_wins[-1][2] = frame_end

    return clean_wins, impact_frames, manifest_cam


def load_3d_circuit_and_powertrain():
    with open(CIRCUIT_JSON, encoding="utf-8") as f:
        cdata = json.load(f)

    meta = cdata["meta"]
    pts = cdata["points"]
    n_pts = len(pts)
    lap_s = float(meta["sim_lap_s"])        # 53.3333 s
    frame_end = int(meta["frame_end"])      # 1281
    bpm = float(meta.get("bpm", 108.0))

    # Build cyclic arrays (appending wrap point at t = lap_s for seamless 1859 -> 0 interpolation!)
    t_arr = np.array([p["t"] for p in pts] + [lap_s], dtype=np.float64)
    rx_arr = np.array([p["racing_xy"][0] for p in pts] + [pts[0]["racing_xy"][0]], dtype=np.float64)
    ry_arr = np.array([p["racing_xy"][1] for p in pts] + [pts[0]["racing_xy"][1]], dtype=np.float64)
    rz_arr = np.array([p["racing_z"] for p in pts] + [pts[0]["racing_z"]], dtype=np.float64)
    hd_unw = np.unwrap(np.radians([p["heading_deg"] for p in pts] + [pts[0]["heading_deg"]]))
    pt_rad = np.radians([p["pitch_deg"] for p in pts] + [pts[0]["pitch_deg"]])
    bk_rad = np.radians([p["bank_deg"] for p in pts] + [pts[0]["bank_deg"]])
    curv_arr = np.array([p["curv_1pm"] for p in pts] + [pts[0]["curv_1pm"]], dtype=np.float64)
    v_arr = np.array([p["v_mps"] for p in pts] + [pts[0]["v_mps"]], dtype=np.float64)
    s_arr = np.array([p["s"] for p in pts] + [float(meta["measured_length_km"]) * 1000.0], dtype=np.float64)
    tun_arr = np.array([1.0 if p.get("tunnel") else 0.0 for p in pts] + [1.0 if pts[0].get("tunnel") else 0.0])
    brg_arr = np.array([1.0 if p.get("bridge") else 0.0 for p in pts] + [1.0 if pts[0].get("bridge") else 0.0])

    # Simulate powertrain at 1000 Hz control rate across exact 1,281 frames (53.3750 s)
    total_dur = frame_end / float(FPS)
    ctrl_sr = 1000.0
    n_ctrl = int(math.ceil(total_dur * ctrl_sr)) + 2
    t_vid = np.arange(n_ctrl, dtype=np.float64) / ctrl_sr

    # Map video time -> cyclic simulation time [0, lap_s)
    t_sim = np.mod((t_vid * FPS) * (lap_s / float(frame_end - 1)), lap_s)

    px = np.interp(t_sim, t_arr, rx_arr)
    py = np.interp(t_sim, t_arr, ry_arr)
    pz = np.interp(t_sim, t_arr, rz_arr)
    hd = np.interp(t_sim, t_arr, hd_unw)
    pitch = np.interp(t_sim, t_arr, pt_rad)
    bank = np.interp(t_sim, t_arr, bk_rad)
    curv = np.interp(t_sim, t_arr, curv_arr)
    v_mps = np.interp(t_sim, t_arr, v_arr)
    s_m = np.interp(t_sim, t_arr, s_arr)
    tunnel = np.interp(t_sim, t_arr, tun_arr)
    bridge = np.interp(t_sim, t_arr, brg_arr)

    v_kmh = v_mps * 3.6
    v_smooth = signal.savgol_filter(v_mps, 31, 2, mode="interp")
    accel = np.gradient(v_smooth, 1.0 / ctrl_sr)

    # True 3D vertical compression G (spikes hard at bottom of Eau-Rouge f=282!)
    dpitch_dt = np.gradient(signal.savgol_filter(pitch, 31, 2, mode="interp"), 1.0 / ctrl_sr)
    vert_comp_g = np.maximum(0.0, (v_mps * dpitch_dt) / 9.81)
    lat_g = ((v_mps ** 2) * np.abs(curv) + 9.81 * np.sin(np.abs(bank))) / 9.81

    # 3D Tractive engine load = dv/dt + aero drag + uphill gravity 9.81*sin(pitch)!
    a_aero = 1.15 + 0.00175 * (v_mps ** 2)
    a_grav = 9.81 * np.sin(pitch)
    a_trac = accel + a_aero + a_grav
    raw_throt = np.clip((a_trac - 0.8) / 11.8, 0.0, 1.0)
    brake_mask = np.clip((-accel - 2.4) / 3.5, 0.0, 1.0)
    raw_throt *= 1.0 - brake_mask

    b_ped, a_ped = signal.butter(2, 18.0 / (0.5 * ctrl_sr), btype="low")
    throttle = np.clip(signal.filtfilt(b_ped, a_ped, raw_throt), 0.0, 1.0)

    # 8-speed F1 seamless gearbox calibrated across 81.1 .. 341.2 km/h (9,800 - 12,550 RPM)
    v_top_12600 = np.array([86.0, 108.5, 136.0, 168.5, 205.5, 247.5, 294.5, 345.5], dtype=np.float64)
    up_kmh = v_top_12600[:-1] * (12460.0 / 12600.0)
    dn_kmh = up_kmh - 2.8

    gear = np.zeros(n_ctrl, dtype=np.int32)
    g = int(np.searchsorted(up_kmh, v_kmh[0]))
    last_shift_t = -1.0
    upshift_times = []
    downshift_times = []

    for i in range(n_ctrl):
        tv = t_vid[i]
        vk = v_kmh[i]
        if tv - last_shift_t >= 0.13:
            if g < 7 and vk > up_kmh[g] and accel[i] > -2.5:
                g += 1
                last_shift_t = tv
                upshift_times.append(tv)
            elif g > 0 and vk < dn_kmh[g - 1]:
                g -= 1
                last_shift_t = tv
                downshift_times.append(tv)
        gear[i] = g + 1

    rpm_tgt = np.clip(v_kmh / v_top_12600[gear - 1] * 12600.0, 7600.0, 12680.0)
    b_r, a_r = signal.butter(2, 16.0 / (0.5 * ctrl_sr), btype="low")
    rpm = signal.lfilter(b_r, a_r, rpm_tgt, zi=signal.lfilter_zi(b_r, a_r) * rpm_tgt[0])[0]

    upshift_cut = np.ones(n_ctrl, dtype=np.float64)
    upshift_pop = np.zeros(n_ctrl, dtype=np.float64)
    downshift_blip = np.zeros(n_ctrl, dtype=np.float64)

    for t_up in upshift_times:
        i0 = int(round(t_up * ctrl_sr))
        i1 = min(n_ctrl, i0 + 46)
        if i1 > i0:
            u = np.linspace(0.0, 1.0, i1 - i0, endpoint=False)
            cut_env = np.where(
                u < 0.60,
                1.0 - 0.66 * np.sin(np.pi * (u / 0.60)),
                1.0 + 0.22 * np.sin(np.pi * ((u - 0.60) / 0.40)),
            )
            upshift_cut[i0:i1] *= cut_env
            upshift_pop[i0:i1] += (np.sin(np.pi * np.minimum(1.0, u / 0.20)) ** 0.6) * np.exp(-3.3 * u)

    for t_dn in downshift_times:
        i0 = max(0, int(round(t_dn * ctrl_sr)) - 5)
        i1 = min(n_ctrl, i0 + 60)
        if i1 > i0:
            u = np.linspace(0.0, 1.0, i1 - i0, endpoint=False)
            blip = (np.sin(np.pi * u) ** 0.75) * np.exp(-1.1 * u)
            downshift_blip[i0:i1] = np.maximum(downshift_blip[i0:i1], blip)
            rpm[i0:i1] += 420.0 * blip

    rpm = np.clip(rpm, 7600.0, 12780.0)
    eff_throttle = np.clip(throttle + 0.72 * downshift_blip, 0.0, 1.0)
    turbo_spool = signal.sosfilt(
        signal.butter(1, 3.5 / (0.5 * ctrl_sr), btype="low", output="sos"),
        0.62 * eff_throttle + 0.38 * np.clip((rpm - 7800.0) / 4800.0, 0.0, 1.0),
    )

    windows, impact_frames, manifest_cam = try_parse_v6_comp_shots(frame_end, lap_s, bpm)

    return {
        "meta": meta,
        "frame_end": frame_end,
        "lap_s": lap_s,
        "bpm": bpm,
        "t_vid": t_vid,
        "px": px,
        "py": py,
        "pz": pz,
        "hd": hd,
        "pitch": pitch,
        "bank": bank,
        "curv": curv,
        "v_mps": v_mps,
        "v_kmh": v_kmh,
        "accel": accel,
        "vert_comp_g": vert_comp_g,
        "lat_g": lat_g,
        "s_m": s_m,
        "tunnel": tunnel,
        "bridge": bridge,
        "gear": gear,
        "rpm": rpm,
        "throttle": throttle,
        "eff_throttle": eff_throttle,
        "upshift_cut": upshift_cut,
        "upshift_pop": upshift_pop,
        "downshift_blip": downshift_blip,
        "turbo_spool": turbo_spool,
        "upshift_times": upshift_times,
        "downshift_times": downshift_times,
        "windows": windows,
        "impact_frames": impact_frames,
        "manifest_cam": manifest_cam,
    }


# ---------------------------------------------------------------------------
# 2. Core F1 V6 Hybrid + 3D Doppler + Set-Piece Acoustic Synthesizer
# ---------------------------------------------------------------------------
def apply_formant_bank(x, mode="exhaust"):
    if mode == "onboard":
        bands = [(130, 290, 0.44), (320, 740, 0.54), (780, 1650, 0.64), (1600, 3450, 0.74), (3200, 5800, 0.30)]
    elif mode == "tunnel":
        bands = [(120, 320, 0.68), (320, 780, 0.82), (780, 1850, 0.76), (1850, 3800, 0.58), (3500, 6200, 0.28)]
    else:
        bands = [(135, 340, 0.58), (340, 780, 0.74), (780, 1750, 0.65), (1750, 3500, 0.44), (3300, 5600, 0.20)]
    acc = np.zeros_like(x)
    for flo, fhi, g in bands:
        acc += g * signal.sosfilt(bp_sos(flo, fhi, order=2), x)
    return 0.22 * x + 0.78 * acc


def synth_vinyl_whip_transient(rng, pan=0.0, intensity=1.0):
    n = int(0.082 * SR)
    t = np.arange(n, dtype=np.float64) / SR
    u = t / 0.082
    f_chirp = 600.0 + 2750.0 * np.sin(np.pi * np.minimum(1.0, u / 0.56)) ** 1.3
    ph = np.cumsum(2.0 * np.pi * f_chirp / SR)
    chirp = (0.72 * np.sin(ph) + 0.28 * np.sin(2.0 * ph + 0.4)) * np.exp(-33.0 * t)
    chirp *= np.sin(np.pi * np.minimum(1.0, t / 0.005))
    crack = signal.sosfilt(bp_sos(1700.0, 7800.0, order=2), rng.standard_normal(n)) * np.exp(-75.0 * t)
    punch = np.sin(2.0 * np.pi * (245.0 * np.exp(-18.0 * t)) * t) * np.exp(-42.0 * t)
    mono = intensity * (0.46 * chirp + 0.44 * crack + 0.34 * punch)
    ang = (np.clip(pan, -0.85, 0.85) + 1.0) * (0.25 * np.pi)
    return mono * math.cos(ang), mono * math.sin(ang)


def synth_portal_glitch_event(rng, seed_dir=1.0, dur_riser=0.22, dur_tear=0.14):
    n_pre = int(round(dur_riser * SR))
    n_post = int(round(dur_tear * SR))
    n_tot = n_pre + n_post
    sig_l = np.zeros(n_tot, dtype=np.float64)
    sig_r = np.zeros(n_tot, dtype=np.float64)
    duck = np.ones(n_tot, dtype=np.float64)

    if n_pre > 0:
        u_pre = np.linspace(0.0, 1.0, n_pre, endpoint=False)
        env_pre = (u_pre ** 2.6) * 0.72
        ph_l = np.cumsum(2.0 * np.pi * (320.0 * (10.2 ** u_pre)) / SR)
        ph_r = np.cumsum(2.0 * np.pi * (400.0 * (9.0 ** u_pre)) / SR)
        whoosh = signal.sosfilt(bp_sos(500.0, 6200.0, order=2), rng.standard_normal(n_pre))
        sig_l[:n_pre] += env_pre * (0.52 * np.sin(ph_l) + 0.48 * whoosh)
        sig_r[:n_pre] += env_pre * (0.52 * np.sin(ph_r + 0.9) + 0.48 * whoosh)
        duck[:n_pre] = 1.0 - 0.48 * (u_pre ** 3.0)

    u_post = np.linspace(0.0, 1.0, n_post, endpoint=False)
    t_post = np.arange(n_post, dtype=np.float64) / SR
    steps = np.floor(u_post * 7.0) / 7.0
    f_tl = (2480.0 * (0.20 ** steps)) if seed_dir > 0 else (410.0 * (5.5 ** steps))
    f_tr = (420.0 * (5.3 ** steps)) if seed_dir > 0 else (2420.0 * (0.21 ** steps))
    ph_tl = np.cumsum(2.0 * np.pi * f_tl / SR)
    ph_tr = np.cumsum(2.0 * np.pi * f_tr / SR)
    raw_tl = 0.65 * np.sign(np.sin(ph_tl)) * np.abs(np.sin(ph_tl)) ** 0.55 + 0.35 * np.sin(2.5 * ph_tl)
    raw_tr = 0.65 * np.sign(np.sin(ph_tr)) * np.abs(np.sin(ph_tr)) ** 0.55 + 0.35 * np.sin(2.5 * ph_tr)

    hold = 7
    idx_sh = (np.arange(n_post) // hold) * hold
    crush_l = signal.sosfilt(bp_sos(180.0, 6800.0, order=2), np.round(raw_tl[idx_sh] * 14.0) / 14.0)
    crush_r = signal.sosfilt(bp_sos(180.0, 6800.0, order=2), np.round(raw_tr[idx_sh] * 14.0) / 14.0)

    f_tape = 190.0 * np.exp(-26.0 * t_post) + 38.0
    tape_sub = np.sin(np.cumsum(2.0 * np.pi * f_tape / SR)) * np.exp(-18.0 * t_post)
    snap = signal.sosfilt(bp_sos(1200.0, 7200.0, order=2), rng.standard_normal(n_post)) * np.exp(-48.0 * t_post)
    env_post = np.sin(np.pi * np.minimum(1.0, u_post / 0.12)) * ((1.0 - u_post) ** 0.85)

    sig_l[n_pre:] += 0.64 * env_post * crush_l + 0.58 * tape_sub + 0.36 * snap
    sig_r[n_pre:] += 0.64 * env_post * crush_r + 0.58 * tape_sub + 0.36 * snap
    duck[n_pre:] = 0.25 + 0.75 * (u_post ** 0.9)
    return sig_l, sig_r, n_pre, duck


def apply_tape_flutter_on_bus(bus_l, bus_r, center_samp, span_frames=4):
    half = int(0.5 * span_frames * SPF)
    s0 = max(0, center_samp - half)
    s1 = min(len(bus_l), center_samp + half)
    n = s1 - s0
    if n < 64:
        return
    u = np.linspace(0.0, 1.0, n)
    warp = (0.0065 * SR) * (np.sin(np.pi * u) ** 2) * np.sin(2.5 * np.pi * u)
    idx = np.arange(n, dtype=np.float64)
    bus_l[s0:s1] = np.interp(np.clip(idx - warp, 0.0, n - 1.0), idx, bus_l[s0:s1])
    bus_r[s0:s1] = np.interp(np.clip(idx + 0.8 * warp, 0.0, n - 1.0), idx, bus_r[s0:s1])


def inject_impact_frame_slam(eng_l, eng_r, mus_duck_env, rng, f_impact, is_2099=True):
    s_hit = max(0, (f_impact - 1) * SPF)
    n_stut = 2 * SPF  # 2 frames = 83.33 ms

    # Pre-impact 0.19s 2099/Prowler warning shriek + reverse vacuum suck
    n_pre = int(0.19 * SR)
    s_pre = max(0, s_hit - n_pre)
    len_pre = s_hit - s_pre
    if len_pre > 0:
        u_pre = np.linspace(0.0, 1.0, len_pre, endpoint=False)
        vac = signal.sosfilt(bp_sos(450.0, 5200.0, order=2), rng.standard_normal(len_pre))
        vac_env = (u_pre ** 2.6) * (0.60 if is_2099 else 0.42)
        if is_2099:
            f_shriek = 622.25 * (0.94387 ** (u_pre ** 1.6))  # Eb5 -> D5 menacing tension bend
            ph_s = np.cumsum(2.0 * np.pi * f_shriek / SR)
            shriek = np.tanh(2.6 * (0.65 * np.sin(ph_s) + 0.45 * np.sin(0.5 * ph_s) + 0.30 * np.sin(1.5 * ph_s)))
            shriek = signal.sosfilt(bp_sos(260.0, 3800.0, order=2), shriek)
            eng_l[s_pre:s_hit] += vac_env * (0.70 * shriek + 0.42 * vac)
            eng_r[s_pre:s_hit] += vac_env * (0.70 * shriek * 0.92 + 0.42 * vac)
        else:
            eng_l[s_pre:s_hit] += vac_env * vac
            eng_r[s_pre:s_hit] += vac_env * vac

        n_dip = min(int(0.035 * SR), len_pre)
        dip = np.linspace(1.0, 0.20, n_dip)
        eng_l[s_hit - n_dip:s_hit] *= dip
        eng_r[s_hit - n_dip:s_hit] *= dip
        mus_duck_env[s_hit - n_dip:s_hit] = np.minimum(mus_duck_env[s_hit - n_dip:s_hit], dip)

    # Hard 2-frame 4x stereo rhythmic grain-stutter
    if s_hit + n_stut <= len(eng_l):
        glen = SPF // 2
        gl_seg = eng_l[s_hit:s_hit + glen].copy()
        gr_seg = eng_r[s_hit:s_hit + glen].copy()
        g_pk = max(float(np.max(np.abs(gl_seg))), float(np.max(np.abs(gr_seg))), 1e-4)
        ng = min(4.5, 0.50 / g_pk)
        gl_seg *= ng
        gr_seg *= ng
        win_g = np.hanning(glen) ** 0.30
        for rep in range(4):
            p0 = s_hit + rep * glen
            p1 = p0 + glen
            al = 1.25 if (rep % 2 == 0) else 0.40
            ar = 0.40 if (rep % 2 == 0) else 1.25
            eng_l[p0:p1] = gl_seg * win_g * al
            eng_r[p0:p1] = gr_seg * win_g * ar

    # Colossal F1 (43.65 Hz) Seismic Sub-Bass Drop + Crimson Ink-Slash Crack
    n_drop = min(int(0.64 * SR), len(eng_l) - s_hit)
    if n_drop > 0:
        t_d = np.arange(n_drop, dtype=np.float64) / SR
        f_sub = 43.6535 + 76.0 * np.exp(-24.0 * t_d)
        ph_sub = np.cumsum(2.0 * np.pi * f_sub / SR)
        sub_env = np.sin(np.pi * np.minimum(1.0, t_d / 0.005)) * np.exp(-3.5 * t_d)
        sub_wave = (0.84 * np.sin(ph_sub) + 0.25 * np.tanh(1.8 * np.sin(2.0 * ph_sub))) * sub_env

        slash_l = signal.sosfilt(bp_sos(1400.0, 8600.0, order=2), rng.standard_normal(n_drop)) * np.exp(-42.0 * t_d)
        slash_r = signal.sosfilt(bp_sos(1400.0, 8600.0, order=2), rng.standard_normal(n_drop)) * np.exp(-40.0 * t_d)

        ph_stab = np.cumsum(2.0 * np.pi * (87.307 * np.exp(-1.2 * t_d)) / SR)
        stab = np.tanh(3.0 * (np.sin(ph_stab) + 0.6 * np.sin(1.5 * ph_stab) + 0.4 * np.sin(2.0 * ph_stab)))
        stab = signal.sosfilt(bp_sos(130.0, 2600.0, order=2), stab) * np.exp(-9.2 * t_d)

        dscale = 0.94 if is_2099 else 0.78
        eng_l[s_hit:s_hit + n_drop] += dscale * (0.85 * sub_wave + 0.44 * slash_l + 0.46 * stab)
        eng_r[s_hit:s_hit + n_drop] += dscale * (0.85 * sub_wave + 0.44 * slash_r + 0.46 * stab)
        duck_d = 1.0 - (0.74 if is_2099 else 0.60) * np.exp(-8.5 * t_d)
        mus_duck_env[s_hit:s_hit + n_drop] = np.minimum(mus_duck_env[s_hit:s_hit + n_drop], duck_d)


def build_3d_skyharbor_master():
    t0 = time.perf_counter()
    print("[synth_sfx_sv] Loading 3D Sky-Harbor circuit telemetry (53.375s / 1,281 frames)...")
    pt = load_3d_circuit_and_powertrain()

    n_frames = pt["frame_end"]
    n_total = n_frames * SPF  # 2,562,000 samples = 53.375000 s
    t_all = np.arange(n_total, dtype=np.float64) / SR
    tv_ctrl = pt["t_vid"]

    rpm_all = np.interp(t_all, tv_ctrl, pt["rpm"])
    v_mps_all = np.interp(t_all, tv_ctrl, pt["v_mps"])
    v_kmh_all = v_mps_all * 3.6
    accel_all = np.interp(t_all, tv_ctrl, pt["accel"])
    eff_throt_all = np.interp(t_all, tv_ctrl, pt["eff_throttle"])
    up_cut_all = np.interp(t_all, tv_ctrl, pt["upshift_cut"])
    up_pop_all = np.interp(t_all, tv_ctrl, pt["upshift_pop"])
    dn_blip_all = np.interp(t_all, tv_ctrl, pt["downshift_blip"])
    turbo_all = np.interp(t_all, tv_ctrl, pt["turbo_spool"])
    curv_all = np.interp(t_all, tv_ctrl, pt["curv"])
    lat_g_all = np.interp(t_all, tv_ctrl, pt["lat_g"])
    vert_g_all = np.interp(t_all, tv_ctrl, pt["vert_comp_g"])
    s_m_all = np.interp(t_all, tv_ctrl, pt["s_m"])
    tunnel_all = np.interp(t_all, tv_ctrl, pt["tunnel"])
    bridge_all = np.interp(t_all, tv_ctrl, pt["bridge"])

    px_all = np.interp(t_all, tv_ctrl, pt["px"])
    py_all = np.interp(t_all, tv_ctrl, pt["py"])
    pz_all = np.interp(t_all, tv_ctrl, pt["pz"])
    hd_all = np.interp(t_all, tv_ctrl, pt["hd"])
    pitch_all = np.interp(t_all, tv_ctrl, pt["pitch"])

    theta_car_master = np.cumsum(2.0 * np.pi * (rpm_all / 60.0) / SR)
    rng = np.random.default_rng(2099053)

    out_l = np.zeros(n_total, dtype=np.float64)
    out_r = np.zeros(n_total, dtype=np.float64)
    xfade_half = int(0.025 * SR)  # 50 ms equal-power shot crossfades

    windows = pt["windows"]
    n_shots = len(windows)
    doppler_log = []

    # --- Per-Shot 3D Acoustic & Doppler Synthesis ---
    for s_idx, (sname, f0, f1, typ, pr) in enumerate(windows):
        core_s0 = 0 if s_idx == 0 else (f0 - 1) * SPF
        core_s1 = n_total if s_idx == n_shots - 1 else f1 * SPF
        s0 = max(0, core_s0 - (xfade_half if s_idx > 0 else 0))
        s1 = min(n_total, core_s1 + (xfade_half if s_idx < n_shots - 1 else 0))
        n_seg = s1 - s0

        rpm = rpm_all[s0:s1]
        v_mps = v_mps_all[s0:s1]
        eff_throt = eff_throt_all[s0:s1]
        up_cut = up_cut_all[s0:s1]
        up_pop = up_pop_all[s0:s1]
        dn_blip = dn_blip_all[s0:s1]
        turbo_sp = turbo_all[s0:s1]
        tun_seg = tunnel_all[s0:s1]

        px, py, pz = px_all[s0:s1], py_all[s0:s1], pz_all[s0:s1]
        hd, ptc = hd_all[s0:s1], pitch_all[s0:s1]
        vx = np.cos(ptc) * np.cos(hd) * v_mps
        vy = np.cos(ptc) * np.sin(hd) * v_mps
        vz = np.sin(ptc) * v_mps

        # Compute 3D camera position & Doppler from v6_shots_manifest.json (when present) or shot geometry
        mcam = pt.get("manifest_cam")
        has_manifest_xyz = mcam is not None
        if has_manifest_xyz:
            f_float = 1.0 + (np.arange(s0, s1, dtype=np.float64) / float(SPF))
            f_grid = np.arange(1, n_frames + 1, dtype=np.float64)
            cx = np.interp(f_float, f_grid, mcam["cam_xyz"][:, 0])
            cy = np.interp(f_float, f_grid, mcam["cam_xyz"][:, 1])
            cz = np.interp(f_float, f_grid, mcam["cam_xyz"][:, 2])
            dx, dy, dz = px - cx, py - cy, (pz + 0.38) - cz
            dist = np.maximum(np.sqrt(dx * dx + dy * dy + dz * dz), 0.75)
            if typ == "fixed":
                v_rad = (vx * dx + vy * dy + vz * dz) / dist
                doppler = SPEED_OF_SOUND / np.maximum(130.0, SPEED_OF_SOUND + v_rad)
                doppler_log.append((sname, float(dist.min()), float(doppler.max()), float(doppler.min())))
            elif typ == "onboard":
                doppler = np.ones(n_seg, dtype=np.float64)
            else:
                vcx = signal.sosfiltfilt(lp_sos(10.0), np.gradient(cx, 1.0 / SR))
                vcy = signal.sosfiltfilt(lp_sos(10.0), np.gradient(cy, 1.0 / SR))
                vcz = signal.sosfiltfilt(lp_sos(10.0), np.gradient(cz, 1.0 / SR))
                v_rad = ((vx - vcx) * dx + (vy - vcy) * dy + (vz - vcz) * dz) / dist
                doppler = np.clip(SPEED_OF_SOUND / (SPEED_OF_SOUND + 0.65 * v_rad), 0.92, 1.09)
        elif typ == "fixed":
            f_pass = int(pr.get("f_pass", (f0 + f1) // 2))
            s_ref = min(n_total - 1, max(0, (f_pass - 1) * SPF))
            hr, ptr = hd_all[s_ref], pitch_all[s_ref]
            tx, ty, tz = cos(ptr) * cos(hr), cos(ptr) * sin(hr), sin(ptr)
            rx_v, ry_v = sin(hr), -cos(hr)
            lead = float(pr.get("lead", -6.0))
            side = float(pr.get("side", 8.2))
            ch = float(pr.get("h", 0.9))
            cx = px_all[s_ref] - tx * lead + rx_v * side
            cy = py_all[s_ref] - ty * lead + ry_v * side
            cz = pz_all[s_ref] - tz * lead + ch

            dx, dy, dz = px - cx, py - cy, (pz + 0.38) - cz
            dist = np.maximum(np.sqrt(dx * dx + dy * dy + dz * dz), 1.5)
            v_rad = (vx * dx + vy * dy + vz * dz) / dist
            doppler = SPEED_OF_SOUND / np.maximum(130.0, SPEED_OF_SOUND + v_rad)
            doppler_log.append((sname, float(dist.min()), float(doppler.max()), float(doppler.min())))
        else:
            cx = cy = cz = None
            dist = np.full(n_seg, 7.0 if typ in ("chase", "orbit") else (1.8 if typ in ("wheel", "scraper", "rail") else 1.2))
            doppler = np.ones(n_seg, dtype=np.float64)

        # Crankshaft phase with combustion micro-jitter
        f_crank = (rpm / 60.0) * doppler
        jit = signal.sosfilt(bp_sos(28.0, 175.0, order=2), rng.standard_normal(n_seg))
        theta = theta_car_master[s0] + np.cumsum(2.0 * np.pi * f_crank * (1.0 + 0.0024 * jit) / SR)

        overrun = np.clip(1.0 - eff_throt * 3.5, 0.0, 1.0)
        load_b = 0.36 + 0.64 * eff_throt
        intake_b = 1.32 if typ == "onboard" else 1.05

        harmonics = [
            (1.0, 0.18, 0.3, 0.20),
            (1.5, 0.32, 0.2, 0.75),
            (3.0, 1.00, 0.35, 0.00),
            (4.5, 0.35, 0.45, 0.55),
            (6.0, 0.70 * intake_b, 0.75, 0.31),
            (9.0, 0.48 * intake_b, 1.05, 0.82),
            (12.0, 0.32 * intake_b, 1.25, 1.64),
            (15.0, 0.22 * intake_b, 1.45, 2.15),
            (18.0, 0.14 * intake_b, 1.65, 0.44),
            (21.0, 0.09 * intake_b, 1.80, 1.90),
        ]
        eng_raw = np.zeros(n_seg, dtype=np.float64)
        for om, a0, lexp, ph0 in harmonics:
            fh = om * f_crank
            aa = np.clip((18500.0 - fh) / 3500.0, 0.0, 1.0)
            amp = a0 * (load_b ** lexp) * aa * (1.0 + 0.55 * overrun if om in (1.5, 4.5) else 1.0)
            eng_raw += amp * np.sin(om * theta + ph0)

        turb_n = signal.sosfilt(bp_sos(240.0, 3400.0, order=2), rng.standard_normal(n_seg))
        valve_p = (0.5 + 0.5 * np.sin(3.0 * theta - 0.4)) ** 2
        eng_raw = eng_raw * (1.0 + 0.07 * turb_n) + 0.24 * turb_n * valve_p * (0.30 + 0.70 * eff_throt)

        drive = 1.12 + 0.90 * eff_throt + 0.35 * dn_blip
        shaped = np.tanh(drive * (0.48 * eng_raw + 0.08 * (eng_raw ** 2))) - np.tanh(0.08 * drive)

        fmode = "tunnel" if np.mean(tun_seg) > 0.5 else ("onboard" if typ == "onboard" else "exhaust")
        eng_core = apply_formant_bank(shaped, mode=fmode) * (0.54 + 0.46 * eff_throt + 0.14 * overrun) * up_cut

        # MGU-H turbo whistle + upshift bark + overrun crackle
        f_turbo = np.clip((2700.0 + 2800.0 * turbo_sp) * doppler, 1600.0, 14000.0)
        ph_tb = np.cumsum(2.0 * np.pi * f_turbo / SR)
        mguh = 0.048 * (0.25 + 0.75 * turbo_sp) * np.sin(ph_tb)

        pop_lo = signal.sosfilt(bp_sos(140.0, 640.0, order=2), rng.standard_normal(n_seg))
        pop_hi = signal.sosfilt(bp_sos(760.0, 3100.0, order=2), rng.standard_normal(n_seg))
        up_bark = 0.56 * up_pop * (0.62 * np.tanh(2.4 * pop_lo) + 0.38 * pop_hi)

        mono = eng_core + mguh + up_bark

        if typ == "fixed":
            d_min = float(dist.min())
            dg = np.clip(((d_min + 7.5) / (dist + 7.5)) ** 0.80 * 1.24, 0.14, 1.28)
            i_cl = int(np.argmin(dist))
            i_ref = int(round(0.65 * i_cl + 0.35 * (n_seg // 2)))
            cx_ref = float(cx[i_ref]) if np.ndim(cx) > 0 else float(cx)
            cy_ref = float(cy[i_ref]) if np.ndim(cy) > 0 else float(cy)
            adx, ady = float(px[i_ref]) - cx_ref, float(py[i_ref]) - cy_ref
            anorm = max(math.hypot(adx, ady), 1e-6)
            rx_ear, ry_ear = ady / anorm, -adx / anorm
            sin_az = ((px - cx) * rx_ear + (py - cy) * ry_ear) / np.maximum(np.hypot(px - cx, py - cy), 1.0)
            pan_c = np.clip(sin_az * 0.94, -0.86, 0.86)
            sig_l, sig_r = stereo_pan_and_itd(mono * dg, pan_c, itd_scale=1.0)

            # High-speed 3D Doppler aerodynamic wake tear ("WHOOSH!")
            wake_env = np.exp(-(((dist - d_min) / 7.5) ** 2)) * ((v_mps / 92.0) ** 1.3)
            wake_n = signal.sosfilt(bp_sos(120.0, 2100.0, order=2), rng.standard_normal(n_seg))
            wl, wr = stereo_pan_and_itd(0.42 * wake_env * wake_n, pan_c, itd_scale=1.2)
            sig_l += wl
            sig_r += wr
        elif typ == "orbit":
            pan_c = np.linspace(-0.38, 0.38, n_seg)
            sig_l, sig_r = stereo_pan_and_itd(mono * 0.92, pan_c, itd_scale=0.6)
        elif typ in ("wheel", "scraper", "rail"):
            # Asphalt-scraping 14mm hero cam / 17.4 deg banked bowl upper-wall rail cam (0.7m from wingtip!):
            # Add visceral close-proximity aero shear & tire/barrier rush!
            prox_rush = 0.24 * ((v_mps / 88.0) ** 1.4) * signal.sosfilt(
                bp_sos(160.0, 3400.0, order=2), rng.standard_normal(n_seg)
            )
            pan_c = np.full(n_seg, -0.32 if typ == "rail" else (0.25 if float(pr.get("side", -2.0)) < 0 else -0.25))
            sig_l, sig_r = stereo_pan_and_itd((mono + prox_rush) * 1.04, pan_c, itd_scale=0.6)
        elif typ == "aerial":
            sig_l, sig_r = stereo_pan_and_itd(signal.sosfilt(lp_sos(3500.0), mono * 0.62), np.zeros(n_seg), 0.3)
        else:
            pan_c = np.clip(-0.12 * curv_all[s0:s1] / 0.02, -0.22, 0.22)
            sig_l, sig_r = stereo_pan_and_itd(mono * 0.90, pan_c, itd_scale=0.35)

        win = np.ones(n_seg, dtype=np.float64)
        if s_idx > 0:
            n_in = min(2 * xfade_half, n_seg)
            win[:n_in] *= np.sin(0.5 * np.pi * np.linspace(0.0, 1.0, n_in))
        if s_idx < n_shots - 1:
            n_out = min(2 * xfade_half, n_seg)
            win[-n_out:] *= np.cos(0.5 * np.pi * np.linspace(0.0, 1.0, n_out))

        out_l[s0:s1] += sig_l * win
        out_r[s0:s1] += sig_r * win

    # --- Continuous Set-Piece Physical FX Layers ---
    v_norm = np.clip(v_kmh_all / 341.2, 0.0, 1.0)

    # A) Golden Titanium Skid-Block Spark Scrape Crackles (+3.5 dB Iteration-2 boost, especially f=276..308 in Clip 1!)
    f_idx_all = 1.0 + (np.arange(n_total, dtype=np.float64) / float(SPF))
    eau_rouge_focus = np.exp(-0.5 * ((f_idx_all - 291.0) / 14.5) ** 2)  # Peaks squarely across f=276..308!
    cork_bottom_focus = 0.65 * np.exp(-0.5 * ((f_idx_all - 862.0) / 14.0) ** 2)
    spark_env = (
        np.clip(vert_g_all / 1.15, 0.0, 1.35)
        + 0.85 * eau_rouge_focus
        + cork_bottom_focus
        + 0.30 * np.clip((v_kmh_all - 324.0) / 18.0, 0.0, 1.0)
    )
    spark_env = signal.sosfilt(lp_sos(16.0, order=1), np.clip(spark_env, 0.0, 1.55))
    # Metallic titanium plank grind (2.1-5.6 kHz) + white-hot spark shower crackles (4.2-13.2 kHz)
    ti_grind_l = signal.sosfilt(bp_sos(2100.0, 5600.0, order=2), rng.standard_normal(n_total))
    ti_grind_r = signal.sosfilt(bp_sos(2100.0, 5600.0, order=2), rng.standard_normal(n_total))
    hi_spark_l = signal.sosfilt(bp_sos(4200.0, 13200.0, order=2), rng.standard_normal(n_total))
    hi_spark_r = signal.sosfilt(bp_sos(4200.0, 13200.0, order=2), rng.standard_normal(n_total))
    sparks_pop_l = np.clip(rng.standard_normal(n_total) - 1.95, 0.0, 5.5) * hi_spark_l
    sparks_pop_r = np.clip(rng.standard_normal(n_total) - 1.95, 0.0, 5.5) * hi_spark_r
    out_l += spark_env * (0.21 * ti_grind_l + 0.38 * sparks_pop_l)
    out_r += spark_env * (0.21 * ti_grind_r + 0.38 * sparks_pop_r)

    # B) Sky-Bridge Stay-Cable Supersonic Pass-By Whooshes (+3.5 dB Iteration-2 boost across f=585..620 in Clip 2!)
    clip2_bridge_boost = 1.0 + 0.75 * np.clip(1.0 - np.abs(f_idx_all - 601.0) / 24.0, 0.0, 1.0)
    cable_phase = 2.0 * np.pi * (s_m_all / 16.0)
    cable_pulse = (np.cos(cable_phase) ** 8) * bridge_all * (v_norm ** 1.25) * clip2_bridge_boost
    # Frequency-swept Doppler cable whip (high-to-low pitch sweep on every stay-cable pass!)
    f_cab = np.clip(980.0 - 560.0 * np.sin(cable_phase), 220.0, 2200.0)
    cab_tone = np.sin(np.cumsum(2.0 * np.pi * f_cab / SR))
    cable_whoosh_l = signal.sosfilt(bp_sos(160.0, 2600.0, order=2), rng.standard_normal(n_total)) + 0.35 * cab_tone
    cable_whoosh_r = signal.sosfilt(bp_sos(160.0, 2600.0, order=2), rng.standard_normal(n_total)) + 0.35 * cab_tone
    out_l += 0.36 * cable_pulse * cable_whoosh_l
    out_r += 0.36 * np.roll(cable_pulse, int(0.014 * SR)) * cable_whoosh_r

    # C) Wet-Asphalt Rooster-Tail Spray Sizzle & Serrated Neon Kerb Rumble
    spray_env = 0.08 * (v_norm ** 1.6) + 0.14 * np.clip((lat_g_all - 2.2) / 4.2, 0.0, 1.0)
    out_l += spray_env * signal.sosfilt(bp_sos(1300.0, 6400.0, order=2), rng.standard_normal(n_total))
    out_r += spray_env * signal.sosfilt(bp_sos(1300.0, 6400.0, order=2), rng.standard_normal(n_total))

    kerb_gate = signal.sosfilt(lp_sos(9.0, order=2), np.clip((np.abs(curv_all) - 0.0075) / 0.007, 0.0, 1.0))
    ph_kerb = np.cumsum(2.0 * np.pi * np.clip(v_mps_all / 0.28, 35.0, 340.0) / SR)
    kerb_sig = 0.16 * kerb_gate * (0.65 * np.sin(ph_kerb) + 0.35 * np.sin(0.5 * ph_kerb))
    out_l += kerb_sig
    out_r += kerb_sig

    # D) 520m ENCLOSED VAULTED TUNNEL ACOUSTIC REVERB ROAR + 12m LASER-ARCH PULSES (tunnel == True, f=908..1041!)
    tun_smooth = signal.sosfilt(lp_sos(6.0, order=1), tunnel_all)
    tun_mid = 0.5 * (out_l + out_r) * tun_smooth
    tun_body = signal.sosfilt(bp_sos(145.0, 2850.0, order=2), np.tanh(1.5 * tun_mid))
    tun_rev_l = np.zeros(n_total, dtype=np.float64)
    tun_rev_r = np.zeros(n_total, dtype=np.float64)
    for d_ms, g_tap in ((13, 0.46), (23, 0.40), (37, 0.34), (59, 0.28), (89, 0.21), (131, 0.15)):
        d = int(0.001 * d_ms * SR)
        tun_rev_l[d:] += g_tap * tun_body[:-d]
    for d_ms, g_tap in ((17, 0.45), (29, 0.39), (43, 0.33), (67, 0.27), (101, 0.20), (149, 0.14)):
        d = int(0.001 * d_ms * SR)
        tun_rev_r[d:] += g_tap * tun_body[:-d]

    # 12-meter hexagonal laser-rib supersonic pressure pulses (s_m % 12.0 == 0 -> ~7.9 Hz @ 341 km/h!)
    rib_pulse = (np.cos(2.0 * np.pi * (s_m_all / 12.0)) ** 10) * tun_smooth * (v_norm ** 1.5)
    rib_thump = signal.sosfilt(bp_sos(95.0, 1450.0, order=2), rng.standard_normal(n_total))
    # Blinding tunnel exit decompression whoosh at f=1041!
    s_exit = (1041 - 1) * SPF
    exit_burst = np.zeros(n_total, dtype=np.float64)
    n_ex = min(int(0.28 * SR), n_total - s_exit)
    if n_ex > 0:
        t_ex = np.arange(n_ex) / SR
        exit_burst[s_exit:s_exit + n_ex] = (
            0.52 * np.exp(-14.0 * t_ex) * signal.sosfilt(bp_sos(120.0, 4800.0, order=2), rng.standard_normal(n_ex))
        )

    out_l = out_l * (1.0 + 0.28 * tun_smooth) + 0.58 * tun_rev_l + 0.32 * rib_pulse * rib_thump + exit_burst
    out_r = out_r * (1.0 + 0.28 * tun_smooth) + 0.58 * tun_rev_r + 0.32 * rib_pulse * rib_thump + exit_burst

    # --- 3-Act Spider-Verse Stylized Sonic Layers (Locked to #33 Exact Frame Cuts!) ---
    # Act I   (sv_dimension=0.0, Earth-1610 Miles): f=1..427   (Portal Cut 1->2: f=426..429)
    # Act II  (sv_dimension=1.0, Earth-65 Gwen):    f=428..894 (Portal Cut 2->3: f=893..896)
    # Act III (sv_dimension=2.0, Earth-928 2099):   f=895..1281
    s_p1 = (428 - 1) * SPF
    s_p2 = (895 - 1) * SPF
    xf = 2 * SPF
    act1_mask = np.clip((s_p1 + xf // 2 - np.arange(n_total)) / float(xf), 0.0, 1.0)
    act3_mask = np.clip((np.arange(n_total) - (s_p2 - xf // 2)) / float(xf), 0.0, 1.0)
    act2_mask = np.clip(1.0 - act1_mask - act3_mask, 0.0, 1.0)

    # Act I: Skyscraper Canyon Slapback + 12fps On-Twos Comic Mid-Punch + DJ Vinyl Whip Cracks
    canyon_mask = np.clip(1.0 - np.arange(n_total) / float(240 * SPF), 0.0, 1.0)
    d_can = int(0.031 * SR)
    out_l[d_can:] += 0.22 * canyon_mask[d_can:] * signal.sosfilt(bp_sos(300, 3200), out_r[:-d_can])
    out_r[d_can:] += 0.22 * canyon_mask[d_can:] * signal.sosfilt(bp_sos(300, 3200), out_l[:-d_can])

    twos_mod = 1.0 + 0.12 * np.sin(2.0 * np.pi * 12.0 * t_all)
    out_l += act1_mask * 0.26 * signal.sosfilt(bp_sos(750.0, 2900.0), np.tanh(1.6 * out_l)) * twos_mod
    out_r += act1_mask * 0.26 * signal.sosfilt(bp_sos(750.0, 2900.0), np.tanh(1.6 * out_r)) * twos_mod

    for idx_u, tu in enumerate(pt["upshift_times"]):
        if tu < (s_p1 / SR):
            i0 = int(round(tu * SR))
            wl, wr = synth_vinyl_whip_transient(rng, pan=((idx_u % 3) - 1) * 0.35, intensity=0.88)
            i1 = min(n_total, i0 + len(wl))
            out_l[i0:i1] += wl[:i1 - i0]
            out_r[i0:i1] += wr[:i1 - i0]

    # Act II (Earth-65 Gwen): Wide Mid-Side Stereo Chorus + Octave-Up Watercolor Shimmer Wash
    mid_hi_l = signal.sosfilt(bp_sos(850.0, 4800.0, order=2), out_l)
    mid_hi_r = signal.sosfilt(bp_sos(850.0, 4800.0, order=2), out_r)
    idx_n = np.arange(n_total, dtype=np.float64)
    del_l = (0.0145 + 0.0024 * np.sin(2.0 * np.pi * 0.85 * t_all)) * SR
    del_r = (0.0192 + 0.0026 * np.cos(2.0 * np.pi * 0.93 * t_all + 0.5)) * SR
    ch_l = np.interp(np.clip(idx_n - del_l, 0.0, n_total - 1.0), idx_n, mid_hi_r)
    ch_r = np.interp(np.clip(idx_n - del_r, 0.0, n_total - 1.0), idx_n, mid_hi_l)
    oct_air = signal.sosfilt(bp_sos(1950.0, 6200.0, order=2), np.abs(0.5 * (mid_hi_l + mid_hi_r)))

    wash_l = np.zeros(n_total, dtype=np.float64)
    wash_r = np.zeros(n_total, dtype=np.float64)
    for d, g in ((int(0.067 * SR), 0.44), (int(0.131 * SR), 0.34), (int(0.229 * SR), 0.24)):
        wash_l[d:] += g * (0.58 * ch_l[:-d] + 0.65 * oct_air[:-d])
    for d, g in ((int(0.083 * SR), 0.43), (int(0.157 * SR), 0.33), (int(0.263 * SR), 0.23)):
        wash_r[d:] += g * (0.58 * ch_r[:-d] + 0.65 * oct_air[:-d])
    wet_m = 0.5 * (0.48 * (ch_l + ch_r) + 0.62 * (wash_l + wash_r))
    wet_s = 0.5 * (0.48 * (ch_l - ch_r) + 0.62 * (wash_l - wash_r)) * 1.65
    out_l += act2_mask * (wet_m + wet_s)
    out_r += act2_mask * (wet_m - wet_s)

    # Act III (Earth-928 2099): Menacing F-Minor Distorted Cyber-Brass Synth Bass Growl
    semi_bend = 2.0 ** ((0.85 * np.clip(-accel_all / 28.0, 0.0, 1.0) + 0.12 * v_norm) / 12.0)
    f_root = 43.6535 * semi_bend  # F1 locked to After Hours key!

    def brass_voice(fc, cents, ph0):
        ph = ph0 + np.cumsum(2.0 * np.pi * (fc * (2.0 ** (cents / 1200.0))) / SR)
        s = np.zeros_like(ph)
        for k, a in ((1, 0.55), (2, 1.00), (3, 0.72), (4, 0.54), (5, 0.38), (6, 0.25)):
            s += a * np.sin(k * ph + 0.2 * k)
        return s * 0.32

    br_l = sum(brass_voice(f_root, c, j * 1.1) for j, c in enumerate((-15.0, -5.0, 0.0, +9.0)))
    br_r = sum(brass_voice(f_root, c, j * 1.7 + 0.4) for j, c in enumerate((-9.0, 0.0, +6.0, +16.0)))
    drive_b = 1.45 + 1.55 * eff_throt_all
    sat_bl = signal.sosfilt(bp_sos(68.0, 2300.0, order=2), np.tanh(drive_b * br_l))
    sat_br = signal.sosfilt(bp_sos(68.0, 2300.0, order=2), np.tanh(drive_b * br_r))
    swell_b = 0.30 * act3_mask * (0.24 + 0.76 * eff_throt_all) * (0.50 + 0.50 * v_norm)
    out_l += swell_b * sat_bl
    out_r += swell_b * sat_br

    # Portal Glitches & Dual Impact Frames (f=414 Eau-Rouge Moon Crest & f=1067 Harbor Hairpin Slam!)
    mus_event_duck = np.ones(n_total, dtype=np.float64)
    for s_portal, sdir in ((s_p1, +1.0), (s_p2, -1.0)):
        apply_tape_flutter_on_bus(out_l, out_r, s_portal, span_frames=4)
        gl_l, gl_r, n_pre, gl_duck = synth_portal_glitch_event(rng, seed_dir=sdir)
        p0 = max(0, s_portal - n_pre)
        p1 = min(n_total, p0 + len(gl_l))
        out_l[p0:p1] += gl_l[:p1 - p0]
        out_r[p0:p1] += gl_r[:p1 - p0]
        mus_event_duck[p0:p1] = np.minimum(mus_event_duck[p0:p1], gl_duck[:p1 - p0])

    impacts = pt["impact_frames"]
    for idx_imp, f_imp in enumerate(impacts):
        if 5 < f_imp < n_frames - 5:
            inject_impact_frame_slam(out_l, out_r, mus_event_duck, rng, f_impact=f_imp, is_2099=(f_imp > 850))

    # Master SFX fades & True-Peak Limit (-1.50 dBFS)
    n_fi = int(0.08 * SR)
    fi = np.sin(0.5 * np.pi * np.linspace(0.0, 1.0, n_fi))
    out_l[:n_fi] *= fi
    out_r[:n_fi] *= fi

    n_fo = int(1.40 * SR)
    fo = np.cos(0.5 * np.pi * np.linspace(0.0, 1.0, n_fo)) ** 1.2
    out_l[-n_fo:] *= fo
    out_r[-n_fo:] *= fo

    out_l = signal.sosfilt(hp_sos(24.0, order=2), out_l)
    out_r = signal.sosfilt(hp_sos(24.0, order=2), out_r)
    sfx_l, sfx_r = brickwall_true_peak_limit(out_l, out_r, ceiling_db=-1.50)

    write_wav_16bit(OUT_WAV_53, sfx_l, sfx_r)
    shutil.copyfile(OUT_WAV_53, OUT_WAV_ALIAS)
    shutil.copyfile(OUT_WAV_53, os.path.join(OUT_DIR, "sfx_spiderverse_54s.wav"))

    # --- Mix with Peak 53.375s Drop of audio/audio.wav (After Hours @ seg_start=240.814s) ---
    seg_start = 240.81415
    if os.path.exists(CUE_JSON):
        with open(CUE_JSON, encoding="utf-8") as f:
            seg_start = float(json.load(f).get("seg_start", seg_start))

    print(f"[synth_sfx_sv] Slicing After Hours peak drop (audio.wav @ {seg_start:.3f}s, 96 beats) & mixing...")
    mus_l, mus_r = decode_audio_slice_48k(AUDIO_WAV, ss_sec=seg_start, dur_sec=n_total / SR + 0.2, n_samples=n_total)

    apply_tape_flutter_on_bus(mus_l, mus_r, s_p1, span_frames=4)
    apply_tape_flutter_on_bus(mus_l, mus_r, s_p2, span_frames=4)

    b_pk, a_pk = signal.iirnotch(600.0, Q=1.4, fs=SR)
    mus_l = 0.76 * mus_l + 0.24 * signal.lfilter(b_pk, a_pk, mus_l)
    mus_r = 0.76 * mus_r + 0.24 * signal.lfilter(b_pk, a_pk, mus_r)

    sfx_env = signal.sosfilt(lp_sos(7.5, order=2), np.sqrt(0.5 * (sfx_l ** 2 + sfx_r ** 2)))
    sc_duck = 1.0 / (1.0 + 1.40 * np.maximum(0.0, sfx_env - 0.11))
    tot_duck = np.minimum(sc_duck, mus_event_duck)

    sfx_hp_l = signal.sosfilt(hp_sos(62.0, order=2), sfx_l)
    sfx_hp_r = signal.sosfilt(hp_sos(62.0, order=2), sfx_r)
    imp_sub = np.clip(1.0 - mus_event_duck, 0.0, 1.0)
    sfx_ml = (1.0 - imp_sub) * sfx_hp_l + imp_sub * sfx_l
    sfx_mr = (1.0 - imp_sub) * sfx_hp_r + imp_sub * sfx_r

    mix_l = 0.43 * mus_l * tot_duck + 0.70 * sfx_ml
    mix_r = 0.43 * mus_r * tot_duck + 0.70 * sfx_mr
    mix_l[:n_fi] *= fi
    mix_r[:n_fi] *= fi
    mix_l[-n_fo:] *= fo
    mix_r[-n_fo:] *= fo

    mix_l, mix_r = brickwall_true_peak_limit(mix_l, mix_r, ceiling_db=-1.70)

    fd_tmp, tmp_wav = tempfile.mkstemp(suffix="_v6_53s_mix.wav")
    os.close(fd_tmp)
    try:
        write_wav_16bit(tmp_wav, mix_l, mix_r)
        subprocess.run(
            [
                FFMPEG, "-hide_banner", "-loglevel", "warning", "-y",
                "-i", tmp_wav,
                "-c:a", "aac", "-b:a", "256k", "-ar", str(SR), "-ac", "2",
                "-movflags", "+faststart", OUT_MIX_53,
            ],
            check=True,
        )
    finally:
        if os.path.exists(tmp_wav):
            os.remove(tmp_wav)

    shutil.copyfile(OUT_MIX_53, OUT_MIX_ALIAS)
    dt_el = time.perf_counter() - t0
    print(f"[synth_sfx_sv] Done in {dt_el:.2f} s:")
    print(f"  WAV: {OUT_WAV_53} ({os.path.getsize(OUT_WAV_53):,} B, {n_total/SR:.4f} s)")
    print(f"  M4A: {OUT_MIX_53} ({os.path.getsize(OUT_MIX_53):,} B)")
    print(
        f"  Gearbox: {len(pt['upshift_times'])} upshifts, {len(pt['downshift_times'])} downshifts | "
        f"RPM: {pt['rpm'].min():.0f}..{pt['rpm'].max():.0f} | Impacts @ frames {impacts}"
    )
    for nm, dm, dhi, dlo in doppler_log:
        print(f"  [3D Doppler] {nm:22s} closest={dm:4.1f}m  pitch={dhi:.3f}x -> {dlo:.3f}x")


def discover_clip_windows():
    """
    Auto-discovers the 3 rendered showcase clip directories & exact frame ranges
    inside renders_v6/clips_frames/ (falls back to landmark windows if not rendered yet).
    """
    clips_root = os.path.join(OUT_DIR, "clips_frames")
    found = []
    if os.path.isdir(clips_root):
        subdirs = sorted(
            [d for d in os.listdir(clips_root) if os.path.isdir(os.path.join(clips_root, d))]
        )
        for sd in subdirs[:3]:
            jpgs = sorted(glob.glob(os.path.join(clips_root, sd, "f_*.jpg")))
            if jpgs:
                nums = [int(re.search(r"f_(\d+)\.jpg$", os.path.basename(p)).group(1)) for p in jpgs]
                found.append((sd, min(nums), len(nums)))
    if len(found) == 3:
        return found
    # Locked to #33 exact 3x 96-frame (4.000s) showcase clip windows on 1,281-frame 3D Sky-Harbor circuit:
    # Clip 1: clip1_miles_1610  f=269..364 (ss=11.166667s — Eau-Rouge f=282 Spark Scrape -> +13.5 deg Raidillon Climb!)
    # Clip 2: clip2_gwen_65     f=585..680 (ss=24.333333s — Sky-Bridge -> 17.4 deg Banked Bowl Wingtip Rail-Scrape!)
    # Clip 3: clip3_2099_impact f=993..1088 (ss=41.333333s — 341 km/h Strobe Tunnel -> f=1041 Exit -> f=1067..1068 Impact!)
    return [
        ("clip1_miles_1610", 269, 96),
        ("clip2_gwen_65", 585, 96),
        ("clip3_2099_impact", 993, 96),
    ]


def build_showcase_reel_wav(out_reel_wav):
    mix_path = OUT_MIX_53 if os.path.exists(OUT_MIX_53) else OUT_MIX_ALIAS
    clips_l, clips_r = decode_audio_slice_48k(mix_path)
    n_avail = len(clips_l)

    clip_specs = discover_clip_windows()
    total_frames = sum(nf for _, _, nf in clip_specs)
    reel_l = np.zeros(total_frames * SPF, dtype=np.float64)
    reel_r = np.zeros(total_frames * SPF, dtype=np.float64)

    xf_half = SPF  # 2-frame (4,000 samples = 83.33 ms) equal-power micro-join
    join_samples = []
    cursor = 0

    for idx, (sd, f_start, nf) in enumerate(clip_specs):
        n_clip = nf * SPF
        st = max(0, min(n_avail - n_clip, (f_start - 1) * SPF))
        dst0 = cursor
        dst1 = cursor + n_clip

        pad_pre = min(xf_half, st, dst0) if idx > 0 else 0
        pad_post = min(xf_half, n_avail - (st + n_clip), len(reel_l) - dst1) if idx < len(clip_specs) - 1 else 0

        seg_l = clips_l[st - pad_pre:st + n_clip + pad_post].copy()
        seg_r = clips_r[st - pad_pre:st + n_clip + pad_post].copy()
        win = np.ones(len(seg_l), dtype=np.float64)

        if pad_pre > 0:
            u = np.linspace(0.0, 1.0, 2 * pad_pre)
            win[:2 * pad_pre] *= np.sin(0.5 * np.pi * u)
        if pad_post > 0:
            u = np.linspace(0.0, 1.0, 2 * pad_post)
            win[-2 * pad_post:] *= np.cos(0.5 * np.pi * u)

        reel_l[dst0 - pad_pre:dst1 + pad_post] += seg_l * win
        reel_r[dst0 - pad_pre:dst1 + pad_post] += seg_r * win
        if idx < len(clip_specs) - 1:
            join_samples.append(dst1)
        cursor = dst1

    rng = np.random.default_rng(161065928)
    for j_idx, j_samp in enumerate(join_samples):
        apply_tape_flutter_on_bus(reel_l, reel_r, j_samp, span_frames=2)
        gl_l, gl_r, n_pre, _ = synth_portal_glitch_event(
            rng, seed_dir=(1.0 if j_idx % 2 == 0 else -1.0), dur_riser=0.07, dur_tear=0.065
        )
        p0 = max(0, j_samp - n_pre)
        p1 = min(len(reel_l), p0 + len(gl_l))
        reel_l[p0:p1] += 0.42 * gl_l[:p1 - p0]
        reel_r[p0:p1] += 0.42 * gl_r[:p1 - p0]

    n_fi = int(0.025 * SR)
    fi = np.sin(0.5 * np.pi * np.linspace(0.0, 1.0, n_fi))
    reel_l[:n_fi] *= fi
    reel_r[:n_fi] *= fi

    n_fo = int(0.30 * SR)
    fo = np.cos(0.5 * np.pi * np.linspace(0.0, 1.0, n_fo)) ** 1.15
    reel_l[-n_fo:] *= fo
    reel_r[-n_fo:] *= fo

    reel_l, reel_r = brickwall_true_peak_limit(reel_l, reel_r, ceiling_db=-1.75)
    write_wav_16bit(out_reel_wav, reel_l, reel_r)
    print(f"[synth_sfx_sv] Built {len(reel_l)/SR:.4f}s showcase reel WAV from {clip_specs}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reel-wav", default=None, help="Build stitched 3-clip showcase WAV at given temp path")
    ap.add_argument("--print-clips", action="store_true", help="Print discovered clip subdirs & start frames")
    args = ap.parse_args()

    if args.print_clips:
        for sd, f0, nf in discover_clip_windows():
            print(f"{sd}|{f0}|{nf}|{(f0 - 1) / float(FPS):.6f}|{nf / float(FPS):.6f}")
        return

    if args.reel_wav:
        if not os.path.exists(OUT_MIX_53):
            build_3d_skyharbor_master()
        build_showcase_reel_wav(args.reel_wav)
    else:
        build_3d_skyharbor_master()


if __name__ == "__main__":
    main()
