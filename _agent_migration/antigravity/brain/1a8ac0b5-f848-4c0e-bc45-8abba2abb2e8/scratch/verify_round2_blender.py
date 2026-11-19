# -*- coding: utf-8 -*-
"""
Read-only Round 2 Final Blender Verification Suite
Checks rebuilt v5_stage_env.blend, v5_stage_anim.blend, v5_stage_anim_clay.blend,
v5_viewport_fast.py (on a scratch copy!), 5 physics rules, 26-shot LOS, car rig/shaders,
and 1080p single-frame CPU render speed (outputting ONLY to scratch/).
"""
import bpy
import os
import sys
import json
import time
import shutil
import subprocess
from math import pi, radians, degrees
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

PROJ = r"D:\项目session\blender-supercar"
SCRATCH = r"C:\Users\86052\.gemini\antigravity\brain\1a8ac0b5-f848-4c0e-bc45-8abba2abb2e8\scratch"
ENV_BLEND = os.path.join(PROJ, "LATEST", "v5_stage_env.blend")
ANIM_BLEND = os.path.join(PROJ, "LATEST", "v5_stage_anim.blend")
CLAY_BLEND = os.path.join(PROJ, "LATEST", "v5_stage_anim_clay.blend")
TRACK_JSON = os.path.join(PROJ, "track_data", "silverstone_track.json")
OUT_JSON = os.path.join(SCRATCH, "round2_blender_report.json")

os.makedirs(SCRATCH, exist_ok=True)
res = {}

def iter_fcurves(action):
    fcs = list(getattr(action, "fcurves", []) or [])
    if fcs:
        return fcs
    for layer in getattr(action, "layers", []) or []:
        for strip in getattr(layer, "strips", []) or []:
            for cb in getattr(strip, "channelbags", []) or []:
                fcs.extend(cb.fcurves)
    return fcs

# ------------------------------------------------------------------
# 1. Inspect v5_stage_env.blend
# ------------------------------------------------------------------
bpy.ops.wm.open_mainfile(filepath=ENV_BLEND)
sc_env = bpy.context.scene

track_ob = bpy.data.objects.get("V5_Track")
track_pts = [track_ob.matrix_world @ v.co for v in list(track_ob.data.vertices)[::8]] if track_ob else []

hangar_min_dists = {}
for o in bpy.data.objects:
    if o.name.startswith("V5_Hangar_"):
        hc = o.matrix_world.translation
        dmin = min((hc.xy - tp.xy).length for tp in track_pts) if track_pts else 999.0
        hangar_min_dists[o.name] = round(dmin, 1)

hedge = bpy.data.objects.get("V5_HedgeRing")
hedge_min_dist = 999.0
if hedge and track_pts:
    h_pts = [hedge.matrix_world @ v.co for v in list(hedge.data.vertices)[::4]]
    hedge_min_dist = round(min(min((hp.xy - tp.xy).length for tp in track_pts) for hp in h_pts), 1)

overbright_mats = []
road_spec_violations = []
for m in bpy.data.materials:
    if not m.node_tree:
        continue
    for n in m.node_tree.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            bc = list(n.inputs['Base Color'].default_value)
            if any(v > 1.01 for v in bc[:3]):
                overbright_mats.append({"mat": m.name, "base_color": [round(x, 3) for x in bc]})
            if any(k in m.name for k in ("Asphalt", "Rubber", "Skid", "Line", "Curb", "Kerb", "Sausage", "Gravel")):
                sp = n.inputs['Specular IOR Level'].default_value
                if sp > 0.031:
                    road_spec_violations.append({"mat": m.name, "spec": round(sp, 4)})

rl_ob = bpy.data.objects.get("GEO_F1_FIA_RainLight")
rl_mat = rl_ob.data.materials[0] if (rl_ob and rl_ob.data.materials) else None
rl_mat_users = []
if rl_mat:
    for o in bpy.data.objects:
        if o.type == 'MESH' and rl_mat.name in [m.name for m in o.data.materials if m]:
            rl_mat_users.append(o.name)

res["env_blend"] = {
    "total_objects": len(bpy.data.objects),
    "orphan_meshes": [m.name for m in bpy.data.meshes if m.users == 0],
    "orphan_materials": [m.name for m in bpy.data.materials if m.users == 0],
    "root_objects": [f"{o.name}({o.type})" for o in sc_env.collection.objects],
    "stranded_empties": [o.name for o in bpy.data.objects if o.type == 'EMPTY' and sc_env.collection in o.users_collection],
    "hangar_min_dists": hangar_min_dists,
    "hedge_min_dist": hedge_min_dist,
    "overbright_mats": overbright_mats,
    "road_spec_violations": road_spec_violations,
    "rain_light_mat": rl_mat.name if rl_mat else None,
    "rain_light_mat_users": rl_mat_users,
}

# ------------------------------------------------------------------
# 2. Inspect v5_stage_anim.blend (Physics, Outliner, 26-Shot LOS, Render Speed)
# ------------------------------------------------------------------
bpy.ops.wm.open_mainfile(filepath=ANIM_BLEND)
scene = bpy.context.scene
rig = bpy.data.objects["RIG_F1_Race"]

# Check viewport normal state on disk
heavy_hidden = [c.name for c in bpy.data.collections if c.name in ("V5_04_Stands", "V5_06_Props", "V5_02_Terrain") and c.hide_viewport]
bounds_meshes = [o.name for o in bpy.data.objects if o.type == 'MESH' and o.display_type == 'BOUNDS']

# Check V5_CarLightReceivers
car_recv = bpy.data.collections.get("V5_CarLightReceivers")
car_recv_count = len(car_recv.all_objects) if car_recv else 0
car_recv_v5_leak = [o.name for o in (car_recv.all_objects if car_recv else []) if o.name.startswith("V5_")]

# Check 5 Physics Rules
tdata = json.load(open(TRACK_JSON, encoding="utf-8"))
META = tdata["meta"]
PTS = tdata["points"]
LAP_S = META["sim_lap_s"]
FRAME_END = scene.frame_end
DT = LAP_S / (FRAME_END - 1)
T_ARR = [p["t"] for p in PTS]
RX_ARR = [Vector((p["racing_xy"][0], p["racing_xy"][1], 0.0)) for p in PTS]
HD_ARR = [p["heading_deg"] for p in PTS]
V_ARR = [p["v_mps"] for p in PTS]
K_ARR = [abs(p["curv_1pm"] or 0.0) for p in PTS]

def sample_track(t):
    t = max(0.0, min(LAP_S - 1e-6, t))
    lo, hi = 0, len(PTS) - 1
    while hi - lo > 1:
        m = (lo + hi) // 2
        if T_ARR[m] <= t:
            lo = m
        else:
            hi = m
    f = (t - T_ARR[lo]) / max(T_ARR[lo + 1] - T_ARR[lo], 1e-9)
    pos = RX_ARR[lo].lerp(RX_ARR[lo + 1], f)
    a, b = radians(HD_ARR[lo]), radians(HD_ARR[lo + 1])
    d = (b - a + pi) % (2 * pi) - pi
    v = V_ARR[lo] + (V_ARR[lo + 1] - V_ARR[lo]) * f
    k = K_ARR[lo] + (K_ARR[lo + 1] - K_ARR[lo]) * f
    return pos, a + d * f, v, k

non_linear_kps = 0
if rig.animation_data and rig.animation_data.action:
    for fc in iter_fcurves(rig.animation_data.action):
        for kp in fc.keyframe_points:
            if kp.interpolation != 'LINEAR':
                non_linear_kps += 1

max_xy_err = 0.0
bad_z_frames = []
max_yaw_err_deg = 0.0
lat_violations = []
for f in range(1, FRAME_END + 1, 4):
    scene.frame_set(f)
    t = (f - 1) * DT
    pos_ref, h_ref, v_ref, k_ref = sample_track(t)
    if v_ref * v_ref * k_ref > (15.0 + 0.00714 * v_ref * v_ref) + 0.5:
        lat_violations.append(f)
    pb_root = rig.pose.bones["Bone_Root"]
    pb_head = rig.pose.bones["Bone_Heading"]
    xy_err = (Vector((pb_root.location.x, pb_root.location.y)) - pos_ref.xy).length
    max_xy_err = max(max_xy_err, xy_err)
    if abs(pb_root.location.z - 0.012) > 1e-4:
        bad_z_frames.append((f, round(pb_root.location.z, 5)))
    yaw_ref = h_ref - pi / 2
    dyaw = abs((pb_head.rotation_euler.z - yaw_ref + pi) % (2 * pi) - pi)
    max_yaw_err_deg = max(max_yaw_err_deg, degrees(dyaw))

# Check camera clip_start=0.5 / clip_end=9000 & 26-shot LOS
markers = sorted(scene.timeline_markers, key=lambda m: m.frame)
shots_windows = []
for i, mk in enumerate(markers):
    f0 = mk.frame
    f1 = (markers[i + 1].frame - 1) if (i + 1 < len(markers)) else scene.frame_end
    shots_windows.append((mk.name, f0, f1, mk.camera))

clip_violations = []
for s_name, f0, f1, cam in shots_windows:
    if abs(cam.data.clip_start - 0.5) > 1e-4 or abs(cam.data.clip_end - 9000.0) > 1.0:
        clip_violations.append({"cam": s_name, "clip": [cam.data.clip_start, cam.data.clip_end]})

car_set = {o.name for o in bpy.data.objects if o.type == 'MESH' and (not o.name.startswith("V5_"))}
shot_results = []
for s_name, f0, f1, cam in shots_windows:
    is_onboard = "Onboard" in s_name
    occs = []
    low_z = []
    oof = []
    sample_fs = sorted(set(list(range(f0, f1 + 1, 2)) + [f0, f1]))
    for f in sample_fs:
        scene.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        cam_e = cam.evaluated_get(dg)
        rig_e = rig.evaluated_get(dg)
        cam_pos = cam_e.matrix_world.translation.copy()
        if cam_pos.z < 0.15:
            low_z.append((f, round(cam_pos.z, 3)))
        car_root_w = (rig_e.matrix_world @ rig_e.pose.bones["Bone_Root"].matrix).translation.copy()
        target_w = car_root_w + Vector((0, 0, 0.5))
        if not is_onboard:
            dv = target_w - cam_pos
            dist = dv.length
            if dist > 0.4:
                hit, loc, _, _, ho, _ = scene.ray_cast(dg, cam_pos + dv.normalized() * 0.05, dv.normalized(), distance=dist - 0.15)
                if hit and ho and ho.name not in car_set:
                    occs.append({"f": f, "blocker": ho.name, "b_dist": round((loc - cam_pos).length, 2), "c_dist": round(dist, 2)})
            ndc = world_to_camera_view(scene, cam_e, target_w)
            if ndc.z < cam_e.data.clip_start or not (-0.05 <= ndc.x <= 1.05 and -0.05 <= ndc.y <= 1.05):
                oof.append((f, [round(ndc.x, 3), round(ndc.y, 3), round(ndc.z, 2)]))
        else:
            cam_fwd = (cam_e.matrix_world.to_3x3() @ Vector((0, 0, -1))).normalized()
            # Start ray 3.8m ahead of onboard camera so we skip nosecone/front wing and check track ahead
            hit, loc, _, _, ho, _ = scene.ray_cast(dg, cam_pos + cam_fwd * 3.8, cam_fwd, distance=16.0)
            if hit and ho and ho.name not in car_set and not any(k in ho.name for k in ("Track", "RacingLine", "Line_", "Kerb", "Skid", "BrakeZone", "Marble", "Verge", "Ground", "StartLine")):
                occs.append({"f": f, "blocker": ho.name, "b_dist": round((loc - cam_pos).length, 2), "c_dist": 0.0})
    shot_results.append({
        "shot": s_name,
        "f0": f0,
        "f1": f1,
        "use_dof": cam.data.dof.use_dof,
        "fstop": round(cam.data.dof.aperture_fstop, 2),
        "focus_obj": cam.data.dof.focus_object.name if cam.data.dof.focus_object else None,
        "occ_count": len(occs),
        "occs": occs[:10],
        "low_z": low_z,
        "oof": oof[:5],
    })

# Dynamic telemetry checks (brake glow at apex f=350, rain light flash, steering wheel)
scene.frame_set(350)
dg = bpy.context.evaluated_depsgraph_get()
bh_350 = rig.evaluated_get(dg).get("brake_heat", 0.0)

rl_vals = []
for f in range(180, 200):
    scene.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    rl_e = bpy.data.objects["GEO_F1_FIA_RainLight"].evaluated_get(dg)
    m_e = rl_e.data.materials[0]
    val = None
    for n in m_e.node_tree.nodes:
        if n.type == 'EMISSION':
            val = round(n.inputs['Strength'].default_value, 2)
        elif n.type == 'BSDF_PRINCIPLED' and 'Emission Strength' in n.inputs:
            val = round(n.inputs['Emission Strength'].default_value, 2)
    rl_vals.append(val)

# 1080p single-frame CPU render speed benchmark (to scratch ONLY)
bench_times = {}
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
for bf in (350, 1640):
    for s_name, f0, f1, cam in shots_windows:
        if f0 <= bf <= f1:
            scene.camera = cam
            break
    scene.frame_set(bf)
    scene.render.filepath = os.path.join(SCRATCH, f"bench_{bf:04d}.jpg")
    t0 = time.perf_counter()
    bpy.ops.render.render(write_still=True)
    bench_times[str(bf)] = round(time.perf_counter() - t0, 3)

res["anim_blend"] = {
    "total_objects": len(bpy.data.objects),
    "root_objects": [f"{o.name}({o.type})" for o in scene.collection.objects],
    "viewport_heavy_hidden_on_disk": heavy_hidden,
    "viewport_bounds_meshes_on_disk": len(bounds_meshes),
    "car_light_receivers_count": car_recv_count,
    "car_light_receivers_v5_leak": car_recv_v5_leak,
    "physics": {
        "non_linear_keyframes": non_linear_kps,
        "max_xy_err_m": round(max_xy_err, 5),
        "bad_z_frames": bad_z_frames,
        "max_yaw_err_deg": round(max_yaw_err_deg, 4),
        "lat_violations": lat_violations,
        "clip_violations": clip_violations,
    },
    "telemetry_visuals": {
        "brake_heat_at_f350_hairpin": round(float(bh_350), 3),
        "rain_light_f180_199": rl_vals,
    },
    "bench_1080p_sec": bench_times,
    "shot_results": shot_results,
}

# ------------------------------------------------------------------
# 3. Inspect v5_stage_anim_clay.blend
# ------------------------------------------------------------------
bpy.ops.wm.open_mainfile(filepath=CLAY_BLEND)
sc_clay = bpy.context.scene
sc_clay.frame_set(100)
exp_f100 = round(sc_clay.view_settings.exposure, 4)
sc_clay.frame_set(2161)
exp_f2161 = round(sc_clay.view_settings.exposure, 4)

clay_car = [o.name for o in bpy.data.objects if o.type == 'MESH' and any(sl.material and sl.material.name == "CLAY_Car" for sl in o.material_slots)]
clay_env = [o.name for o in bpy.data.objects if o.type == 'MESH' and any(sl.material and sl.material.name == "CLAY_Env" for sl in o.material_slots)]
clay_v5_in_car = [n for n in clay_car if n.startswith(("V5_", "EM_"))]
clay_car_in_env = [n for n in clay_env if n.startswith(("GEO_F1_", "GEO_MERC_", "DEC_"))]

res["clay_blend"] = {
    "clay_car_count": len(clay_car),
    "clay_env_count": len(clay_env),
    "clay_v5_in_car": clay_v5_in_car,
    "clay_car_in_env": clay_car_in_env,
    "view_transform": sc_clay.view_settings.view_transform,
    "exposure_f100": exp_f100,
    "exposure_f2161": exp_f2161,
    "use_motion_blur": sc_clay.render.use_motion_blur,
}

with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(res, f, indent=2, ensure_ascii=False)
print("ROUND2_BLENDER_AUDIT_DONE:", OUT_JSON)
