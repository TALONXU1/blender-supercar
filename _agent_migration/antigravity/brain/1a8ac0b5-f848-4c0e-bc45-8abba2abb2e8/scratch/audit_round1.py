# -*- coding: utf-8 -*-
"""
Read-only Round 1 Baseline Audit for blender-supercar
Writes JSON + text report ONLY to scratch directory. Never saves or modifies any project file.
"""
import bpy
import os
import sys
import json
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

PROJ = r"D:\项目session\blender-supercar"
ANIM_BLEND = os.path.join(PROJ, "LATEST", "v5_stage_anim.blend")
CLAY_BLEND = os.path.join(PROJ, "LATEST", "v5_stage_anim_clay.blend")
ENV_BLEND = os.path.join(PROJ, "LATEST", "v5_stage_env.blend")
OUT_JSON = r"C:\Users\86052\.gemini\antigravity\brain\1a8ac0b5-f848-4c0e-bc45-8abba2abb2e8\scratch\audit_round1_report.json"

report = {}

# ==============================================================================
# PART 1: Inspect v5_stage_env.blend (Outliner hygiene right out of v5_env.py)
# ==============================================================================
bpy.ops.wm.open_mainfile(filepath=ENV_BLEND)
sc_env = bpy.context.scene
env_root_objs = [f"{o.name} ({o.type})" for o in sc_env.collection.objects]
env_colls = {}
for c in bpy.data.collections:
    env_colls[c.name] = {
        "direct_count": len(c.objects),
        "all_count": len(c.all_objects),
        "sample_objs": [o.name for o in list(c.objects)[:8]],
    }
env_empties = []
for o in bpy.data.objects:
    if o.type == 'EMPTY':
        env_empties.append({
            "name": o.name,
            "collections": [c.name for c in o.users_collection],
            "children_count": len(o.children),
            "parent": o.parent.name if o.parent else None,
        })
report["env_blend"] = {
    "total_objects": len(bpy.data.objects),
    "total_meshes": len(bpy.data.meshes),
    "orphan_meshes": [m.name for m in bpy.data.meshes if m.users == 0],
    "orphan_materials": [m.name for m in bpy.data.materials if m.users == 0],
    "root_scene_collection_objects": env_root_objs,
    "collections": env_colls,
    "empties": env_empties,
}

# ==============================================================================
# PART 2: Inspect v5_stage_anim.blend
# ==============================================================================
bpy.ops.wm.open_mainfile(filepath=ANIM_BLEND)
scene = bpy.context.scene

# 2a. Outliner & Collections
anim_root_objs = [f"{o.name} ({o.type})" for o in scene.collection.objects]
anim_colls = {}
for c in bpy.data.collections:
    in_scene_tree = any(c.name == ch.name for ch in scene.collection.children_recursive)
    anim_colls[c.name] = {
        "in_scene_tree": in_scene_tree,
        "direct_count": len(c.objects),
        "all_count": len(c.all_objects),
        "sample_objs": [o.name for o in list(c.objects)[:10]],
    }

# Orphan / broken links / textures / material sanity
orphan_meshes = [m.name for m in bpy.data.meshes if m.users == 0]
orphan_mats = [m.name for m in bpy.data.materials if m.users == 0]
missing_images = []
all_images = []
for img in bpy.data.images:
    if img.name in ("Render Result", "Viewer Node"):
        continue
    fp = bpy.path.abspath(img.filepath) if img.filepath else ""
    exists = os.path.exists(fp) if fp else bool(img.packed_file)
    all_images.append({
        "name": img.name,
        "filepath": fp,
        "packed": bool(img.packed_file),
        "exists": exists,
        "size": list(img.size),
    })
    if not exists:
        missing_images.append(img.name)

broken_mat_slots = []
for o in bpy.data.objects:
    if o.type == 'MESH':
        if len(o.material_slots) == 0:
            broken_mat_slots.append(f"{o.name}: 0 material slots")
        for idx, sl in enumerate(o.material_slots):
            if sl.material is None:
                broken_mat_slots.append(f"{o.name}: slot {idx} is None")

overbright_mats = []
road_spec_violations = []
for m in bpy.data.materials:
    if not m.use_nodes or not m.node_tree:
        continue
    for n in m.node_tree.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            bc = list(n.inputs['Base Color'].default_value)
            if any(v > 1.01 for v in bc[:3]):
                overbright_mats.append({"mat": m.name, "base_color": bc})
            if any(k in m.name for k in ("Asphalt", "Rubber", "Line", "Curb", "Kerb", "Gravel")):
                sp = n.inputs['Specular IOR Level'].default_value
                if sp > 0.031:
                    road_spec_violations.append({"mat": m.name, "specular_ior_level": sp})

# Check V5_CarLightReceivers specifically
car_recv_coll = bpy.data.collections.get("V5_CarLightReceivers")
car_recv_objs = [o.name for o in car_recv_coll.objects] if car_recv_coll else []

# 2b. Car Rig & Shader Inspection
rig = bpy.data.objects.get("RIG_F1_Race")
rig_info = {}
if rig and rig.type == 'ARMATURE':
    bones_info = []
    for pb in rig.pose.bones:
        bones_info.append({
            "name": pb.name,
            "parent": pb.parent.name if pb.parent else None,
            "head_rest": [round(x, 4) for x in rig.data.bones[pb.name].head_local],
            "tail_rest": [round(x, 4) for x in rig.data.bones[pb.name].tail_local],
            "rotation_mode": pb.rotation_mode,
            "constraints": [c.type for c in pb.constraints],
        })
    drivers_info = []
    if rig.animation_data and rig.animation_data.drivers:
        for drv in rig.animation_data.drivers:
            vars_list = []
            for v in drv.driver.variables:
                t0 = v.targets[0] if v.targets else None
                vars_list.append({
                    "name": v.name,
                    "type": v.type,
                    "id": t0.id.name if (t0 and t0.id) else None,
                    "data_path": t0.data_path if t0 else None,
                })
            drivers_info.append({
                "data_path": drv.data_path,
                "array_index": drv.array_index,
                "expression": drv.driver.expression,
                "vars": vars_list,
            })
    rig_info = {
        "custom_props": {k: rig[k] for k in rig.keys() if not k.startswith("_")},
        "bones": bones_info,
        "drivers": drivers_info,
    }

# Also check drivers on ALL objects/materials/meshes
other_drivers = []
for datablock_group, label in ((bpy.data.objects, "OBJ"), (bpy.data.materials, "MAT"), (bpy.data.scenes, "SCN")):
    for db in datablock_group:
        if db == rig:
            continue
        ad = getattr(db, "animation_data", None)
        if ad and ad.drivers:
            for drv in ad.drivers:
                other_drivers.append({"owner": f"{label}:{db.name}", "path": drv.data_path, "expr": drv.driver.expression})
        nt = getattr(db, "node_tree", None)
        if nt and nt.animation_data and nt.animation_data.drivers:
            for drv in nt.animation_data.drivers:
                other_drivers.append({"owner": f"{label}_NT:{db.name}", "path": drv.data_path, "expr": drv.driver.expression})

car_meshes = []
non_v5_objects = []
for o in sorted(bpy.data.objects, key=lambda x: x.name):
    if not o.name.startswith("V5_") and not o.name.startswith("Cam_S") and not o.name.startswith("LGT_V5"):
        non_v5_objects.append({
            "name": o.name,
            "type": o.type,
            "collections": [c.name for c in o.users_collection],
            "parent": o.parent.name if o.parent else None,
            "parent_type": o.parent_type,
            "parent_bone": o.parent_bone,
        })
        if o.type == 'MESH':
            mats_detail = []
            for sl in o.material_slots:
                m = sl.material
                if not m:
                    mats_detail.append({"name": None})
                    continue
                md = {"name": m.name, "nodes": []}
                if m.use_nodes and m.node_tree:
                    for n in m.node_tree.nodes:
                        nd = {"name": n.name, "type": n.type}
                        if n.type == 'BSDF_PRINCIPLED':
                            nd["base_color"] = [round(x, 4) for x in n.inputs['Base Color'].default_value]
                            nd["metallic"] = round(n.inputs['Metallic'].default_value, 4)
                            nd["roughness"] = round(n.inputs['Roughness'].default_value, 4)
                            if 'Coat Weight' in n.inputs:
                                nd["coat"] = round(n.inputs['Coat Weight'].default_value, 4)
                            if 'Emission Strength' in n.inputs:
                                nd["emission_strength"] = round(n.inputs['Emission Strength'].default_value, 4)
                                nd["emission_color"] = [round(x, 4) for x in n.inputs['Emission Color'].default_value]
                        elif n.type == 'EMISSION':
                            nd["strength"] = round(n.inputs['Strength'].default_value, 4)
                            nd["color"] = [round(x, 4) for x in n.inputs['Color'].default_value]
                        elif n.type == 'TEX_IMAGE':
                            nd["image"] = n.image.name if n.image else None
                        md["nodes"].append(nd)
                mats_detail.append(md)
            # Bounding box in local/parent space
            verts = o.data.vertices
            car_meshes.append({
                "name": o.name,
                "verts": len(verts),
                "polys": len(o.data.polygons),
                "parent": o.parent.name if o.parent else None,
                "parent_bone": o.parent_bone,
                "modifiers": [f"{mod.name}({mod.type}:{getattr(mod, 'object', None) and mod.object.name})" for mod in o.modifiers],
                "materials": mats_detail,
            })

# 2c. Camera Line-of-Sight, Frustum & Ground Check across ALL 26 shots (step 2 + boundaries)
markers = sorted(scene.timeline_markers, key=lambda m: m.frame)
shots_windows = []
for i, mk in enumerate(markers):
    f0 = mk.frame
    f1 = (markers[i + 1].frame - 1) if (i + 1 < len(markers)) else scene.frame_end
    shots_windows.append((mk.name, f0, f1, mk.camera))

car_obj_names = set(m["name"] for m in car_meshes)
shot_audit = []

for s_name, f0, f1, cam in shots_windows:
    is_onboard = "Onboard" in s_name
    occlusions = []
    low_cam_frames = []
    out_of_frustum_frames = []
    near_clip_hits = []
    min_cam_z = 9999.0
    max_focus_err = 0.0

    # Sample frames: f0, f1, and every 2 frames (step 2 covers step 4 and finer!)
    sample_fs = sorted(set(list(range(f0, f1 + 1, 2)) + [f0, f1]))
    for f in sample_fs:
        scene.frame_set(f)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        cam_eval = cam.evaluated_get(depsgraph)
        rig_eval = rig.evaluated_get(depsgraph)

        cam_mw = cam_eval.matrix_world
        cam_pos = cam_mw.translation.copy()
        min_cam_z = min(min_cam_z, cam_pos.z)
        if cam_pos.z < 0.15:
            low_cam_frames.append((f, round(cam_pos.z, 4)))

        # Bone_Root world position
        pb_root = rig_eval.pose.bones["Bone_Root"]
        car_root_w = (rig_eval.matrix_world @ pb_root.matrix).translation.copy()
        target_w = car_root_w + Vector((0.0, 0.0, 0.5))

        # Check camera near-clip self-intersection along view ray (-Z)
        cam_fwd = (cam_mw.to_3x3() @ Vector((0.0, 0.0, -1.0))).normalized()
        hit_near, loc_near, _, _, obj_near, _ = scene.ray_cast(
            depsgraph, cam_pos + cam_fwd * 0.02, cam_fwd, distance=cam_eval.data.clip_start + 0.15
        )
        if hit_near and obj_near:
            near_clip_hits.append({"frame": f, "obj": obj_near.name, "dist": round((loc_near - cam_pos).length, 3)})

        if not is_onboard:
            vec_to_car = target_w - cam_pos
            dist_to_car = vec_to_car.length
            if dist_to_car > 0.4:
                dir_to_car = vec_to_car.normalized()
                # Step along ray if we hit transparent/car objects? Scene ray_cast stops at first mesh.
                # Raycast from cam_pos to target_w:
                cur_orig = cam_pos + dir_to_car * 0.05
                rem_dist = dist_to_car - 0.15
                for _hop in range(4):
                    if rem_dist <= 0.05:
                        break
                    hit, loc, norm, idx, hit_obj, _ = scene.ray_cast(depsgraph, cur_orig, dir_to_car, distance=rem_dist)
                    if not hit or hit_obj is None:
                        break
                    if hit_obj.name in car_obj_names:
                        # Hit the car itself before reaching Bone_Root+0.5z -> line of sight to car is CLEAR!
                        break
                    else:
                        # Hit an environment / non-car object!
                        occlusions.append({
                            "frame": f,
                            "blocker": hit_obj.name,
                            "blocker_dist": round((loc - cam_pos).length, 2),
                            "car_dist": round(dist_to_car, 2),
                            "cam_pos": [round(x, 2) for x in cam_pos],
                        })
                        break

            # Frustum check for car target_w
            ndc = world_to_camera_view(scene, cam_eval, target_w)
            if ndc.z < cam_eval.data.clip_start or not (-0.05 <= ndc.x <= 1.05 and -0.05 <= ndc.y <= 1.05):
                out_of_frustum_frames.append({
                    "frame": f,
                    "ndc": [round(ndc.x, 3), round(ndc.y, 3), round(ndc.z, 2)],
                })

            # DOF focus error
            if cam_eval.data.dof.use_dof:
                if cam_eval.data.dof.focus_object is None:
                    f_err = abs(cam_eval.data.dof.focus_distance - dist_to_car)
                    max_focus_err = max(max_focus_err, f_err)
        else:
            # Onboard: check forward track visibility 15m ahead along camera forward
            hit, loc, _, _, hit_obj, _ = scene.ray_cast(depsgraph, cam_pos + cam_fwd * 1.5, cam_fwd, distance=15.0)
            if hit and hit_obj and hit_obj.name not in car_obj_names and hit_obj.name not in ("V5_Track", "V5_RacingLine", "V5_Line_L", "V5_Line_R"):
                occlusions.append({
                    "frame": f,
                    "blocker": hit_obj.name,
                    "blocker_dist": round((loc - cam_pos).length, 2),
                    "car_dist": 0.0,
                    "cam_pos": [round(x, 2) for x in cam_pos],
                })

    shot_audit.append({
        "shot": s_name,
        "f0": f0,
        "f1": f1,
        "lens": round(cam.data.lens, 1),
        "use_dof": cam.data.dof.use_dof,
        "fstop": round(cam.data.dof.aperture_fstop, 2),
        "focus_object": cam.data.dof.focus_object.name if cam.data.dof.focus_object else None,
        "max_focus_err_m": round(max_focus_err, 2),
        "min_cam_z": round(min_cam_z, 3),
        "low_cam_frames": low_cam_frames,
        "occlusion_count": len(occlusions),
        "occlusions": occlusions,
        "out_of_frustum_count": len(out_of_frustum_frames),
        "out_of_frustum": out_of_frustum_frames[:10],
        "near_clip_hits": near_clip_hits[:10],
    })

report["anim_blend"] = {
    "total_objects": len(bpy.data.objects),
    "root_scene_collection_objects": anim_root_objs,
    "collections": anim_colls,
    "orphan_meshes": orphan_meshes,
    "orphan_materials": orphan_mats,
    "images": all_images,
    "missing_images": missing_images,
    "broken_mat_slots": broken_mat_slots,
    "overbright_mats": overbright_mats,
    "road_spec_violations": road_spec_violations,
    "car_light_receivers": car_recv_objs,
    "rig": rig_info,
    "other_drivers": other_drivers,
    "non_v5_objects": non_v5_objects,
    "car_meshes": car_meshes,
    "shot_audit": shot_audit,
}

# ==============================================================================
# PART 3: Inspect v5_stage_anim_clay.blend
# ==============================================================================
bpy.ops.wm.open_mainfile(filepath=CLAY_BLEND)
sc_clay = bpy.context.scene
sc_clay.frame_set(100)

clay_car_objs = []
clay_env_objs = []
clay_other_objs = []
for o in sorted(bpy.data.objects, key=lambda x: x.name):
    if o.type != 'MESH':
        continue
    mats = [sl.material.name if sl.material else None for sl in o.material_slots]
    if "CLAY_Car" in mats:
        clay_car_objs.append(o.name)
    elif "CLAY_Env" in mats:
        clay_env_objs.append(o.name)
    else:
        clay_other_objs.append({"name": o.name, "mats": mats})

# Check non-V5 objects that got CLAY_Env or V5 objects that got CLAY_Car
clay_misclassified_as_env = [n for n in clay_env_objs if not n.startswith("V5_")]
clay_misclassified_as_car = [n for n in clay_car_objs if n.startswith("V5_")]

report["clay_blend"] = {
    "clay_car_count": len(clay_car_objs),
    "clay_env_count": len(clay_env_objs),
    "clay_car_objs": clay_car_objs,
    "clay_non_v5_marked_as_env": clay_misclassified_as_env,
    "clay_v5_marked_as_car": clay_misclassified_as_car,
    "clay_other_objs": clay_other_objs,
    "exposure_at_f100": round(sc_clay.view_settings.exposure, 4),
    "view_transform": sc_clay.view_settings.view_transform,
    "use_motion_blur": sc_clay.render.use_motion_blur,
    "scene_has_anim_data": bool(sc_clay.animation_data and sc_clay.animation_data.action),
}

os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print("AUDIT_ROUND1_JSON_WRITTEN:", OUT_JSON)
