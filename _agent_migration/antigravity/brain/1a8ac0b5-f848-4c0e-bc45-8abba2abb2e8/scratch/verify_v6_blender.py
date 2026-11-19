# -*- coding: utf-8 -*-
"""
Read-only V6 Spider-Verse Headless Blender Verification Suite
Checks v6_stage_lookdev.blend and v6_stage_anim_sv.blend:
- EEVEE raytracing=False, motion_blur_shutter (~0.07)
- sv_dimension 3-Act evaluation (Act I=0.0, Act II=1.0, Act III=2.0)
- NG_SV_ComicSurface (ShaderToRGB, Window coords, Rim LayerWeight)
- 3D Inverted-Hull Ink Outlines (Solidify + MAT_SV_InkOutline backface culling)
- V6_09_ComicFX collection (aero vortex ribbons + wheel smear arcs, 0 camera obstructions)
- Safe On-Twos: Bone_Root/Bone_Heading/Cameras stay 24fps LINEAR; secondary motion stepped on Twos (CONSTANT)
- Multi-pass Compositor (ViewLayer passes + Kuwahara + Filter + CMYK Separate/Translate/Combine)
- 1080p CPU single-frame render speed benchmark (to scratch/ ONLY)
"""
import bpy
import os
import json
import time
from mathutils import Vector

PROJ = r"D:\项目session\blender-supercar"
SCRATCH = r"C:\Users\86052\.gemini\antigravity\brain\1a8ac0b5-f848-4c0e-bc45-8abba2abb2e8\scratch"
LOOKDEV_BLEND = os.path.join(PROJ, "v6_spiderverse", "v6_stage_lookdev.blend")
ANIM_SV_BLEND = os.path.join(PROJ, "v6_spiderverse", "v6_stage_anim_sv.blend")
OUT_JSON = os.path.join(SCRATCH, "v6_blender_report.json")

def iter_fcurves(action):
    fcs = list(getattr(action, "fcurves", []) or [])
    if fcs:
        return fcs
    for layer in getattr(action, "layers", []) or []:
        for strip in getattr(layer, "strips", []) or []:
            for cb in getattr(strip, "channelbags", []) or []:
                fcs.extend(cb.fcurves)
    return fcs

report = {}

# 1. Check lookdev blend exists & basic stats
if os.path.exists(LOOKDEV_BLEND):
    bpy.ops.wm.open_mainfile(filepath=LOOKDEV_BLEND)
    sc_ld = bpy.context.scene
    report["lookdev_blend"] = {
        "exists": True,
        "total_objects": len(bpy.data.objects),
        "use_raytracing": sc_ld.eevee.use_raytracing,
        "has_sv_dimension": "sv_dimension" in sc_ld,
        "has_NG_SV_ComicSurface": "NG_SV_ComicSurface" in bpy.data.node_groups,
        "has_V6_09_ComicFX": "V6_09_ComicFX" in bpy.data.collections,
    }
else:
    report["lookdev_blend"] = {"exists": False}

# 2. Deep audit of v6_stage_anim_sv.blend
bpy.ops.wm.open_mainfile(filepath=ANIM_SV_BLEND)
scene = bpy.context.scene
rig = bpy.data.objects["RIG_F1_Race"]

# 2a. Render & ViewLayer settings
vl = scene.view_layers[0]
vl_passes = {
    "use_pass_normal": getattr(vl, "use_pass_normal", False),
    "use_pass_mist": getattr(vl, "use_pass_mist", False),
    "use_pass_z": getattr(vl, "use_pass_z", False),
    "use_pass_emit": getattr(vl, "use_pass_emit", False),
    "use_pass_cryptomatte_object": getattr(vl, "use_pass_cryptomatte_object", False),
}

# 2b. NPR Shader NodeGroup & Outline check
ng_comic = bpy.data.node_groups.get("NG_SV_ComicSurface")
ng_comic_node_types = sorted({n.type for n in ng_comic.nodes}) if ng_comic else []

ink_mat = bpy.data.materials.get("MAT_SV_InkOutline")
ink_info = None
if ink_mat:
    ink_info = {
        "use_backface_culling": getattr(ink_mat, "use_backface_culling", None),
        "use_backface_culling_shadow": getattr(ink_mat, "use_backface_culling_shadow", None),
    }
solidify_objs = []
for o in bpy.data.objects:
    for m in o.modifiers:
        if m.type == 'SOLIDIFY' and m.use_flip_normals:
            solidify_objs.append(o.name)

# 2c. V6_09_ComicFX check
fx_coll = bpy.data.collections.get("V6_09_ComicFX")
fx_objs = [{"name": o.name, "parent": o.parent.name if o.parent else None, "parent_bone": o.parent_bone} for o in fx_coll.all_objects] if fx_coll else []

# 2d. 3-Act sv_dimension evaluation
sv_dim_samples = {}
for label, f in (("Act1_f100", 100), ("Act2_f1200", 1200), ("Act3_f1800", 1800)):
    scene.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    sc_e = scene.evaluated_get(dg)
    sv_dim_samples[label] = round(float(sc_e.get("sv_dimension", -999.0)), 3)

# 2e. Safe On-Twos (12fps) vs Smooth 24fps World/Cam check
rig_fc_interp = {}
if rig.animation_data and rig.animation_data.action:
    for fc in iter_fcurves(rig.animation_data.action):
        interps = sorted({kp.interpolation for kp in fc.keyframe_points})
        # Check step spacing on CONSTANT fcurves
        xs = [kp.co.x for kp in fc.keyframe_points[:10]]
        avg_dx = round((xs[-1] - xs[0]) / max(1, len(xs) - 1), 2) if len(xs) > 1 else 0
        rig_fc_interp[f"{fc.data_path}[{fc.array_index}]"] = {"interps": interps, "sample_dx": avg_dx, "n_keys": len(fc.keyframe_points)}

cam_non_linear = []
for o in bpy.data.objects:
    if o.type == 'CAMERA' and o.name.startswith("Cam_S"):
        if o.animation_data and o.animation_data.action:
            for fc in iter_fcurves(o.animation_data.action):
                if any(kp.interpolation == 'CONSTANT' for kp in fc.keyframe_points):
                    cam_non_linear.append(f"{o.name}:{fc.data_path}")

# 2f. Compositor Node Tree inspection
comp_ng = getattr(scene, "compositing_node_group", None) or getattr(scene, "node_tree", None)
comp_nodes = []
if comp_ng:
    def collect_nodes(nt, prefix=""):
        for n in nt.nodes:
            comp_nodes.append(f"{prefix}{n.type}:{n.name}")
            if n.type == 'GROUP' and getattr(n, "node_tree", None):
                collect_nodes(n.node_tree, prefix=f"{n.name}/")
    collect_nodes(comp_ng)

# 2g. 26-Shot Camera LOS check (verify V6_09_ComicFX / outlines never block cameras!)
markers = sorted(scene.timeline_markers, key=lambda m: m.frame)
shots_windows = []
for i, mk in enumerate(markers):
    f0 = mk.frame
    f1 = (markers[i + 1].frame - 1) if (i + 1 < len(markers)) else scene.frame_end
    shots_windows.append((mk.name, f0, f1, mk.camera))

car_and_fx = {o.name for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith("V5_")}
fx_names = {o["name"] for o in fx_objs}
occ_hits = []
onboard_fx_hits = []
for s_name, f0, f1, cam in shots_windows:
    is_onboard = "Onboard" in s_name
    for f in range(f0, f1 + 1, 8):
        scene.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        cam_e = cam.evaluated_get(dg)
        rig_e = rig.evaluated_get(dg)
        cp = cam_e.matrix_world.translation.copy()
        if not is_onboard:
            rp = (rig_e.matrix_world @ rig_e.pose.bones["Bone_Root"].matrix).translation + Vector((0, 0, 0.5))
            dv = rp - cp
            hit, loc, _, _, ho, _ = scene.ray_cast(dg, cp + dv.normalized() * 0.05, dv.normalized(), distance=dv.length - 0.15)
            if hit and ho and ho.name not in car_and_fx:
                occ_hits.append({"shot": s_name, "f": f, "blocker": ho.name})
        else:
            cam_fwd = (cam_e.matrix_world.to_3x3() @ Vector((0, 0, -1))).normalized()
            hit, loc, _, _, ho, _ = scene.ray_cast(dg, cp + cam_fwd * 0.1, cam_fwd, distance=3.0)
            if hit and ho and ho.name in fx_names:
                onboard_fx_hits.append({"shot": s_name, "f": f, "fx_blocker": ho.name, "dist": round((loc - cp).length, 2)})

# 2h. 1080p CPU Render Speed Benchmark (warm frame to scratch/)
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
bench_sec = {}
for bf in (100, 1320):
    for s_name, f0, f1, cam in shots_windows:
        if f0 <= bf <= f1:
            scene.camera = cam
            break
    scene.frame_set(bf)
    scene.render.filepath = os.path.join(SCRATCH, f"v6_bench_{bf:04d}.jpg")
    t0 = time.perf_counter()
    bpy.ops.render.render(write_still=True)
    bench_sec[str(bf)] = round(time.perf_counter() - t0, 3)

report["anim_sv_blend"] = {
    "total_objects": len(bpy.data.objects),
    "root_objects": [o.name for o in scene.collection.objects],
    "use_raytracing": scene.eevee.use_raytracing,
    "motion_blur_shutter": round(scene.render.motion_blur_shutter, 4),
    "view_layer_passes": vl_passes,
    "ng_comic_node_types": ng_comic_node_types,
    "ink_outline_mat": ink_info,
    "solidify_outline_obj_count": len(solidify_objs),
    "solidify_sample": solidify_objs[:12],
    "comic_fx_count": len(fx_objs),
    "comic_fx_objs": fx_objs,
    "sv_dimension_3acts": sv_dim_samples,
    "rig_fcurves": rig_fc_interp,
    "cam_constant_violations": cam_non_linear,
    "scene_use_nodes": scene.use_nodes,
    "compositor_node_count": len(comp_nodes),
    "compositor_nodes": comp_nodes,
    "occ_hits": occ_hits,
    "onboard_fx_hits": onboard_fx_hits,
    "bench_1080p_sec": bench_sec,
}

with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)
print("V6_BLENDER_REPORT_WRITTEN:", OUT_JSON)
