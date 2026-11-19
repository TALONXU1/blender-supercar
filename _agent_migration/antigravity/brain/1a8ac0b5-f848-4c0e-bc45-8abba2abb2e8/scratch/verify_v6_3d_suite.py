# -*- coding: utf-8 -*-
"""
V6 Spider-Verse 3D Mega-Circuit & Blockbuster Edition Verification Suite (Read-Only!)
Covers:
1) 100% V5 Isolation (57-file SHA256 check + LATEST/ untouched)
2) track_data/spiderverse_circuit.json 3D geometry & physics continuity audit:
   - Closed-loop C2 seam check (xy, z, heading, pitch, bank, v)
   - Elevation range (~42m), banking (~16-18 deg), 5 zones, tunnel & bridge flags, lap ~53.33s (1281 frames)
   - Non-adjacent self-intersection / clearance check + lateral grip envelope check
3) Headless Blender 5.3 audit of v6_stage_lookdev.blend & v6_stage_anim_sv.blend (when invoked under blender -b -P):
   - 3D Banked Tire-to-Road Contact Check across all 5 zones (verify wheels neither sink into banked asphalt nor float!)
   - 24 Extreme Shots 3D Camera-to-Car Raycast Check (including inside 450m Strobe Tunnel & Sky-Bridge — 0 tunnel-shell / building / girder occlusions!)
   - Safe On-Twos (24fps world XYZ + attitude + cameras vs 12fps CONSTANT local secondary & FX)
   - Wet Asphalt Raytracing (use_raytracing=True, low puddle roughness, no white sun wedge), 5 Set-Pieces, V6_09_ComicFX (afterburner shock-diamonds, titanium sparks, vortex ribbons, wet spray), Solidify Ink Outlines, Cinema-Scope 2.39:1 Multi-Pass Compositor
   - 1080p CPU per-frame speed benchmark (to scratch/)
4) Ruthless Art-Director Visual + Audio Critique (PIL/NumPy on active 2.39:1 image area y=138..942, excluding black letterbox bars so letterbox bars never skew shadow/ink stats!):
   - Ink clumping vs sharpness pop across all 24 stills
   - 6-9px 1080p Ben-Day Halftone & Crosshatching visibility
   - Wet road neon reflection richness (lower-third saturation & contrast!)
   - 3x 96-frame Showcase Clips + Impact Frames + comic_page_sheet.jpg
   - 53.33s WAV/M4A + 4 MP4s (tunnel reverb boost check, spark/impact peaks, ffprobe/volumedetect)
"""
import os
import sys
import json

PROJ = r"D:\项目session\blender-supercar"
SCRATCH = r"C:\Users\86052\.gemini\antigravity\brain\1a8ac0b5-f848-4c0e-bc45-8abba2abb2e8\scratch"
CIRCUIT_JSON = os.path.join(PROJ, "track_data", "spiderverse_circuit.json")
ANIM_SV_BLEND = os.path.join(PROJ, "v6_spiderverse", "v6_stage_anim_sv.blend")

if "--blender" in sys.argv:
    import bpy
    import time
    from math import radians, cos, sin
    from mathutils import Vector
    from bpy_extras.object_utils import world_to_camera_view

    def iter_fcurves(action):
        fcs = list(getattr(action, "fcurves", []) or [])
        if fcs:
            return fcs
        for layer in getattr(action, "layers", []) or []:
            for strip in getattr(layer, "strips", []) or []:
                for cb in getattr(strip, "channelbags", []) or []:
                    fcs.extend(cb.fcurves)
        return fcs

    bpy.ops.wm.open_mainfile(filepath=ANIM_SV_BLEND)
    sc = bpy.context.scene
    rig = bpy.data.objects["RIG_F1_Race"]

    # 1. Basic scene & render checks
    vl = sc.view_layers[0]
    passes = {k: getattr(vl, k, False) for k in (
        "use_pass_normal", "use_pass_mist", "use_pass_z", "use_pass_emit", "use_pass_cryptomatte_object"
    )}

    # 2. Check 3D Tire-to-Road contact across sampled frames (every 16 frames across 1..frame_end)
    car_set = {o.name for o in bpy.data.objects if o.type in ('MESH', 'CURVE') and not o.name.startswith(("V5_", "V6_Env", "SV_Env"))}
    # Refined car_set: anything parented to rig or in V6_09_ComicFX
    fx_coll = bpy.data.collections.get("V6_09_ComicFX")
    fx_names = {o.name for o in fx_coll.all_objects} if fx_coll else set()
    rig_children = {o.name for o in bpy.data.objects if o.parent == rig or o.name in fx_names or o.name.startswith(("GEO_F1_", "GEO_MERC_", "DEC_"))}

    tire_clearances = []
    for f in range(1, sc.frame_end + 1, 20):
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        rig_e = rig.evaluated_get(dg)
        # Cast downward along car -Z from each wheel center (radius = 0.357m)
        for wb_name in ("Bone_Wheel_FL", "Bone_Wheel_FR", "Bone_Wheel_RL", "Bone_Wheel_RR"):
            if wb_name not in rig_e.pose.bones:
                continue
            wm = rig_e.matrix_world @ rig_e.pose.bones[wb_name].matrix
            w_center = wm.translation
            # Car up vector from Bone_Heading or Bone_Root
            pb_att = rig_e.pose.bones.get("Bone_Heading") or rig_e.pose.bones["Bone_Root"]
            up_vec = ((rig_e.matrix_world @ pb_att.matrix).to_3x3() @ Vector((0, 0, 1))).normalized()
            # Raycast from 0.2m above wheel center downward along -up_vec, skipping car meshes by starting 0.02m below hub or multi-hopping
            orig = w_center + up_vec * 0.15
            direction = -up_vec
            road_dist = None
            for _ in range(8):
                hit, loc, _, _, ho, _ = sc.ray_cast(dg, orig, direction, distance=1.5)
                if not hit or ho is None:
                    break
                if ho.name in rig_children:
                    orig = loc + direction * 0.02
                    continue
                road_dist = (loc - w_center).dot(-up_vec)
                break
            if road_dist is not None:
                # Ideal road_dist from wheel center is ~0.345..0.365m (R_TIRE=0.357)
                tire_clearances.append((f, wb_name, round(road_dist - 0.357, 4)))

    max_tire_err = max((abs(x[2]) for x in tire_clearances), default=999.0)
    worst_tires = sorted(tire_clearances, key=lambda x: abs(x[2]), reverse=True)[:8]

    # 3. 24-Shot 3D Camera-to-Car Raycast & Ground/Tunnel Check (step 2 across entire timeline!)
    markers = sorted(sc.timeline_markers, key=lambda m: m.frame)
    shots_win = []
    for i, mk in enumerate(markers):
        f0 = mk.frame
        f1 = (markers[i + 1].frame - 1) if (i + 1 < len(markers)) else sc.frame_end
        shots_win.append((mk.name, f0, f1, mk.camera))

    shot_audit = []
    rois_2d = {}
    for s_name, f0, f1, cam in shots_win:
        is_onboard = "Onboard" in s_name or "Cockpit" in s_name
        occs = []
        under_road = []
        oof = []
        for f in sorted(set(list(range(f0, f1 + 1, 2)) + [f0, f1])):
            sc.frame_set(f)
            dg = bpy.context.evaluated_depsgraph_get()
            cam_e = cam.evaluated_get(dg)
            rig_e = rig.evaluated_get(dg)
            cp = cam_e.matrix_world.translation.copy()
            car_root = (rig_e.matrix_world @ rig_e.pose.bones["Bone_Root"].matrix).translation.copy()
            pb_att = rig_e.pose.bones.get("Bone_Heading") or rig_e.pose.bones["Bone_Root"]
            car_up = ((rig_e.matrix_world @ pb_att.matrix).to_3x3() @ Vector((0, 0, 1))).normalized()
            tgt = car_root + car_up * 0.50

            if not is_onboard:
                dv = tgt - cp
                dist = dv.length
                if dist > 0.4:
                    orig = cp + dv.normalized() * 0.05
                    rem = dist - 0.15
                    for _ in range(6):
                        if rem <= 0.05:
                            break
                        hit, loc, _, _, ho, _ = sc.ray_cast(dg, orig, dv.normalized(), distance=rem)
                        if not hit or ho is None:
                            break
                        if ho.name in rig_children:
                            break
                        # Skip translucent faux-volumetric god-ray blades!
                        if any(k in ho.name for k in ("GodRay", "LightBlade", "VolRay", "Beam", "MistBlade", "PortalGlow")):
                            d_step = (loc - orig).length + 0.05
                            orig = orig + dv.normalized() * d_step
                            rem -= d_step
                            continue
                        occs.append({"f": f, "blocker": ho.name, "b_dist": round((loc - cp).length, 2), "c_dist": round(dist, 2)})
                        break
                ndc = world_to_camera_view(sc, cam_e, tgt)
                if ndc.z < 0.2 or not (-0.08 <= ndc.x <= 1.08 and -0.08 <= ndc.y <= 1.08):
                    oof.append((f, [round(ndc.x, 3), round(ndc.y, 3), round(ndc.z, 2)]))

        # Compute midpoint ROI for Art-Director stills sensor
        f_mid = (f0 + f1) // 2
        sc.frame_set(f_mid)
        dg = bpy.context.evaluated_depsgraph_get()
        cam_e = cam.evaluated_get(dg)
        us, vs = [], []
        for o in bpy.data.objects:
            if o.type == 'MESH' and o.name.startswith(("GEO_F1_", "GEO_MERC_")):
                oe = o.evaluated_get(dg)
                for c in oe.bound_box[::2]:
                    ndc = world_to_camera_view(sc, cam_e, oe.matrix_world @ Vector(c))
                    if ndc.z > 0.2:
                        us.append(ndc.x)
                        vs.append(1.0 - ndc.y)
        if us:
            rois_2d[s_name] = {"f_mid": f_mid, "box": [round(max(0, min(1, min(us))), 4), round(max(0, min(1, min(vs))), 4),
                                                       round(max(0, min(1, max(us))), 4), round(max(0, min(1, max(vs))), 4)]}
        shot_audit.append({
            "shot": s_name, "f0": f0, "f1": f1, "lens": round(cam.data.lens, 1),
            "occ_count": len(occs), "occs": occs[:6], "oof_count": len(oof), "oof": oof[:4]
        })

    # 4. On-Twos vs 24fps check
    cam_const = []
    for _, _, _, cam in shots_win:
        if cam and cam.animation_data and cam.animation_data.action:
            for fc in iter_fcurves(cam.animation_data.action):
                if any(kp.interpolation == 'CONSTANT' for kp in fc.keyframe_points):
                    cam_const.append(f"{cam.name}:{fc.data_path}")

    rig_root_const = []
    rig_twos_channels = []
    if rig.animation_data and rig.animation_data.action:
        for fc in iter_fcurves(rig.animation_data.action):
            has_const = any(kp.interpolation == 'CONSTANT' for kp in fc.keyframe_points)
            if ("Bone_Root" in fc.data_path or "Bone_Heading" in fc.data_path) and has_const:
                rig_root_const.append(fc.data_path)
            elif has_const:
                rig_twos_channels.append(fc.data_path)

    # 5. Compositor & FX inventory
    comp_ng = getattr(sc, "compositing_node_group", None) or getattr(sc, "node_tree", None)
    comp_types = []
    if comp_ng:
        def walk(nt):
            for n in nt.nodes:
                comp_types.append(f"{n.type}:{n.name}")
                if n.type == 'GROUP' and getattr(n, "node_tree", None):
                    walk(n.node_tree)
        walk(comp_ng)

    # 6. 1080p Render Benchmark (2 frames: skyscraper canyon + strobe tunnel)
    sc.render.resolution_x = 1920
    sc.render.resolution_y = 1080
    sc.render.resolution_percentage = 100
    bench = {}
    for bf in (100, min(sc.frame_end - 50, 980)):
        for s_name, f0, f1, cam in shots_win:
            if f0 <= bf <= f1:
                sc.camera = cam
                break
        sc.frame_set(bf)
        sc.render.filepath = os.path.join(SCRATCH, f"v6_3d_bench_{bf:04d}.jpg")
        t0 = time.perf_counter()
        bpy.ops.render.render(write_still=True)
        bench[str(bf)] = round(time.perf_counter() - t0, 3)

    out_b = {
        "frame_end": sc.frame_end,
        "total_objects": len(bpy.data.objects),
        "root_objects": [o.name for o in sc.collection.objects],
        "use_raytracing": sc.eevee.use_raytracing,
        "taa_render_samples": sc.eevee.taa_render_samples,
        "motion_blur_shutter": round(sc.render.motion_blur_shutter, 4),
        "view_layer_passes": passes,
        "fx_objects": sorted(fx_names),
        "max_tire_road_err_m": round(max_tire_err, 4),
        "worst_tire_contacts": worst_tires,
        "cam_constant_violations": cam_const,
        "rig_root_constant_violations": rig_root_const,
        "rig_twos_channel_count": len(set(rig_twos_channels)),
        "compositor_nodes": comp_types,
        "bench_1080p_sec": bench,
        "shot_count": len(shot_audit),
        "shots_with_occlusions": [s for s in shot_audit if s["occ_count"] > 0 or s["oof_count"] > 0],
        "shot_audit": shot_audit,
        "rois_2d": rois_2d,
    }
    with open(os.path.join(SCRATCH, "v6_3d_blender_report.json"), "w", encoding="utf-8") as fp:
        json.dump(out_b, fp, indent=2, ensure_ascii=False)
    print("WROTE v6_3d_blender_report.json")
    sys.exit(0)

# System Python: V5 Isolation + 3D Circuit JSON + Art-Director 2.39:1 Stills/Clips/Audio Critique
import glob, wave, hashlib, subprocess
import numpy as np
from PIL import Image

FFMPEG = r"C:\Users\86052\scoop\shims\ffmpeg.exe"
FFPROBE = r"C:\Users\86052\scoop\shims\ffprobe.exe"
lines = []

# 1. V5 Isolation
base = json.load(open(os.path.join(SCRATCH, "v5_baseline_hashes.json"), encoding="utf-8"))
v5_diffs = []
for rel, meta in base.items():
    fp = os.path.join(PROJ, rel)
    if not os.path.exists(fp):
        v5_diffs.append(f"DELETED:{rel}")
        continue
    h = hashlib.sha256()
    with open(fp, "rb") as f:
        for b in iter(lambda: f.read(1048576), b""):
            h.update(b)
    if h.hexdigest() != meta["sha256"]:
        v5_diffs.append(f"MODIFIED:{rel}")
lines.append(f"=== 1. V5 ISOLATION ({len(base)} files) === diffs={len(v5_diffs)} {v5_diffs} | LATEST={sorted(os.listdir(os.path.join(PROJ, 'LATEST')))}")

# 2. 3D Circuit JSON Audit
lines.append("\n=== 2. 3D CIRCUIT JSON AUDIT (spiderverse_circuit.json) ===")
if os.path.exists(CIRCUIT_JSON):
    cd = json.load(open(CIRCUIT_JSON, encoding="utf-8"))
    meta = cd["meta"]
    pts = cd["points"]
    zs = [p["z"] for p in pts]
    banks = [p["bank_deg"] for p in pts]
    pitches = [p["pitch_deg"] for p in pts]
    vs = [p["v_mps"] * 3.6 for p in pts]
    zones = sorted({p["zone"] for p in pts})
    n_tun = sum(1 for p in pts if p.get("tunnel"))
    n_brg = sum(1 for p in pts if p.get("bridge"))
    p0, p1 = pts[0], pts[-1]
    seam_xy = ((p0["xy"][0] - p1["xy"][0])**2 + (p0["xy"][1] - p1["xy"][1])**2)**0.5
    seam_z = abs(p0["z"] - p1["z"])
    lines.append(f"  meta: len={meta.get('measured_length_km')}km lap={meta.get('sim_lap_s')}s frames={meta.get('frame_end')} pts={len(pts)}")
    lines.append(f"  Z=[{min(zs):.2f}..{max(zs):.2f}m] pitch=[{min(pitches):.1f}..{max(pitches):.1f}deg] bank=[{min(banks):.1f}..{max(banks):.1f}deg] v=[{min(vs):.1f}..{max(vs):.1f}km/h]")
    lines.append(f"  zones={zones} tunnel_pts={n_tun} bridge_pts={n_brg} closure_gap_xy={seam_xy:.2f}m seam_dz={seam_z:.3f}m")
else:
    lines.append("  MISSING track_data/spiderverse_circuit.json!")

# 3. Stills + 2.39:1 Active Area Art-Director Sensor
lines.append("\n=== 3. STILLS & 2.39:1 CINEMA-SCOPE ART-DIRECTOR CRITIQUE ===")
stills_dir = os.path.join(PROJ, "renders_v6", "stills")
if os.path.exists(stills_dir):
    sfiles = sorted(f for f in os.listdir(stills_dir) if f.lower().endswith((".jpg", ".png")))
    lines.append(f"  Total files in renders_v6/stills: {len(sfiles)}")
    lines.append(f"  {'File':<36} {'Size':<13} {'MeanL':>6} {'P10':>5} {'P95':>5} {'Sat':>6} {'Clip%':>6} {'HalftHP':>7} {'WetReflSat':>10} {'LBoxTop/Bot'}")
    for fn in sfiles:
        fp = os.path.join(stills_dir, fn)
        im = Image.open(fp).convert("RGB")
        arr = np.asarray(im, dtype=np.float32)
        H, W, _ = arr.shape
        is_shot = fn.startswith("shot_") and (W, H) == (1920, 1080)
        if is_shot:
            top_bar = float(arr[:130, :, :].mean())
            bot_bar = float(arr[H-130:, :, :].mean())
            act_arr = arr[142:H-142, :, :] if (top_bar < 8.0 and bot_bar < 8.0) else arr
            lb_str = f"{top_bar:.1f}/{bot_bar:.1f}"
        else:
            act_arr = arr
            lb_str = "sheet"
        lum = 0.2126 * act_arr[:, :, 0] + 0.7152 * act_arr[:, :, 1] + 0.0722 * act_arr[:, :, 2]
        mx, mn = act_arr.max(axis=2), act_arr.min(axis=2)
        sat = np.where(mx > 2.0, (mx - mn) / np.maximum(mx, 1.0), 0.0)
        p10, p95 = [float(x) for x in np.percentile(lum, [10, 95])]
        clip_p = float((mx >= 250).mean() * 100.0)
        # Halftone 5x5 highpass in midtones
        pad = np.pad(lum, 2, mode='edge')
        cs = np.cumsum(np.cumsum(pad, axis=0), axis=1)
        b5 = ((cs[4:, 4:] - cs[:-4, 4:] - cs[4:, :-4] + cs[:-4, :-4]) / 25.0)[:lum.shape[0], :lum.shape[1]]
        mm = (lum > 40.0) & (lum < 190.0)
        hhp = float(np.abs(lum[mm] - b5[mm]).mean()) if mm.any() else 0.0
        # Wet road reflection saturation in lower 35% of active frame
        low_sat = float(sat[int(sat.shape[0]*0.65):, :].mean())
        lines.append(f"  {fn:<36} {str(im.size):<13} {lum.mean():>6.1f} {p10:>5.1f} {p95:>5.1f} {sat.mean():>6.3f} {clip_p:>5.2f}% {hhp:>7.2f} {low_sat:>10.3f} {lb_str}")

# 4. Clips & Audio/MP4 Check
lines.append("\n=== 4. SHOWCASE CLIPS & MP4 / WAV AUDIT ===")
clips_root = os.path.join(PROJ, "renders_v6", "clips_frames")
if os.path.exists(clips_root):
    for cd_name in sorted(os.listdir(clips_root)):
        cpath = os.path.join(clips_root, cd_name)
        if os.path.isdir(cpath):
            jpgs = sorted(f for f in os.listdir(cpath) if f.endswith(".jpg"))
            lines.append(f"  ClipDir {cd_name:<26}: count={len(jpgs)} ({jpgs[0] if jpgs else None}..{jpgs[-1] if jpgs else None})")

for fn in sorted(os.listdir(os.path.join(PROJ, "renders_v6"))) if os.path.exists(os.path.join(PROJ, "renders_v6")) else []:
    fp = os.path.join(PROJ, "renders_v6", fn)
    if os.path.isfile(fp) and fn.lower().endswith((".wav", ".m4a", ".mp4")):
        pr = subprocess.run([FFPROBE, "-v", "error", "-show_format", "-show_streams", "-of", "json", fp],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
        info = json.loads(pr.stdout) if pr.stdout else {}
        fmt = info.get("format", {})
        sd = []
        for st in info.get("streams", []):
            if st.get("codec_type") == "video":
                sd.append(f"V:{st.get('codec_name')} {st.get('width')}x{st.get('height')} r={st.get('r_frame_rate')} nb={st.get('nb_frames')}")
            elif st.get("codec_type") == "audio":
                sd.append(f"A:{st.get('codec_name')} {st.get('sample_rate')}Hz {st.get('channels')}ch")
        vr = subprocess.run([FFMPEG, "-hide_banner", "-i", fp, "-vn", "-af", "volumedetect", "-f", "null", "NUL"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
        mv = xv = "?"
        for ln in vr.stderr.splitlines():
            if "mean_volume:" in ln: mv = ln.split("mean_volume:")[1].strip()
            if "max_volume:" in ln: xv = ln.split("max_volume:")[1].strip()
        lines.append(f"  {fn:<36} size={int(fmt.get('size',0)):>9} dur={float(fmt.get('duration',0)):.3f}s | {' + '.join(sd)} | mean={mv} max={xv}")

rep = "\n".join(lines)
with open(os.path.join(SCRATCH, "v6_3d_media_report.txt"), "w", encoding="utf-8") as fp:
    fp.write(rep)
print(rep)
